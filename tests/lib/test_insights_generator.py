"""Tests for session insights generator library."""

import json

import pytest

from lib.insights_generator import (
    InsightsValidationError,
    extract_json_from_response,
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
            InsightsValidationError, match="date.*must be ISO 8601 format"
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

    def test_valid_with_bead_tracking(self):
        """Test that insights with bead tracking fields pass validation."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test session",
            "outcome": "success",
            "accomplishments": ["task1"],
            "current_bead_id": "aops-kdl0",
            "worker_name": "Claude Opus 4.5",
        }
        validate_insights_schema(insights)  # Should not raise

    def test_bead_tracking_fields_accept_null(self):
        """Test that bead tracking fields accept null values."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test session",
            "outcome": "success",
            "accomplishments": [],
            "current_bead_id": None,
            "worker_name": None,
        }
        validate_insights_schema(insights)  # Should not raise

    def test_current_bead_id_type_validation(self):
        """Test that current_bead_id must be string or null."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test",
            "outcome": "success",
            "accomplishments": [],
            "current_bead_id": 123,  # Should be string
        }
        with pytest.raises(
            InsightsValidationError, match="current_bead_id.*must be a string or null"
        ):
            validate_insights_schema(insights)

    def test_worker_name_type_validation(self):
        """Test that worker_name must be string or null."""
        insights = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test",
            "outcome": "success",
            "accomplishments": [],
            "worker_name": ["list", "not", "string"],  # Should be string
        }
        with pytest.raises(
            InsightsValidationError, match="worker_name.*must be a string or null"
        ):
            validate_insights_schema(insights)


class TestInsightsFilePath:
    """Test insights file path generation."""

    def test_file_path_format_without_project(self):
        """Test that file path follows correct format without project."""
        path = get_insights_file_path("2026-01-13", "a1b2c3d4", hour="09")
        # Without project: YYYYMMDD-HH-session_id.json
        assert path.name == "20260113-09-a1b2c3d4.json"
        assert str(path).endswith("sessions/summaries/20260113-09-a1b2c3d4.json")

    def test_file_path_format_with_project(self):
        """Test that file path includes project name when provided."""
        path = get_insights_file_path(
            "2026-01-13", "a1b2c3d4", project="writing", hour="14"
        )
        # With project: YYYYMMDD-HH-project-session_id.json
        assert path.name == "20260113-14-writing-a1b2c3d4.json"
        assert str(path).endswith(
            "sessions/summaries/20260113-14-writing-a1b2c3d4.json"
        )

    def test_file_path_format_with_project_and_slug(self):
        """Test that file path includes project and slug."""
        path = get_insights_file_path(
            "2026-01-13", "a1b2c3d4", slug="review", project="aops", hour="17"
        )
        # With project and slug: YYYYMMDD-HH-project-session_id-slug.json
        assert path.name == "20260113-17-aops-a1b2c3d4-review.json"

    def test_file_path_sanitizes_project_name(self):
        """Test that project name is sanitized for filesystem safety."""
        path = get_insights_file_path(
            "2026-01-13", "a1b2c3d4", project="My Project!", hour="23"
        )
        # Special chars removed, lowercase
        assert path.name == "20260113-23-my-project-a1b2c3d4.json"

    def test_file_path_uses_centralized_location(self):
        """Test that file path uses centralized ~/writing/sessions/summaries/ location."""
        path = get_insights_file_path(
            "2026-01-13", "a1b2c3d4", project="test", hour="08"
        )
        # Centralized location, no env var dependency
        assert "writing/sessions/summaries" in str(path)

    def test_file_path_extracts_hour_from_iso8601(self):
        """Test that hour is extracted from ISO 8601 date format."""
        path = get_insights_file_path(
            "2026-01-13T15:30:00+10:00", "a1b2c3d4", project="test"
        )
        # Hour extracted from ISO 8601 timestamp
        assert path.name == "20260113-15-test-a1b2c3d4.json"


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
        operational = {
            "workflows_used": [],
            "subagents_invoked": [],
            "subagent_count": 0,
        }
        fallback = generate_fallback_insights(metadata, operational)

        validate_insights_schema(fallback)  # Should not raise

    def test_fallback_includes_metadata(self):
        """Test that fallback includes provided metadata."""
        metadata = {
            "session_id": "abc123",
            "date": "2026-01-13",
            "project": "myproject",
        }
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


class TestTokenMetricsValidation:
    """Test token_metrics field validation."""

    def _minimal_insights(self, **extra):
        """Create minimal valid insights with optional extra fields."""
        base = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test session",
            "outcome": "success",
            "accomplishments": [],
        }
        base.update(extra)
        return base

    def test_valid_token_metrics_full(self):
        """Test that full token_metrics structure passes validation."""
        insights = self._minimal_insights(
            token_metrics={
                "totals": {
                    "input_tokens": 45000,
                    "output_tokens": 12000,
                    "cache_read_tokens": 30000,
                    "cache_create_tokens": 5000,
                },
                "by_model": {
                    "claude-opus-4-5-20251101": {"input": 40000, "output": 10000},
                    "claude-3-5-haiku-20241022": {"input": 5000, "output": 2000},
                },
                "by_agent": {
                    "main": {"input": 35000, "output": 8000},
                    "prompt-hydrator": {"input": 3000, "output": 1000},
                },
                "efficiency": {
                    "cache_hit_rate": 0.67,
                    "tokens_per_minute": 2500,
                    "session_duration_minutes": 23,
                },
            }
        )
        validate_insights_schema(insights)  # Should not raise

    def test_valid_token_metrics_partial(self):
        """Test that partial token_metrics (only some sub-objects) passes."""
        insights = self._minimal_insights(
            token_metrics={
                "totals": {"input_tokens": 1000, "output_tokens": 500},
            }
        )
        validate_insights_schema(insights)  # Should not raise

    def test_token_metrics_accepts_null(self):
        """Test that token_metrics accepts null value."""
        insights = self._minimal_insights(token_metrics=None)
        validate_insights_schema(insights)  # Should not raise

    def test_token_metrics_must_be_dict(self):
        """Test that token_metrics must be a dict if present."""
        insights = self._minimal_insights(token_metrics="not a dict")
        with pytest.raises(
            InsightsValidationError, match="token_metrics.*must be a dict"
        ):
            validate_insights_schema(insights)

    def test_token_metrics_totals_must_be_dict(self):
        """Test that token_metrics.totals must be a dict."""
        insights = self._minimal_insights(token_metrics={"totals": "not a dict"})
        with pytest.raises(
            InsightsValidationError, match="token_metrics.totals.*must be a dict"
        ):
            validate_insights_schema(insights)

    def test_token_metrics_totals_numeric_fields(self):
        """Test that totals numeric fields must be numeric."""
        insights = self._minimal_insights(
            token_metrics={"totals": {"input_tokens": "not a number"}}
        )
        with pytest.raises(
            InsightsValidationError,
            match="token_metrics.totals.input_tokens.*must be numeric",
        ):
            validate_insights_schema(insights)

    def test_token_metrics_by_model_must_be_dict(self):
        """Test that token_metrics.by_model must be a dict."""
        insights = self._minimal_insights(
            token_metrics={"by_model": ["list", "not", "dict"]}
        )
        with pytest.raises(
            InsightsValidationError, match="token_metrics.by_model.*must be a dict"
        ):
            validate_insights_schema(insights)

    def test_token_metrics_by_model_entries_must_be_dict(self):
        """Test that each by_model entry must be a dict."""
        insights = self._minimal_insights(
            token_metrics={"by_model": {"claude-opus": "not a dict"}}
        )
        with pytest.raises(
            InsightsValidationError,
            match="token_metrics.by_model.claude-opus.*must be a dict",
        ):
            validate_insights_schema(insights)

    def test_token_metrics_by_agent_must_be_dict(self):
        """Test that token_metrics.by_agent must be a dict."""
        insights = self._minimal_insights(token_metrics={"by_agent": 123})
        with pytest.raises(
            InsightsValidationError, match="token_metrics.by_agent.*must be a dict"
        ):
            validate_insights_schema(insights)

    def test_token_metrics_by_agent_entries_must_be_dict(self):
        """Test that each by_agent entry must be a dict."""
        insights = self._minimal_insights(
            token_metrics={"by_agent": {"main": [1, 2, 3]}}
        )
        with pytest.raises(
            InsightsValidationError, match="token_metrics.by_agent.main.*must be a dict"
        ):
            validate_insights_schema(insights)

    def test_token_metrics_efficiency_must_be_dict(self):
        """Test that token_metrics.efficiency must be a dict."""
        insights = self._minimal_insights(token_metrics={"efficiency": True})
        with pytest.raises(
            InsightsValidationError, match="token_metrics.efficiency.*must be a dict"
        ):
            validate_insights_schema(insights)

    def test_token_metrics_efficiency_numeric_fields(self):
        """Test that efficiency numeric fields must be numeric."""
        insights = self._minimal_insights(
            token_metrics={"efficiency": {"tokens_per_minute": "fast"}}
        )
        with pytest.raises(
            InsightsValidationError,
            match="token_metrics.efficiency.tokens_per_minute.*must be numeric",
        ):
            validate_insights_schema(insights)

    def test_token_metrics_cache_hit_rate_range(self):
        """Test that cache_hit_rate must be between 0.0 and 1.0."""
        insights = self._minimal_insights(
            token_metrics={"efficiency": {"cache_hit_rate": 1.5}}
        )
        with pytest.raises(
            InsightsValidationError, match="cache_hit_rate.*must be between 0.0 and 1.0"
        ):
            validate_insights_schema(insights)

    def test_token_metrics_cache_hit_rate_valid_bounds(self):
        """Test that cache_hit_rate at boundaries (0.0 and 1.0) passes."""
        # Test 0.0
        insights = self._minimal_insights(
            token_metrics={"efficiency": {"cache_hit_rate": 0.0}}
        )
        validate_insights_schema(insights)  # Should not raise

        # Test 1.0
        insights = self._minimal_insights(
            token_metrics={"efficiency": {"cache_hit_rate": 1.0}}
        )
        validate_insights_schema(insights)  # Should not raise

    def test_token_metrics_with_null_sub_fields(self):
        """Test that numeric fields in token_metrics accept null."""
        insights = self._minimal_insights(
            token_metrics={
                "totals": {"input_tokens": None, "output_tokens": None},
                "efficiency": {"cache_hit_rate": None, "tokens_per_minute": None},
            }
        )
        validate_insights_schema(insights)  # Should not raise


class TestFrameworkReflectionsValidation:
    """Test framework_reflections field validation, especially 'followed' coercion."""

    def _minimal_insights(self, **extra):
        """Create minimal valid insights with optional extra fields."""
        base = {
            "session_id": "a1b2c3d4",
            "date": "2026-01-13",
            "project": "test",
            "summary": "Test session",
            "outcome": "success",
            "accomplishments": [],
        }
        base.update(extra)
        return base

    def test_followed_accepts_bool_true(self):
        """Test that followed accepts boolean True."""
        insights = self._minimal_insights(framework_reflections=[{"followed": True}])
        validate_insights_schema(insights)  # Should not raise

    def test_followed_accepts_bool_false(self):
        """Test that followed accepts boolean False."""
        insights = self._minimal_insights(framework_reflections=[{"followed": False}])
        validate_insights_schema(insights)  # Should not raise

    def test_followed_coerces_int_1_to_true(self):
        """Test that followed coerces integer 1 to True."""
        insights = self._minimal_insights(framework_reflections=[{"followed": 1}])
        validate_insights_schema(insights)  # Should not raise
        assert insights["framework_reflections"][0]["followed"] is True

    def test_followed_coerces_int_0_to_false(self):
        """Test that followed coerces integer 0 to False."""
        insights = self._minimal_insights(framework_reflections=[{"followed": 0}])
        validate_insights_schema(insights)  # Should not raise
        assert insights["framework_reflections"][0]["followed"] is False

    def test_followed_coerces_string_true(self):
        """Test that followed coerces string 'true' to True."""
        insights = self._minimal_insights(framework_reflections=[{"followed": "true"}])
        validate_insights_schema(insights)  # Should not raise
        assert insights["framework_reflections"][0]["followed"] is True

    def test_followed_coerces_string_false(self):
        """Test that followed coerces string 'false' to False."""
        insights = self._minimal_insights(framework_reflections=[{"followed": "false"}])
        validate_insights_schema(insights)  # Should not raise
        assert insights["framework_reflections"][0]["followed"] is False

    def test_followed_coerces_string_yes(self):
        """Test that followed coerces string 'yes' to True."""
        insights = self._minimal_insights(framework_reflections=[{"followed": "yes"}])
        validate_insights_schema(insights)  # Should not raise
        assert insights["framework_reflections"][0]["followed"] is True

    def test_followed_coerces_string_no(self):
        """Test that followed coerces string 'no' to False."""
        insights = self._minimal_insights(framework_reflections=[{"followed": "no"}])
        validate_insights_schema(insights)  # Should not raise
        assert insights["framework_reflections"][0]["followed"] is False

    def test_followed_coerces_string_case_insensitive(self):
        """Test that followed string coercion is case-insensitive."""
        for val in ["TRUE", "True", "YES", "Yes", "Y", "1"]:
            insights = self._minimal_insights(framework_reflections=[{"followed": val}])
            validate_insights_schema(insights)
            assert insights["framework_reflections"][0]["followed"] is True

        for val in ["FALSE", "False", "NO", "No", "N", "0", ""]:
            insights = self._minimal_insights(framework_reflections=[{"followed": val}])
            validate_insights_schema(insights)
            assert insights["framework_reflections"][0]["followed"] is False

    def test_followed_rejects_invalid_string(self):
        """Test that followed rejects unrecognized string values."""
        insights = self._minimal_insights(framework_reflections=[{"followed": "maybe"}])
        with pytest.raises(
            InsightsValidationError, match="cannot be coerced to boolean"
        ):
            validate_insights_schema(insights)

    def test_followed_rejects_invalid_type(self):
        """Test that followed rejects non-coercible types like lists."""
        insights = self._minimal_insights(framework_reflections=[{"followed": [True]}])
        with pytest.raises(
            InsightsValidationError, match="must be a boolean or coercible value"
        ):
            validate_insights_schema(insights)

    def test_followed_accepts_null(self):
        """Test that followed accepts None/null."""
        insights = self._minimal_insights(framework_reflections=[{"followed": None}])
        validate_insights_schema(insights)  # Should not raise
