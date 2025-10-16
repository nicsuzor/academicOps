#!/usr/bin/env python3
"""Test validation rules for tool usage and file locations.

Tests both the PreToolUse hook (validate_tool.py) and code review rules (code_review.py).
"""

from pathlib import Path

from bot.scripts.code_review import TestFileLocationRule


class TestFileLocationValidation:
    """Test that test files must be in proper locations."""

    def test_tmp_test_files_blocked(self):
        """Test files in /tmp should be blocked."""
        rule = TestFileLocationRule()
        violations = rule.check(Path("/tmp/test_foo.py"), "")

        assert len(violations) == 1
        assert violations[0].rule == "no-tmp-tests"
        assert "axiom #5" in violations[0].message

    def test_proper_location_allowed(self):
        """Test files in projects/*/tests/ should be allowed."""
        rule = TestFileLocationRule()
        violations = rule.check(Path("projects/buttermilk/tests/test_foo.py"), "")

        assert len(violations) == 0

    def test_non_tests_directory_blocked(self):
        """Test files outside tests/ directories should be blocked."""
        rule = TestFileLocationRule()
        violations = rule.check(Path("projects/buttermilk/test_foo.py"), "")

        assert len(violations) == 1
        assert violations[0].rule == "tests-in-tests-dir"
        assert "tests/ directory" in violations[0].message

    def test_bot_tests_allowed(self):
        """Framework tests in bot/tests/ should be allowed."""
        rule = TestFileLocationRule()
        violations = rule.check(Path("bot/tests/test_validation.py"), "")

        assert len(violations) == 0

    def test_non_test_files_ignored(self):
        """Non-test files should not be checked."""
        rule = TestFileLocationRule()

        # /tmp Python file without "test" in name
        violations = rule.check(Path("/tmp/script.py"), "")
        assert len(violations) == 0

        # Regular source file
        violations = rule.check(Path("projects/buttermilk/src/config.py"), "")
        assert len(violations) == 0
