#!/usr/bin/env python3
"""Validate .github/ configuration files for consistency and correctness.

Why: The .github/ directory contains agents, prompts, rules, instructions,
     and skills that must reference each other correctly. Manual
     checks are error-prone as the framework grows.
How: Parse YAML frontmatters from agents and prompts, verify cross-references
     (handoffs, file links, tool lists), and report issues with actionable
     messages. Exit code reflects validation result for CI integration.
"""

import re
import sys
from pathlib import Path

# Why: YAML is used for agent/prompt frontmatter parsing.
# How: Lazy import with clear error message if not installed.
try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(2)


# -- Constants ---------------------------------------------------------------

# Why: Copilot agents support a fixed set of tool identifiers.
# How: Maintained as a set for O(1) lookup during validation.
VALID_AGENT_TOOLS: set[str] = {
    "read",
    "edit",
    "execute",
    "search",
    "problems",
    "usages",
    "changes",
    "web",
    "todo",
}

# Why: Prompt files use agent tools plus the "agent" tool for sub-agent invocation.
VALID_PROMPT_TOOLS: set[str] = VALID_AGENT_TOOLS | {"agent"}


def format_error(error: str, file: str, why: str, fix: str) -> str:
    """Format validation error with actionable fix instructions.

    Why: Harness Engineering pattern - error messages should teach agents
         how to fix issues, not just report them. Agents cannot ignore CI errors.
    How: Structured ERROR/WHY/FIX format that agents can parse and act on.
    """
    return f"ERROR: {error}\n  FILE: {file}\n  WHY: {why}\n  FIX: {fix}"


# -- Types -------------------------------------------------------------------


class ValidationResult:
    """Accumulate validation errors and warnings.

    Why: Collecting all issues before reporting gives a complete picture
         instead of stopping at the first failure.
    How: Separate lists for errors (fail) and warnings (informational).
    """

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, file_path: str, message: str, why: str, fix: str) -> None:
        """Record a validation error that causes overall failure."""
        self.errors.append(format_error(message, file_path, why, fix))

    def warn(self, file_path: str, message: str) -> None:
        """Record a non-blocking warning."""
        self.warnings.append(f"  WARN  [{file_path}]: {message}")

    @property
    def is_valid(self) -> bool:
        """Return True if no errors were recorded."""
        return len(self.errors) == 0

    def summary(self) -> str:
        """Format a human-readable summary of all findings.

        Why: A single summary string simplifies both CLI output and testing.
        How: Group warnings first, then errors, with a final verdict line.
        """
        lines: list[str] = []
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(self.warnings)
        if self.errors:
            lines.append("Errors:")
            lines.append("\n\n".join(self.errors))
        total = len(self.errors) + len(self.warnings)
        verdict = "PASS" if self.is_valid else "FAIL"
        lines.append(f"\n{verdict}: {len(self.errors)} error(s), {len(self.warnings)} warning(s) in {total} finding(s)")
        return "\n".join(lines)


# -- Frontmatter parsing ----------------------------------------------------


def parse_frontmatter(file_path: Path) -> dict | None:
    """Extract YAML frontmatter from a Markdown file.

    Why: Agent and prompt files embed configuration in YAML frontmatter
         delimited by '---' lines.
    How: Regex captures content between the first two '---' delimiters.
         Returns None if frontmatter is missing or unparseable.
    """
    content = file_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


# -- Agent validation --------------------------------------------------------


