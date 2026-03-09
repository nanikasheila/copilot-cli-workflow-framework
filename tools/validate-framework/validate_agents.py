#!/usr/bin/env python3
"""Validate agent files in .github/agents/.

Why: Agent files define the behavioral contract for every agent in the workflow.
     Missing required sections (Overview, Role, Board Integration, Output Schema,
     Prohibited Actions) leave agents under-specified, causing inconsistent runtime
     behavior and silent orchestration failures.
How: Walk .github/agents/, parse YAML frontmatter and markdown headings for each
     *.agent.md file, report pass/fail per agent with specific missing items,
     and return exit code 1 if any agent fails validation.
"""

import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import]

    YAML_AVAILABLE = True
except ImportError:
    print("WARNING: PyYAML not installed. Frontmatter validation will use basic parsing.")
    print("         Install with: pip install pyyaml")
    YAML_AVAILABLE = False


def format_error(error: str, file: str, why: str, fix: str) -> str:
    """Format validation error with actionable fix instructions.

    Why: Harness Engineering pattern - error messages should teach agents
         how to fix issues, not just report them. Agents cannot ignore CI errors.
    How: Structured ERROR/WHY/FIX format that agents can parse and act on.
    """
    return f"ERROR: {error}\n  FILE: {file}\n  WHY: {why}\n  FIX: {fix}"


# Required frontmatter fields present in every agent file's --- block.
REQUIRED_FRONTMATTER_FIELDS: list[str] = ["name", "description", "model"]

