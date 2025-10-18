#!/usr/bin/env python3
"""
Unit tests for hook_models.py Pydantic schemas.

Tests verify:
1. Model validation works correctly
2. JSON serialization produces correct structure
3. Invalid data is rejected properly
4. All hook types are covered
"""

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from .hooks import parse_hook_output, run_hook
# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from hook_models import (
    PostToolUseHookOutput,
    PostToolUseOutput,
    PreToolUseHookOutput,
    PreToolUseOutput,
    SessionStartHookOutput,
    SessionStartOutput,
    StopHookOutput,
    UserPromptSubmitHookOutput,
    UserPromptSubmitOutput,
)


class TestPreToolUseModels:
    """Test PreToolUse hook models."""

    def test_pretooluse_minimal_output(self):
        """Test PreToolUse output with minimal required fields."""
        output = PreToolUseOutput(
            hookSpecificOutput=PreToolUseHookOutput(permissionDecision="allow")
        )

        # Convert to dict
        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        # Verify structure
        assert "hookSpecificOutput" in output_dict
        assert output_dict["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert output_dict["hookSpecificOutput"]["permissionDecision"] == "allow"
        # permissionDecisionReason should be excluded when None
        assert "permissionDecisionReason" not in output_dict["hookSpecificOutput"]

    def test_pretooluse_with_reason(self):
        """Test PreToolUse output with permission reason."""
        output = PreToolUseOutput(
            hookSpecificOutput=PreToolUseHookOutput(
                permissionDecision="deny",
                permissionDecisionReason="This operation is blocked",
            )
        )

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert output_dict["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert (
            output_dict["hookSpecificOutput"]["permissionDecisionReason"]
            == "This operation is blocked"
        )

    def test_pretooluse_invalid_decision(self):
        """Test that invalid permissionDecision values are rejected."""
        with pytest.raises(ValidationError):
            PreToolUseHookOutput(permissionDecision="invalid")

    def test_pretooluse_with_optional_fields(self):
        """Test PreToolUse output with optional common fields."""
        output = PreToolUseOutput(
            hookSpecificOutput=PreToolUseHookOutput(permissionDecision="allow"),
            continue_=False,
            stopReason="User cancelled",
            systemMessage="This is a warning",
            suppressOutput=True,
        )

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        # Verify optional fields are included
        assert output_dict["continue"] is False
        assert output_dict["stopReason"] == "User cancelled"
        assert output_dict["systemMessage"] == "This is a warning"
        assert output_dict["suppressOutput"] is True

    def test_pretooluse_json_serialization(self):
        """Test that PreToolUse output can be serialized to JSON."""
        output = PreToolUseOutput(
            hookSpecificOutput=PreToolUseHookOutput(
                permissionDecision="ask",
                permissionDecisionReason="Confirm this action",
            )
        )

        # Serialize to JSON
        json_str = json.dumps(output.model_dump(by_alias=True, exclude_none=True))

        # Verify it can be parsed back
        parsed = json.loads(json_str)
        assert parsed["hookSpecificOutput"]["permissionDecision"] == "ask"


class TestPostToolUseModels:
    """Test PostToolUse hook models."""

    def test_posttooluse_minimal(self):
        """Test PostToolUse output with minimal fields."""
        output = PostToolUseOutput(hookSpecificOutput=PostToolUseHookOutput())

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert output_dict["hookSpecificOutput"]["hookEventName"] == "PostToolUse"

    def test_posttooluse_with_context(self):
        """Test PostToolUse output with additional context."""
        output = PostToolUseOutput(
            hookSpecificOutput=PostToolUseHookOutput(
                additionalContext="Tool completed successfully"
            )
        )

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert (
            output_dict["hookSpecificOutput"]["additionalContext"]
            == "Tool completed successfully"
        )

    def test_posttooluse_with_legacy_fields(self):
        """Test PostToolUse output with legacy decision/reason fields."""
        output = PostToolUseOutput(
            hookSpecificOutput=PostToolUseHookOutput(),
            decision="block",
            reason="Action blocked",
        )

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert output_dict["decision"] == "block"
        assert output_dict["reason"] == "Action blocked"


class TestUserPromptSubmitModels:
    """Test UserPromptSubmit hook models."""

    def test_userpromptsubmit_minimal(self):
        """Test UserPromptSubmit output with minimal fields."""
        output = UserPromptSubmitOutput(
            hookSpecificOutput=UserPromptSubmitHookOutput()
        )

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert (
            output_dict["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        )

    def test_userpromptsubmit_with_context(self):
        """Test UserPromptSubmit output with additional context."""
        output = UserPromptSubmitOutput(
            hookSpecificOutput=UserPromptSubmitHookOutput(
                additionalContext="Prompt validated"
            )
        )

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert (
            output_dict["hookSpecificOutput"]["additionalContext"] == "Prompt validated"
        )


class TestSessionStartModels:
    """Test SessionStart hook models."""

    def test_sessionstart_minimal(self):
        """Test SessionStart output with minimal fields."""
        output = SessionStartOutput(hookSpecificOutput=SessionStartHookOutput())

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert output_dict["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_sessionstart_with_context(self):
        """Test SessionStart output with additional context."""
        output = SessionStartOutput(
            hookSpecificOutput=SessionStartHookOutput(
                additionalContext="Session initialized"
            )
        )

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert (
            output_dict["hookSpecificOutput"]["additionalContext"]
            == "Session initialized"
        )


class TestStopHookModels:
    """Test Stop/SubagentStop hook models."""

    def test_stop_allow(self):
        """Test Stop hook allowing execution."""
        output = StopHookOutput()

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        # When decision is None, it should be excluded
        assert "decision" not in output_dict

    def test_stop_block(self):
        """Test Stop hook blocking execution."""
        output = StopHookOutput(decision="block", reason="Stopping execution")

        output_dict = output.model_dump(by_alias=True, exclude_none=True)

        assert output_dict["decision"] == "block"
        assert output_dict["reason"] == "Stopping execution"


class TestModelInteroperability:
    """Test that different models work together correctly."""

    def test_all_models_serialize_to_valid_json(self):
        """Test that all hook output models can be serialized to valid JSON."""
        models = [
            PreToolUseOutput(
                hookSpecificOutput=PreToolUseHookOutput(permissionDecision="allow")
            ),
            PostToolUseOutput(hookSpecificOutput=PostToolUseHookOutput()),
            UserPromptSubmitOutput(hookSpecificOutput=UserPromptSubmitHookOutput()),
            SessionStartOutput(hookSpecificOutput=SessionStartHookOutput()),
            StopHookOutput(),
        ]

        for model in models:
            # Should not raise
            json_str = json.dumps(model.model_dump(by_alias=True, exclude_none=True))
            # Verify it can be parsed back
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