def validate_agents(
    github_dir: Path,
    result: ValidationResult,
) -> dict[str, dict]:
    """Validate all agent definition files under .github/agents/.

    Why: Agents define tools, models, and handoffs. Invalid references
         cause runtime failures in Copilot CLI.
    How: Parse each .agent.md file, verify tools against the allowed set,
         collect agent names for handoff cross-reference validation.
    """
    agents_dir = github_dir / "agents"
    agent_data: dict[str, dict] = {}

    if not agents_dir.is_dir():
        result.error(
            "agents/",
            "Directory not found",
            "The agents/ directory is required for the framework to function. "
            "Without it, no agent definitions can be loaded or cross-referenced.",
            "Create the .github/agents/ directory and add at least one *.agent.md file.",
        )
        return agent_data

    agent_files = sorted(agents_dir.glob("*.agent.md"))
    if not agent_files:
        result.error(
            "agents/",
            "No .agent.md files found",
            "The framework requires at least one agent definition. "
            "An empty agents/ directory means no skills or prompts can reference agents.",
            "Create at least one *.agent.md file in .github/agents/.",
        )
        return agent_data

    for agent_file in agent_files:
        rel_path = str(agent_file.relative_to(github_dir.parent))
        fm = parse_frontmatter(agent_file)
        if fm is None:
            result.error(
                rel_path,
                "Missing or invalid YAML frontmatter",
                "Agent files require a YAML frontmatter block (between --- delimiters) to define "
                "name, model, tools, and handoffs. Without it, the agent cannot be loaded.",
                f"Add a valid YAML frontmatter block at the top of {rel_path} "
                "with at least 'description' and 'tools' fields.",
            )
            continue

        agent_name = agent_file.stem.replace(".agent", "")
        agent_data[agent_name] = fm

        # Validate tools
        tools = fm.get("tools", [])
        if not isinstance(tools, list):
            result.error(
                rel_path,
                f"'tools' must be a list, got {type(tools).__name__}",
                "The 'tools' field must be a YAML list so Copilot CLI can enumerate available tools. "
                "A non-list value causes the agent to fail to load.",
                'Change \'tools\' to a YAML list. Example: tools: ["read", "edit", "execute"]',
            )
        else:
            invalid_tools = set(tools) - VALID_AGENT_TOOLS
            if invalid_tools:
                result.error(
                    rel_path,
                    f"Invalid tool(s): {', '.join(sorted(invalid_tools))}",
                    "Agent tools must be from the supported set. Unsupported tools are silently "
                    "ignored or cause the agent to fail, making debugging difficult.",
                    f"Replace the invalid tools with supported ones: {sorted(VALID_AGENT_TOOLS)}",
                )

        # Validate description
        if not fm.get("description"):
            result.warn(rel_path, "Missing 'description'")

        # Validate model
        model = fm.get("model")
        if model is not None and not isinstance(model, (str, list)):
            result.warn(rel_path, "'model' should be a string or array")

    return agent_data


def validate_handoffs(
    agent_data: dict[str, dict],
    github_dir: Path,
    result: ValidationResult,
) -> None:
    """Verify that all handoff targets reference existing agents.

    Why: A handoff to a non-existent agent silently fails at runtime.
    How: For each agent's handoffs, check that the target agent name
         exists in the parsed agent_data dictionary.
    """
    for agent_name, fm in agent_data.items():
        rel_path = f".github/agents/{agent_name}.agent.md"
        handoffs = fm.get("handoffs", [])
        if not isinstance(handoffs, list):
            result.error(
                rel_path,
                "'handoffs' must be a list",
                "The 'handoffs' field must be a YAML list of dicts with 'label' and 'agent' keys. "
                "A non-list value prevents the handoff graph from being built.",
                "Change 'handoffs' to a YAML list. "
                "Example: handoffs:\\n  - label: Go to reviewer\\n    agent: reviewer",
            )
            continue
        for handoff in handoffs:
            if not isinstance(handoff, dict):
                result.error(
                    rel_path,
                    f"Each handoff entry must be a dict, got {type(handoff).__name__}",
                    "Each handoff must be a YAML mapping with 'label' and 'agent' keys. "
                    "A non-dict entry prevents the handoff target from being resolved.",
                    "Change the handoff entry to a dict. Example: - label: Go to reviewer\\n    agent: reviewer",
                )
                continue
            target = handoff.get("agent", "")
            if target not in agent_data:
                result.error(
                    rel_path,
                    f"Handoff target '{target}' does not match any agent file",
                    "Handoffs to non-existent agents silently fail at runtime, breaking the workflow. "
                    "Every handoff target must match a file in .github/agents/.",
                    f"Rename the target to an existing agent, or create .github/agents/{target}.agent.md.",
                )
            if not handoff.get("label"):
                result.warn(rel_path, f"Handoff to '{target}' is missing a label")


# -- Prompt validation -------------------------------------------------------


