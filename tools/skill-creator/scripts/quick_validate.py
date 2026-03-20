#!/usr/bin/env python3
"""
Quick validation script for skills - minimal version
"""

import re
import sys
from pathlib import Path

import yaml


def format_error(error: str, file: str, why: str, fix: str) -> str:
    """Format validation error with actionable fix instructions.

    Why: Harness Engineering pattern - error messages should teach agents
         how to fix issues, not just report them. Agents cannot ignore CI errors.
    How: Structured ERROR/WHY/FIX format that agents can parse and act on.
    """
    return f"ERROR: {error}\n  FILE: {file}\n  WHY: {why}\n  FIX: {fix}"


def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, format_error(
            "SKILL.md not found",
            str(skill_md),
            "Every skill directory must contain a SKILL.md file with YAML frontmatter "
            "defining at minimum 'name' and 'description'.",
            f"Create SKILL.md in {skill_path} with 'name' and 'description' fields.",
        )

    # Read and validate frontmatter
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, format_error(
            "No YAML frontmatter found",
            str(skill_md),
            "SKILL.md must begin with a YAML frontmatter block between '---' delimiters. "
            "Without it, the skill cannot be parsed or validated.",
            f"Add an opening '---' block at the top of {skill_md} with at least 'name' and 'description' fields.",
        )

    # Extract frontmatter
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, format_error(
            "Invalid frontmatter format",
            str(skill_md),
            "SKILL.md frontmatter must be delimited by '---' on its own line at the start and end. "
            "Malformed delimiters prevent the frontmatter from being extracted.",
            f"Ensure {skill_md} starts with '---\\n', followed by YAML content, and closes with '\\n---'.",
        )

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, format_error(
                "Frontmatter must be a YAML dictionary",
                str(skill_md),
                "SKILL.md frontmatter must parse to a YAML mapping (key: value pairs). "
                "A non-dict value (e.g., a list or scalar) prevents field extraction.",
                f"Rewrite the frontmatter in {skill_md} as a YAML mapping. "
                "Example: name: my-skill\\ndescription: Does something useful",
            )
    except yaml.YAMLError as e:
        return False, format_error(
            f"Invalid YAML in frontmatter: {e}",
            str(skill_md),
            "SKILL.md frontmatter must be valid YAML. A syntax error prevents the skill from being loaded.",
            f"Fix the YAML syntax error in {skill_md}. "
            "Use a YAML validator or check for indentation issues and special characters.",
        )

    # Define allowed properties
    ALLOWED_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}

    # Check for unexpected properties (excluding nested keys under metadata)
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, format_error(
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}",
            str(skill_md),
            "SKILL.md frontmatter only accepts a defined set of properties. "
            "Unknown keys are either typos or unsupported extensions that will be ignored.",
            f"Remove the unexpected keys from {skill_md}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}",
        )

    # Check required fields
    if "name" not in frontmatter:
        return False, format_error(
            "Missing 'name' in frontmatter",
            str(skill_md),
            "The 'name' field is required and used to identify the skill in the registry. "
            "Without it, the skill cannot be referenced or invoked.",
            f"Add a 'name' field to {skill_md}. Use kebab-case (e.g., name: my-skill). Maximum 64 characters.",
        )
    if "description" not in frontmatter:
        return False, format_error(
            "Missing 'description' in frontmatter",
            str(skill_md),
            "The 'description' field is required and shown to users when selecting a skill. "
            "Without it, agents cannot determine what the skill does.",
            f"Add a 'description' field to {skill_md}. Maximum 1024 characters.",
        )

    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, format_error(
            f"Name must be a string, got {type(name).__name__}",
            str(skill_md),
            "The 'name' field must be a YAML string. A non-string value cannot be used as a skill identifier.",
            f"Change 'name' in {skill_md} to a quoted or unquoted string. Example: name: my-skill",
        )
    name = name.strip()
    if name:
        # Check naming convention (kebab-case: lowercase with hyphens)
        if not re.match(r"^[a-z0-9-]+$", name):
            return False, format_error(
                f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)",
                str(skill_md),
                "Skill names must be kebab-case to ensure consistent URL slugs and file name compatibility. "
                "Uppercase letters, spaces, or special characters cause registration failures.",
                f"Rename the skill to use only lowercase letters, digits, and hyphens. "
                f"Example: '{name.lower().replace(' ', '-')}' or a similar kebab-case variant.",
            )
        if name.startswith("-") or name.endswith("-") or "--" in name:
            return False, format_error(
                f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens",
                str(skill_md),
                "Leading, trailing, or consecutive hyphens produce invalid identifiers that break "
                "URL routing and shell tab-completion.",
                f"Remove leading/trailing hyphens and replace '--' with '-' in '{name}'.",
            )
        # Check name length (max 64 characters per spec)
        if len(name) > 64:
            return False, format_error(
                f"Name is too long ({len(name)} characters). Maximum is 64 characters.",
                str(skill_md),
                "Skill names are stored in registries and used in file paths. "
                "Names longer than 64 characters exceed filesystem and API limits.",
                f"Shorten the 'name' value in {skill_md} to 64 characters or fewer.",
            )

    # Extract and validate description
    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return False, format_error(
            f"Description must be a string, got {type(description).__name__}",
            str(skill_md),
            "The 'description' field must be a YAML string. "
            "A non-string value cannot be displayed to users when selecting a skill.",
            f"Change 'description' in {skill_md} to a quoted or unquoted string.",
        )
    description = description.strip()
    if description:
        # Check for angle brackets
        if "<" in description or ">" in description:
            return False, format_error(
                "Description cannot contain angle brackets (< or >)",
                str(skill_md),
                "Angle brackets in descriptions cause HTML injection issues when rendered in UIs. "
                "They also break YAML parsers that interpret them as special characters.",
                f"Remove '<' and '>' from the 'description' field in {skill_md}.",
            )
        # Check description length (max 1024 characters per spec)
        if len(description) > 1024:
            return False, format_error(
                f"Description is too long ({len(description)} characters). Maximum is 1024 characters.",
                str(skill_md),
                "Descriptions are stored in registries and shown in UI tooltips. "
                "Values longer than 1024 characters exceed API limits and are truncated.",
                f"Shorten the 'description' value in {skill_md} to 1024 characters or fewer.",
            )

    # Validate compatibility field if present (optional)
    compatibility = frontmatter.get("compatibility", "")
    if compatibility:
        if not isinstance(compatibility, str):
            return False, format_error(
                f"Compatibility must be a string, got {type(compatibility).__name__}",
                str(skill_md),
                "The 'compatibility' field must be a YAML string describing version requirements. "
                "A non-string value cannot be parsed by the skill resolver.",
                f"Change 'compatibility' in {skill_md} to a string. Example: compatibility: '>=1.0.0'",
            )
        if len(compatibility) > 500:
            return False, format_error(
                f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters.",
                str(skill_md),
                "Compatibility strings are stored in the registry. "
                "Values longer than 500 characters exceed storage limits.",
                f"Shorten the 'compatibility' value in {skill_md} to 500 characters or fewer.",
            )

    return True, "Skill is valid!"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
