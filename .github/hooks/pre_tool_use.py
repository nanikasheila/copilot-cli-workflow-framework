#!/usr/bin/env python3
"""PreToolUse hook — enforce safety policies before tool execution.

Why: Project rules prohibit direct edits to main branch and enforce branch
     naming conventions, but these rules are in markdown (probabilistic).
     This hook makes enforcement deterministic — violations are blocked
     before the tool executes.
How: Inspect tool_name and tool_input. Block dangerous operations:
     1. Terminal commands that modify main branch directly (git checkout main
        && git commit, etc.)
     2. File edits when current branch is main
     3. Branch creation that violates naming conventions
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import (
    find_repo_root,
    get_current_branch,
    is_main_branch,
    load_settings,
    read_hook_input,
    write_hook_output,
)

# Why: These tool names represent file-modifying operations.
# How: Maintained as a set for O(1) lookup.
FILE_EDIT_TOOLS: set[str] = {
    "create_file", "editFiles", "replace_string_in_file",
    "multi_replace_string_in_file", "edit_notebook_file",
}

# Why: These terminal command patterns indicate direct main-branch modification.
# How: Regex patterns matched against terminal command strings.
DANGEROUS_TERMINAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"git\s+push\s+.*\bmain\b", re.IGNORECASE),
    re.compile(r"git\s+commit\b.*(?:--allow-empty)?", re.IGNORECASE),
    re.compile(r"rm\s+-rf\s+/", re.IGNORECASE),
    re.compile(r"Remove-Item\s+-Recurse\s+-Force\s+[/\\]", re.IGNORECASE),
    re.compile(r"DROP\s+TABLE", re.IGNORECASE),
    re.compile(r"DROP\s+DATABASE", re.IGNORECASE),
]


def check_main_branch_protection(
    tool_name: str,
    tool_input: dict,
    branch: str | None,
    repo_root: Path,
) -> dict | None:
    """Block file edits and commits when on the main branch.

    Why: rules/development-workflow.md prohibits direct main branch editing.
    How: If the current branch is main and the tool modifies files, deny it.
    """
    if not is_main_branch(branch):
        return None

    if tool_name in FILE_EDIT_TOOLS:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Direct file edits on '{branch}' branch are prohibited. "
                    "Create a feature branch with start-feature skill first."
                ),
            }
        }

    return None


def check_terminal_safety(
    tool_name: str,
    tool_input: dict,
    branch: str | None,
) -> dict | None:
    """Block dangerous terminal commands.

    Why: Destructive commands (rm -rf /, DROP TABLE, push to main) should be
         caught before execution regardless of agent intent.
    How: Match command string against known dangerous patterns.
    """
    if tool_name not in ("run_in_terminal",):
        return None

    command = tool_input.get("command", "")
    if not command:
        return None

    # Block push to main directly
    if is_main_branch(branch) and re.search(r"git\s+commit", command, re.IGNORECASE):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "Committing directly on main branch is prohibited. "
                    "Use a feature branch and submit-pull-request skill."
                ),
            }
        }

    # Block globally dangerous patterns
    for pattern in DANGEROUS_TERMINAL_PATTERNS:
        if pattern.search(command):
            # git push main is only dangerous if we're on main
            if "git push" in command.lower() and "main" in command.lower():
                if is_main_branch(branch):
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": (
                                "Direct push to main is prohibited. "
                                "Use submit-pull-request skill to create a PR."
                            ),
                        }
                    }
            elif any(kw in command.lower() for kw in ("rm -rf /", "drop table", "drop database")):
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"Destructive command blocked by safety policy: {command[:80]}"
                        ),
                    }
                }

    return None


def check_branch_naming(
    tool_name: str,
    tool_input: dict,
    settings: dict | None,
) -> dict | None:
    """Warn about branch names that violate naming conventions.

    Why: rules/branch-naming.md defines a format template. Non-compliant
         branches cause confusion and break Issue tracker integration.
    How: When a branch is being created via terminal, check if the name
         matches the expected format pattern.
    """
    if tool_name != "run_in_terminal":
        return None

    command = tool_input.get("command", "")

    # Detect branch creation commands
    branch_create_match = re.search(
        r"git\s+(?:branch|checkout\s+-b|switch\s+-c)\s+(\S+)",
        command, re.IGNORECASE
    )
    if not branch_create_match:
        return None

    branch_name = branch_create_match.group(1)

    if not settings:
        return None

    branch_config = settings.get("branch", {})
    user_prefix = branch_config.get("user", "")

    if user_prefix and not branch_name.startswith(f"{user_prefix}/"):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    f"Branch '{branch_name}' does not start with user prefix "
                    f"'{user_prefix}/'. Expected format: "
                    f"{branch_config.get('format', '<user>/<type>-<description>')}. "
                    f"Proceed anyway?"
                ),
            }
        }

    return None


def main() -> None:
    """Evaluate tool invocation against safety policies.

    Why: Deterministic enforcement of branch protection and safety rules.
    How: Run each check in priority order. First denial/ask wins.
    """
    hook_input = read_hook_input()
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    cwd = hook_input.get("cwd")

    repo_root = find_repo_root(cwd)
    branch = get_current_branch(repo_root)
    settings = load_settings(repo_root)

    # Check 1: Main branch protection (highest priority)
    result = check_main_branch_protection(tool_name, tool_input, branch, repo_root)
    if result:
        write_hook_output(result)
        return

    # Check 2: Dangerous terminal commands
    result = check_terminal_safety(tool_name, tool_input, branch)
    if result:
        write_hook_output(result)
        return

    # Check 3: Branch naming conventions (ask, not deny)
    result = check_branch_naming(tool_name, tool_input, settings)
    if result:
        write_hook_output(result)
        return

    # All checks passed — allow
    write_hook_output({})


if __name__ == "__main__":
    main()
