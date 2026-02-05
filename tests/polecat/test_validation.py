#!/usr/bin/env python3
"""Tests for polecat task ID validation.

Tests both the validate_task_id() function and validate_task_id_or_raise().
Covers valid formats, invalid formats, and security-relevant edge cases.
"""

import sys
from pathlib import Path

import pytest

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from validation import (
    TaskIDValidationError,
    validate_task_id,
    validate_task_id_or_raise,
    MAX_TASK_ID_LENGTH,
)


class TestValidTaskIDs:
    """Tests for task IDs that should be accepted."""

    def test_new_format_aops_project(self):
        """New format: aops-<hash8>"""
        assert validate_task_id("aops-5056bc83") is True
        assert validate_task_id_or_raise("aops-5056bc83") == "aops-5056bc83"

    def test_new_format_ns_project(self):
        """New format: ns-<hash8> (no-project namespace)"""
        assert validate_task_id("ns-eb5a092a") is True
        assert validate_task_id_or_raise("ns-eb5a092a") == "ns-eb5a092a"

    def test_new_format_framework_project(self):
        """New format with framework project prefix"""
        assert validate_task_id("framework-47178eaa") is True

    def test_legacy_date_format(self):
        """Legacy format: YYYYMMDD-slug"""
        assert validate_task_id("20260119-my-task") is True
        assert validate_task_id("20260112-write-book") is True

    def test_simple_slug(self):
        """Simple slug format for permalinks"""
        assert validate_task_id("my-task-id") is True
        assert validate_task_id("simple") is True

    def test_underscores_allowed(self):
        """Underscores are allowed in task IDs"""
        assert validate_task_id("my_task_id") is True
        assert validate_task_id("ns-task_with_underscore") is True

    def test_single_character(self):
        """Single alphanumeric character is valid (minimum length)"""
        assert validate_task_id("a") is False  # Too short (min is 2)
        assert validate_task_id("ab") is True  # Minimum valid

    def test_numbers_only(self):
        """Numbers-only IDs are valid"""
        assert validate_task_id("12345678") is True

    def test_mixed_case_normalized(self):
        """Mixed case is accepted (normalized to lowercase for validation)"""
        # The function accepts mixed case but validates against lowercase pattern
        assert validate_task_id("Aops-5056BC83") is True


class TestInvalidTaskIDs:
    """Tests for task IDs that should be rejected."""

    def test_path_traversal_double_dot(self):
        """Path traversal with .. should be rejected"""
        assert validate_task_id("../etc/passwd") is False
        assert validate_task_id("task/../escape") is False
        assert validate_task_id("..") is False

    def test_path_traversal_slash(self):
        """Forward slashes should be rejected"""
        assert validate_task_id("task/subtask") is False
        assert validate_task_id("/etc/passwd") is False

    def test_path_traversal_backslash(self):
        """Backslashes should be rejected"""
        assert validate_task_id("task\\subtask") is False
        assert validate_task_id("..\\..\\etc") is False

    def test_git_reflog_syntax(self):
        """Git reflog syntax @{ should be rejected"""
        assert validate_task_id("task@{0}") is False
        assert validate_task_id("HEAD@{1}") is False

    def test_null_byte(self):
        """Null bytes should be rejected"""
        assert validate_task_id("task\x00id") is False

    def test_newline(self):
        """Newlines should be rejected (command injection)"""
        assert validate_task_id("task\nid") is False
        assert validate_task_id("task\rid") is False

    def test_spaces(self):
        """Spaces should be rejected"""
        assert validate_task_id("task id") is False
        assert validate_task_id(" task") is False
        assert validate_task_id("task ") is False

    def test_git_special_refs(self):
        """Git special refs should be rejected"""
        assert validate_task_id("HEAD") is False
        assert validate_task_id("head") is False
        assert validate_task_id("FETCH_HEAD") is False
        assert validate_task_id("main") is False
        assert validate_task_id("master") is False
        assert validate_task_id("origin") is False

    def test_empty_string(self):
        """Empty string should be rejected"""
        assert validate_task_id("") is False

    def test_too_short(self):
        """Single character should be rejected (too short)"""
        assert validate_task_id("a") is False

    def test_too_long(self):
        """Extremely long strings should be rejected"""
        long_id = "a" * (MAX_TASK_ID_LENGTH + 1)
        assert validate_task_id(long_id) is False

    def test_special_characters(self):
        """Special characters should be rejected"""
        assert validate_task_id("task@special") is False
        assert validate_task_id("task#id") is False
        assert validate_task_id("task$id") is False
        assert validate_task_id("task%id") is False
        assert validate_task_id("task&id") is False
        assert validate_task_id("task*id") is False

    def test_starts_with_hyphen(self):
        """IDs starting with hyphen should be rejected"""
        assert validate_task_id("-task") is False

    def test_ends_with_hyphen(self):
        """IDs ending with hyphen should be rejected"""
        assert validate_task_id("task-") is False

    def test_starts_with_underscore(self):
        """IDs starting with underscore should be rejected"""
        assert validate_task_id("_task") is False

    def test_ends_with_underscore(self):
        """IDs ending with underscore should be rejected"""
        assert validate_task_id("task_") is False


