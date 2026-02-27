#!/usr/bin/env python3
"""PostToolUse hook — validate JSON files after edits in .github/ or .copilot/.

Why: Editing JSON config files (settings.json, board.json, gate-profiles.json)
     can introduce schema violations that silently break the workflow. Currently
     validation is manual and often forgotten.
How: After any file edit tool completes, check if the modified file is a JSON
     file in .github/ or .copilot/. If so, run structural validation and report
     errors as additionalContext so the agent can self-correct immediately.
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import (
    find_repo_root,
    load_settings,
    read_hook_input,
    write_hook_output,
)

# Why: Only validate JSON files in framework-managed directories.
WATCHED_DIRS: tuple[str, ...] = (".github", ".copilot")

# Why: These tool names represent file-modifying operations.
FILE_EDIT_TOOLS: set[str] = {
    "create_file", "editFiles", "replace_string_in_file",
    "multi_replace_string_in_file",
}


def extract_file_paths(tool_name: str, tool_input: dict) -> list[str]:
    """Extract file paths from tool input.

    Why: Different tools use different parameter names for file paths.
    How: Check known parameter patterns for each tool type.
    """
    paths: list[str] = []

    if tool_name == "create_file":
        path = tool_input.get("filePath", "")
        if path:
            paths.append(path)
    elif tool_name == "editFiles":
        files = tool_input.get("files", [])
        for f in files:
            path = f.get("path", "") if isinstance(f, dict) else ""
            if path:
                paths.append(path)
    elif tool_name in ("replace_string_in_file", "multi_replace_string_in_file"):
        path = tool_input.get("filePath", "")
        if path:
            paths.append(path)
        # multi_replace has replacements array
        replacements = tool_input.get("replacements", [])
        for r in replacements:
            path = r.get("filePath", "") if isinstance(r, dict) else ""
            if path:
                paths.append(path)

    return paths


def is_watched_json(file_path: str, repo_root: Path) -> bool:
    """Check if the file is a JSON file in a watched directory.

    Why: Only run validation on framework config files, not user code.
    How: Resolve the path relative to repo root and check prefix.
    """
    try:
        resolved = Path(file_path).resolve()
        relative = resolved.relative_to(repo_root.resolve())
        relative_str = str(relative).replace("\\", "/")
    except (ValueError, OSError):
        return False

    if not relative_str.endswith(".json"):
        return False

    return any(relative_str.startswith(d + "/") or relative_str.startswith(d + "\\")
               for d in WATCHED_DIRS)


def validate_json_file(file_path: Path) -> list[str]:
    """Validate a JSON file for structural correctness.

    Why: Catch malformed JSON and missing required fields immediately.
    How: Parse the file. If it's a known schema type, do structural checks.
    """
    errors: list[str] = []

    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except FileNotFoundError:
        return [f"File not found: {file_path.name}"]
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON in {file_path.name}: {exc}"]

    file_name = file_path.name

    if file_name == "settings.json":
        errors.extend(_validate_settings(data))
    elif file_name == "gate-profiles.json":
        errors.extend(_validate_gate_profiles(data))
    elif file_name == "board.json":
        errors.extend(_validate_board(data))

    return errors


def _validate_settings(data: dict[str, Any]) -> list[str]:
    """Check settings.json required fields.

    Why: Missing github or project sections break all workflows.
    How: Verify required top-level keys exist.
    """
    errors: list[str] = []
    for key in ("github", "project"):
        if key not in data:
            errors.append(f"settings.json: missing required section '{key}'")

    github = data.get("github", {})
    for key in ("owner", "repo", "mergeMethod"):
        if key not in github:
            errors.append(f"settings.json: github.{key} is missing")

    return errors


def _validate_gate_profiles(data: dict[str, Any]) -> list[str]:
    """Check gate-profiles.json structure.

    Why: Gate profiles with missing 'required' fields cause runtime errors.
    How: Verify each gate in each profile has the required field.
    """
    errors: list[str] = []
    profiles = data.get("profiles", {})

    if not profiles:
        errors.append("gate-profiles.json: no profiles defined")
        return errors

    for profile_name, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"gate-profiles.json: profile '{profile_name}' is not an object")
            continue
        for gate_name, gate_config in profile.items():
            if isinstance(gate_config, dict) and "required" not in gate_config:
                errors.append(
                    f"gate-profiles.json: {profile_name}.{gate_name} missing 'required'"
                )

    return errors


def _validate_board(data: dict[str, Any]) -> list[str]:
    """Check board.json runtime data.

    Why: Board is the shared context between agents; structural errors break
         the entire workflow.
    How: Verify required fields and valid flow_state values.
    """
    errors: list[str] = []
    required = ["feature_id", "flow_state", "maturity", "cycle", "gates"]
    for key in required:
        if key not in data:
            errors.append(f"board.json: missing required field '{key}'")

    valid_states = {
        "initialized", "analyzing", "designing", "planned",
        "implementing", "testing", "reviewing", "approved",
        "documenting", "submitting", "completed",
    }
    flow_state = data.get("flow_state", "")
    if flow_state and flow_state not in valid_states:
        errors.append(f"board.json: invalid flow_state '{flow_state}'")

    return errors


def main() -> None:
    """Validate JSON files after edits in watched directories.

    Why: Deterministic schema validation replaces manual verification.
    How: Check if edited files are in .github/ or .copilot/, validate them,
         and inject errors as additionalContext for self-correction.
    """
    hook_input = read_hook_input()
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    cwd = hook_input.get("cwd")

    # Only run for file edit tools
    if tool_name not in FILE_EDIT_TOOLS:
        write_hook_output({})
        return

    repo_root = find_repo_root(cwd)
    file_paths = extract_file_paths(tool_name, tool_input)

    all_errors: list[str] = []
    validated_count = 0

    for file_path_str in file_paths:
        if not is_watched_json(file_path_str, repo_root):
            continue

        file_path = Path(file_path_str).resolve()
        errors = validate_json_file(file_path)
        validated_count += 1
        all_errors.extend(errors)

    if validated_count == 0:
        write_hook_output({})
        return

    if all_errors:
        error_text = "\n".join(f"- {e}" for e in all_errors)
        write_hook_output({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"[PostToolUse Hook — JSON Validation FAILED]\n"
                    f"{error_text}\n"
                    f"Fix these errors before proceeding."
                ),
            }
        })
    else:
        write_hook_output({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"[PostToolUse Hook — JSON Validation PASSED] "
                    f"{validated_count} file(s) validated."
                ),
            }
        })


if __name__ == "__main__":
    main()
