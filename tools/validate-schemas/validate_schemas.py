#!/usr/bin/env python3
"""Validate JSON files against their schemas.

Why: Multiple JSON files (settings.json, board.json, gate-profiles.json) reference
     schemas, and inconsistencies between them cause silent failures at runtime.
How: Use jsonschema library if available, fall back to basic structural checks.
     Validate schema references, required fields, enum consistency, and
     cross-file references (e.g., gate key naming conventions).
"""

import json
import sys
from pathlib import Path


def format_error(error: str, file: str, why: str, fix: str) -> str:
    """Format validation error with actionable fix instructions.

    Why: Harness Engineering pattern - error messages should teach agents
         how to fix issues, not just report them. Agents cannot ignore CI errors.
    How: Structured ERROR/WHY/FIX format that agents can parse and act on.
    """
    return f"ERROR: {error}\n  FILE: {file}\n  WHY: {why}\n  FIX: {fix}"


def find_github_dir() -> Path:
    """Find .github directory by walking up from script location.

    Why: Script may be run from different working directories.
    How: Walk up from the script's parent until .github/ is found.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / ".github"
        if candidate.is_dir():
            return candidate
        current = current.parent
    print("ERROR: .github/ directory not found")
    sys.exit(1)


def load_json(file_path: Path) -> dict | None:
    """Load and parse a JSON file, returning None on failure.

    Why: Graceful error handling for missing or malformed files.
    How: Try to read and parse; print error and return None if it fails.
    """
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"  SKIP: {file_path.name} not found")
        return None
    except json.JSONDecodeError as exc:
        print(f"  FAIL: {file_path.name} — invalid JSON: {exc}")
        return None


def validate_settings(github_dir: Path) -> list[str]:
    """Validate settings.json against settings.schema.json.

    Why: settings.json is the central config; inconsistencies break all skills.
    How: Check required fields, enum values, and type constraints.
    """
    errors: list[str] = []
    settings = load_json(github_dir / "settings.json")
    schema = load_json(github_dir / "settings.schema.json")

    if settings is None or schema is None:
        return [
            format_error(
                "settings.json or settings.schema.json could not be loaded",
                ".github/settings.json",
                "Both files are required for schema validation. "
                "Missing or malformed files prevent all downstream checks.",
                "Ensure .github/settings.json and .github/settings.schema.json exist and contain valid JSON.",
            )
        ]

    # Check required top-level keys
    required_keys = schema.get("required", [])
    for key in required_keys:
        if key not in settings:
            errors.append(
                format_error(
                    f"Missing required key '{key}'",
                    ".github/settings.json",
                    "settings.json is the central config; all skills read it at startup. "
                    "Missing required keys cause cascading failures across the framework.",
                    f"Add the '{key}' key to .github/settings.json. "
                    "See .github/settings.schema.json for the required structure.",
                )
            )

    # Validate issueTracker.provider enum
    provider = settings.get("issueTracker", {}).get("provider")
    if provider is not None:
        allowed_providers = (
            schema.get("properties", {})
            .get("issueTracker", {})
            .get("properties", {})
            .get("provider", {})
            .get("enum", [])
        )
        if allowed_providers and provider not in allowed_providers:
            errors.append(
                format_error(
                    f"issueTracker.provider '{provider}' is not a valid value",
                    ".github/settings.json",
                    "The provider must match the enum in settings.schema.json. "
                    "An invalid value causes issue-tracking integrations to fail.",
                    f"Set issueTracker.provider to one of: {allowed_providers}",
                )
            )

    # Validate project.language enum
    language = settings.get("project", {}).get("language")
    if language is not None:
        allowed_languages = (
            schema.get("properties", {}).get("project", {}).get("properties", {}).get("language", {}).get("enum", [])
        )
        if allowed_languages and language not in allowed_languages:
            errors.append(
                format_error(
                    f"project.language '{language}' is not a valid value",
                    ".github/settings.json",
                    "The language must match the enum in settings.schema.json. "
                    "An invalid value disables language-specific skill behavior.",
                    f"Set project.language to one of: {allowed_languages}",
                )
            )

    return errors


def validate_gate_profiles(github_dir: Path) -> list[str]:
    """Validate gate-profiles.json structure and cross-reference with board.schema.json.

    Why: Gate key names in gate-profiles.json must correspond to gates in board.schema.json.
         Mismatches cause Gate evaluation failures that are hard to debug.
    How: Compare gate keys (with _gate suffix) against board schema's gates properties.
    """
    errors: list[str] = []
    gate_profiles = load_json(github_dir / "rules" / "gate-profiles.json")
    board_schema = load_json(github_dir / "board.schema.json")

    if gate_profiles is None:
        return [
            format_error(
                "gate-profiles.json could not be loaded",
                ".github/rules/gate-profiles.json",
                "gate-profiles.json controls which CI gates are mandatory. Without it, gate evaluation always fails.",
                "Ensure .github/rules/gate-profiles.json exists and contains valid JSON.",
            )
        ]

    profiles = gate_profiles.get("profiles", {})

    # Expected gate keys (from board.schema.json)
    expected_gate_keys: set[str] = set()
    if board_schema is not None:
        gates_props = board_schema.get("properties", {}).get("gates", {}).get("properties", {})
        # Board uses short names (e.g., "analysis"), gate-profiles uses suffixed names (e.g., "analysis_gate")
        expected_gate_keys = {f"{key}_gate" for key in gates_props}

    for profile_name, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(
                format_error(
                    f"Profile '{profile_name}' is not a JSON object",
                    ".github/rules/gate-profiles.json",
                    "Each profile must be a JSON object mapping gate names to gate config objects. "
                    "A non-object value prevents all gate configs in the profile from being read.",
                    f"Change the '{profile_name}' value to an object. "
                    'Example: { "analysis_gate": { "required": true } }',
                )
            )
            continue

        # Check each gate has required fields
        for gate_name, gate_config in profile.items():
            if not isinstance(gate_config, dict):
                errors.append(
                    format_error(
                        f"Gate config '{profile_name}.{gate_name}' is not a JSON object",
                        ".github/rules/gate-profiles.json",
                        "Each gate configuration must be a JSON object with at least a 'required' boolean field. "
                        "A non-object value causes a TypeError during gate evaluation.",
                        f"Change '{gate_name}' in profile '{profile_name}' to an object. "
                        'Example: { "required": true }',
                    )
                )
                continue

            if "required" not in gate_config:
                errors.append(
                    format_error(
                        f"Gate '{profile_name}.{gate_name}' is missing the 'required' field",
                        ".github/rules/gate-profiles.json",
                        "The 'required' boolean controls whether this gate must pass before the workflow proceeds. "
                        "Without it, gate evaluation raises a KeyError.",
                        f"Add '\"required\": true' or '\"required\": false' to '{gate_name}' "
                        f"in profile '{profile_name}'.",
                    )
                )

            # Cross-reference with board schema
            if expected_gate_keys and gate_name not in expected_gate_keys:
                errors.append(
                    format_error(
                        f"Gate '{gate_name}' in profile '{profile_name}'"
                        " has no corresponding gate in board.schema.json",
                        ".github/rules/gate-profiles.json",
                        "Gate keys in gate-profiles.json must match gates defined in board.schema.json. "
                        "Unknown gates are silently ignored by the orchestrator.",
                        f"Rename '{gate_name}' to one of: {sorted(expected_gate_keys)}, "
                        "or add the gate definition to board.schema.json.",
                    )
                )

    # Check all board gates have entries in each profile
    if expected_gate_keys:
        for profile_name, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            missing_gates = expected_gate_keys - set(profile.keys())
            if missing_gates:
                errors.append(
                    format_error(
                        f"Profile '{profile_name}' is missing gate entries: {sorted(missing_gates)}",
                        ".github/rules/gate-profiles.json",
                        "Every gate defined in board.schema.json must have a corresponding entry in each profile. "
                        "Missing entries cause a KeyError during gate evaluation.",
                        f"Add the missing gates to the '{profile_name}' profile: {sorted(missing_gates)}",
                    )
                )

    return errors


def validate_board_schema(github_dir: Path) -> list[str]:
    """Validate board.schema.json structural integrity.

    Why: Board schema defines the contract between all agents.
    How: Check required fields, valid enum values, and definition references.
    """
    errors: list[str] = []
    board_schema = load_json(github_dir / "board.schema.json")
    artifacts_schema = load_json(github_dir / "board-artifacts.schema.json")

    if board_schema is None:
        return [
            format_error(
                "board.schema.json could not be loaded",
                ".github/board.schema.json",
                "board.schema.json defines the contract between all agents. "
                "Without it, Board state validation and artifact schema checks cannot run.",
                "Ensure .github/board.schema.json exists and contains valid JSON.",
            )
        ]

    # Check required top-level fields
    required = board_schema.get("required", [])
    properties = board_schema.get("properties", {})
    for field in required:
        if field not in properties:
            errors.append(
                format_error(
                    f"Required field '{field}' is listed in 'required' but not defined in 'properties'",
                    ".github/board.schema.json",
                    "Every field in the 'required' array must have a corresponding definition in 'properties'. "
                    "This mismatch causes JSON Schema validation to always fail.",
                    f"Add a property definition for '{field}' under 'properties' in board.schema.json, "
                    "or remove it from the 'required' array.",
                )
            )

    # Validate flow_state enum
    flow_states = properties.get("flow_state", {}).get("enum", [])
    expected_states = [
        "initialized",
        "eliciting",
        "analyzing",
        "designing",
        "planned",
        "implementing",
        "testing",
        "validating",
        "reviewing",
        "approved",
        "documenting",
        "submitting",
        "completed",
    ]
    if flow_states and set(flow_states) != set(expected_states):
        missing = set(expected_states) - set(flow_states)
        extra = set(flow_states) - set(expected_states)
        if missing:
            errors.append(
                format_error(
                    f"flow_state enum is missing expected states: {missing}",
                    ".github/board.schema.json",
                    "The flow_state enum must contain all workflow states used by orchestration skills. "
                    "Missing states cause Board transition validation to reject valid transitions.",
                    f"Add the missing states to the flow_state enum: {sorted(missing)}",
                )
            )
        if extra:
            errors.append(
                format_error(
                    f"flow_state enum contains unrecognised states: {extra}",
                    ".github/board.schema.json",
                    "Unrecognised states suggest a stale definition or a typo. "
                    "Skills that check against the expected set will reject these states.",
                    f"Remove the unexpected states from the flow_state enum: {sorted(extra)}, "
                    "or update EXPECTED_STATES in validate_schemas.py if the workflow was intentionally extended.",
                )
            )

    # Check artifacts references
    if artifacts_schema is not None:
        artifact_defs = artifacts_schema.get("definitions", {})
        artifacts_props = properties.get("artifacts", {}).get("properties", {})
        for artifact_name, artifact_def in artifacts_props.items():
            # Check if $ref references exist
            refs = artifact_def.get("oneOf", [])
            for ref in refs:
                ref_path = ref.get("$ref", "")
                if "board-artifacts.schema.json" in ref_path:
                    def_name = ref_path.split("/")[-1]
                    if def_name not in artifact_defs:
                        errors.append(
                            format_error(
                                f"artifacts.{artifact_name} references '{def_name}' "
                                "not found in board-artifacts.schema.json",
                                ".github/board.schema.json",
                                "All $ref targets must be defined in board-artifacts.schema.json. "
                                "A dangling reference causes JSON Schema validation to fail at runtime.",
                                f"Add a '{def_name}' definition to board-artifacts.schema.json, "
                                f"or fix the $ref in artifacts.{artifact_name} to an existing definition.",
                            )
                        )

    return errors


def main() -> int:
    """Run all validations and report results.

    Why: Single entry point for CI or manual validation.
    How: Run each validator, collect errors, print summary, return exit code.
    """
    github_dir = find_github_dir()
    print(f"Validating schemas in: {github_dir}\n")

    all_errors: list[str] = []

    print("1. Validating settings.json...")
    errors = validate_settings(github_dir)
    all_errors.extend(errors)
    print(f"   {'PASS' if not errors else 'FAIL'} ({len(errors)} error(s))")

    print("2. Validating gate-profiles.json...")
    errors = validate_gate_profiles(github_dir)
    all_errors.extend(errors)
    print(f"   {'PASS' if not errors else 'FAIL'} ({len(errors)} error(s))")

    print("3. Validating board.schema.json...")
    errors = validate_board_schema(github_dir)
    all_errors.extend(errors)
    print(f"   {'PASS' if not errors else 'FAIL'} ({len(errors)} error(s))")

    print()
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) found:\n")
        for error in all_errors:
            print(error)
            print()
        return 1

    print("ALL PASSED: No errors found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
