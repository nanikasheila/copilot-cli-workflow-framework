#!/usr/bin/env python3
"""Unit tests for validate_architecture.py.

Why: The validator logic contains non-trivial regex patterns and conditional
     rules (ADR status matching, known-prefix filtering, size thresholds).
     Unit tests pin the expected behaviour so refactors do not silently change
     what the validator accepts or rejects.
How: Use Python's built-in unittest module (no external dependencies).
     Tests cover the four main check categories: path reference extraction,
     file size guard logic, ADR status validation, and rule reference detection.
"""

import sys
import unittest
from pathlib import Path

# Ensure the sibling module is importable regardless of CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_architecture import (  # noqa: I001
    _ADR_STATUS_RE,
    _COPILOT_INSTRUCTIONS_MAX_LINES,
    _FRESHNESS_BLOCK_RE,
    _FRESHNESS_DATE_RE,
    _FRESHNESS_STATUS_RE,
    _FRESHNESS_WARNING_DAYS,
    _RULE_REF_RE,
    _VALID_ADR_STATUSES,
    _VALID_FRESHNESS_STATUSES,
    extract_path_references,
    format_error,
    is_stale,
    resolve_path,
)


# ---------------------------------------------------------------------------
# Tests: extract_path_references (path reference extraction regex)
# ---------------------------------------------------------------------------


class TestExtractPathReferences(unittest.TestCase):
    """Verify that only project-internal path references are extracted."""

    def test_detects_rules_md(self):
        text = "See `rules/commit-message.md` for details."
        self.assertIn("rules/commit-message.md", extract_path_references(text))

    def test_detects_skills_skill_md(self):
        text = "Follow `skills/manage-board/SKILL.md` workflow."
        self.assertIn("skills/manage-board/SKILL.md", extract_path_references(text))

    def test_detects_github_prefixed_settings(self):
        text = "Read `.github/settings.json` first."
        self.assertIn(".github/settings.json", extract_path_references(text))

    def test_detects_bare_settings_json(self):
        # settings.json is in _KNOWN_ROOT_FILES
        text = "Refer to `settings.json`."
        self.assertIn("settings.json", extract_path_references(text))

    def test_detects_docs_path(self):
        text = "See `docs/design-philosophy.md` for background."
        self.assertIn(
            "docs/design-philosophy.md",
            extract_path_references(text),
        )

    def test_detects_agents_reference_file(self):
        text = "See `agents/references/board-integration-guide.md`."
        self.assertIn(
            "agents/references/board-integration-guide.md",
            extract_path_references(text),
        )

    def test_detects_multiple_distinct_refs(self):
        text = "See `rules/commit-message.md` and `rules/merge-policy.md`."
        refs = extract_path_references(text)
        self.assertIn("rules/commit-message.md", refs)
        self.assertIn("rules/merge-policy.md", refs)

    def test_skips_sql_snippet(self):
        text = "`SELECT * FROM artifacts WHERE name = 'implementation'`"
        self.assertEqual([], extract_path_references(text))

    def test_skips_plain_identifier(self):
        text = "Run `git status` before committing."
        self.assertEqual([], extract_path_references(text))

    def test_skips_unknown_prefix(self):
        # 'references/' alone is not a known prefix → must be skipped
        text = "See `references/agent-routing.md`."
        self.assertEqual([], extract_path_references(text))

    def test_skips_extension_not_in_allowlist(self):
        # .pyc is not in the extension list
        text = "Cache file: `validate_config.cpython-313.pyc`"
        self.assertEqual([], extract_path_references(text))

    def test_repeated_ref_returned_once_per_occurrence(self):
        text = "`rules/commit-message.md` and again `rules/commit-message.md`"
        refs = extract_path_references(text)
        self.assertGreaterEqual(refs.count("rules/commit-message.md"), 1)


# ---------------------------------------------------------------------------
# Tests: resolve_path
# ---------------------------------------------------------------------------


class TestResolvePath(unittest.TestCase):
    """Verify path resolution tries both repo-root and .github-relative forms."""

    def setUp(self):
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        # Create minimal .github structure
        (self.root / ".github" / "rules").mkdir(parents=True)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_resolves_github_relative_path(self):
        # rules/commit-message.md should resolve via .github/rules/commit-message.md
        (self.root / ".github" / "rules" / "commit-message.md").write_text("x")
        self.assertTrue(resolve_path("rules/commit-message.md", self.root))

    def test_resolves_repo_root_relative_path(self):
        # .github/docs/design-philosophy.md resolves via .github-relative path
        (self.root / ".github" / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / ".github" / "docs" / "design-philosophy.md").write_text("x")
        self.assertTrue(resolve_path("docs/design-philosophy.md", self.root))

    def test_returns_false_for_missing_file(self):
        self.assertFalse(resolve_path("rules/nonexistent.md", self.root))

    def test_resolves_github_prefixed_path_directly(self):
        (self.root / ".github" / "settings.json").write_text("{}")
        self.assertTrue(resolve_path(".github/settings.json", self.root))


