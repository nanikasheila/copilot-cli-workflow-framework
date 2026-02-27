#!/usr/bin/env python3
"""Stop hook — check for uncommitted changes and Board consistency at session end.

Why: Sessions can end with uncommitted changes in worktrees, leaving work in
     a partial state. Board consistency issues (stale flow_state, missing
     artifacts) can also go undetected. This hook catches both.
How: When the agent session ends, check for uncommitted changes and Board
     integrity. If issues are found and this is not already a continuation
     from a previous stop hook, block the stop and instruct the agent to
     address the issues first.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import (
    find_active_boards,
    find_repo_root,
    get_current_branch,
    get_uncommitted_summary,
    get_worktree_branches,
    has_uncommitted_changes,
    is_main_branch,
    read_hook_input,
    write_hook_output,
)


def check_uncommitted(repo_root: Path, branch: str | None) -> list[str]:
    """Check for uncommitted changes in the repo root worktree.

    Why: Uncommitted changes are lost if the session ends without saving.
    How: Run git status and report any modified/untracked files.
    """
    issues: list[str] = []

    if is_main_branch(branch):
        return issues

    if has_uncommitted_changes(repo_root):
        summary = get_uncommitted_summary(repo_root)
        file_count = len(summary.strip().splitlines()) if summary else 0
        issues.append(
            f"Uncommitted changes detected ({file_count} file(s)) on branch '{branch}'.\n"
            f"```\n{summary}\n```\n"
            f"Consider committing or stashing these changes."
        )

    return issues


def check_worktree_uncommitted(repo_root: Path) -> list[str]:
    """Check for uncommitted changes in all worktrees.

    Why: Active worktrees may have unsaved work that would be lost on
         session end. The repo-root check only covers the main worktree.
    How: Iterate .worktrees/, run git status in each, report changes.
    """
    issues: list[str] = []
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.is_dir():
        return issues

    wt_branches = get_worktree_branches(repo_root)
    for wt_name, wt_branch in wt_branches.items():
        wt_path = worktrees_dir / wt_name
        if has_uncommitted_changes(wt_path):
            summary = get_uncommitted_summary(wt_path)
            file_count = len(summary.strip().splitlines()) if summary else 0
            issues.append(
                f"Worktree '{wt_name}' (branch '{wt_branch}') has "
                f"uncommitted changes ({file_count} file(s)).\n"
                f"```\n{summary}\n```\n"
                f"Consider committing or stashing these changes."
            )

    return issues


def check_board_consistency(boards: list[dict]) -> list[str]:
    """Check active Boards for consistency issues.

    Why: A Board in a mid-workflow state at session end may indicate
         incomplete work that should be addressed or noted.
    How: Check for Boards with in-progress states and missing expected artifacts.
    """
    issues: list[str] = []

    # Map of flow_state to the artifacts that should exist at that point
    expected_artifacts: dict[str, list[str]] = {
        "analyzing": [],
        "designing": ["impact_analysis"],
        "planned": ["impact_analysis"],
        "implementing": ["execution_plan"],
        "testing": ["implementation"],
        "reviewing": ["implementation", "test_results"],
        "approved": ["implementation", "review_findings"],
        "documenting": ["implementation", "review_findings"],
        "submitting": ["implementation"],
    }

    for board in boards:
        feature_id = board.get("feature_id", "?")
        flow_state = board.get("flow_state", "initialized")
        board_path = board.get("_board_path", "?")

        # Check for expected artifacts
        expected = expected_artifacts.get(flow_state, [])
        artifacts = board.get("artifacts", {})
        missing: list[str] = []

        for artifact_name in expected:
            if artifacts.get(artifact_name) is None:
                missing.append(artifact_name)

        if missing:
            issues.append(
                f"Board '{feature_id}' ({board_path}) is in state '{flow_state}' "
                f"but missing expected artifacts: {', '.join(missing)}."
            )

        # Warn about mid-workflow state
        if flow_state not in ("initialized", "completed"):
            issues.append(
                f"Board '{feature_id}' is in mid-workflow state '{flow_state}'. "
                f"Consider resuming or documenting the current progress."
            )

    return issues


def main() -> None:
    """Check for issues before session ends.

    Why: Prevent data loss and ensure workflow consistency.
    How: If stop_hook_active is True, this is a re-check after a previous
         block — allow the stop to proceed to prevent infinite loops.
         Otherwise, check for uncommitted changes and Board issues.
    """
    hook_input = read_hook_input()
    stop_hook_active = hook_input.get("stop_hook_active", False)
    cwd = hook_input.get("cwd")

    # Prevent infinite continuation loops
    if stop_hook_active:
        write_hook_output({})
        return

    repo_root = find_repo_root(cwd)
    branch = get_current_branch(repo_root)
    boards = find_active_boards(repo_root)

    all_issues: list[str] = []
    all_issues.extend(check_uncommitted(repo_root, branch))
    all_issues.extend(check_worktree_uncommitted(repo_root))
    all_issues.extend(check_board_consistency(boards))

    if all_issues:
        reason_text = "\n\n".join(f"- {issue}" for issue in all_issues)
        write_hook_output({
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "decision": "block",
                "reason": (
                    f"[Stop Hook — Issues Detected]\n{reason_text}\n\n"
                    f"Address these issues or acknowledge them before ending the session."
                ),
            }
        })
    else:
        write_hook_output({})


if __name__ == "__main__":
    main()
