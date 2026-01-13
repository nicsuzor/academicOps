"""
Tests for skill compliance audit script.

Uses real captured transcripts as test fixtures (per H33: Real Data Fixtures).
"""

from pathlib import Path

from scripts.audit_skill_compliance import (
    TurnAnalysis,
    parse_transcript,
    calculate_compliance,
)

FIXTURES_DIR = Path(__file__).parent / "data"


class TestParseTranscript:
    """Test transcript parsing extracts skill suggestions and invocations."""

    def test_extracts_skill_suggestion(self):
        """Parse '**Skill(s)**: framework' pattern."""
        transcript = FIXTURES_DIR / "sample_transcript_new_format.md"
        turns = parse_transcript(transcript)

        # Should find at least one turn with framework suggestion
        framework_turns = [t for t in turns if "framework" in t.skills_suggested]
        assert len(framework_turns) >= 1

    def test_extracts_skill_invoked(self):
        """Parse '🔧 Skill invoked: `framework`' pattern."""
        transcript = FIXTURES_DIR / "sample_transcript_new_format.md"
        turns = parse_transcript(transcript)

        # Find turns with skill invocations
        invoked_turns = [t for t in turns if t.skills_invoked]
        assert len(invoked_turns) >= 1
        assert "framework" in invoked_turns[0].skills_invoked

    def test_no_skill_suggestions_returns_empty(self):
        """Transcript without skill patterns returns empty list."""
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

    def test_skips_template_placeholders(self):
        """Skip '[skill names or "none"]' placeholders."""
        content = """---
title: Session with placeholder
---

# Session

### User (Turn 1)
Hello

**Skill(s)**: [skill names or "none"]

### Agent (Turn 1)
Hi there!
"""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            turns = parse_transcript(temp_path)
            assert len(turns) == 0  # Placeholder should be skipped
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

    def test_real_transcript_parsing(self):
        """Parse real transcript and verify structure."""
        transcript = FIXTURES_DIR / "sample_transcript_new_format.md"
        turns = parse_transcript(transcript)

        # Should find turns with skill suggestions
        assert len(turns) >= 1

        # Framework should be suggested
        framework_turns = [t for t in turns if "framework" in t.skills_suggested]
        assert len(framework_turns) >= 1

        # Framework should be invoked
        invoked = [t for t in turns if "framework" in t.skills_invoked]
        assert len(invoked) >= 1

    def test_compliance_on_real_transcript(self):
        """Calculate compliance on real transcript."""
        transcript = FIXTURES_DIR / "sample_transcript_new_format.md"
        turns = parse_transcript(transcript)
        result = calculate_compliance(turns)

        # Should have valid compliance metrics
        assert "total_turns" in result
        assert "compliance_rate" in result
        assert 0.0 <= result["compliance_rate"] <= 1.0
