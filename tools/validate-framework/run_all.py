#!/usr/bin/env python3
"""Orchestrate all framework validators in sequence.

Why: Individual validators catch narrowly-scoped problems (schema validity, config
     correctness, agent wiring, cross-references). Running them one by one by hand
     is error-prone and easy to forget. A single entry point ensures every layer of
     the framework is checked consistently—whether triggered manually or from CI.
How: Walk up from this script's location to find the repo root (parent of .github/).
     Resolve each validator's absolute path, then invoke it via subprocess using
     sys.executable so the same Python interpreter is always used. Capture stdout
     and stderr from each run, print them under labelled section headers, track
     pass/fail status, and emit a summary table. Exit 0 only when all validators
     pass; exit 1 on any failure or unexpected error.
"""

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ValidatorResult:
    """Outcome of running a single validator script.

    Why: Grouping name, status, error count, and captured output into one object
         makes it straightforward to render the summary table without re-parsing
         anything later.
    """

    name: str
    status: str  # "PASS" | "FAIL" | "SKIP" | "ERROR"
    error_count: int = 0
    output: str = field(default="", repr=False)


# ---------------------------------------------------------------------------
# Repository discovery
# ---------------------------------------------------------------------------


def find_repo_root() -> Path:
    """Walk up directory tree to find the repo root (parent of .github/).

    Why: This script may be invoked from any working directory—from the repo root,
         from inside tools/, or from a CI runner with an arbitrary CWD. Anchoring
         discovery to the script file's own location makes it location-independent.
    How: Start at the directory that contains this file and walk toward the
         filesystem root. The first directory that contains a .github/ sub-directory
         is the repo root. Abort after 10 hops to avoid infinite loops on broken
         environments.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / ".github").is_dir():
            return current
        current = current.parent
    print("ERROR: repo root (parent of .github/) not found")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------


def run_validator(script_path: Path) -> ValidatorResult:
    """Execute a single Python validator script and return its result.

    Why: Each validator is an independent script that already knows how to report
         its own findings to stdout/stderr and signal overall pass/fail via its
         exit code. Re-using that contract means no logic needs to be duplicated
         here; we only need to capture the output and translate the exit code.
    How: Check for the script's existence first—if missing, return SKIP so the
         runner can continue rather than aborting the whole suite. When the script
         is present, invoke it with sys.executable (the same interpreter running
         this file) via subprocess.run with combined stdout+stderr capture.
         A non-zero return code is treated as FAIL; an exception during launch
         is reported as ERROR.

    Args:
        script_path: Absolute path to the Python validator script to run.

    Returns:
        ValidatorResult populated with name, status, error_count, and raw output.
    """
    name = script_path.name

    if not script_path.exists():
        return ValidatorResult(
            name=name,
            status="SKIP",
            output=f"WARNING: {script_path} not found — skipping.",
        )

    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return ValidatorResult(
            name=name,
            status="ERROR",
            error_count=1,
            output=f"ERROR: failed to launch {script_path}: {exc}",
        )

    combined = result.stdout or ""
    if result.stderr:
        combined = combined + result.stderr if combined else result.stderr

    if result.returncode == 0:
        return ValidatorResult(name=name, status="PASS", output=combined)

    # Count error lines as a rough indicator of severity for the summary table.
    error_count = sum(1 for line in combined.splitlines() if line.strip().startswith("FAIL"))
    error_count = max(error_count, 1)  # at least 1 since the process failed

    return ValidatorResult(
        name=name,
        status="FAIL",
        error_count=error_count,
        output=combined,
    )


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def print_section(index: int, name: str, script_path: Path) -> None:
    """Print a labelled section header before running a validator.

    Why: When multiple validators produce output back-to-back, unmarked output
         is impossible to attribute. Clear headers make the log scannable.
    How: Print a separator line, the 1-based index, script name, and full path.
    """
    separator = "─" * 60
    print(separator)
    print(f"{index}. {name}  ({script_path})")
    print(separator)


def print_validator_output(result: ValidatorResult) -> None:
    """Print captured stdout/stderr from a validator, indented for readability.

    Why: Raw subprocess output mixed with runner output is visually noisy.
         Indenting each line makes it clear which text belongs to which validator.
    How: Split on newlines and prefix every non-empty line with four spaces.
    """
    if not result.output:
        return
    for line in result.output.splitlines():
        print(f"    {line}" if line else "")


def print_summary(results: list[ValidatorResult]) -> None:
    """Print a tabular summary of all validator outcomes.

    Why: After many lines of raw output, the operator needs a quick at-a-glance
         view of which validators passed or failed without scrolling back up.
    How: Compute column widths from actual data, print a header row, then one
         row per validator. Append a totals line showing overall pass/fail counts.
    """
    col_name = max(len(r.name) for r in results)
    col_name = max(col_name, len("Validator"))
    col_status = max(len(r.status) for r in results)
    col_status = max(col_status, len("Status"))

    header = f"  {'Validator':<{col_name}}  {'Status':<{col_status}}  Errors"
    divider = "  " + "-" * (len(header) - 2)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(header)
    print(divider)

    passed = 0
    failed = 0
    skipped = 0

    for r in results:
        print(f"  {r.name:<{col_name}}  {r.status:<{col_status}}  {r.error_count}")
        if r.status == "PASS":
            passed += 1
        elif r.status == "SKIP":
            skipped += 1
        else:
            failed += 1

    print(divider)
    print(f"  {'TOTAL':<{col_name}}  {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all framework validators in order and print a final summary.

    Why: Single command that a developer or CI job can run to verify the entire
         framework is internally consistent. Exit code propagates to the caller
         so CI pipelines can gate on the result without parsing output.
    How: Resolve the repo root, build absolute paths to each validator, run them
         sequentially via run_validator(), print section headers and captured
         output, then emit the summary table. Return 0 only if every validator
         that was found (not skipped) passed.
    """
    repo_root = find_repo_root()
    print(f"Repo root: {repo_root}\n")

    validators: list[tuple[str, Path]] = [
        (
            "validate_schemas",
            repo_root / "tools" / "validate-schemas" / "validate_schemas.py",
        ),
        (
            "validate_config",
            repo_root / "tools" / "validate-github-config" / "validate_config.py",
        ),
        (
            "validate_agents",
            repo_root / "tools" / "validate-framework" / "validate_agents.py",
        ),
        (
            "validate_cross_refs",
            repo_root / "tools" / "validate-framework" / "validate_cross_refs.py",
        ),
        (
            "validate_architecture",
            repo_root / "tools" / "validate-architecture" / "validate_architecture.py",
        ),
    ]

    results: list[ValidatorResult] = []

    for index, (name, script_path) in enumerate(validators, start=1):
        print_section(index, name, script_path)

        result = run_validator(script_path)
        result.name = name  # use the friendly name instead of the bare filename

        print_validator_output(result)

        status_line = f"   → {result.status}"
        if result.status in ("FAIL", "ERROR"):
            status_line += f" ({result.error_count} error(s))"
        elif result.status == "SKIP":
            status_line += " (validator not found)"
        print(status_line)
        print()

        results.append(result)

    print_summary(results)

    any_failed = any(r.status in ("FAIL", "ERROR") for r in results)
    if any_failed:
        print("\nRESULT: FAILED — one or more validators reported errors.")
        return 1

    print("\nRESULT: ALL PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
