"""
Test session analyzer dashboard state extraction.

Tests for extract_dashboard_state() method which provides data for live dashboard display.
"""

import os
from pathlib import Path


from lib.session_analyzer import SessionAnalyzer


class TestDashboardStateExtraction:
    """Test dashboard state extraction from session files."""

    def test_extract_dashboard_state_returns_required_keys(self) -> None:
        """Test that extract_dashboard_state() returns dict with all required keys.

        Uses real session data from ~/.claude/projects/ to verify
        the method correctly extracts dashboard state information.
        """
        # Find any session file in projects directory
        projects_dir = Path.home() / ".claude" / "projects"
        assert (
            projects_dir.exists()
        ), f"Claude projects directory missing: {projects_dir}"

        session_files = list(projects_dir.rglob("*.jsonl"))
        assert session_files, f"No session files found in {projects_dir}"

        # Use most recent session file
        session_path = max(session_files, key=lambda f: f.stat().st_mtime)

        analyzer = SessionAnalyzer()
        result = analyzer.extract_dashboard_state(session_path)

        assert isinstance(result, dict), "extract_dashboard_state() should return dict"

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

        assert isinstance(result["first_prompt"], str)
        assert isinstance(result["first_prompt_full"], str)
        assert isinstance(result["last_prompt"], str)
        assert isinstance(result["memory_notes"], list)
        assert isinstance(result["in_progress_count"], int)
        assert result["todos"] is None or isinstance(result["todos"], list)


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
