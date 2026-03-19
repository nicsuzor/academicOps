"""Regression tests for is_subagent_session() detection.

Commit 9c8b10bd added an explicit `is_subagent` flag check (method 0) and
ensured is_subagent_session() is called BEFORE fields are popped from raw_input.

These tests verify all detection methods work correctly with a complete
raw_input dict (as they would receive from the router after the fix).
"""

import os
from unittest.mock import patch

from lib.hook_utils import is_subagent_session


class TestExplicitIsSubagentFlag:
    """Method 0: Explicit is_subagent flag (added in commit 9c8b10bd)."""

    def test_explicit_is_subagent_true(self):
        assert is_subagent_session({"is_subagent": True}) is True

    def test_explicit_is_subagent_false(self):
        """is_subagent=False should not short-circuit - other methods may detect."""
        # False doesn't mean "not a subagent" - other heuristics might still match
        result = is_subagent_session({"is_subagent": False})
        # With no other indicators, should be False
        assert result is False

    def test_explicit_is_subagent_none(self):
        """is_subagent=None should not trigger detection."""
        result = is_subagent_session({"is_subagent": None})
        assert result is False


class TestAgentIdDetection:
    """Method 1: agent_id/agentId fields in payload."""

    def test_agent_id_snake_case(self):
        assert is_subagent_session({"agent_id": "abc123"}) is True

    def test_agentId_camel_case(self):
        assert is_subagent_session({"agentId": "abc123"}) is True

    def test_agent_type_snake_case(self):
        assert is_subagent_session({"agent_type": "explorer"}) is True

    def test_agentType_camel_case(self):
        assert is_subagent_session({"agentType": "explorer"}) is True

    def test_empty_agent_id_not_detected(self):
        """Empty string agent_id should not trigger detection."""
        result = is_subagent_session({"agent_id": ""})
        assert result is False


class TestSessionIdPattern:
    """Method 2: Short hex session IDs indicate subagent sessions."""

    def test_short_hex_session_id(self):
        """Claude subagent IDs are short lowercase hex (e.g., aafdeee)."""
        assert is_subagent_session({"session_id": "aafdeee"}) is True

    def test_full_uuid_not_subagent(self):
        """Full UUID session IDs are main sessions."""
        result = is_subagent_session({"session_id": "f4e3f1cb-775c-4aaf-8bf6-4e18a18dad3d"})
        assert result is False

    def test_gemini_session_id_not_subagent(self):
        """Gemini session IDs with timestamps are not subagent."""
        result = is_subagent_session({"session_id": "gemini-20260213-143000-abc12345"})
        assert result is False


class TestEnvVarDetection:
    """Method 3: Environment variables."""

    def test_claude_agent_type_env(self):
        with patch.dict(os.environ, {"CLAUDE_AGENT_TYPE": "explorer"}, clear=False):
            assert is_subagent_session({}) is True

    def test_claude_subagent_type_env(self):
        with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": "hydrator"}, clear=False):
            assert is_subagent_session({}) is True

    def test_claude_parent_session_id_env(self):
        with patch.dict(os.environ, {"CLAUDE_PARENT_SESSION_ID": "abc-123"}, clear=False):
            assert is_subagent_session({}) is True


class TestTranscriptPathDetection:
    """Method 4: Transcript path containing /subagents/ or /agent-."""

    def test_subagents_in_transcript_path(self):
        assert (
            is_subagent_session(
                {"transcript_path": "/home/user/.claude/subagents/abc123/transcript.jsonl"}
            )
            is True
        )

    def test_agent_dash_in_transcript_path(self):
        assert is_subagent_session({"transcript_path": "/tmp/agent-explorer/output.json"}) is True

    def test_subagents_in_cwd(self):
        assert is_subagent_session({"cwd": "/home/user/.claude/subagents/def456"}) is True

    def test_normal_path_not_detected(self):
        assert (
            is_subagent_session(
                {"transcript_path": "/home/user/.claude/sessions/main/transcript.jsonl"}
            )
            is False
        )


class TestNoneAndEmptyInputs:
    """Edge cases: None, empty dict, missing fields."""

    def test_none_input(self):
        assert is_subagent_session(None) is False

    def test_empty_dict(self):
        assert is_subagent_session({}) is False

    def test_no_argument(self):
        assert is_subagent_session() is False


class TestCombinedDetection:
    """Integration: multiple signals in a single payload (as router provides)."""

    def test_full_subagent_payload(self):
        """A realistic subagent payload with multiple indicators."""
        payload = {
            "session_id": "adc71f1",
            "agent_id": "adc71f1",
            "subagent_type": "Explore",
            "hook_event_name": "PreToolUse",
            "tool_name": "Grep",
            "tool_input": '{"pattern": "class.*Error"}',
            "is_sidechain": False,
        }
        assert is_subagent_session(payload) is True

    def test_main_session_payload(self):
        """A realistic main session payload should not be detected as subagent."""
        payload = {
            "session_id": "f4e3f1cb-775c-4aaf-8bf6-4e18a18dad3d",
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": '{"file_path": "/tmp/test.py"}',
            "slug": "my-project",
            "cwd": "/home/user/projects/myapp",
        }
        result = is_subagent_session(payload)
        assert result is False
