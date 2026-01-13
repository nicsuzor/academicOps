"""Tests for session insights generator library."""

import json
import tempfile
from pathlib import Path

import pytest

from lib.insights_generator import (
    InsightsValidationError,
    extract_json_from_response,
    extract_project_name,
    extract_short_hash,
    generate_fallback_insights,
    get_insights_file_path,
    substitute_prompt_variables,
    validate_insights_schema,
    write_insights_file,
)


class TestPromptVariableSubstitution:
    """Test prompt variable substitution."""

    def test_substitute_all_variables(self):
        """Test substituting all three variables."""
        template = "Session {session_id} on {date} for {project}"
        metadata = {"session_id": "abc123", "date": "2026-01-13", "project": "test"}
        result = substitute_prompt_variables(template, metadata)
        assert result == "Session abc123 on 2026-01-13 for test"

    def test_substitute_repeated_variables(self):
        """Test that repeated variables are all replaced."""
        template = "{session_id} and {session_id} again"
        metadata = {"session_id": "abc123"}
        result = substitute_prompt_variables(template, metadata)
        assert result == "abc123 and abc123 again"

    def test_substitute_with_extra_metadata(self):
        """Test that extra metadata keys don't cause issues."""
        template = "Project: {project}"
        metadata = {"project": "test", "extra_key": "ignored"}
        result = substitute_prompt_variables(template, metadata)
        assert result == "Project: test"


class TestSessionIdExtraction:
    """Test session ID hash extraction."""

    def test_extract_8char_hex(self):
        """Test extracting standard 8-char hex session ID."""
        assert extract_short_hash("a1b2c3d4") == "a1b2c3d4"
        assert extract_short_hash("12345678") == "12345678"

    def test_extract_from_path(self):
        """Test extracting hash from path-like session ID."""
        assert extract_short_hash("/path/to/a1b2c3d4/session") == "a1b2c3d4"
        # Date format "20260113" is also valid hex, so it gets matched first
        assert extract_short_hash("20260113-abcdefgh") == "20260113"
        assert extract_short_hash("project-a1b2c3d4") == "a1b2c3d4"

    def test_extract_from_short_string(self):
        """Test handling short strings."""
        assert extract_short_hash("abc") == "abc"
        assert extract_short_hash("") == ""


