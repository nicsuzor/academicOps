"""
Test session analyzer dashboard state extraction.

Tests for extract_dashboard_state() method which provides data for live dashboard display.
Uses real session data from ~/.claude/projects/ to validate extraction logic.
"""

from pathlib import Path

import pytest

from lib.session_analyzer import SessionAnalyzer


class TestDashboardStateExtraction:
    """Test dashboard state extraction from session files."""

    def test_extract_dashboard_state_returns_required_keys(self) -> None:
        """Test that extract_dashboard_state() returns dict with all required keys.

        This test uses REAL session data from ~/.claude/projects/ to verify
        the method correctly extracts dashboard state information.

        Expected keys:
        - first_prompt: Truncated first user message
        - first_prompt_full: Complete first user message
        - last_prompt: Most recent user message
        - todos: Current TODO list state
        - bmem_notes: List of created knowledge base notes
        - in_progress_count: Count of in-progress todos
        """
        # Find a real session file
        session_path = Path.home() / ".claude" / "projects" / "-Users-suzor-writing-academicOps" / "e9278972-de74-40e4-a169-d22f333f0f01.jsonl"

        if not session_path.exists():
            pytest.skip(f"Test session file not found: {session_path}")

        # Initialize analyzer
        analyzer = SessionAnalyzer()

        # Call the method (should fail with AttributeError)
        result = analyzer.extract_dashboard_state(session_path)

        # Verify return type
        assert isinstance(result, dict), "extract_dashboard_state() should return dict"

        # Verify required keys exist
        required_keys = [
            "first_prompt",
            "first_prompt_full",
            "last_prompt",
            "todos",
            "bmem_notes",
            "in_progress_count",
        ]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

        # Basic type validation
        assert isinstance(result["first_prompt"], str)
        assert isinstance(result["first_prompt_full"], str)
        assert isinstance(result["last_prompt"], str)
        assert isinstance(result["bmem_notes"], list)
        assert isinstance(result["in_progress_count"], int)
        # todos can be None or list
        assert result["todos"] is None or isinstance(result["todos"], list)
