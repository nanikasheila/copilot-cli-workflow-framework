#!/usr/bin/env python3
"""SubagentStart hook — inject Board context when a subagent is spawned.

Why: Currently the orchestrator must manually include Board file paths in every
     runSubagent prompt, and each subagent then calls read_file to load the
     Board. This consumes 1-3 tool calls per agent invocation (×5-7 agents per
     workflow = ~15 unnecessary calls).
How: When a subagent starts, automatically discover the active Board, extract
     the fields relevant to that agent type, and inject as additionalContext.
     The subagent receives its working context without any read_file calls.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_utils import (
    find_active_boards,
    find_repo_root,
    load_settings,
    read_hook_input,
    write_hook_output,
)

# Why: Each agent type needs different Board fields. Defining the mapping here
#      keeps the logic declarative and easy to extend.
# How: Map agent_type to the Board fields that agent reads as input.
AGENT_BOARD_FIELDS: dict[str, list[str]] = {
    "manager": [
        "feature_id", "maturity", "cycle", "flow_state", "gate_profile",
        "artifacts.impact_analysis", "artifacts.execution_plan",
        "artifacts.review_findings",
    ],
    "architect": [
        "feature_id", "maturity", "flow_state",
        "artifacts.impact_analysis", "artifacts.architecture_decision",
    ],
    "developer": [
        "feature_id", "maturity", "flow_state",
        "artifacts.execution_plan", "artifacts.architecture_decision",
        "artifacts.review_findings", "artifacts.implementation",
    ],
    "reviewer": [
        "feature_id", "maturity", "flow_state",
        "artifacts.execution_plan", "artifacts.implementation",
        "artifacts.test_results", "artifacts.review_findings",
    ],
    "writer": [
        "feature_id", "maturity", "flow_state",
        "artifacts.execution_plan", "artifacts.implementation",
        "artifacts.review_findings",
    ],
}


def extract_nested_field(data: dict, field_path: str) -> object:
    """Extract a nested field from a dict using dot notation.

    Why: Board artifacts use nested paths like "artifacts.impact_analysis".
    How: Split the path and traverse the dict. Return None if any key is missing.
    """
    current: object = data
    for key in field_path.split("."):
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def build_agent_context(
    agent_type: str,
    board: dict,
    board_path: str,
    settings: dict | None,
) -> str:
    """Build context string tailored to the agent type.

    Why: Each agent needs a different subset of Board data. Injecting only
         relevant fields reduces token consumption vs. injecting the full Board.
    How: Look up the agent's field list, extract values, format concisely.
    """
    parts: list[str] = [
        f"[SubagentStart Hook — Board Context for {agent_type}]",
        f"Board path: {board_path}",
    ]

    # Always include core state
    parts.append(
        f"Feature: {board.get('feature_id', '?')} | "
        f"State: {board.get('flow_state', '?')} | "
        f"Maturity: {board.get('maturity', '?')} | "
        f"Cycle: {board.get('cycle', '?')} | "
        f"Profile: {board.get('gate_profile', '?')}"
    )

    # Include settings summary for context
    if settings:
        tracker = settings.get("issueTracker", {})
        parts.append(f"Issue tracker: {tracker.get('provider', 'none')}")

        test_config = settings.get("project", {}).get("test", {})
        if test_config.get("command") and agent_type == "developer":
            parts.append(f"Test command: {test_config['command']}")

    # Extract agent-specific fields
    fields = AGENT_BOARD_FIELDS.get(agent_type, [])
    for field_path in fields:
        if field_path in ("feature_id", "maturity", "flow_state", "cycle", "gate_profile"):
            continue  # Already included in core state
        value = extract_nested_field(board, field_path)
        if value is not None:
            # Truncate large artifacts to a summary line
            if isinstance(value, dict):
                summary = value.get("summary", value.get("description", str(value)[:200]))
                parts.append(f"{field_path}: {summary}")
            elif isinstance(value, list):
                parts.append(f"{field_path}: [{len(value)} items]")
            else:
                parts.append(f"{field_path}: {value}")

    # Gate statuses (compact)
    gates = board.get("gates", {})
    active_gates = {
        name: data.get("status", "?")
        for name, data in gates.items()
        if isinstance(data, dict) and data.get("status") != "not_reached"
    }
    if active_gates:
        gate_str = ", ".join(f"{k}={v}" for k, v in active_gates.items())
        parts.append(f"Gates: {gate_str}")

    return "\n".join(parts)


def main() -> None:
    """Detect agent type, find active Board, inject relevant context.

    Why: Automate Board-to-subagent context flow that was previously manual.
    How: Read hook input for agent_type, match to active Board, build and
         inject tailored context via additionalContext.
    """
    hook_input = read_hook_input()
    cwd = hook_input.get("cwd")
    agent_type = hook_input.get("agent_type", "").lower()
    repo_root = find_repo_root(cwd)

    boards = find_active_boards(repo_root)
    settings = load_settings(repo_root)

    if not boards:
        # No active board — still inject basic settings info
        context = f"[SubagentStart Hook — No active Board found for {agent_type}]"
        if settings:
            project = settings.get("project", {})
            context += f"\nProject: {project.get('name', '?')} ({project.get('language', '?')})"
        write_hook_output({
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": context,
            }
        })
        return

    # Use the first active board (most common case: single Feature in progress)
    board = boards[0]
    board_path = board.pop("_board_path", "unknown")

    context = build_agent_context(agent_type, board, board_path, settings)

    write_hook_output({
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": context,
        }
    })


if __name__ == "__main__":
    main()
