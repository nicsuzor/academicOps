"""
Test session analyzer dashboard state extraction.

Tests for extract_dashboard_state() method which provides data for live dashboard display.
Uses real session data from ~/.claude/projects/ to validate extraction logic.
"""

import os
from datetime import date
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
        - memory_notes: List of created knowledge base notes
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
            "memory_notes",
            "in_progress_count",
        ]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

        # Basic type validation
        assert isinstance(result["first_prompt"], str)
        assert isinstance(result["first_prompt_full"], str)
        assert isinstance(result["last_prompt"], str)
        assert isinstance(result["memory_notes"], list)
        assert isinstance(result["in_progress_count"], int)
        # todos can be None or list
        assert result["todos"] is None or isinstance(result["todos"], list)


class TestReadDailyNote:
    """Test reading and parsing daily note files."""

    def test_read_daily_note_returns_structured_data(self) -> None:
        """Test that read_daily_note() parses today's daily note file.

        Daily notes are stored at $ACA_DATA/sessions/YYYYMMDD-daily.md
        Format is markdown with frontmatter (title, type, date) and session summaries.

        This test uses a REAL daily note file that exists in the data directory.
        The function does NOT exist yet, so this test WILL FAIL.

        Expected structure:
        - date: Date of the daily note
        - title: Title from frontmatter
        - sessions: List of session summaries
        - Each session has: session_id, project, duration, accomplishments, decisions, topics, blockers
        """
        # Get data directory from environment (fail-fast if not set)
        aca_data = os.environ.get("ACA_DATA")
        if not aca_data:
            pytest.skip("ACA_DATA environment variable not set")

        data_path = Path(aca_data)
        if not data_path.exists():
            pytest.skip(f"ACA_DATA directory does not exist: {data_path}")

        # Check for today's daily note
        today_str = date.today().strftime("%Y%m%d")
        daily_note_path = data_path / "sessions" / f"{today_str}-daily.md"

        if not daily_note_path.exists():
            pytest.skip(f"Today's daily note does not exist: {daily_note_path}")

        # Initialize analyzer
        analyzer = SessionAnalyzer()

        # Call read_daily_note() - should fail with AttributeError
        result = analyzer.read_daily_note()

        # Verify return type is not None (found the file)
        assert result is not None, "read_daily_note() should return data for today's note"

        # Verify has required attributes/keys
        assert hasattr(result, "date") or "date" in result, "Missing 'date' field"
        assert hasattr(result, "title") or "title" in result, "Missing 'title' field"
        assert hasattr(result, "sessions") or "sessions" in result, "Missing 'sessions' field"

        # Verify sessions is a list
        sessions = result.sessions if hasattr(result, "sessions") else result["sessions"]
        assert isinstance(sessions, list), "sessions should be a list"
        assert len(sessions) > 0, "Expected at least one session in today's daily note"

        # Verify first session has expected structure
        first_session = sessions[0]
        expected_fields = ["session_id", "project", "accomplishments", "decisions", "topics", "blockers"]
        for field in expected_fields:
            assert (
                hasattr(first_session, field) or field in first_session
            ), f"Session missing expected field: {field}"
