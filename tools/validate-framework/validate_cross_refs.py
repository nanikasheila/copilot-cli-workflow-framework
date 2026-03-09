#!/usr/bin/env python3
"""Validate file cross-references in .github/ framework markdown files.

Why: Documentation references to non-existent files silently mislead contributors
     and agents that rely on them for navigation. A renamed or deleted file leaves
     dangling references that are invisible until someone follows them.
How: Scan every .md file under .github/ for path-like references, resolve each
     path against the .github/ directory (with source-file-relative fallback),
     and report any that do not exist on disk.
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple


def format_error(error: str, file: str, why: str, fix: str) -> str:
    """Format validation error with actionable fix instructions.

    Why: Harness Engineering pattern - error messages should teach agents
         how to fix issues, not just report them. Agents cannot ignore CI errors.
    How: Structured ERROR/WHY/FIX format that agents can parse and act on.
    """
    return f"ERROR: {error}\n  FILE: {file}\n  WHY: {why}\n  FIX: {fix}"


# ── Known .github/ top-level subdirectories ───────────────────────────────────
# Used to anchor bare-text path references and to qualify slash-containing paths.
_GITHUB_SUBDIRS: frozenset[str] = frozenset(
    {
        "agents",
        "instructions",
        "ISSUE_TEMPLATE",
        "references",
        "rules",
        "skills",
        "workflows",
    }
)

# File extensions that mark a token as a potential file path reference.
_VALID_EXTS: frozenset[str] = frozenset(
    {
        ".json",
        ".md",
        ".sh",
        ".txt",
        ".yaml",
        ".yml",
    }
)

# URI schemes that disqualify a string from being a local file path.
_URI_PREFIXES: tuple[str, ...] = ("http://", "https://", "ftp://", "mailto:")

# ── Compiled regex patterns ────────────────────────────────────────────────────

# Backtick-wrapped inline code that contains at least one forward slash.
# Captures: `rules/gate-profiles.json`, `.github/board.schema.json`,
#           `skills/manage-board/SKILL.md`, `references/agent-routing.md`
_RE_BACKTICK: re.Pattern[str] = re.compile(r"`([^`\n]+/[^`\n]+)`")

# Markdown link target portion: [any text](target)
# Captures: [rules](rules/commit-message.md), [see board](../board.schema.json)
_RE_MD_LINK: re.Pattern[str] = re.compile(r"\[[^\]\n]*\]\(([^)\n]+)\)")

# Bare-text references that begin with a known .github/ subdirectory name.
# Captures: rules/gate-profiles.json, skills/orchestrate-workflow/SKILL.md,
#           references/context-management.md
_RE_BARE_PATH: re.Pattern[str] = re.compile(
    r"\b(?:" + "|".join(re.escape(d) for d in sorted(_GITHUB_SUBDIRS)) + r")"
    r"[/\\][^\s,;:'\"()\[\]<>\n]+"
    r"\.(?:json|md|sh|txt|yaml|yml)\b"
)

# Template/variable markers that disqualify a string as a real path.
_RE_TEMPLATE_VAR: re.Pattern[str] = re.compile(r"<[^>]+>")

# Opening or closing of a fenced code block (``` or ~~~).
_RE_CODE_FENCE: re.Pattern[str] = re.compile(r"^\s*(?:```|~~~)")


# ── Data types ─────────────────────────────────────────────────────────────────


class BrokenRef(NamedTuple):
    """A broken file reference found inside a markdown file.

    Attributes:
        source_file: Absolute path to the .md file that contains the reference.
        line_number:  1-based line number of the offending reference.
        raw_path:     The path string exactly as it appears in the source file.
    """

    source_file: Path
    line_number: int
    raw_path: str


# ── Core helpers ───────────────────────────────────────────────────────────────


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


def should_skip(raw: str) -> bool:
    """Return True if the candidate string is not a checkable local file path.

    Why: Regex patterns inevitably match non-path tokens — URLs, shell commands,
         branch names, template variables, glob patterns, and project-scoped
         paths outside .github/ — that must be excluded to avoid false positives.
    How: Apply cheap heuristic tests in order of increasing cost:
         1. URI schemes, anchors, absolute paths → always skip.
         2. Upward-relative paths (../../...) → skip; these document $schema
            path examples relative to board.json runtime locations, not SKILL.md.
         3. Template variables (<owner>, <prefix>) and spaces → skip.
         4. Glob characters (* ?) → skip; e.g. workflows/*.yml is a pattern,
            not a resolvable path.
         5. No path separator → skip (bare filenames, not cross-references).
         6. First path component must be a known .github/ subdirectory or the
            .github prefix itself. Project-scoped paths (docs/, src/, .circleci/)
            are outside this script's validation scope.
    """
    s = raw.strip()
    if not s:
        return True

    # 1a. Skip remote URIs and e-mail links.
    if any(s.startswith(p) for p in _URI_PREFIXES):
        return True

    # 1b. Skip in-page anchors.
    if s.startswith("#"):
        return True

    # 1c. Skip absolute Unix/Windows paths — these are not .github/-relative.
    if s.startswith("/") or (len(s) > 1 and s[1] == ":"):
        return True

    # 2. Skip paths that go up the directory tree.
    if s.startswith("../") or s.startswith("..\\"):
        return True

    # 3a. Skip strings that contain template/variable markers.
    if _RE_TEMPLATE_VAR.search(s):
        return True

    # 3b. Skip strings with embedded spaces (prose fragments or commands).
    if " " in s:
        return True

    # 4. Skip glob patterns — these describe file-name patterns, not real paths.
    if "*" in s or "?" in s:
        return True

    # 5. A cross-reference must contain a path separator.
    if "/" not in s and "\\" not in s:
        return True

    # 6. Only validate paths whose first component anchors to .github/ or a known
    #    .github/ subdirectory. Paths like docs/architecture/... or .circleci/...
    #    are project-scoped and outside this script's scope.
    first = s.replace("\\", "/").split("/")[0]
    return bool(first not in _GITHUB_SUBDIRS and first != ".github")


def resolve_path(raw: str, github_dir: Path, source_file: Path) -> Path:
    """Resolve a raw path string to an absolute candidate Path.

    Why: Paths appear in at least three forms across the framework:
         (1) .github/-relative: rules/gate-profiles.json
         (2) repo-root-relative with .github/ prefix: .github/board.schema.json
         (3) source-file-relative: references/agent-routing.md (inside a skill)
         All must be normalised to absolute paths before existence checks.
    How: Apply resolution strategies 1→2→3 in order; return the first hit.
         Fall back to the .github/-relative candidate so the caller always
         receives a Path to report, even when none of the strategies matched.

    Returns:
        Resolved absolute Path. The caller must call `.exists()` independently.
    """
    # Strip anchor and query-string fragments before resolving.
    clean = raw.strip().split("#")[0].split("?")[0]
    if not clean:
        return github_dir / raw

    # Strategy 1 — explicit .github/ prefix (repo-root-relative form).
    for prefix in (".github/", ".github\\"):
        if clean.startswith(prefix):
            return (github_dir / clean[len(prefix) :]).resolve()

    # Strategy 2 — resolve relative to .github/ (most common framework pattern).
    candidate_a = (github_dir / clean).resolve()
    if candidate_a.exists():
        return candidate_a

    # Strategy 3 — resolve relative to the source file's own directory.
    # Handles skill-local references like `references/agent-routing.md` found
    # inside skills/orchestrate-workflow/SKILL.md.
    candidate_b = (source_file.parent / clean).resolve()
    if candidate_b.exists():
        return candidate_b

    # Default: return the .github/-relative candidate for the error report.
    return candidate_a


def extract_candidates(line: str) -> list[str]:
    """Extract all candidate path strings from a single markdown line.

    Why: A single line may contain several references in different syntactic
         forms; all must be captured before filtering.
    How: Apply each compiled pattern and deduplicate while preserving
         left-to-right order (markdown links first, then backticks, then bare).
    """
    seen: set[str] = set()
    results: list[str] = []

    def _add(value: str) -> None:
        if value not in seen:
            seen.add(value)
            results.append(value)

    for m in _RE_MD_LINK.finditer(line):
        _add(m.group(1))
    for m in _RE_BACKTICK.finditer(line):
        _add(m.group(1))
    for m in _RE_BARE_PATH.finditer(line):
        _add(m.group(0))

    return results


# ── Per-file validator ─────────────────────────────────────────────────────────


def check_file(md_file: Path, github_dir: Path) -> list[BrokenRef]:
    """Scan one markdown file and collect every broken cross-reference.

    Why: Each .md file may reference files that were renamed, moved, or deleted
         without the referencing document being updated.
    How: Read the file line-by-line. Toggle a code-fence flag on ``` / ~~~
         delimiters and skip content inside fenced blocks to avoid flagging
         example paths. For every other line extract path candidates, apply
         the skip filter, resolve each to an absolute path, and record it as
         broken when the resolved path does not exist on disk.
    """
    broken: list[BrokenRef] = []
    try:
        lines = md_file.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"  WARN: could not read {md_file}: {exc}")
        return broken

    in_fence: bool = False
    for lineno, line in enumerate(lines, start=1):
        # Toggle fenced-block tracking; skip the delimiter line itself.
        if _RE_CODE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for raw in extract_candidates(line):
            if should_skip(raw):
                continue
            resolved = resolve_path(raw, github_dir, md_file)
            if not resolved.exists():
                broken.append(BrokenRef(md_file, lineno, raw))

    return broken


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> int:
    """Run cross-reference validation across all .github/ markdown files.

    Why: Single entry point for CI or manual validation runs; must return a
         usable exit code so the caller can gate on success or failure.
    How: Locate .github/, enumerate every .md file recursively, call
         check_file() on each, print per-file status and a final summary of
         all broken references, then exit 0 (all valid) or 1 (any broken).
    """
    github_dir = find_github_dir()
    print(f"Scanning cross-references in: {github_dir}\n")

    md_files = sorted(github_dir.rglob("*.md"))
    print(f"Found {len(md_files)} markdown file(s) to scan.\n")

    all_broken: list[BrokenRef] = []

    for md_file in md_files:
        rel = md_file.relative_to(github_dir)
        broken = check_file(md_file, github_dir)
        all_broken.extend(broken)
        status = "PASS" if not broken else f"FAIL ({len(broken)} broken ref(s))"
        print(f"   {status:<30} {rel}")

    print()
    if all_broken:
        print(f"FAILED: {len(all_broken)} broken reference(s) found:\n")
        for ref in all_broken:
            rel_source = ref.source_file.relative_to(github_dir)
            print(
                format_error(
                    f"Broken cross-reference to '{ref.raw_path}'",
                    f"{rel_source}:{ref.line_number}",
                    "Documentation references to non-existent files silently mislead contributors "
                    "and agents that rely on them for navigation. A renamed or deleted file leaves "
                    "dangling references that are invisible until someone follows them.",
                    "Update the reference to point to the correct file path, "
                    "or remove the reference if the file was intentionally deleted.",
                )
            )
            print()
        return 1

    print("ALL PASSED: No broken cross-references found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