class TestValidateOrRaise:
    """Tests for the validate_task_id_or_raise function."""

    def test_returns_valid_id(self):
        """Should return the ID unchanged if valid"""
        result = validate_task_id_or_raise("aops-5056bc83")
        assert result == "aops-5056bc83"

    def test_raises_on_invalid(self):
        """Should raise TaskIDValidationError on invalid ID"""
        with pytest.raises(TaskIDValidationError) as exc_info:
            validate_task_id_or_raise("../escape")
        assert "forbidden pattern" in str(exc_info.value)
        assert exc_info.value.task_id == "../escape"

    def test_raises_on_empty(self):
        """Should raise on empty string"""
        with pytest.raises(TaskIDValidationError) as exc_info:
            validate_task_id_or_raise("")
        assert "too short" in str(exc_info.value)

    def test_raises_on_none(self):
        """Should raise on None input"""
        with pytest.raises(TaskIDValidationError) as exc_info:
            validate_task_id_or_raise(None)
        assert "must be a string" in str(exc_info.value)

    def test_raises_on_non_string(self):
        """Should raise on non-string input"""
        with pytest.raises(TaskIDValidationError):
            validate_task_id_or_raise(12345)
        with pytest.raises(TaskIDValidationError):
            validate_task_id_or_raise(["task-id"])

    def test_error_message_truncated(self):
        """Error messages should truncate very long task IDs"""
        long_id = "x" * 200
        with pytest.raises(TaskIDValidationError) as exc_info:
            validate_task_id_or_raise(long_id)
        # The displayed ID should be truncated to 50 chars
        error_str = str(exc_info.value)
        assert len(error_str) < 200  # Should be much shorter than the input

    def test_git_special_ref_error_message(self):
        """Git special refs should have specific error message"""
        with pytest.raises(TaskIDValidationError) as exc_info:
            validate_task_id_or_raise("HEAD")
        assert "git special ref" in str(exc_info.value)


class TestEdgeCases:
    """Edge cases and security-focused tests."""

    def test_unicode_lookalikes_rejected(self):
        """Unicode lookalikes should be rejected (only ASCII alphanumeric allowed)"""
        # Cyrillic 'а' looks like Latin 'a'
        assert validate_task_id("tаsk") is False  # Contains Cyrillic 'а'

    def test_boundary_length_valid(self):
        """Exactly at min/max length should be valid"""
        min_id = "ab"  # MIN_TASK_ID_LENGTH = 2
        max_id = "a" * MAX_TASK_ID_LENGTH
        assert validate_task_id(min_id) is True
        assert validate_task_id(max_id) is True

    def test_consecutive_hyphens_allowed(self):
        """Consecutive hyphens are allowed (they're not ..)"""
        assert validate_task_id("task--id") is True

    def test_real_world_task_ids(self):
        """Test actual task IDs from production"""
        real_ids = [
            "aops-5056bc83",
            "ns-eb5a092a",
            "framework-47178eaa",
            "aops-dedb6e95",
            "aops-4188eb66",
            "ns-89679868",
        ]
        for task_id in real_ids:
            assert validate_task_id(task_id) is True, f"Failed for {task_id}"
