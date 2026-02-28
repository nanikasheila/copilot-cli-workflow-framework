#!/usr/bin/env python3
"""Tests for validate_config module.

Why: The validation tool itself must be correct — false positives erode
     trust, false negatives miss real issues.
How: Unit tests for each validation function using synthetic fixtures.
     No external dependencies beyond PyYAML (already required).
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_config import (
    ValidationResult,
    parse_frontmatter,
    validate_agents,
    validate_handoffs,
    validate_prompts,
    validate_settings,
    validate_all,
)

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    """Assert a test condition and track results."""
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name}")
        failed += 1


def create_agent_file(agents_dir: Path, name: str, content: str) -> None:
    """Write an agent file with given content."""
    (agents_dir / f"{name}.agent.md").write_text(content, encoding="utf-8")


def create_prompt_file(prompts_dir: Path, name: str, content: str) -> None:
    """Write a prompt file with given content."""
    (prompts_dir / f"{name}.prompt.md").write_text(content, encoding="utf-8")


if __name__ == "__main__":

    # -- Test: parse_frontmatter -------------------------------------------------

    print("=== parse_frontmatter ===")

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)

        # Valid frontmatter
        valid_file = p / "valid.md"
        valid_file.write_text('---\nname: test\ndescription: "A test"\n---\n# Body\n')
        fm = parse_frontmatter(valid_file)
        check("valid frontmatter parsed", fm is not None and fm["name"] == "test")

        # Missing frontmatter
        no_fm_file = p / "no_fm.md"
        no_fm_file.write_text("# Just a heading\n")
        check("missing frontmatter returns None", parse_frontmatter(no_fm_file) is None)

        # Invalid YAML
        bad_yaml_file = p / "bad.md"
        bad_yaml_file.write_text("---\n[invalid: yaml: here\n---\n")
        check("invalid YAML returns None", parse_frontmatter(bad_yaml_file) is None)


    # -- Test: validate_agents ---------------------------------------------------

    print("\n=== validate_agents ===")

    with tempfile.TemporaryDirectory() as tmp:
        github_dir = Path(tmp) / ".github"
        agents_dir = github_dir / "agents"
        agents_dir.mkdir(parents=True)

        # Valid agent
        create_agent_file(agents_dir, "dev", (
            '---\ndescription: "Dev agent"\n'
            'tools: ["read", "edit", "execute"]\n'
            'model: ["Claude Sonnet 4.6 (copilot)"]\n---\n# Dev\n'
        ))

        result = ValidationResult()
        data = validate_agents(github_dir, result)
        check("valid agent passes", result.is_valid)
        check("agent data populated", "dev" in data)

        # Invalid tool
        create_agent_file(agents_dir, "bad", (
            '---\ndescription: "Bad"\ntools: ["read", "invalid_tool"]\n---\n'
        ))
        result2 = ValidationResult()
        validate_agents(github_dir, result2)
        check("invalid tool detected", not result2.is_valid)


    # -- Test: validate_handoffs -------------------------------------------------

    print("\n=== validate_handoffs ===")

    with tempfile.TemporaryDirectory() as tmp:
        github_dir = Path(tmp) / ".github"
        agents_dir = github_dir / "agents"
        agents_dir.mkdir(parents=True)

        create_agent_file(agents_dir, "alpha", (
            '---\ndescription: "Alpha"\ntools: ["read"]\n'
            'handoffs:\n  - label: "Go to beta"\n    agent: beta\n---\n'
        ))
        create_agent_file(agents_dir, "beta", (
            '---\ndescription: "Beta"\ntools: ["read"]\n---\n'
        ))

        result = ValidationResult()
        data = validate_agents(github_dir, result)
        validate_handoffs(data, github_dir, result)
        check("valid handoff passes", result.is_valid)

        # Handoff to non-existent agent
        create_agent_file(agents_dir, "ghost", (
            '---\ndescription: "Ghost"\ntools: ["read"]\n'
            'handoffs:\n  - label: "Go to nowhere"\n    agent: nonexistent\n---\n'
        ))
        result2 = ValidationResult()
        data2 = validate_agents(github_dir, result2)
        validate_handoffs(data2, github_dir, result2)
        check("handoff to missing agent detected", not result2.is_valid)


    # -- Test: validate_prompts --------------------------------------------------

    print("\n=== validate_prompts ===")

    with tempfile.TemporaryDirectory() as tmp:
        github_dir = Path(tmp) / ".github"
        agents_dir = github_dir / "agents"
        prompts_dir = github_dir / "prompts"
        agents_dir.mkdir(parents=True)
        prompts_dir.mkdir(parents=True)

        create_agent_file(agents_dir, "dev", (
            '---\ndescription: "Dev"\ntools: ["read"]\n---\n'
        ))

        # Valid prompt referencing existing agent
        create_prompt_file(prompts_dir, "start", (
            '---\ndescription: "Start"\nagent: dev\ntools: ["read", "execute"]\n---\n'
        ))

        result = ValidationResult()
        data = validate_agents(github_dir, result)
        validate_prompts(github_dir, data, result)
        check("valid prompt passes", result.is_valid)

        # Prompt referencing non-existent agent
        create_prompt_file(prompts_dir, "broken", (
            '---\ndescription: "Broken"\nagent: nonexistent\n---\n'
        ))
        result2 = ValidationResult()
        data2 = validate_agents(github_dir, result2)
        validate_prompts(github_dir, data2, result2)
        check("prompt with missing agent detected", not result2.is_valid)


    # -- Test: validate_settings -------------------------------------------------

    print("\n=== validate_settings ===")

    with tempfile.TemporaryDirectory() as tmp:
        github_dir = Path(tmp) / ".github"
        github_dir.mkdir(parents=True)

        import json

        # Valid settings
        settings = {
            "github": {"owner": "test", "repo": "test-repo"},
            "project": {"name": "test"},
        }
        (github_dir / "settings.json").write_text(json.dumps(settings))

        result = ValidationResult()
        validate_settings(github_dir, result)
        check("valid settings pass", result.is_valid)

        # Missing required fields
        (github_dir / "settings.json").write_text(json.dumps({"github": {}}))
        result2 = ValidationResult()
        validate_settings(github_dir, result2)
        check("missing fields detected", not result2.is_valid)


    # -- Test: validate_all (integration) ----------------------------------------

    print("\n=== validate_all (real repo) ===")

    # Why: Run against the actual repository to ensure it passes.
    # How: Walk up from this test file to find the repo root.
    repo_root = Path(__file__).resolve().parent.parent.parent
    github_dir = repo_root / ".github"

    if github_dir.is_dir():
        result = validate_all(repo_root)
        check("real repository passes validation", result.is_valid)
        if not result.is_valid:
            print(result.summary())
    else:
        print("  SKIP: Not running from within the repository")


    # -- Summary -----------------------------------------------------------------

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    sys.exit(1 if failed else 0)