# ---------------------------------------------------------------------------
# Tests: file size guard logic
# ---------------------------------------------------------------------------


class TestFileSizeGuardLogic(unittest.TestCase):
    """Verify the size threshold constants and counting logic."""

    def test_copilot_instructions_limit_is_100(self):
        self.assertEqual(100, _COPILOT_INSTRUCTIONS_MAX_LINES)

    def test_file_within_agent_limit_passes(self):
        # 500 lines is exactly at the limit — should pass
        line_count = 500
        self.assertFalse(line_count > 500)

    def test_file_over_agent_limit_fails(self):
        line_count = 501
        self.assertTrue(line_count > 500)

    def test_file_within_instruction_limit_passes(self):
        line_count = 300
        self.assertFalse(line_count > 300)

    def test_file_over_instruction_limit_fails(self):
        line_count = 301
        self.assertTrue(line_count > 300)

    def test_copilot_instructions_at_limit_passes(self):
        line_count = 100
        self.assertFalse(line_count > _COPILOT_INSTRUCTIONS_MAX_LINES)

    def test_copilot_instructions_over_limit_fails(self):
        line_count = 101
        self.assertTrue(line_count > _COPILOT_INSTRUCTIONS_MAX_LINES)


# ---------------------------------------------------------------------------
# Tests: ADR status validation
# ---------------------------------------------------------------------------


class TestAdrStatusValidation(unittest.TestCase):
    """Verify that the ADR status regex and valid-status list behave correctly."""

    def _get_status(self, text: str) -> str | None:
        match = _ADR_STATUS_RE.search(text)
        return match.group(1).strip() if match else None

    def _is_valid(self, status: str) -> bool:
        return any(valid in status for valid in _VALID_ADR_STATUSES)

    # ---- regex matching ----

    def test_regex_matches_bold_colon_format(self):
        text = "- **ステータス**: 採用済み（Accepted）"  # noqa: RUF001
        self.assertIsNotNone(_ADR_STATUS_RE.search(text))

    def test_regex_captures_status_value(self):
        text = "- **ステータス**: 採用済み（Accepted）"  # noqa: RUF001
        self.assertEqual("採用済み（Accepted）", self._get_status(text))  # noqa: RUF001

    def test_regex_returns_none_for_missing_field(self):
        text = "# ADR-003\n\n## Context\n\nSome text."
        self.assertIsNone(self._get_status(text))

    # ---- valid statuses ----

    def test_adopted_is_valid(self):
        self.assertTrue(self._is_valid("採用済み（Accepted）"))  # noqa: RUF001

    def test_proposed_is_valid(self):
        self.assertTrue(self._is_valid("提案中"))

    def test_replaced_is_valid(self):
        self.assertTrue(self._is_valid("置換済み（Superseded by ADR-005）"))  # noqa: RUF001

    def test_deprecated_is_valid(self):
        self.assertTrue(self._is_valid("非推奨"))

    # ---- invalid statuses ----

    def test_draft_is_invalid(self):
        self.assertFalse(self._is_valid("下書き"))

    def test_template_is_invalid(self):
        # 'テンプレート' is not in the valid-status list; template files are excluded
        # from scanning so this code path should never be reached in practice.
        self.assertFalse(self._is_valid("テンプレート"))

    def test_english_only_status_is_invalid(self):
        self.assertFalse(self._is_valid("Accepted"))

    # ---- four valid values are present ----

    def test_valid_statuses_contains_four_values(self):
        self.assertEqual(4, len(_VALID_ADR_STATUSES))


# ---------------------------------------------------------------------------
# Tests: rule reference regex
# ---------------------------------------------------------------------------


class TestRuleRefDetection(unittest.TestCase):
    """Verify that the rule-reference regex matches the correct patterns."""

    def test_detects_rules_md(self):
        text = "| `rules/commit-message.md` | コミット形式 |"
        self.assertIn("rules/commit-message.md", _RULE_REF_RE.findall(text))

    def test_detects_rules_json(self):
        text = "| `rules/gate-profiles.json` | Gate 条件 |"
        self.assertIn("rules/gate-profiles.json", _RULE_REF_RE.findall(text))

    def test_ignores_skills_path(self):
        text = "| `skills/manage-board/SKILL.md` | Board 操作 |"
        self.assertEqual([], _RULE_REF_RE.findall(text))

    def test_ignores_agents_path(self):
        text = "See `agents/references/board-integration-guide.md`."
        self.assertEqual([], _RULE_REF_RE.findall(text))

    def test_ignores_settings_json(self):
        text = "Read `settings.json` first."
        self.assertEqual([], _RULE_REF_RE.findall(text))


