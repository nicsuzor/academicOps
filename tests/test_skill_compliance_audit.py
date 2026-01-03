"""
Tests for skill compliance audit script.

Uses real captured transcripts as test fixtures (per H33: Real Data Fixtures).
"""

import pytest
from pathlib import Path

# Import will be created
from scripts.audit_skill_compliance import (
    TurnAnalysis,
    parse_transcript,
    calculate_compliance,
)

FIXTURES_DIR = Path(__file__).parent / "data"


class TestParseTranscript:
    """Test transcript parsing extracts skill suggestions and invocations."""

    def test_extracts_skills_matched_single(self):
        """Parse 'Skills matched: `framework`' pattern."""
        transcript = FIXTURES_DIR / "sample_transcript_1.md"
        turns = parse_transcript(transcript)

        # Transcript 1 has 3 turns with skill suggestions
        assert len(turns) >= 3

        # First turn should have framework and bmem
        turn_with_bmem = [t for t in turns if "bmem" in t.skills_suggested]
        assert len(turn_with_bmem) == 1
        assert "framework" in turn_with_bmem[0].skills_suggested
        assert "bmem" in turn_with_bmem[0].skills_suggested

    def test_extracts_skills_matched_multiple(self):
        """Parse 'Skills matched: `framework`, `python-dev`' pattern."""
        transcript = FIXTURES_DIR / "sample_transcript_2.md"
        turns = parse_transcript(transcript)

        # Find turn with both framework and python-dev
        multi_skill_turns = [
            t for t in turns
            if "framework" in t.skills_suggested and "python-dev" in t.skills_suggested
        ]
        assert len(multi_skill_turns) >= 1

    def test_extracts_skill_invoked(self):
        """Parse '🔧 Skill invoked: `learning-log`' pattern."""
        transcript = FIXTURES_DIR / "sample_transcript_2.md"
        turns = parse_transcript(transcript)

        # Find turns with skill invocations
        invoked_turns = [t for t in turns if t.skills_invoked]
        assert len(invoked_turns) >= 1
        assert "learning-log" in invoked_turns[0].skills_invoked

    def test_no_skill_suggestions_returns_empty(self):
        """Transcript without skill patterns returns empty list."""
        # Create a minimal transcript without skill patterns
        content = """---
title: Minimal Session
---

# Session

### User (Turn 1)
Hello

### Agent (Turn 1)
Hi there!
"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            turns = parse_transcript(temp_path)
            assert len(turns) == 0
        finally:
            temp_path.unlink()


class TestComplianceCalculation:
    """Test compliance rate calculation."""

    def test_compliance_when_skill_followed(self):
        """Compliance is True when suggested skill was invoked."""
        turn = TurnAnalysis(
            turn_number=1,
            skills_suggested=["framework"],
            skills_invoked=["framework"],
            followed=True,
            commands_suggested=[],
        )
        assert turn.followed is True

    def test_compliance_when_different_skill_invoked(self):
        """Compliance is False when different skill invoked."""
        turn = TurnAnalysis(
            turn_number=1,
            skills_suggested=["framework"],
            skills_invoked=["learning-log"],
            followed=False,
            commands_suggested=[],
        )
        assert turn.followed is False

    def test_compliance_when_no_skill_invoked(self):
        """Compliance is False when no skill invoked but one was suggested."""
        turn = TurnAnalysis(
            turn_number=1,
            skills_suggested=["framework"],
            skills_invoked=[],
            followed=False,
            commands_suggested=[],
        )
        assert turn.followed is False

    def test_calculate_compliance_rate(self):
        """Calculate overall compliance percentage."""
        turns = [
            TurnAnalysis(1, ["framework"], ["framework"], True, []),
            TurnAnalysis(2, ["framework"], ["learning-log"], False, []),
            TurnAnalysis(3, ["python-dev"], ["python-dev"], True, []),
            TurnAnalysis(4, ["framework"], [], False, []),
        ]
        result = calculate_compliance(turns)

        assert result["total_turns"] == 4
        assert result["compliant_turns"] == 2
        assert result["compliance_rate"] == 0.5  # 50%

    def test_calculate_compliance_by_skill(self):
        """Calculate compliance rate per suggested skill."""
        turns = [
            TurnAnalysis(1, ["framework"], ["framework"], True, []),
            TurnAnalysis(2, ["framework"], [], False, []),
            TurnAnalysis(3, ["python-dev"], ["python-dev"], True, []),
        ]
        result = calculate_compliance(turns)

        assert result["by_skill"]["framework"]["total"] == 2
        assert result["by_skill"]["framework"]["compliant"] == 1
        assert result["by_skill"]["python-dev"]["total"] == 1
        assert result["by_skill"]["python-dev"]["compliant"] == 1

    def test_tracks_command_suggestions(self):
        """Track commands as router quality issues."""
        turns = [
            TurnAnalysis(1, ["framework"], [], False, ["/meta", "/log"]),
            TurnAnalysis(2, ["python-dev"], [], False, ["/meta"]),
        ]
        result = calculate_compliance(turns)

        assert result["total_command_suggestions"] == 3
        assert result["command_suggestions"]["/meta"] == 2
        assert result["command_suggestions"]["/log"] == 1


class TestEndToEnd:
    """End-to-end tests on real transcript fixtures."""

    def test_sample_transcript_1_parsing(self):
        """Parse sample_transcript_1 and verify expected results."""
        transcript = FIXTURES_DIR / "sample_transcript_1.md"
        turns = parse_transcript(transcript)

        # Known from manual inspection: 3 turns with skill suggestions, 0 invocations
        assert len(turns) == 3

        # All turns suggest framework
        for turn in turns:
            assert "framework" in turn.skills_suggested

        # No skills were invoked in this transcript
        for turn in turns:
            assert turn.skills_invoked == []
            assert turn.followed is False

    def test_sample_transcript_2_parsing(self):
        """Parse sample_transcript_2 and verify expected results."""
        transcript = FIXTURES_DIR / "sample_transcript_2.md"
        turns = parse_transcript(transcript)

        # Known from grep count: 13 turns with skill suggestions, 1 invocation
        assert len(turns) == 13

        # Find the turn with learning-log invocation
        invoked = [t for t in turns if "learning-log" in t.skills_invoked]
        assert len(invoked) == 1

        # That turn suggested framework but invoked learning-log (mismatch)
        assert "framework" in invoked[0].skills_suggested
        assert invoked[0].followed is False  # learning-log != framework
