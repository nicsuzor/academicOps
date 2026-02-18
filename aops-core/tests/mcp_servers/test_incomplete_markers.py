#!/usr/bin/env python3
"""Tests for _check_incomplete_markers validation function."""

from mcp_servers.tasks_server import (
    _check_incomplete_markers,
    _format_incomplete_items_error,
)


class TestCheckIncompleteMarkers:
    """Test _check_incomplete_markers function."""

    def test_empty_body_returns_empty_list(self):
        """Empty body should return empty list."""
        assert _check_incomplete_markers("") == []
        assert _check_incomplete_markers(None) == []

    def test_detects_remaining_section(self):
        """Should detect 'Remaining:' section."""
        body = """
Some content here
## Remaining:
- Item 1
- Item 2
"""
        markers = _check_incomplete_markers(body)
        assert any("Remaining" in m for m in markers)

    def test_detects_remaining_work_variant(self):
        """Should detect 'Remaining work:' variant."""
        body = "Remaining work: fix tests"
        markers = _check_incomplete_markers(body)
        assert any("Remaining" in m for m in markers)

    def test_remaining_case_insensitive(self):
        """Should detect 'REMAINING:' (case insensitive)."""
        body = "REMAINING: some stuff"
        markers = _check_incomplete_markers(body)
        assert any("Remaining" in m for m in markers)

    def test_detects_percentage_less_than_100(self):
        """Should detect percentage < 100%."""
        body = "This task is 90% complete"
        markers = _check_incomplete_markers(body)
        assert any("90%" in m for m in markers)

    def test_does_not_trigger_on_100_percent(self):
        """100% complete should NOT trigger."""
        body = "This task is 100% complete"
        markers = _check_incomplete_markers(body)
        pct_markers = [m for m in markers if "complete" in m.lower() and "%" in m]
        assert len(pct_markers) == 0

    def test_detects_unchecked_todo_items(self):
        """Should detect unchecked TODO items."""
        body = """
- [x] Done item
- [ ] Unchecked item 1
- [ ] Unchecked item 2
"""
        markers = _check_incomplete_markers(body)
        assert any("unchecked TODO" in m for m in markers)

    def test_unchecked_todo_shows_count_and_preview(self):
        """Should show count and preview of unchecked items."""
        body = """
- [ ] First item
- [ ] Second item
"""
        markers = _check_incomplete_markers(body)
        todo_marker = [m for m in markers if "unchecked TODO" in m][0]
        assert "2 unchecked TODO items" in todo_marker
        assert "First item" in todo_marker

    def test_detects_wip_marker(self):
        """Should detect WIP marker."""
        body = "This is a WIP implementation"
        markers = _check_incomplete_markers(body)
        assert any("work-in-progress" in m for m in markers)

    def test_detects_work_in_progress_marker(self):
        """Should detect work-in-progress marker."""
        body = "This is a work-in-progress implementation"
        markers = _check_incomplete_markers(body)
        assert any("work-in-progress" in m for m in markers)

    def test_detects_in_progress_marker(self):
        """Should detect 'in progress' marker."""
        body = "Currently in progress"
        markers = _check_incomplete_markers(body)
        assert any("work-in-progress" in m for m in markers)

    def test_clean_body_no_markers(self):
        """Clean body should have no markers."""
        body = """
# Task Complete

All items have been implemented.
- [x] Item 1
- [x] Item 2
"""
        markers = _check_incomplete_markers(body)
        assert markers == []

    def test_multiple_markers_detected(self):
        """Should detect multiple markers in one body."""
        body = """
90% complete

## Remaining:
- [ ] Fix this
- [ ] Fix that

Work in progress
"""
        markers = _check_incomplete_markers(body)
        assert len(markers) >= 3  # percentage, remaining, unchecked, wip


class TestFormatIncompleteItemsError:
    """Test _format_incomplete_items_error function."""

    def test_formats_single_marker(self):
        """Should format single marker correctly."""
        error = _format_incomplete_items_error(["Task shows 90% complete"])
        assert "90% complete" in error
        assert "force=True" in error

    def test_formats_multiple_markers(self):
        """Should format multiple markers with semicolon separator."""
        markers = ["Task shows 90% complete", "Task has 'Remaining' section"]
        error = _format_incomplete_items_error(markers)
        assert "90% complete" in error
        assert "Remaining" in error
        assert ";" in error