class TestSchemaValidation:
    """Test insights schema validation."""

    def test_valid_minimal_insights(self):
        """Test that minimal valid insights pass validation."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test session",
            "outcome": "success",
            "accomplishments": ["task1"],
        }
        validate_insights_schema(insights)  # Should not raise

    def test_valid_full_insights(self):
        """Test that full insights with all fields pass validation."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test session",
            "outcome": "partial",
            "accomplishments": ["task1", "task2"],
            "friction_points": ["issue1"],
            "proposed_changes": ["change1"],
            "workflows_used": ["tdd"],
            "subagents_invoked": ["critic"],
            "subagent_count": 1,
            "custodiet_blocks": 0,
            "stop_reason": "end_turn",
            "critic_verdict": "PROCEED",
            "acceptance_criteria_count": 3,
            "learning_observations": [],
            "skill_compliance": {
                "suggested": ["skill1"],
                "invoked": ["skill1"],
                "compliance_rate": 1.0,
            },
            "context_gaps": [],
            "user_mood": 0.5,
            "conversation_flow": [],
            "user_prompts": [],
        }
        validate_insights_schema(insights)  # Should not raise

    def test_missing_required_field(self):
        """Test that missing required fields raise error."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            # Missing: summary, outcome, accomplishments
        }
        with pytest.raises(
            InsightsValidationError, match="Missing required field: summary"
        ):
            validate_insights_schema(insights)

    def test_invalid_outcome_value(self):
        """Test that invalid outcome values raise error."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test",
            "outcome": "invalid",
            "accomplishments": [],
        }
        with pytest.raises(
            InsightsValidationError, match="outcome.*must be one of.*success"
        ):
            validate_insights_schema(insights)

    def test_invalid_date_format(self):
        """Test that invalid date formats raise error."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "01-13-2026",  # Wrong format
            "project": "test",
            "summary": "Test",
            "outcome": "success",
            "accomplishments": [],
        }
        with pytest.raises(
            InsightsValidationError, match="date.*must be YYYY-MM-DD format"
        ):
            validate_insights_schema(insights)

    def test_invalid_field_type(self):
        """Test that wrong field types raise error."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test",
            "outcome": "success",
            "accomplishments": "not an array",  # Should be list
        }
        with pytest.raises(
            InsightsValidationError, match="accomplishments.*must be list"
        ):
            validate_insights_schema(insights)

    def test_user_mood_out_of_range(self):
        """Test that user_mood outside [-1.0, 1.0] raises error."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test",
            "outcome": "success",
            "accomplishments": [],
            "user_mood": 2.0,  # Out of range
        }
        with pytest.raises(
            InsightsValidationError, match="user_mood.*must be between -1.0 and 1.0"
        ):
            validate_insights_schema(insights)


class TestInsightsFilePath:
    """Test insights file path generation."""

    def test_file_path_format(self):
        """Test that file path follows correct format."""
        path = get_insights_file_path("2026-01-13", "a1b2c3d4")
        assert path.name == "2026-01-13-a1b2c3d4.json"
        assert "sessions/insights" in str(path)

    def test_file_path_uses_aca_data(self, monkeypatch, tmp_path):
        """Test that file path uses ACA_DATA env var."""
        monkeypatch.setenv("ACA_DATA", str(tmp_path))
        path = get_insights_file_path("2026-01-13", "a1b2c3d4")
        assert str(tmp_path) in str(path)
        assert path == tmp_path / "sessions/insights/2026-01-13-a1b2c3d4.json"


class TestWriteInsightsFile:
    """Test atomic file writing."""

    def test_write_valid_insights(self, tmp_path):
        """Test writing valid insights to file."""
        insights = {
            "session_id": "test123",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test",
            "outcome": "success",
            "accomplishments": ["task1"],
        }
        file_path = tmp_path / "test.json"
        write_insights_file(file_path, insights)

        # Verify file exists and content is correct
        assert file_path.exists()
        loaded = json.loads(file_path.read_text())
        assert loaded == insights

    def test_write_creates_parent_dirs(self, tmp_path):
        """Test that write creates parent directories."""
        file_path = tmp_path / "nested" / "dirs" / "insights.json"
        insights = {
            "session_id": "test",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test",
            "outcome": "success",
            "accomplishments": [],
        }
        write_insights_file(file_path, insights)

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_write_overwrites_existing(self, tmp_path):
        """Test that write overwrites existing file."""
        file_path = tmp_path / "test.json"
        file_path.write_text("old content")

        insights = {
            "session_id": "new",
            "date": "2026-01-13",
            "project": "test",
            "summary": "New",
            "outcome": "success",
            "accomplishments": [],
        }
        write_insights_file(file_path, insights)

        loaded = json.loads(file_path.read_text())
        assert loaded["session_id"] == "new"


class TestFallbackInsights:
    """Test fallback insights generation."""

    def test_fallback_has_required_fields(self):
        """Test that fallback insights have all required fields."""
        metadata = {"session_id": "abc", "date": "2026-01-13", "project": "test"}
        operational = {"workflows_used": [], "subagents_invoked": [], "subagent_count": 0}
        fallback = generate_fallback_insights(metadata, operational)

        validate_insights_schema(fallback)  # Should not raise

    def test_fallback_includes_metadata(self):
        """Test that fallback includes provided metadata."""
        metadata = {"session_id": "abc123", "date": "2026-01-13", "project": "myproject"}
        operational = {}
        fallback = generate_fallback_insights(metadata, operational)

        assert fallback["session_id"] == "abc123"
        assert fallback["date"] == "2026-01-13"
        assert fallback["project"] == "myproject"

    def test_fallback_includes_operational_metrics(self):
        """Test that fallback includes operational metrics."""
        metadata = {"session_id": "abc", "date": "2026-01-13", "project": "test"}
        operational = {
            "workflows_used": ["tdd"],
            "subagents_invoked": ["critic", "qa-verifier"],
            "subagent_count": 2,
        }
        fallback = generate_fallback_insights(metadata, operational)

        assert fallback["workflows_used"] == ["tdd"]
        assert fallback["subagents_invoked"] == ["critic", "qa-verifier"]
        assert fallback["subagent_count"] == 2


class TestJsonExtraction:
    """Test JSON extraction from LLM responses."""

    def test_extract_plain_json(self):
        """Test extracting plain JSON without markdown."""
        response = '{"key": "value"}'
        result = extract_json_from_response(response)
        assert result == '{"key": "value"}'

    def test_extract_from_json_fence(self):
        """Test extracting JSON from ```json fence."""
        response = """Some text before
```json
{"key": "value"}
```
Some text after"""
        result = extract_json_from_response(response)
        assert result == '{"key": "value"}'

    def test_extract_from_generic_fence(self):
        """Test extracting from generic ``` fence."""
        response = """```
{"key": "value"}
```"""
        result = extract_json_from_response(response)
        assert result == '{"key": "value"}'

    def test_extract_with_whitespace(self):
        """Test extracting JSON with leading/trailing whitespace."""
        response = """

        {"key": "value"}

        """
        result = extract_json_from_response(response)
        assert result == '{"key": "value"}'
