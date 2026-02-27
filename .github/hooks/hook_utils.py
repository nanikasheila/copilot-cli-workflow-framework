"""Shared utilities for Copilot hook scripts.

Why: All hook scripts need common operations — reading stdin JSON, finding
     project files, loading settings, discovering active boards, outputting
     structured JSON. Centralizing prevents duplication and keeps hooks small.
How: Provide helper functions for stdin parsing, settings loading, board
     discovery, Git state inspection, and JSON stdout output.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


def read_hook_input() -> dict[str, Any]:
    """Read and parse JSON from stdin provided by VS Code.

    Why: Every hook receives structured JSON input via stdin.
    How: Read all of stdin, parse as JSON. Return empty dict on failure.
    """
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def write_hook_output(output: dict[str, Any]) -> None:
    """Write JSON output to stdout for VS Code to consume.

    Why: Hooks communicate decisions/context back to VS Code via stdout JSON.
    How: Serialize dict to JSON and print to stdout.
    """
    print(json.dumps(output, ensure_ascii=False))


def find_repo_root(cwd: Optional[str] = None) -> Path:
    """Find the repository root directory.

    Why: Hook scripts may run from varying working directories.
    How: Use the cwd from hook input, then walk up looking for .github/.
         Fall back to git rev-parse if needed.
    """
    start = Path(cwd) if cwd else Path.cwd()

    # Walk up from start looking for .github/
    current = start.resolve()
    for _ in range(15):
        if (current / ".github").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Fall back to git rev-parse
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=str(start), timeout=5
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return start


def load_settings(repo_root: Path) -> Optional[dict[str, Any]]:
    """Load .github/settings.json.

    Why: Settings are the central project configuration used by all hooks.
    How: Read and parse the JSON file. Return None if not found.
    """
    settings_path = repo_root / ".github" / "settings.json"
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_gate_profiles(repo_root: Path) -> Optional[dict[str, Any]]:
    """Load .github/rules/gate-profiles.json.

    Why: Gate profiles define Gate conditions per Maturity level.
    How: Read and parse the JSON file. Return None if not found.
    """
    path = repo_root / ".github" / "rules" / "gate-profiles.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def find_active_boards(repo_root: Path) -> list[dict[str, Any]]:
    """Find all active Board JSON files and return their parsed content.

    Why: Hooks need to know the current Feature context without manual read_file.
    How: Scan .copilot/boards/ (excluding _archived) for board.json files.
    """
    boards_dir = repo_root / ".copilot" / "boards"
    if not boards_dir.is_dir():
        return []

    boards: list[dict[str, Any]] = []
    for board_dir in boards_dir.iterdir():
        if not board_dir.is_dir() or board_dir.name.startswith("_"):
            continue
        board_file = board_dir / "board.json"
        if board_file.is_file():
            try:
                data = json.loads(board_file.read_text(encoding="utf-8"))
                data["_board_path"] = str(board_file.relative_to(repo_root))
                boards.append(data)
            except (json.JSONDecodeError, OSError):
                continue
    return boards


def get_current_branch(repo_root: Path) -> Optional[str]:
    """Get the name of the current Git branch.

    Why: Branch name determines Feature context and naming rule compliance.
    How: Run git rev-parse --abbrev-ref HEAD.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def has_uncommitted_changes(repo_root: Path) -> bool:
    """Check if there are uncommitted changes in the working tree.

    Why: Used by Stop hook to warn about unsaved work.
    How: Run git status --porcelain and check for non-empty output.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=10
        )
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_uncommitted_summary(repo_root: Path) -> str:
    """Get a concise summary of uncommitted changes.

    Why: Provides actionable detail when warning the user about unsaved changes.
    How: Run git status --short and return the output.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def is_main_branch(branch: Optional[str]) -> bool:
    """Check if the given branch name is the main branch.

    Why: Direct edits to main are prohibited by project rules.
    How: Match against common main branch names.
    """
    return branch in ("main", "master")