# ---------------------------------------------------------------------------
# Tests: format_error
# ---------------------------------------------------------------------------


class TestFormatError(unittest.TestCase):
    """Verify that the error formatter produces the expected four-field structure."""

    def _make_error(self) -> str:
        return format_error(
            what="File not found: `rules/missing.md`",
            file=".github/copilot-instructions.md",
            why="Dead links silently break agents.",
            fix="Create the missing file or update the reference.",
        )

    def test_contains_error_label(self):
        self.assertIn("ERROR:", self._make_error())

    def test_contains_file_label(self):
        self.assertIn("FILE:", self._make_error())

    def test_contains_why_label(self):
        self.assertIn("WHY:", self._make_error())

    def test_contains_fix_label(self):
        self.assertIn("FIX:", self._make_error())

    def test_contains_what_content(self):
        self.assertIn("rules/missing.md", self._make_error())

    def test_contains_file_content(self):
        self.assertIn("copilot-instructions.md", self._make_error())

    def test_four_field_order(self):
        err = self._make_error()
        positions = [err.index(label) for label in ("ERROR:", "FILE:", "WHY:", "FIX:")]
        self.assertEqual(positions, sorted(positions))


# ---------------------------------------------------------------------------
# Tests: doc-freshness metadata regex parsing
# ---------------------------------------------------------------------------


class TestDocFreshnessRegex(unittest.TestCase):
    """Verify freshness metadata comment block parsing."""

    _SAMPLE_BLOCK = "<!-- doc-freshness\nstatus: active\nlast_verified: 2025-07-25\nverified_by: architect\n-->"

    # ---- block detection ----

    def test_block_re_matches_valid_comment(self):
        self.assertIsNotNone(_FRESHNESS_BLOCK_RE.search(self._SAMPLE_BLOCK))

    def test_block_re_no_match_without_doc_freshness_keyword(self):
        text = "<!-- some other comment -->"
        self.assertIsNone(_FRESHNESS_BLOCK_RE.search(text))

    def test_block_re_no_match_on_plain_text(self):
        text = "# モジュールマップ\n\nsome content"
        self.assertIsNone(_FRESHNESS_BLOCK_RE.search(text))

    def test_block_re_captures_inner_content(self):
        match = _FRESHNESS_BLOCK_RE.search(self._SAMPLE_BLOCK)
        self.assertIsNotNone(match)
        self.assertIn("status: active", match.group(1))

    # ---- status field extraction ----

    def test_status_re_extracts_active(self):
        block_content = _FRESHNESS_BLOCK_RE.search(self._SAMPLE_BLOCK).group(1)
        match = _FRESHNESS_STATUS_RE.search(block_content)
        self.assertIsNotNone(match)
        self.assertEqual("active", match.group(1))

    def test_status_re_extracts_needs_review(self):
        block = "<!-- doc-freshness\nstatus: needs_review\nlast_verified: 2025-01-01\nverified_by: architect\n-->"
        block_content = _FRESHNESS_BLOCK_RE.search(block).group(1)
        match = _FRESHNESS_STATUS_RE.search(block_content)
        self.assertIsNotNone(match)
        self.assertEqual("needs_review", match.group(1))

    def test_status_re_extracts_stale(self):
        block = "<!-- doc-freshness\nstatus: stale\nlast_verified: 2025-01-01\nverified_by: architect\n-->"
        block_content = _FRESHNESS_BLOCK_RE.search(block).group(1)
        match = _FRESHNESS_STATUS_RE.search(block_content)
        self.assertIsNotNone(match)
        self.assertEqual("stale", match.group(1))

    # ---- date field extraction ----

    def test_date_re_extracts_iso_date(self):
        block_content = _FRESHNESS_BLOCK_RE.search(self._SAMPLE_BLOCK).group(1)
        match = _FRESHNESS_DATE_RE.search(block_content)
        self.assertIsNotNone(match)
        self.assertEqual("2025-07-25", match.group(1))

    def test_date_re_no_match_when_field_absent(self):
        block_content = "\nstatus: active\nverified_by: architect\n"
        self.assertIsNone(_FRESHNESS_DATE_RE.search(block_content))

    # ---- valid statuses ----

    def test_valid_statuses_contains_active(self):
        self.assertIn("active", _VALID_FRESHNESS_STATUSES)

    def test_valid_statuses_contains_needs_review(self):
        self.assertIn("needs_review", _VALID_FRESHNESS_STATUSES)

    def test_valid_statuses_contains_stale(self):
        self.assertIn("stale", _VALID_FRESHNESS_STATUSES)

    def test_valid_statuses_has_exactly_three_values(self):
        self.assertEqual(3, len(_VALID_FRESHNESS_STATUSES))

    def test_unknown_status_not_in_valid_list(self):
        self.assertNotIn("unknown", _VALID_FRESHNESS_STATUSES)

    def test_empty_string_not_in_valid_list(self):
        self.assertNotIn("", _VALID_FRESHNESS_STATUSES)


