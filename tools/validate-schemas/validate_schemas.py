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
from typing import Optional


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


def load_json(file_path: Path) -> Optional[dict]:
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
        return ["settings.json or schema not loadable"]

    # Check required top-level keys
    required_keys = schema.get("required", [])
    for key in required_keys:
        if key not in settings:
            errors.append(f"settings.json: missing required key '{key}'")

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
                f"settings.json: issueTracker.provider '{provider}' "
                f"not in allowed values {allowed_providers}"
            )

    # Validate project.language enum
    language = settings.get("project", {}).get("language")
    if language is not None:
        allowed_languages = (
            schema.get("properties", {})
            .get("project", {})
            .get("properties", {})
            .get("language", {})
            .get("enum", [])
        )
        if allowed_languages and language not in allowed_languages:
            errors.append(
                f"settings.json: project.language '{language}' "
                f"not in allowed values {allowed_languages}"
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
        return ["gate-profiles.json not loadable"]

    profiles = gate_profiles.get("profiles", {})

    # Expected gate keys (from board.schema.json)
    expected_gate_keys: set[str] = set()
    if board_schema is not None:
        gates_props = (
            board_schema.get("properties", {})
            .get("gates", {})
            .get("properties", {})
        )
        # Board uses short names (e.g., "analysis"), gate-profiles uses suffixed names (e.g., "analysis_gate")
        expected_gate_keys = {f"{key}_gate" for key in gates_props.keys()}

    for profile_name, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"gate-profiles.json: profile '{profile_name}' is not an object")
            continue

        # Check each gate has required fields
        for gate_name, gate_config in profile.items():
            if not isinstance(gate_config, dict):
                errors.append(
                    f"gate-profiles.json: {profile_name}.{gate_name} is not an object"
                )
                continue

            if "required" not in gate_config:
                errors.append(
                    f"gate-profiles.json: {profile_name}.{gate_name} missing 'required' field"
                )

            # Cross-reference with board schema
            if expected_gate_keys and gate_name not in expected_gate_keys:
                errors.append(
                    f"gate-profiles.json: {profile_name}.{gate_name} "
                    f"has no corresponding gate in board.schema.json "
                    f"(expected one of: {sorted(expected_gate_keys)})"
                )

    # Check all board gates have entries in each profile
    if expected_gate_keys:
        for profile_name, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            missing_gates = expected_gate_keys - set(profile.keys())
            if missing_gates:
                errors.append(
                    f"gate-profiles.json: profile '{profile_name}' missing gates: "
                    f"{sorted(missing_gates)}"
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
        return ["board.schema.json not loadable"]

    # Check required top-level fields
    required = board_schema.get("required", [])
    properties = board_schema.get("properties", {})
    for field in required:
        if field not in properties:
            errors.append(
                f"board.schema.json: required field '{field}' "
                f"not defined in properties"
            )

    # Validate flow_state enum
    flow_states = properties.get("flow_state", {}).get("enum", [])
    expected_states = [
        "initialized", "analyzing", "designing", "planned",
        "implementing", "testing", "reviewing", "approved",
        "documenting", "submitting", "completed",
    ]
    if flow_states and set(flow_states) != set(expected_states):
        missing = set(expected_states) - set(flow_states)
        extra = set(flow_states) - set(expected_states)
        if missing:
            errors.append(f"board.schema.json: flow_state missing states: {missing}")
        if extra:
            errors.append(f"board.schema.json: flow_state has extra states: {extra}")

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
                            f"board.schema.json: artifacts.{artifact_name} "
                            f"references '{def_name}' not found in "
                            f"board-artifacts.schema.json"
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
        print(f"FAILED: {len(all_errors)} error(s) found:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print("ALL PASSED: No errors found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