# Required sections — each entry is (Japanese heading, English alias, allow_h3).
# An agent passes if it contains EITHER the Japanese OR the English variant.
# When allow_h3 is True, both ## and ### heading levels satisfy the requirement.
REQUIRED_SECTIONS: list[tuple[str, str, bool]] = [
    ("概要", "Overview", False),
    ("役割", "Role", False),
    ("Board 連携", "Board Integration", False),
    ("出力スキーマ契約", "Output Schema", True),
    ("禁止事項", "Prohibited", False),
]


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


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Why: Agent files store metadata (name, model, description) in a YAML block
         delimited by '---'. Parsing it separately from the body allows targeted
         field validation without polluting heading detection.
    How: Detect opening and closing '---' delimiters; use PyYAML if available,
         otherwise fall back to simple key: value line parsing (no nested structures).
    """
    if not content.startswith("---"):
        return {}, content

    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}, content

    fm_text = content[3:end_idx].strip()
    body = content[end_idx + 3 :].lstrip("\n")

    if YAML_AVAILABLE:
        try:
            parsed = yaml.safe_load(fm_text)
            return parsed if isinstance(parsed, dict) else {}, body
        except yaml.YAMLError as exc:
            print(f"  WARN: YAML parse error in frontmatter: {exc}")
            return {}, body

    # Fallback: basic key: value parsing (handles simple scalar values only).
    fm: dict = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm, body


def validate_frontmatter(frontmatter: dict, filename: str) -> list[str]:
    """Validate required fields in an agent's YAML frontmatter.

    Why: Missing name, description, or model fields cause the agent runtime to
         reject or misidentify the file, breaking orchestration and skill lookups.
    How: Check each required key exists and is non-empty in the parsed dict.
    """
    errors: list[str] = []
    for field in REQUIRED_FRONTMATTER_FIELDS:
        if field not in frontmatter:
            errors.append(
                format_error(
                    f"Frontmatter missing required field '{field}'",
                    filename,
                    "Missing name, description, or model fields cause the agent runtime to reject "
                    "or misidentify the file, breaking orchestration and skill lookups.",
                    f"Add the '{field}' field to the YAML frontmatter block at the top of {filename}.",
                )
            )
        elif not frontmatter[field]:
            errors.append(
                format_error(
                    f"Frontmatter field '{field}' is empty",
                    filename,
                    "Empty required fields are treated as missing by the agent runtime, "
                    "causing the same failures as absent fields.",
                    f"Set a non-empty value for '{field}' in the YAML frontmatter of {filename}.",
                )
            )
    return errors


def validate_sections(body: str, filename: str) -> list[str]:
    """Validate that all required ## sections are present in the agent body.

    Why: Required sections document the agent's role, board integration contract,
         output schema, and prohibited actions. Without them, the agent definition
         is incomplete and downstream consumers (orchestrator, writer) cannot
         reliably interpret the agent's scope.
    How: Extract all level-2 heading texts via regex, then check each required
         section pair (Japanese / English alias) has at least one match.
         Only ## (level-2) headings are checked; ### or deeper do not satisfy
         the requirement.
    """
    errors: list[str] = []
    h2_headings = set(re.findall(r"^## (.+)$", body, re.MULTILINE))
    h3_headings = set(re.findall(r"^### (.+)$", body, re.MULTILINE))

    for ja_name, en_name, allow_h3 in REQUIRED_SECTIONS:
        found_in_h2 = ja_name in h2_headings or en_name in h2_headings
        found_in_h3 = allow_h3 and (ja_name in h3_headings or en_name in h3_headings)
        if not found_in_h2 and not found_in_h3:
            level = "## or ###" if allow_h3 else "##"
            errors.append(
                format_error(
                    f"Missing required section '{level} {ja_name}' (or '{level} {en_name}')",
                    filename,
                    "Required sections document the agent's role, board integration contract, "
                    "output schema, and prohibited actions. Without them, the agent definition "
                    "is incomplete and downstream consumers (orchestrator, writer) cannot "
                    "reliably interpret the agent's scope.",
                    f"Add a '{level} {ja_name}' (or '{level} {en_name}') heading to {filename} "
                    "and fill in the required content.",
                )
            )

    return errors


def validate_agent_file(file_path: Path) -> list[str]:
    """Validate a single agent file for frontmatter fields and section presence.

    Why: Each agent file must satisfy the structural contract to integrate
         correctly with the orchestration framework and board artifact pipeline.
    How: Read the file, split frontmatter from body, run both validators, and
         return the combined error list.
    """
    errors: list[str] = []
    filename = file_path.name

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            format_error(
                f"Cannot read file — {exc}",
                filename,
                "An unreadable agent file is treated as missing, skipping all validation. "
                "This may hide structural errors that would otherwise be caught.",
                f"Check file permissions and encoding for {filename}.",
            )
        ]

    frontmatter, body = parse_frontmatter(content)

    if not frontmatter:
        errors.append(
            format_error(
                "No YAML frontmatter found",
                filename,
                "Agent files must begin with a YAML frontmatter block delimited by '---'. "
                "Without it, the agent runtime cannot read name, description, or model fields.",
                f"Add an opening '---' block with at least 'name', 'description', and 'model' "
                f"fields at the top of {filename}.",
            )
        )
    else:
        errors.extend(validate_frontmatter(frontmatter, filename))

    errors.extend(validate_sections(body, filename))
    return errors


def validate_agents(github_dir: Path) -> list[str]:
    """Validate all *.agent.md files in .github/agents/ and report per-agent results.

    Why: Centralising agent discovery ensures no file is silently skipped and
         every agent is held to the same structural standard.
    How: Glob for *.agent.md in sorted order, run validate_agent_file on each,
         print inline pass/fail with per-agent details, and return all errors.
    """
    agents_dir = github_dir / "agents"
    if not agents_dir.is_dir():
        return [
            format_error(
                ".github/agents/ directory not found",
                str(agents_dir),
                "The agents/ directory is required for the framework to function. "
                "Without it, no agent definitions can be loaded.",
                "Create the .github/agents/ directory and add at least one *.agent.md file.",
            )
        ]

    agent_files = sorted(agents_dir.glob("*.agent.md"))
    if not agent_files:
        return [
            format_error(
                "No *.agent.md files found in .github/agents/",
                str(agents_dir),
                "The framework requires at least one agent definition to function. "
                "An empty agents/ directory means no workflow can be executed.",
                "Create at least one *.agent.md file in .github/agents/.",
            )
        ]

    all_errors: list[str] = []
    for i, agent_file in enumerate(agent_files, start=1):
        print(f"{i}. Validating {agent_file.name}...")
        errors = validate_agent_file(agent_file)
        all_errors.extend(errors)
        if errors:
            print(f"   FAIL ({len(errors)} error(s)):")
            for error in errors:
                for line in error.splitlines():
                    print(f"     {line}")
                print()
        else:
            print("   PASS")

    return all_errors


def main() -> int:
    """Run agent validation and report a final summary.

    Why: Single entry point for CI or manual validation of all agent files.
    How: Discover .github/, run validate_agents(), print aggregate summary,
         and return exit code 0 on success or 1 on any failure.
    """
    github_dir = find_github_dir()
    print(f"Validating agents in: {github_dir / 'agents'}\n")

    all_errors = validate_agents(github_dir)

    print()
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) found across all agent files.")
        return 1

    print("ALL PASSED: No errors found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
