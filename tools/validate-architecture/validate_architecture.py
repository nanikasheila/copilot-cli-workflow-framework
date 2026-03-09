#!/usr/bin/env python3
"""Architecture validation for the copilot-cli-workflow-framework.

Why: Pointer corruption in configuration files (dead links to non-existent rules,
     oversized agent files, invalid ADR statuses) silently degrades the framework.
     Deterministic automated checks catch these problems before they reach main.
How: Validate four categories: (1) path references in key files exist on disk,
     (2) file sizes stay within defined limits, (3) ADR lifecycle statuses are
     valid, (4) rule files referenced in agent '必要ルール' sections exist.
"""

import re
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Repository discovery
# ---------------------------------------------------------------------------


def find_repo_root() -> Path:
    """Walk up directory tree to find the repo root (parent of .github/).

    Why: This script may be invoked from any working directory. Anchoring
         discovery to the script file's own location makes it location-independent.
    How: Start at the directory containing this file and walk toward the filesystem
         root. The first directory that contains a .github/ sub-directory is the
         repo root. Abort after 10 hops to avoid infinite loops.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / ".github").is_dir():
            return current
        current = current.parent
    print("ERROR: repo root (parent of .github/) not found")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Error formatting
# ---------------------------------------------------------------------------


def format_error(what: str, file: str, why: str, fix: str) -> str:
    """Format a validation error message in the project-standard four-field format.

    Args:
        what: Short description of what is wrong.
        file: Path to the file where the problem was found.
        why: Explanation of why this rule exists.
        fix: Concrete steps to resolve the problem.

    Returns:
        Multi-line error string ready to print.
    """
    return f"ERROR: {what}\n  FILE: {file}\n  WHY: {why}\n  FIX: {fix}"


# ---------------------------------------------------------------------------
# Path reference detection (shared utilities)
# ---------------------------------------------------------------------------

# Matches any backtick-enclosed token that looks like a file path.
_PATH_RE = re.compile(r"`([a-zA-Z0-9_./-]+\.(md|json|yml|yaml|py|jsonc))`")

# Only check paths that start with one of these well-known prefixes.
# This avoids false positives from example code, SQL snippets, external
# references, or paths that are intentionally documented but not local.
_KNOWN_PREFIXES: tuple[str, ...] = (
    "rules/",
    "skills/",
    "agents/",
    "instructions/",
    "docs/",
    "tools/",
    ".github/",
)

# Bare filenames (no directory component) that are well-known root-level or
# .github-level files and should be checked.
_KNOWN_ROOT_FILES: frozenset[str] = frozenset(
    {
        "settings.json",
        "settings.schema.json",
        "board.schema.json",
        "board-artifacts.schema.json",
        "gate-profiles.schema.json",
        "lefthook.yml",
        "pyproject.toml",
        "CHANGELOG.md",
        "README.md",
        "CONTRIBUTING.md",
    }
)


def _is_checkable_path(path: str) -> bool:
    """Return True if *path* looks like a project-internal file reference.

    Why: The PATH_RE intentionally casts a wide net; this filter narrows the
         results to paths that are clearly local to this repository, avoiding
         false positives from code-block examples or third-party references.
    """
    return path in _KNOWN_ROOT_FILES or any(path.startswith(prefix) for prefix in _KNOWN_PREFIXES)


def extract_path_references(text: str) -> list[str]:
    """Return a list of checkable file path references found in *text*.

    Scans for backtick-enclosed tokens matching the file-path pattern and
    keeps only those that pass the known-prefix filter.

    Args:
        text: Raw file content to scan.

    Returns:
        List of path strings (may contain duplicates if a path appears
        multiple times in the source).
    """
    found = _PATH_RE.findall(text)
    return [path for path, _ext in found if _is_checkable_path(path)]


def resolve_path(path: str, repo_root: Path) -> bool:
    """Return True if *path* resolves to an existing file under *repo_root*.

    Tries two candidate locations:
      1. ``repo_root / path``          — path is repo-relative (e.g. docs/…)
      2. ``repo_root / ".github" / path`` — path is .github-relative (e.g. rules/…)

    Args:
        path: Relative path string extracted from a backtick reference.
        repo_root: Absolute path to the repository root.

    Returns:
        True if at least one candidate exists on disk.
    """
    candidates = [
        repo_root / path,
        repo_root / ".github" / path,
    ]
    return any(c.exists() for c in candidates)


# ---------------------------------------------------------------------------
# 2a. Pointer corruption detection
# ---------------------------------------------------------------------------


def check_pointer_corruption(repo_root: Path) -> list[str]:
    """Verify that all file path references in key files actually exist on disk.

    Why: When an agent or skill references a file that has been renamed or
         deleted, it silently operates without the intended policy constraint.
         Catching dead pointers early prevents agents from running with
         incomplete or stale operational context.
    How: Scan three file groups — copilot-instructions.md, agent definitions,
         and skill definitions — extract backtick-enclosed path references that
         match known project prefixes, then verify each resolves to a real file.

    Scans:
        - .github/copilot-instructions.md
        - .github/agents/*.agent.md
        - .github/skills/*/SKILL.md
    """
    errors: list[str] = []

    files_to_scan: list[Path] = []

    copilot_instructions = repo_root / ".github" / "copilot-instructions.md"
    if copilot_instructions.exists():
        files_to_scan.append(copilot_instructions)

    agents_dir = repo_root / ".github" / "agents"
    if agents_dir.is_dir():
        files_to_scan.extend(sorted(agents_dir.glob("*.agent.md")))

    skills_dir = repo_root / ".github" / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                files_to_scan.append(skill_file)

    for source_file in files_to_scan:
        text = source_file.read_text(encoding="utf-8")
        rel_source = source_file.relative_to(repo_root)

        for ref in extract_path_references(text):
            if not resolve_path(ref, repo_root):
                errors.append(
                    format_error(
                        what=f"Referenced file not found: `{ref}`",
                        file=str(rel_source),
                        why=(
                            "Broken path references cause agents to fail silently "
                            "when they try to `view` a file that does not exist."
                        ),
                        fix=(f"Create `{ref}` or update the reference to point to the correct existing path."),
                    )
                )

    return errors


# ---------------------------------------------------------------------------
# 2b. File size guards
# ---------------------------------------------------------------------------

# Each entry: (glob pattern relative to .github/, max lines, human label)
_SIZE_LIMITS: list[tuple[str, int, str]] = [
    ("agents/*.agent.md", 500, "agent definition"),
    ("skills/*/SKILL.md", 500, "skill definition"),
    ("rules/*.md", 500, "rule file"),
    ("instructions/*.instructions.md", 300, "instruction file"),
]

_COPILOT_INSTRUCTIONS_MAX_LINES = 100


def check_file_sizes(repo_root: Path) -> list[str]:
    """Verify that key framework files do not exceed maximum line counts.

    Why: Oversized files dilute agent focus, increase token cost, and are a
         maintenance burden. Hard limits enforce the principle that framework
         files should be dense pointers, not prose monoliths.
    How: Count newline-delimited lines for each file matching the known glob
         patterns and for copilot-instructions.md. Report any that exceed
         their category-specific limit.
    """
    errors: list[str] = []
    github_dir = repo_root / ".github"

    # copilot-instructions.md has its own stricter limit
    ci_file = github_dir / "copilot-instructions.md"
    if ci_file.exists():
        lines = len(ci_file.read_text(encoding="utf-8").splitlines())
        if lines > _COPILOT_INSTRUCTIONS_MAX_LINES:
            errors.append(
                format_error(
                    what=(f"copilot-instructions.md has {lines} lines (limit: {_COPILOT_INSTRUCTIONS_MAX_LINES})"),
                    file=str(ci_file.relative_to(repo_root)),
                    why=(
                        "copilot-instructions.md is loaded on every Copilot request. "
                        "Keeping it compact (≤100 lines) minimises token usage and "
                        "forces important content to be expressed as pointer references."
                    ),
                    fix=(
                        "Move detailed content to rules/, skills/, or agents/ and "
                        "replace inline prose with a one-line pointer."
                    ),
                )
            )

    for pattern, max_lines, description in _SIZE_LIMITS:
        for path in sorted(github_dir.glob(pattern)):
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines > max_lines:
                errors.append(
                    format_error(
                        what=(f"{description} {path.name} has {lines} lines (limit: {max_lines})"),
                        file=str(path.relative_to(repo_root)),
                        why=(
                            f"Large {description} files increase load time, make "
                            "maintenance harder, and dilute the agent's focus area."
                        ),
                        fix=(
                            f"Refactor to ≤{max_lines} lines by extracting content "
                            "into separate reference files under the appropriate "
                            "sub-directory."
                        ),
                    )
                )

    return errors


# ---------------------------------------------------------------------------
# 2c. ADR status validation
# ---------------------------------------------------------------------------

# Valid lifecycle status values (Japanese canonical forms)
_VALID_ADR_STATUSES: tuple[str, ...] = ("提案中", "採用済み", "置換済み", "非推奨")

# Matches lines like: - **ステータス**: 採用済み (Accepted)
_ADR_STATUS_RE = re.compile(r"\*\*ステータス\*\*\s*[:]\s*(.+)")


def check_adr_statuses(repo_root: Path) -> list[str]:
    """Verify that every non-template ADR file declares a valid status.

    Why: ADR status drives discoverability and trust. An ADR without a status
         (or with a free-form value) cannot be reliably filtered by tooling or
         humans looking for currently-active decisions.
    How: Glob for ADR-*.md in docs/architecture/adr/, skip files whose name
         contains 'template', then assert each file has a **ステータス** header
         whose value is one of the four recognised lifecycle stages.
    """
    errors: list[str] = []
    adr_dir = repo_root / "docs" / "architecture" / "adr"

    if not adr_dir.is_dir():
        return []  # No ADR directory — nothing to validate

    for adr_file in sorted(adr_dir.glob("ADR-*.md")):
        if "template" in adr_file.name.lower():
            continue  # Template files are excluded by design

        text = adr_file.read_text(encoding="utf-8")
        rel_path = str(adr_file.relative_to(repo_root))

        match = _ADR_STATUS_RE.search(text)
        if match is None:
            errors.append(
                format_error(
                    what=f"ADR missing required `**ステータス**:` field: {adr_file.name}",
                    file=rel_path,
                    why=(
                        "Every ADR must declare its lifecycle stage so consumers "
                        "can quickly determine whether a decision is still current."
                    ),
                    fix=(
                        "Add `- **ステータス**: <値>` near the top of the file. "
                        f"Valid values: {', '.join(_VALID_ADR_STATUSES)}"
                    ),
                )
            )
            continue

        status_value = match.group(1).strip()
        if not any(valid in status_value for valid in _VALID_ADR_STATUSES):
            errors.append(
                format_error(
                    what=(f"ADR has unrecognised status `{status_value}`: {adr_file.name}"),
                    file=rel_path,
                    why=(
                        "Only approved status values are accepted to keep ADR "
                        "lifecycle tracking consistent across the project."
                    ),
                    fix=(f"Change the status to one of: {', '.join(_VALID_ADR_STATUSES)}"),
                )
            )

    return errors


# ---------------------------------------------------------------------------
# 2d. Agent-rule reference consistency
# ---------------------------------------------------------------------------

# Matches backtick-enclosed rules/ file references specifically
_RULE_REF_RE = re.compile(r"`(rules/[a-zA-Z0-9_./-]+\.(?:md|json))`")

# Matches the start of a 必要ルール section heading (with or without CLI prefix)
_REQUIRED_RULES_SECTION_RE = re.compile(
    r"##\s*(?:CLI\s*固有:\s*)?必要ルール(.*?)(?=\n##\s|\Z)",
    re.DOTALL,
)


def check_agent_rule_refs(repo_root: Path) -> list[str]:
    """Verify that every rule referenced in an agent's '必要ルール' section exists.

    Why: Agents that reference missing rules silently operate without their
         intended operational constraints, leading to policy violations or
         unexpected behaviour during feature development.
    How: For each agent file, locate the '必要ルール' section (if present),
         extract all rules/ references within it, then verify each resolves to
         a real file under .github/rules/.
    """
    errors: list[str] = []
    agents_dir = repo_root / ".github" / "agents"

    if not agents_dir.is_dir():
        return []

    for agent_file in sorted(agents_dir.glob("*.agent.md")):
        text = agent_file.read_text(encoding="utf-8")
        rel_path = str(agent_file.relative_to(repo_root))

        section_match = _REQUIRED_RULES_SECTION_RE.search(text)
        if section_match is None:
            continue  # Agent has no required-rules section — skip

        section_text = section_match.group(1)
        refs = _RULE_REF_RE.findall(section_text)

        for ref in refs:
            if not resolve_path(ref, repo_root):
                errors.append(
                    format_error(
                        what=f"Agent references non-existent rule: `{ref}`",
                        file=rel_path,
                        why=(
                            "Agents that reference missing rules will fail to load "
                            "their operational constraints, leading to policy violations "
                            "or unexpected behaviour."
                        ),
                        fix=(
                            f"Create `{ref}` or update the reference to point to an "
                            "existing rule file in .github/rules/."
                        ),
                    )
                )

    return errors


# ---------------------------------------------------------------------------
# 2e. Documentation freshness checks
# ---------------------------------------------------------------------------

# Matches the entire <!-- doc-freshness ... --> comment block.
# The inner content is captured for further field extraction.
_FRESHNESS_BLOCK_RE = re.compile(r"<!--\s*doc-freshness\b(.*?)-->", re.DOTALL)

# Extracts the status field value from inside a freshness block.
_FRESHNESS_STATUS_RE = re.compile(r"^\s*status:\s*(\S+)", re.MULTILINE)

# Extracts the last_verified date (ISO-8601) from inside a freshness block.
_FRESHNESS_DATE_RE = re.compile(r"^\s*last_verified:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)

# Valid values for the freshness status field.
_VALID_FRESHNESS_STATUSES: tuple[str, ...] = ("active", "needs_review", "stale")

# Number of days since last_verified before a WARNING is emitted.
_FRESHNESS_WARNING_DAYS = 180


def is_stale(last_verified: date, today: date | None = None) -> bool:
    """Return True if *last_verified* is at least _FRESHNESS_WARNING_DAYS days ago.

    Args:
        last_verified: The date the document was last verified.
        today: Reference date for the comparison; defaults to ``date.today()``.

    Returns:
        True when the document age meets or exceeds the warning threshold.
    """
    if today is None:
        today = date.today()
    return (today - last_verified).days >= _FRESHNESS_WARNING_DAYS


def format_warning(what: str, file: str, why: str, review: str) -> str:
    """Format a non-blocking freshness warning in the project-standard four-field format.

    Args:
        what: Short description of what triggered the warning.
        file: Path to the file where the issue was found.
        why: Explanation of why this warning exists.
        review: Concrete steps to resolve the warning.

    Returns:
        Multi-line warning string ready to print.
    """
    return f"WARNING: {what}\n  FILE: {file}\n  WHY: {why}\n  REVIEW: {review}"


def check_doc_freshness_metadata(repo_root: Path) -> list[str]:
    """Verify that every docs/architecture/*.md file contains a doc-freshness block.

    Why: Without a freshness marker, there is no machine-readable signal that a
         document has been reviewed recently. Stale documentation silently misleads
         agents and developers who rely on it for architectural context.
    How: Glob for .md files directly under docs/architecture/ (the adr/
         subdirectory is intentionally excluded — ADRs are immutable by design).
         Report an error for any file that lacks the <!-- doc-freshness --> block.
    """
    errors: list[str] = []
    arch_dir = repo_root / "docs" / "architecture"

    if not arch_dir.is_dir():
        return []

    for md_file in sorted(arch_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        rel_path = str(md_file.relative_to(repo_root))

        if _FRESHNESS_BLOCK_RE.search(text) is None:
            errors.append(
                format_error(
                    what=f"Missing doc-freshness metadata: {md_file.name}",
                    file=rel_path,
                    why=(
                        "Architecture documentation without a freshness marker cannot "
                        "be monitored for staleness, allowing silent drift between the "
                        "document and the actual system."
                    ),
                    fix=(
                        "Add the following block at the top of the file:\n"
                        "  <!-- doc-freshness\n"
                        "  status: active\n"
                        "  last_verified: <YYYY-MM-DD>\n"
                        "  verified_by: <role>\n"
                        "  -->"
                    ),
                )
            )

    return errors


def check_doc_freshness_staleness(repo_root: Path) -> list[str]:
    """Emit warnings for docs/architecture/*.md files whose last_verified is old.

    Why: Documentation that has not been reviewed in over six months may no longer
         reflect the current system, increasing the risk of architectural drift.
    How: Parse the last_verified date from each freshness block. Emit a WARNING
         (non-blocking) when the date is at least _FRESHNESS_WARNING_DAYS days ago.
         Files without a freshness block are skipped here (handled by
         check_doc_freshness_metadata instead).
    """
    warnings: list[str] = []
    arch_dir = repo_root / "docs" / "architecture"

    if not arch_dir.is_dir():
        return []

    today = date.today()

    for md_file in sorted(arch_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        rel_path = str(md_file.relative_to(repo_root))

        block_match = _FRESHNESS_BLOCK_RE.search(text)
        if block_match is None:
            continue  # Missing block is reported by check_doc_freshness_metadata

        block_content = block_match.group(1)
        date_match = _FRESHNESS_DATE_RE.search(block_content)
        if date_match is None:
            continue  # Malformed block — skip staleness check

        try:
            last_verified = date.fromisoformat(date_match.group(1))
        except ValueError:
            continue  # Unparseable date — skip staleness check

        if is_stale(last_verified, today):
            age_days = (today - last_verified).days
            warnings.append(
                format_warning(
                    what=f"Documentation may be stale: {md_file.name}",
                    file=rel_path,
                    why=(
                        f"last_verified ({last_verified}) is {age_days} days old "
                        f"(threshold: {_FRESHNESS_WARNING_DAYS} days). "
                        "Content may no longer reflect the current system state."
                    ),
                    review=(
                        "Review the document for accuracy, update content as needed, "
                        "then set last_verified to today's date and status to 'active'."
                    ),
                )
            )

    return warnings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all architecture validation checks and report findings.

    Why: A single command that developers and CI can run to verify the entire
         framework is internally consistent. Exit code propagates to the caller
         so pipelines can gate on the result without parsing output.
    How: Discover the repo root, run each check function, collect and print all
         errors, then exit 0 only if no errors were found. Freshness staleness
         warnings are printed but do not affect the exit code.
    """
    repo_root = find_repo_root()
    print(f"Repo root: {repo_root}")
    print()

    checks = [
        ("Pointer corruption detection", check_pointer_corruption),
        ("File size guards", check_file_sizes),
        ("ADR status validation", check_adr_statuses),
        ("Agent-rule reference consistency", check_agent_rule_refs),
        ("Documentation freshness metadata", check_doc_freshness_metadata),
    ]

    all_errors: list[str] = []

    for check_name, check_fn in checks:
        print(f"Checking: {check_name}...")
        errors = check_fn(repo_root)
        if errors:
            for err in errors:
                print(err)
                print()
        else:
            print("  OK - no issues found")
        all_errors.extend(errors)

    # Freshness staleness warnings — non-blocking, do not affect exit code
    print("Checking: Documentation freshness staleness...")
    staleness_warnings = check_doc_freshness_staleness(repo_root)
    if staleness_warnings:
        for warn in staleness_warnings:
            print(warn)
            print()
        print(f"  {len(staleness_warnings)} freshness warning(s) — review recommended but CI continues.")
    else:
        print("  OK - no stale documents found")

    print()
    if all_errors:
        print(f"FAIL: {len(all_errors)} architecture violation(s) found.")
        return 1

    print("PASS: All architecture checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
