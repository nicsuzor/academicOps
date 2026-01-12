"""
Test session analyzer dashboard state extraction.

Tests for extract_dashboard_state() method which provides data for live dashboard display.
"""

import os
from pathlib import Path


from lib.session_analyzer import SessionAnalyzer


class TestParseDailyLog:
    """Test parsing daily log files (new format with priority sections)."""

    def test_parse_daily_log_returns_structured_data(self) -> None:
        """Test that parse_daily_log() parses a daily note file.

        Daily notes are stored at $ACA_DATA/sessions/YYYYMMDD-daily.md
        New format uses priority sections (## PRIMARY:, etc.) with task checklists.
        """
        aca_data = os.environ.get("ACA_DATA")
        assert aca_data, "ACA_DATA environment variable not set"

        data_path = Path(aca_data)
        assert data_path.exists(), f"ACA_DATA directory does not exist: {data_path}"

        # Find any daily note (not necessarily today's)
        daily_notes = sorted(data_path.glob("sessions/*-daily.md"))
        assert daily_notes, f"No daily notes found in {data_path}/sessions/"

        # Use most recent daily note
        most_recent = daily_notes[-1]
        date_str = most_recent.stem.replace("-daily", "")

        analyzer = SessionAnalyzer()
        result = analyzer.parse_daily_log(date_str)

        assert result is not None, f"parse_daily_log({date_str}) should return data"

        # Check expected keys from parse_daily_log()
        expected_keys = [
            "primary_title",
            "primary_link",
            "next_action",
            "incomplete",
            "completed",
            "blockers",
            "outcomes",
            "progress",
        ]
        for key in expected_keys:
            assert key in result, f"Missing expected key: {key}"

        # Verify types
        assert result["incomplete"] is None or isinstance(result["incomplete"], list)
        assert result["completed"] is None or isinstance(result["completed"], list)
        assert isinstance(result["progress"], tuple)
        assert len(result["progress"]) == 2

        # A valid daily note should have at least some tasks
        total_tasks = len(result["incomplete"]) + len(result["completed"])
        assert total_tasks > 0, f"Expected at least one task in {most_recent.name}"
