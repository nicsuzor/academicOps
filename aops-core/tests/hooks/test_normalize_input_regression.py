"""Regression tests for HookRouter.normalize_input().

Commit 9c8b10bd fixed a critical bug where raw_input.pop() was used during
context building, destroying fields before they could be read by later logic.
The fix changed all .pop() calls to .get(), with a batch pop of processed
fields at the end.

These tests ensure the bug does not regress:
1. is_subagent_session() must see all fields (agent_id, subagent_type, etc.)
2. Fields must be correctly extracted regardless of processing order
3. raw_input remainder must exclude processed fields but retain extras
"""

from unittest.mock import patch

import pytest
from hooks.router import HookRouter


@pytest.fixture
def router():
    """Create HookRouter with mocked session data."""
    with patch("hooks.router.get_session_data", return_value={}):
        yield HookRouter()


class TestPopVsGetRegression:
    """Core regression: .pop() was destroying raw_input mid-processing.

    The old code did raw_input.pop("agent_id") early, so is_subagent_session()
    called later couldn't see agent_id and failed to detect subagent sessions.
    """

    def test_subagent_detected_when_agent_id_in_payload(self, router):
        """agent_id in payload must cause is_subagent=True.

        This was the primary bug: .pop("agent_id") removed it before
        is_subagent_session() could check it.
        """
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "abc123def",
            "agent_id": "abc123def",
            "tool_name": "Read",
            "tool_input": "{}",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw.copy())

        assert ctx.is_subagent is True
        assert ctx.agent_id == "abc123def"

    def test_subagent_detected_when_subagent_type_in_payload(self, router):
        """subagent_type in payload must cause is_subagent=True."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session-uuid",
            "subagent_type": "prompt-hydrator",
            "tool_name": "Read",
            "tool_input": "{}",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw.copy())

        assert ctx.is_subagent is True
        assert ctx.subagent_type == "prompt-hydrator"

    def test_subagent_detected_when_is_sidechain_in_payload(self, router):
        """is_sidechain flag must cause is_subagent=True."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session-uuid",
            "is_sidechain": True,
            "tool_name": "Read",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw.copy())

        assert ctx.is_subagent is True

    def test_subagent_detected_when_isSidechain_camelcase(self, router):
        """isSidechain (camelCase variant) must also work."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session-uuid",
            "isSidechain": True,
            "tool_name": "Read",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw.copy())

        assert ctx.is_subagent is True


class TestFieldExtraction:
    """Verify all fields are correctly extracted from raw_input."""

    def test_all_core_fields_extracted(self, router):
        """Every known field must be extracted into the correct HookContext attribute."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session-123",
            "tool_name": "Bash",
            "tool_input": '{"command": "ls"}',
            "agent_id": "agent-abc",
            "slug": "my-project",
            "cwd": "/home/user/project",
            "trace_id": "trace-xyz",
            "transcript_path": "/tmp/transcript.jsonl",
            "subagent_type": "explorer",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw.copy())

        assert ctx.hook_event == "PreToolUse"
        assert ctx.session_id == "test-session-123"
        assert ctx.tool_name == "Bash"
        assert ctx.tool_input == {"command": "ls"}
        assert ctx.agent_id == "agent-abc"
        assert ctx.slug == "my-project"
        assert ctx.cwd == "/home/user/project"
        assert ctx.trace_id == "trace-xyz"
        assert ctx.transcript_path == "/tmp/transcript.jsonl"
        assert ctx.subagent_type == "explorer"

    def test_tool_result_variants(self, router):
        """All tool_result field variants must be normalized to ctx.tool_output."""
        for field_name in ("tool_result", "toolResult", "tool_response", "subagent_result"):
            raw = {
                "hook_event_name": "PostToolUse",
                "session_id": "test-session",
                "tool_name": "Read",
                field_name: '{"content": "file data"}',
            }
            with patch("hooks.router.persist_session_data"):
                ctx = router.normalize_input(raw.copy())

            assert ctx.tool_output == {"content": "file data"}, (
                f"Failed for field variant: {field_name}"
            )

    def test_agent_id_variants(self, router):
        """Both agent_id and agentId must be extracted."""
        for field_name in ("agent_id", "agentId"):
            raw = {
                "hook_event_name": "PreToolUse",
                "session_id": "test-session",
                field_name: "my-agent-id",
            }
            with patch("hooks.router.persist_session_data"):
                ctx = router.normalize_input(raw.copy())

            assert ctx.agent_id == "my-agent-id", f"Failed for agent_id variant: {field_name}"