def validate_prompts(
    github_dir: Path,
    agent_data: dict[str, dict],
    result: ValidationResult,
) -> None:
    """Validate all prompt files under .github/prompts/.

    Why: Prompts reference agents and skills via frontmatter. Broken
         references cause the slash command to fail silently.
    How: Parse each .prompt.md, verify the agent reference exists, and
         check that tools are from the valid set.
    """
    prompts_dir = github_dir / "prompts"
    if not prompts_dir.is_dir():
        result.warn("prompts/", "Directory not found (optional)")
        return

    prompt_files = sorted(prompts_dir.glob("*.prompt.md"))
    if not prompt_files:
        result.warn("prompts/", "No .prompt.md files found")
        return

    for prompt_file in prompt_files:
        rel_path = str(prompt_file.relative_to(github_dir.parent))
        fm = parse_frontmatter(prompt_file)
        if fm is None:
            result.error(
                rel_path,
                "Missing or invalid YAML frontmatter",
                "Prompt files require a YAML frontmatter block (between --- delimiters) to define "
                "description, agent, and tools. Without it, the slash command cannot be registered.",
                f"Add a valid YAML frontmatter block at the top of {rel_path}.",
            )
            continue

        # Validate agent reference
        agent_ref = fm.get("agent")
        if agent_ref and agent_ref not in agent_data:
            result.error(
                rel_path,
                f"Agent '{agent_ref}' not found in .github/agents/",
                "Prompts that reference non-existent agents cause the slash command to fail silently. "
                "Every 'agent' field must match a file in .github/agents/.",
                f"Rename the agent to an existing one, or create .github/agents/{agent_ref}.agent.md.",
            )

        # Validate tools
        tools = fm.get("tools", [])
        if isinstance(tools, list):
            invalid_tools = set(tools) - VALID_PROMPT_TOOLS
            if invalid_tools:
                result.error(
                    rel_path,
                    f"Invalid tool(s): {', '.join(sorted(invalid_tools))}",
                    "Prompt tools must be from the supported set. Unsupported tools are silently "
                    "ignored or cause the prompt to fail, making debugging difficult.",
                    f"Replace the invalid tools with supported ones: {sorted(VALID_PROMPT_TOOLS)}",
                )

        # Validate description
        if not fm.get("description"):
            result.warn(rel_path, "Missing 'description'")


# -- Settings validation -----------------------------------------------------


def validate_settings(
    github_dir: Path,
    result: ValidationResult,
) -> None:
    """Validate .github/settings.json structure.

    Why: settings.json is the central configuration used by all skills and
         skills. Missing required fields cause cascading failures.
    How: Parse JSON and check for required top-level keys.
    """
    import json

    settings_file = github_dir / "settings.json"
    if not settings_file.exists():
        result.error(
            ".github/settings.json",
            "File not found",
            "settings.json is the central configuration for all skills. "
            "Without it, the framework cannot determine repository, project, or team settings.",
            "Create .github/settings.json. See .github/settings.schema.json for the required structure.",
        )
        return

    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.error(
            ".github/settings.json",
            f"Invalid JSON: {exc}",
            "settings.json must be valid JSON. A syntax error prevents all configuration from loading.",
            "Fix the JSON syntax error. Use a JSON validator or run: "
            "python -c \"import json; json.load(open('.github/settings.json'))\"",
        )
        return

    # Required sections
    for required_key in ("github", "project"):
        if required_key not in settings:
            result.error(
                ".github/settings.json",
                f"Missing required section: '{required_key}'",
                f"The '{required_key}' section is required in settings.json. "
                "Skills that read this section will fail with KeyError at startup.",
                f"Add a '{required_key}' section to settings.json. See settings.schema.json for the required fields.",
            )

    # GitHub section
    github_section = settings.get("github", {})
    for field in ("owner", "repo"):
        if not github_section.get(field):
            result.error(
                ".github/settings.json",
                f"Missing github.{field}",
                f"The 'github.{field}' field is required for GitHub API integration. "
                "Skills that create issues or pull requests will fail without it.",
                f'Add \'github.{field}\' to settings.json. Example: {{ "github": {{ "{field}": "your-{field}" }} }}',
            )

    # Branch section (optional but validated if present)
    branch_section = settings.get("branch", {})
    if branch_section and not branch_section.get("user"):
        result.warn("settings.json", "branch.user is empty — naming checks will be skipped")


# -- Entry point -------------------------------------------------------------


def validate_all(repo_root: Path) -> ValidationResult:
    """Run all validations against a repository root.

    Why: Single entry point for both CLI usage and programmatic testing.
    How: Discover .github/ directory, run each validation category,
         and return the accumulated result.
    """
    result = ValidationResult()
    github_dir = repo_root / ".github"

    if not github_dir.is_dir():
        result.error(
            ".github/",
            "Directory not found",
            "The .github/ directory is the root of the framework. "
            "Without it, no configuration, agents, prompts, or rules can be found.",
            "Create the .github/ directory at the repository root and populate it with framework files.",
        )
        return result

    # Phase 1: Settings (foundation for everything else)
    validate_settings(github_dir, result)

    # Phase 2: Agents (needed for handoff + prompt cross-reference)
    agent_data = validate_agents(github_dir, result)

    # Phase 3: Handoff graph integrity
    validate_handoffs(agent_data, github_dir, result)

    # Phase 4: Prompts (reference agents)
    validate_prompts(github_dir, agent_data, result)

    return result


def main() -> None:
    """CLI entry point for .github/ configuration validation.

    Why: Enables CI integration and manual pre-commit checks.
    How: Accept optional repo root argument, run validation, print report.
    """
    repo_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    print(f"Validating .github/ configuration in: {repo_root}\n")
    result = validate_all(repo_root)
    print(result.summary())
    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
