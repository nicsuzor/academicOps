"""
Tests for session-insights skill outputs.

Verifies the skill writes outputs to correct locations per SKILL.md specification:
- Transcripts: $ACA_DATA/sessions/claude/YYYYMMDD-*-(full|abridged).md
- Daily summaries: $ACA_DATA/sessions/YYYYMMDD-daily.md
- Learning insights: $AOPS/learning/LOG.md + thematic files
"""

import os
import re
from datetime import datetime
from pathlib import Path

import pytest


class TestEnvironment:
    """Test environment is properly configured."""

    def test_environment_configured(self) -> None:
        """Test that ACA_DATA environment variable is set and valid."""
        aca_data = os.environ.get("ACA_DATA")
        assert aca_data, "ACA_DATA environment variable not set"

        data_path = Path(aca_data)
        assert data_path.exists(), f"ACA_DATA directory does not exist: {data_path}"
        assert data_path.is_dir(), f"ACA_DATA is not a directory: {data_path}"


class TestTranscriptOutputs:
    """Test transcript generation outputs (Steps 1-2b of skill)."""

    @pytest.fixture
    def transcript_dir(self) -> Path:
        """Get the transcript output directory."""
        aca_data = os.environ.get("ACA_DATA")
        assert aca_data, "ACA_DATA not set"
        return Path(aca_data) / "sessions" / "claude"

    def test_transcript_output_directory_exists(self, transcript_dir: Path) -> None:
        """Test that transcript output directory exists."""
        assert (
            transcript_dir.exists()
        ), f"Transcript directory missing: {transcript_dir}"
        assert transcript_dir.is_dir(), f"Not a directory: {transcript_dir}"

    def test_transcript_both_variants_exist(self, transcript_dir: Path) -> None:
        """Test that both -full.md and -abridged.md variants exist."""
        full_files = list(transcript_dir.glob("*-full.md"))
        abridged_files = list(transcript_dir.glob("*-abridged.md"))

        assert full_files, f"No -full.md transcripts found in {transcript_dir}"
        assert abridged_files, f"No -abridged.md transcripts found in {transcript_dir}"

    def test_transcript_files_not_empty(self, transcript_dir: Path) -> None:
        """Test that transcript files are not empty."""
        abridged_files = list(transcript_dir.glob("*-abridged.md"))
        assert abridged_files, "No abridged transcripts found"

        # Check at least one is non-empty
        non_empty = [f for f in abridged_files if f.stat().st_size > 0]
        assert non_empty, "All transcript files are empty"

    def test_transcript_naming_convention(self, transcript_dir: Path) -> None:
        """Test transcripts follow YYYYMMDD-*-(full|abridged).md pattern."""
        all_md = list(transcript_dir.glob("*.md"))
        assert all_md, f"No markdown files in {transcript_dir}"

        date_pattern = re.compile(r"^(\d{8})-.*-(full|abridged)\.md$")

        valid_files = []
        for f in all_md:
            match = date_pattern.match(f.name)
            if match:
                date_str = match.group(1)
                try:
                    datetime.strptime(date_str, "%Y%m%d")
                    valid_files.append(f)
                except ValueError:
                    pass

        assert valid_files, "No files match YYYYMMDD-*-(full|abridged).md pattern"

    def test_transcript_has_markdown_structure(self, transcript_dir: Path) -> None:
        """Test that transcripts contain valid markdown structure."""
        abridged_files = sorted(transcript_dir.glob("*-abridged.md"))
        assert abridged_files, "No abridged transcripts found"

        # Use most recent
        most_recent = abridged_files[-1]
        content = most_recent.read_text()

        # Should have YAML frontmatter (starts with ---) OR markdown heading
        starts_valid = content.strip().startswith("---") or content.strip().startswith(
            "#"
        )
        assert (
            starts_valid
        ), f"{most_recent.name} doesn't start with frontmatter or heading"

        # Should contain a markdown heading somewhere
        assert "# " in content, f"{most_recent.name} has no markdown heading"

        # Should have substantial content (not just frontmatter)
        # Strip frontmatter and count remaining lines
        if content.startswith("---"):
            # Find end of frontmatter
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
            else:
                body = content
        else:
            body = content

        lines = [line for line in body.split("\n") if line.strip()]
        assert (
            len(lines) > 5
        ), f"{most_recent.name} has too little content after frontmatter"


