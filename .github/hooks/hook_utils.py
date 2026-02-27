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


def _scan_boards_dir(boards_dir: Path, base_for_relative: Path) -> list[dict[str, Any]]:
    """Scan a single .copilot/boards/ directory for active Boards.

    Why: Board discovery logic is reused for both repo root and worktrees.
    How: Iterate subdirectories (excluding _archived), load board.json files.
    """
    boards: list[dict[str, Any]] = []
    if not boards_dir.is_dir():
        return boards
    for board_dir in boards_dir.iterdir():
        if not board_dir.is_dir() or board_dir.name.startswith("_"):
            continue
        board_file = board_dir / "board.json"
        if board_file.is_file():
            try:
                data = json.loads(board_file.read_text(encoding="utf-8"))
                data["_board_path"] = str(
                    board_file.relative_to(base_for_relative)
                ).replace("\\", "/")
                boards.append(data)
            except (json.JSONDecodeError, OSError):
                continue
    return boards


def find_active_boards(repo_root: Path) -> list[dict[str, Any]]:
    """Find all active Board JSON files and return their parsed content.

    Why: Hooks need to know the current Feature context without manual read_file.
    How: Scan .copilot/boards/ at repo root AND inside each worktree under
         .worktrees/. Worktree boards are the primary location during
         feature development.
    """
    boards: list[dict[str, Any]] = []

    # 1. Repo-root boards
    boards.extend(_scan_boards_dir(
        repo_root / ".copilot" / "boards", repo_root
    ))

    # 2. Worktree boards
    worktrees_dir = repo_root / ".worktrees"
    if worktrees_dir.is_dir():
        for wt_dir in worktrees_dir.iterdir():
            if not wt_dir.is_dir():
                continue
            boards.extend(_scan_boards_dir(
                wt_dir / ".copilot" / "boards", repo_root
            ))

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


def resolve_worktree_root(
    file_path: Optional[str],
    repo_root: Path,
) -> Optional[Path]:
    """Resolve the worktree root directory for a given file path.

    Why: Multiple hooks need to determine which worktree a file belongs to
         for branch detection, path normalization, and change detection.
    How: If file_path is inside .worktrees/<name>/, return that directory.
         Return None if the file is not inside a worktree.
    """
    if not file_path:
        return None
    try:
        path = Path(file_path).resolve()
        worktrees_dir = repo_root.resolve() / ".worktrees"
        rel = path.relative_to(worktrees_dir)
        worktree_name = rel.parts[0]
        worktree_root = worktrees_dir / worktree_name
        if worktree_root.is_dir():
            return worktree_root
    except (ValueError, IndexError):
        pass
    return None


def get_branch_for_path(
    file_path: Optional[str],
    repo_root: Path,
) -> Optional[str]:
    """Get the branch associated with a file path, handling worktrees.

    Why: In worktree setups, edited files may reside in a different worktree
         than the repo root. Each worktree has its own HEAD / branch.
         Without this, hooks always see the repo-root branch (usually main)
         and incorrectly block edits inside worktrees.
    How: Delegate to resolve_worktree_root to find the worktree, then run
         git rev-parse from there. Otherwise fall back to repo_root.
    """
    wt_root = resolve_worktree_root(file_path, repo_root)
    if wt_root:
        branch = get_current_branch(wt_root)
        if branch:
            return branch

    return get_current_branch(repo_root)


def get_worktree_branches(repo_root: Path) -> dict[str, str]:
    """Get a mapping of worktree name to its current branch.

    Why: SessionStart and PreCompact need to report branch info for all
         active worktrees, not just the repo root.
    How: Iterate .worktrees/ and run git rev-parse in each.
    """
    branches: dict[str, str] = {}
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.is_dir():
        return branches
    for wt_dir in worktrees_dir.iterdir():
        if not wt_dir.is_dir():
            continue
        branch = get_current_branch(wt_dir)
        if branch:
            branches[wt_dir.name] = branch
    return branches


def normalize_worktree_path(
    file_path: str,
    repo_root: Path,
) -> str:
    """Normalize a worktree file path to its repo-relative equivalent.

    Why: PostToolUse checks if a file is in .github/ or .copilot/ by
         looking at the path relative to repo root. But worktree files
         have paths like .worktrees/<name>/.copilot/... which don't match.
    How: Strip the .worktrees/<name>/ prefix to get the logical repo path.
    """
    try:
        resolved = Path(file_path).resolve()
        worktrees_dir = repo_root.resolve() / ".worktrees"
        rel = resolved.relative_to(worktrees_dir)
        # Skip the worktree name (first component) to get the inner path
        inner_parts = rel.parts[1:]
        if inner_parts:
            return str(Path(*inner_parts)).replace("\\", "/")
    except (ValueError, IndexError):
        pass
    return file_path