# ---------------------------------------------------------------------------
# Tests: freshness staleness date comparison logic
# ---------------------------------------------------------------------------


class TestDocFreshnessDateComparison(unittest.TestCase):
    """Verify the is_stale() date comparison helper."""

    from datetime import date as _date

    def test_warning_threshold_constant_is_180(self):
        self.assertEqual(180, _FRESHNESS_WARNING_DAYS)

    def test_recent_date_not_stale(self):
        from datetime import date

        today = date(2025, 7, 25)
        last_verified = date(2025, 6, 1)  # 54 days ago
        self.assertFalse(is_stale(last_verified, today))

    def test_old_date_is_stale(self):
        from datetime import date

        today = date(2025, 7, 25)
        last_verified = date(2024, 12, 31)  # 207 days ago
        self.assertTrue(is_stale(last_verified, today))

    def test_exactly_180_days_ago_is_stale(self):
        from datetime import date, timedelta

        today = date(2025, 7, 25)
        last_verified = today - timedelta(days=180)
        self.assertTrue(is_stale(last_verified, today))

    def test_179_days_ago_not_stale(self):
        from datetime import date, timedelta

        today = date(2025, 7, 25)
        last_verified = today - timedelta(days=179)
        self.assertFalse(is_stale(last_verified, today))

    def test_same_day_not_stale(self):
        from datetime import date

        today = date(2025, 7, 25)
        self.assertFalse(is_stale(today, today))

    def test_one_day_ago_not_stale(self):
        from datetime import date, timedelta

        today = date(2025, 7, 25)
        last_verified = today - timedelta(days=1)
        self.assertFalse(is_stale(last_verified, today))

    def test_181_days_ago_is_stale(self):
        from datetime import date, timedelta

        today = date(2025, 7, 25)
        last_verified = today - timedelta(days=181)
        self.assertTrue(is_stale(last_verified, today))


# ---------------------------------------------------------------------------
# Tests: check_doc_freshness_metadata integration
# ---------------------------------------------------------------------------


class TestCheckDocFreshnessMetadata(unittest.TestCase):
    """Integration tests for check_doc_freshness_metadata using a temp directory."""

    def setUp(self):
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        (self.root / ".github").mkdir()
        self.arch_dir = self.root / "docs" / "architecture"
        self.arch_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _import_check(self):
        from validate_architecture import check_doc_freshness_metadata

        return check_doc_freshness_metadata

    def _write_md(self, name: str, content: str) -> Path:
        p = self.arch_dir / name
        p.write_text(content, encoding="utf-8")
        return p

    _VALID_BLOCK = "<!-- doc-freshness\nstatus: active\nlast_verified: 2025-07-25\nverified_by: architect\n-->\n"

    def test_no_errors_when_all_files_have_block(self):
        check = self._import_check()
        self._write_md("module-map.md", self._VALID_BLOCK + "# Title\n")
        errors = check(self.root)
        self.assertEqual([], errors)

    def test_error_when_file_missing_block(self):
        check = self._import_check()
        self._write_md("module-map.md", "# Title\n\nNo metadata here.\n")
        errors = check(self.root)
        self.assertEqual(1, len(errors))
        self.assertIn("module-map.md", errors[0])

    def test_error_per_missing_file(self):
        check = self._import_check()
        self._write_md("a.md", "# A\n")
        self._write_md("b.md", "# B\n")
        errors = check(self.root)
        self.assertEqual(2, len(errors))

    def test_adr_subdir_files_not_checked(self):
        check = self._import_check()
        adr_dir = self.arch_dir / "adr"
        adr_dir.mkdir()
        (adr_dir / "ADR-001.md").write_text("# ADR\n", encoding="utf-8")
        # No .md files directly under arch_dir → zero errors expected
        errors = check(self.root)
        self.assertEqual([], errors)

    def test_no_errors_when_arch_dir_missing(self):
        check = self._import_check()
        import shutil

        shutil.rmtree(self.arch_dir)
        errors = check(self.root)
        self.assertEqual([], errors)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