class TestDailySummaryOutputs:
    """Test daily summary outputs (Step 3 of skill)."""

    @pytest.fixture
    def sessions_dir(self) -> Path:
        """Get the sessions directory containing daily notes."""
        aca_data = os.environ.get("ACA_DATA")
        assert aca_data, "ACA_DATA not set"
        return Path(aca_data) / "sessions"

    def test_daily_summary_directory_contains_notes(self, sessions_dir: Path) -> None:
        """Test that sessions directory contains daily note files."""
        daily_notes = list(sessions_dir.glob("*-daily.md"))
        assert daily_notes, f"No daily notes (*-daily.md) found in {sessions_dir}"

    def test_daily_summary_naming_convention(self, sessions_dir: Path) -> None:
        """Test daily notes follow YYYYMMDD-daily.md pattern."""
        daily_notes = list(sessions_dir.glob("*-daily.md"))
        assert daily_notes, "No daily notes found"

        date_pattern = re.compile(r"^(\d{8})-daily\.md$")

        valid_notes = []
        for f in daily_notes:
            match = date_pattern.match(f.name)
            if match:
                date_str = match.group(1)
                try:
                    datetime.strptime(date_str, "%Y%m%d")
                    valid_notes.append(f)
                except ValueError:
                    pass

        assert valid_notes, "No files match YYYYMMDD-daily.md pattern"

    def test_daily_summary_has_spec_structure(self, sessions_dir: Path) -> None:
        """Test daily note has structure per SKILL.md spec."""
        daily_notes = sorted(sessions_dir.glob("*-daily.md"))
        assert daily_notes, "No daily notes found"

        # Use most recent
        most_recent = daily_notes[-1]
        content = most_recent.read_text()

        # Check for expected heading (flexible format)
        has_heading = "# Daily Summary" in content or content.strip().startswith("#")
        assert has_heading, f"{most_recent.name} missing daily summary heading"

        # Check for expected sections per current SKILL.md spec
        # Can be any of: Today's Priorities, P0 Tasks, Session Log, or project sections
        expected_sections = [
            "## Today's Priorities",
            "### P0 Tasks",
            "### Pressing",
            "## Session Log",
            "## [[",  # Project section like ## [[academicOps]]
            "## Session Insights",
        ]
        has_section = any(section in content for section in expected_sections)
        assert has_section, (
            f"{most_recent.name} missing expected section header. "
            f"Expected one of: {expected_sections}"
        )

    def test_daily_summary_session_log_table(self, sessions_dir: Path) -> None:
        """Test daily note contains Session Log table with expected columns."""
        daily_notes = sorted(sessions_dir.glob("*-daily.md"))
        assert daily_notes, "No daily notes found"

        # Check a few recent notes for the table
        found_table = False
        for note in daily_notes[-3:]:  # Check last 3
            content = note.read_text()
            if "## Session Log" in content and "| Session |" in content:
                found_table = True
                break

        # Session Log table is optional per spec review, so we just note if present
        if not found_table:
            pytest.skip(
                "Session Log table not found in recent daily notes (optional per spec)"
            )


class TestLearningOutputs:
    """Test learning output routing (Step 6b of skill).

    Note: Per current SKILL.md spec, learning observations are routed to
    bd issues via the /log skill, NOT to local markdown files.
    These tests verify the routing mechanism exists.
    """

    def test_learning_log_skill_exists(self) -> None:
        """Test that learning-log skill exists for routing observations."""
        aops = os.environ.get("AOPS")
        assert aops, "AOPS not set"

        skill_path = Path(aops) / "skills" / "learning-log" / "SKILL.md"
        assert skill_path.exists(), (
            f"learning-log skill not found at {skill_path}. "
            "This skill routes learning observations to bd issues."
        )

    def test_dashboard_sessions_dir_exists(self) -> None:
        """Test that dashboard sessions directory exists for mined JSONs."""
        aca_data = os.environ.get("ACA_DATA")
        assert aca_data, "ACA_DATA not set"

        dashboard_dir = Path(aca_data) / "dashboard" / "sessions"
        # Directory should exist if session-insights has been run
        if not dashboard_dir.exists():
            pytest.skip(
                "Dashboard sessions directory not yet created (run session-insights first)"
            )
