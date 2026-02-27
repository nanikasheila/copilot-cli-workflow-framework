#!/usr/bin/env python3
"""SessionStart hook — inject project context at session initialization.

Why: Every session begins with the orchestrator manually reading settings.json,
     gate-profiles.json, and scanning for active Boards. This costs 5-7 tool
     calls and ~3,000-5,000 tokens each time.
How: Automatically collect project settings, active Board state, current Git
     branch, and issue tracker config, then inject as additionalContext. The
     agent receives this context without any tool calls.
"""

import sys
from pathlib import Path

# Why: Allow importing hook_utils from the same directory regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import (
    find_active_boards,
    find_repo_root,
    get_current_branch,
    get_worktree_branches,
    load_gate_profiles,
    load_settings,
    read_hook_input,
    write_hook_output,
)


def build_board_summary(boards: list[dict]) -> str:
    """Build a concise summary of active Boards for context injection.

    Why: Full Board JSON is large; a summary provides the essential state
         without consuming excessive tokens.
    How: Extract feature_id, flow_state, maturity, cycle, gate_profile,
         and board path for each active Board.
    """
    if not boards:
        return "No active boards."

    lines: list[str] = []
    for board in boards:
        feature_id = board.get("feature_id", "unknown")
        flow_state = board.get("flow_state", "unknown")
        maturity = board.get("maturity", "unknown")
        cycle = board.get("cycle", 1)
        gate_profile = board.get("gate_profile", "unknown")
        board_path = board.get("_board_path", "unknown")

        # Summarize gate statuses
        gates = board.get("gates", {})
        gate_summary_parts: list[str] = []
        for gate_name, gate_data in gates.items():
            status = gate_data.get("status", "unknown") if isinstance(gate_data, dict) else "unknown"
            if status != "not_reached":
                gate_summary_parts.append(f"{gate_name}={status}")

        gate_summary = ", ".join(gate_summary_parts) if gate_summary_parts else "all not_reached"

        lines.append(
            f"- Feature: {feature_id} | State: {flow_state} | "
            f"Maturity: {maturity} | Cycle: {cycle} | "
            f"Profile: {gate_profile} | Gates: [{gate_summary}] | "
            f"Path: {board_path}"
        )

    return "\n".join(lines)


def build_settings_summary(settings: dict) -> str:
    """Build a concise summary of project settings.

    Why: Inject the most frequently referenced settings fields so the agent
         doesn't need to read_file settings.json.
    How: Extract github, issueTracker, branch, project, and agents sections.
    """
    parts: list[str] = []

    github = settings.get("github", {})
    parts.append(f"Repo: {github.get('owner', '?')}/{github.get('repo', '?')}")
    parts.append(f"Merge: {github.get('mergeMethod', '?')}")

    tracker = settings.get("issueTracker", {})
    provider = tracker.get("provider", "none")
    parts.append(f"Issue tracker: {provider}")
    if provider != "none":
        if tracker.get("prefix"):
            parts.append(f"Prefix: {tracker['prefix']}")
        if tracker.get("mcpServer"):
            parts.append(f"MCP server: {tracker['mcpServer']}")

    branch = settings.get("branch", {})
    if branch.get("user"):
        parts.append(f"Branch user: {branch['user']}")
    if branch.get("format"):
        parts.append(f"Branch format: {branch['format']}")

    project = settings.get("project", {})
    parts.append(f"Project: {project.get('name', '?')} ({project.get('language', '?')})")

    test_config = project.get("test", {})
    if test_config.get("command"):
        parts.append(f"Test command: {test_config['command']}")

    return " | ".join(parts)


def build_gate_summary(gate_profiles: dict) -> str:
    """Build a concise summary of available gate profiles.

    Why: Knowing which profiles exist and their key gate requirements helps
         the agent plan workflow without reading gate-profiles.json.
    How: List profile names with their required gate count.
    """
    profiles = gate_profiles.get("profiles", {})
    parts: list[str] = []
    for name, profile in profiles.items():
        required_count = sum(
            1 for g in profile.values()
            if isinstance(g, dict) and g.get("required") is True
        )
        total = len(profile)
        parts.append(f"{name}({required_count}/{total} required)")
    return "Gate profiles: " + ", ".join(parts)


def main() -> None:
    """Collect project state and inject as session context.

    Why: Eliminate the need for initial read_file calls at session start.
    How: Read settings, boards, git state; format as additionalContext.
    """
    hook_input = read_hook_input()
    cwd = hook_input.get("cwd")
    repo_root = find_repo_root(cwd)

    context_parts: list[str] = ["[SessionStart Hook — Project Context]"]

    # Settings
    settings = load_settings(repo_root)
    if settings:
        context_parts.append(f"Settings: {build_settings_summary(settings)}")

    # Gate profiles
    gate_profiles = load_gate_profiles(repo_root)
    if gate_profiles:
        context_parts.append(build_gate_summary(gate_profiles))

    # Git branch
    branch = get_current_branch(repo_root)
    if branch:
        context_parts.append(f"Current branch: {branch}")

    # Worktree branches
    wt_branches = get_worktree_branches(repo_root)
    if wt_branches:
        wt_lines = [f"  {name}: {br}" for name, br in wt_branches.items()]
        context_parts.append(f"Worktrees:\n" + "\n".join(wt_lines))

    # Active boards
    boards = find_active_boards(repo_root)
    context_parts.append(f"Active boards:\n{build_board_summary(boards)}")

    write_hook_output({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(context_parts)
        }
    })


if __name__ == "__main__":
    main()
