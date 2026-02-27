#!/usr/bin/env python3
"""PreCompact hook — preserve critical Board state before context compaction.

Why: Long agent sessions trigger automatic context compaction, which can
     discard Board state (flow_state, gates, maturity, active Feature info).
     Losing this forces expensive re-reads (5-10 tool calls) to reconstruct.
How: Before compaction, emit a systemMessage containing the current Board
     summary, settings essentials, and workflow position. This information
     survives compaction as part of the hook output and is re-injected into
     the compressed context.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import (
    find_active_boards,
    find_repo_root,
    get_current_branch,
    get_worktree_branches,
    load_settings,
    read_hook_input,
    write_hook_output,
)


def build_preservation_context(
    repo_root: Path,
    settings: dict | None,
    boards: list[dict],
    branch: str | None,
    worktree_branches: dict[str, str] | None = None,
) -> str:
    """Build a compact context string that captures the essential state.

    Why: After compaction, the agent needs to resume work without re-reading
         files. This context provides the minimum viable state.
    How: Include settings summary, Board state, Git branch, and any in-progress
         work indicators.
    """
    lines: list[str] = ["[PreCompact Hook — Preserved Context]"]

    # Settings essentials
    if settings:
        github = settings.get("github", {})
        lines.append(
            f"Repo: {github.get('owner', '?')}/{github.get('repo', '?')} "
            f"(merge: {github.get('mergeMethod', '?')})"
        )

        tracker = settings.get("issueTracker", {})
        lines.append(f"Issue tracker: {tracker.get('provider', 'none')}")

        branch_config = settings.get("branch", {})
        lines.append(
            f"Branch: user={branch_config.get('user', '?')}, "
            f"format={branch_config.get('format', '?')}"
        )

        project = settings.get("project", {})
        lines.append(
            f"Project: {project.get('name', '?')} "
            f"(lang: {project.get('language', '?')})"
        )

        test_config = project.get("test", {})
        if test_config.get("command"):
            lines.append(f"Test: {test_config['command']}")

    # Git state
    if branch:
        lines.append(f"Current branch: {branch}")

    # Worktree branches (critical for knowing active feature work)
    if worktree_branches:
        wt_lines = [f"  {name}: {br}" for name, br in worktree_branches.items()]
        lines.append("Worktrees:\n" + "\n".join(wt_lines))

    # Board state (critical for workflow continuity)
    if boards:
        lines.append(f"Active boards: {len(boards)}")
        for board in boards:
            board_path = board.get("_board_path", "?")
            feature_id = board.get("feature_id", "?")
            flow_state = board.get("flow_state", "?")
            maturity = board.get("maturity", "?")
            cycle = board.get("cycle", "?")
            gate_profile = board.get("gate_profile", "?")

            lines.append(
                f"  Board: {board_path}\n"
                f"  Feature: {feature_id} | State: {flow_state} | "
                f"Maturity: {maturity} | Cycle: {cycle} | "
                f"Profile: {gate_profile}"
            )

            # Gate statuses (only non-trivial)
            gates = board.get("gates", {})
            active_gates: list[str] = []
            for gate_name, gate_data in gates.items():
                if isinstance(gate_data, dict):
                    status = gate_data.get("status", "not_reached")
                    if status != "not_reached":
                        active_gates.append(f"{gate_name}={status}")
            if active_gates:
                lines.append(f"  Gates: {', '.join(active_gates)}")

            # Key artifacts (existence only, not content)
            artifacts = board.get("artifacts", {})
            present = [k for k, v in artifacts.items() if v is not None]
            if present:
                lines.append(f"  Artifacts present: {', '.join(present)}")
    else:
        lines.append("No active boards.")

    return "\n".join(lines)


def main() -> None:
    """Emit preserved context before compaction.

    Why: Ensure the agent retains workflow state after context compaction.
    How: Build a compact summary and output it as systemMessage (visible to
         the agent after compaction).
    """
    hook_input = read_hook_input()
    cwd = hook_input.get("cwd")
    repo_root = find_repo_root(cwd)

    settings = load_settings(repo_root)
    boards = find_active_boards(repo_root)
    branch = get_current_branch(repo_root)
    wt_branches = get_worktree_branches(repo_root)

    context = build_preservation_context(
        repo_root, settings, boards, branch, wt_branches
    )

    write_hook_output({
        "systemMessage": context,
    })


if __name__ == "__main__":
    main()
