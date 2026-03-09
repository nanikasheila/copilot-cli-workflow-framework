#!/usr/bin/env python3
"""Validate git commit message format against project conventions.

Why: Consistent commit messages improve git log readability, enable automated
     changelogs, and keep Issue tracker integration reliable. Catching format
     errors at commit time is faster than reviewing them in PRs.
How: Parse the commit message file passed by the commit-msg hook, validate type,
     format, and subject length, then report structured ERROR/WHY/FIX output
     that guides the author to fix the message immediately.

Convention source: .github/rules/commit-message.md

Format:
    <type>: <description>
    <type>: <description> (<prefix>-<number>)   # with Issue tracker

Valid types: feat, fix, docs, chore, refactor, merge
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TYPES: frozenset[str] = frozenset({"feat", "fix", "docs", "chore", "refactor", "merge"})

# <type>: <description>  [optional trailing: (<PREFIX>-<digits>)]
# - type   : lowercase letters only
# - description: any non-empty text (may not be blank)
# - issue-id: LETTERS-digits inside parens, anchored to end of line (optional)
_COMMIT_PATTERN = re.compile(r"^(?P<type>[a-z]+): (?P<description>.+?)(?:\s+\((?P<issue_id>[A-Za-z]+-\d+)\))?$")

SUBJECT_SOFT_LIMIT = 50  # recommended; emit a warning
SUBJECT_HARD_LIMIT = 80  # required; emit an error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def format_error(error: str, why: str, fix: str) -> str:
    """Format a validation error with actionable fix instructions.

    Why: Harness Engineering pattern — error messages should teach the author
         how to fix the issue, not just report it. Structured ERROR/WHY/FIX
         format mirrors other validators in this project for consistency.
    How: Return a multi-line string that is easy to scan in terminal output.
    """
    return f"ERROR: {error}\n  WHY:  {why}\n  FIX:  {fix}"


def read_commit_msg(path: str) -> str:
    """Read and return the commit message, stripping comment lines.

    Why: Git appends comment lines (# ...) to the commit file that must be
         excluded from validation so they do not trigger false positives.
    How: Read the file, discard lines starting with '#', join remaining lines.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Cannot read commit message file '{path}': {exc}", file=sys.stderr)
        sys.exit(1)

    lines = [line for line in raw.splitlines() if not line.startswith("#")]
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_commit_msg(message: str) -> tuple[list[str], list[str]]:
    """Validate a commit message and return (errors, warnings).

    Why: Separating hard errors from soft warnings lets the hook fail on
         required violations while still surfacing style recommendations.
    How: Validate the subject line (first line) against format, type enum,
         and length limits. Extended body lines are not validated.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not message:
        errors.append(
            format_error(
                "Commit message is empty",
                "An empty commit message gives no context about the change. "
                "Git requires a non-empty message to create a commit.",
                "Write a commit message following the format: <type>: <description>\n"
                f"  Valid types: {', '.join(sorted(VALID_TYPES))}",
            )
        )
        return errors, warnings

    subject = message.splitlines()[0]

    # ── Format check ────────────────────────────────────────────────────────
    match = _COMMIT_PATTERN.match(subject)
    if not match:
        errors.append(
            format_error(
                f"Invalid commit message format: '{subject}'",
                "The commit message does not follow the required format. "
                "Inconsistent formats break automated changelog generation and "
                "Issue tracker integration.",
                "Use the format: <type>: <description>\n"
                "  Examples:\n"
                "    feat: add retry logic to board loader\n"
                "    fix: resolve KeyError in gate evaluation\n"
                "    docs: update README with setup instructions\n"
                f"  Valid types: {', '.join(sorted(VALID_TYPES))}",
            )
        )
        # Cannot proceed with further checks without a valid match
        return errors, warnings

    commit_type = match.group("type")
    description = match.group("description")

    # ── Type check ──────────────────────────────────────────────────────────
    if commit_type not in VALID_TYPES:
        errors.append(
            format_error(
                f"Unknown commit type: '{commit_type}'",
                "Only recognised types are allowed; unrecognised types make it "
                "impossible to categorise changes for changelogs or release notes.",
                f"Replace '{commit_type}' with one of: {', '.join(sorted(VALID_TYPES))}\n"
                "  Type meanings:\n"
                "    feat     - new feature\n"
                "    fix      - bug fix\n"
                "    docs     - documentation only\n"
                "    chore    - build / tooling changes\n"
                "    refactor - restructuring without behaviour change\n"
                "    merge    - conflict-resolution merge commit",
            )
        )

    # ── Description check ───────────────────────────────────────────────────
    if not description.strip():
        errors.append(
            format_error(
                "Commit description is empty",
                "The description must explain what the commit does. "
                "An empty description provides no value to reviewers or tools.",
                "Add a concise description after '<type>: '.\n  Example: feat: add OAuth2 login support",
            )
        )

    # ── Subject length checks ───────────────────────────────────────────────
    subject_length = len(subject)

    if subject_length > SUBJECT_HARD_LIMIT:
        errors.append(
            format_error(
                f"Subject line too long: {subject_length} characters (limit: {SUBJECT_HARD_LIMIT})",
                "Long subject lines are truncated in many git UIs (GitHub, git log --oneline) "
                "and make scanning history harder.",
                f"Shorten the subject to {SUBJECT_HARD_LIMIT} characters or fewer. "
                "Move extra detail into the extended body (separated by a blank line).",
            )
        )
    elif subject_length > SUBJECT_SOFT_LIMIT:
        warnings.append(
            f"WARNING: Subject line is {subject_length} characters "
            f"(recommended: <={SUBJECT_SOFT_LIMIT}, required: <={SUBJECT_HARD_LIMIT}). "
            "Consider shortening for readability."
        )

    return errors, warnings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Run commit message validation and report results.

    Why: Single entry point called by the lefthook commit-msg hook.
    How: Read the commit message file path from argv[1], validate, and return
         exit code 0 (pass) or 1 (fail) so lefthook can block the commit.
    """
    if len(sys.argv) < 2:
        print("Usage: validate-commit-msg.py <commit-msg-file>", file=sys.stderr)
        return 1

    msg_path = sys.argv[1]
    message = read_commit_msg(msg_path)

    errors, warnings = validate_commit_msg(message)

    for warning in warnings:
        print(warning)

    if errors:
        print()
        print(f"Commit message validation FAILED ({len(errors)} error(s)):\n")
        for error in errors:
            print(error)
            print()
        return 1

    if warnings:
        print("\nCommit message validation PASSED (with warnings).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