class TestRawInputRemainder:
    """After processing, raw_input should only contain unrecognized fields."""

    def test_processed_fields_removed_from_raw_input(self, router):
        """All known processed fields must be popped from raw_input."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Read",
            "tool_input": "{}",
            "agent_id": "agent-1",
            "agentId": "agent-1",
            "slug": "proj",
            "cwd": "/tmp",
            "trace_id": "trace-1",
            "transcript_path": "/tmp/t.jsonl",
            "is_sidechain": True,
            "isSidechain": True,
            "subagent_type": "explorer",
            "agent_type": "explorer",
            "tool_result": '{"ok": true}',
            "toolResult": '{"ok": true}',
            "tool_response": '{"ok": true}',
            "subagent_result": '{"ok": true}',
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw)

        processed_fields = [
            "hook_event_name",
            "session_id",
            "transcript_path",
            "trace_id",
            "tool_name",
            "tool_input",
            "tool_result",
            "toolResult",
            "tool_response",
            "subagent_result",
            "agent_id",
            "agentId",
            "slug",
            "cwd",
            "is_sidechain",
            "isSidechain",
            "subagent_type",
            "agent_type",
        ]
        for field in processed_fields:
            assert field not in ctx.raw_input, (
                f"Processed field '{field}' should not remain in raw_input"
            )

    def test_extra_fields_preserved_in_raw_input(self, router):
        """Unrecognized fields must be preserved in raw_input."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "custom_field": "should_survive",
            "another_extra": 42,
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw)

        assert ctx.raw_input.get("custom_field") == "should_survive"
        assert ctx.raw_input.get("another_extra") == 42


class TestSubagentTypeFromSpawningTools:
    """subagent_type must be extractable from Task/Skill tool_input."""

    def test_subagent_type_from_task_tool_input(self, router):
        """When tool_name=Task, subagent_type should come from tool_input."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Task",
            "tool_input": '{"subagent_type": "Explore", "prompt": "find files"}',
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw.copy())

        assert ctx.subagent_type == "Explore"
        assert ctx.is_subagent is True

    def test_subagent_type_from_skill_tool_input(self, router):
        """When tool_name=Skill, subagent_type should come from tool_input."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Skill",
            "tool_input": '{"agent_name": "commit"}',
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw.copy())

        assert ctx.subagent_type == "commit"

    def test_explicit_subagent_type_takes_precedence_over_tool_input(self, router):
        """Explicit subagent_type in payload should win over tool_input extraction."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "subagent_type": "explicit-type",
            "tool_name": "Task",
            "tool_input": '{"subagent_type": "from-tool-input"}',
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw.copy())

        assert ctx.subagent_type == "explicit-type"


class TestSessionDataPersistence:
    """Session data must persist on SessionStart and SubagentStart."""

    def test_persist_called_on_session_start(self, router):
        """persist_session_data must be called on SessionStart."""
        raw = {
            "hook_event_name": "SessionStart",
            "session_id": "new-session-123",
        }
        with patch("hooks.router.persist_session_data") as mock_persist:
            router.normalize_input(raw.copy())

        mock_persist.assert_called_once()
        call_args = mock_persist.call_args[0][0]
        assert call_args["session_id"] == "new-session-123"

    def test_persist_called_on_subagent_start(self, router):
        """persist_session_data must be called on SubagentStart."""
        raw = {
            "hook_event_name": "SubagentStart",
            "session_id": "sub-agent-abc",
            "agent_id": "abc123",
            "subagent_type": "explorer",
        }
        with patch("hooks.router.persist_session_data") as mock_persist:
            router.normalize_input(raw.copy())

        mock_persist.assert_called_once()
        call_args = mock_persist.call_args[0][0]
        assert call_args["session_id"] == "sub-agent-abc"
        assert call_args["agent_id"] == "abc123"
        assert call_args["subagent_type"] == "explorer"

    def test_persist_not_called_on_pretooluse(self, router):
        """persist_session_data must NOT be called on regular events."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Read",
        }
        with patch("hooks.router.persist_session_data") as mock_persist:
            router.normalize_input(raw.copy())

        mock_persist.assert_not_called()


class TestSessionDataFallback:
    """Agent ID and subagent type should fall back to persisted session data."""

    def test_agent_id_from_session_data(self):
        """When agent_id not in payload, should fall back to persisted session data."""
        session_data = {"session_id": "test-session", "agent_id": "persisted-agent"}
        with patch("hooks.router.get_session_data", return_value=session_data):
            r = HookRouter()

        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Read",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = r.normalize_input(raw.copy())

        assert ctx.agent_id == "persisted-agent"

    def test_subagent_type_from_session_data(self):
        """When subagent_type not in payload, should fall back to persisted session data."""
        session_data = {"session_id": "test-session", "subagent_type": "explorer"}
        with patch("hooks.router.get_session_data", return_value=session_data):
            r = HookRouter()

        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Read",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = r.normalize_input(raw.copy())

        assert ctx.subagent_type == "explorer"
        assert ctx.is_subagent is True


class TestGeminiEventMapping:
    """Gemini events must be correctly mapped to canonical names."""

    def test_gemini_before_tool_maps_to_pretooluse(self, router):
        raw = {"session_id": "test-session", "tool_name": "Read"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="BeforeTool")
        assert ctx.hook_event == "PreToolUse"

    def test_gemini_session_end_maps_to_stop(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="SessionEnd")
        assert ctx.hook_event == "Stop"

    def test_gemini_event_without_mapping_passes_through(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="UnknownEvent")
        assert ctx.hook_event == "UnknownEvent"
