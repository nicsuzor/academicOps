import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import CanonicalHookOutput, HookRouter
from hooks.schemas import GeminiHookOutput


class TestUniversalRouter:
    @pytest.fixture
    def router_instance(self, monkeypatch):
        # Mock get_session_data to avoid reading shared PID session map during xdist tests
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        return HookRouter()

    def test_normalize_input_basic(self, router_instance):
        raw = {
            "tool_name": "read_file",
            "tool_input": {"path": "test.txt"},
            "hook_event_name": "BeforeTool",
        }
        # Clear CLAUDE_SESSION_ID so the router doesn't pick up a real session ID
        # when running inside a Claude Code session (env leak into test)
        with patch.dict("os.environ", {"CLAUDE_SESSION_ID": ""}, clear=False):
            router_instance.session_data = {}  # Also clear cached session data
            ctx = router_instance.normalize_input(raw, gemini_event="BeforeTool")

        assert ctx.hook_event == "PreToolUse"
        assert ctx.tool_name == "read_file"
        assert ctx.session_id.startswith("gemini-") or ctx.session_id.startswith("unknown-")

    def test_normalize_input_claude(self, router_instance):
        raw = {
            "tool_name": "Read",
            "tool_input": {"path": "test.txt"},
            "hook_event_name": "PreToolUse",
            "session_id": "claude-1",
        }
        ctx = router_instance.normalize_input(raw)

        assert ctx.hook_event == "PreToolUse"
        assert ctx.session_id == "claude-1"

    def test_output_for_gemini(self, router_instance):
        canonical = CanonicalHookOutput(
            verdict="deny", context_injection="Reason", system_message="Msg"
        )
        out = router_instance.output_for_gemini(canonical, "BeforeTool")

        assert isinstance(out, GeminiHookOutput)
        assert out.decision == "deny"
        # `reason` is the user-visible short denial summary (system_message).
        # The recovery payload (context_injection) goes to additionalContext
        # so the model can see it.
        assert out.reason == "Msg"
        assert out.systemMessage == "Msg"
        assert out.hookSpecificOutput is not None
        assert out.hookSpecificOutput.additionalContext == "Reason"

    def test_output_for_claude_stop(self, router_instance):
        canonical = CanonicalHookOutput(
            verdict="deny", context_injection="Stop Reason", system_message="User Msg"
        )
        out = router_instance.output_for_claude(canonical, "Stop")

        # Check dictionary representation or attributes
        # ClaudeHookOutput is a Union, so it might be ClaudeStopHookOutput
        assert out.decision == "block"
        assert out.reason == "Stop Reason"
        assert out.stopReason == "User Msg"

    def test_output_for_claude_standard(self, router_instance):
        canonical = CanonicalHookOutput(verdict="deny", context_injection="Context")
        out = router_instance.output_for_claude(canonical, "PreToolUse")

        assert out.hookSpecificOutput.permissionDecision == "deny"
        assert out.hookSpecificOutput.additionalContext == "Context"


class TestToolInputNormalization:
    """Tests for JSON string normalization in router.py."""

    @pytest.fixture
    def router_instance(self, monkeypatch):
        # Mock get_session_data to avoid reading shared PID session map during xdist tests
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        return HookRouter()

    def test_normalize_json_field_string(self, router_instance):
        """JSON string is parsed to dict."""
        value = '{"key": "value"}'
        result = router_instance._normalize_json_field(value)
        assert result == {"key": "value"}

    def test_normalize_json_field_dict(self, router_instance):
        """Dict passes through unchanged."""
        value = {"key": "value"}
        result = router_instance._normalize_json_field(value)
        assert result == {"key": "value"}

    def test_normalize_json_field_invalid_json(self, router_instance):
        """Invalid JSON string passes through unchanged."""
        value = "not valid json"
        result = router_instance._normalize_json_field(value)
        assert result == "not valid json"

    def test_normalize_json_field_list(self, router_instance):
        """JSON array string is parsed to list."""
        value = '["a", "b", "c"]'
        result = router_instance._normalize_json_field(value)
        assert result == ["a", "b", "c"]

    def test_normalize_input_tool_input_json_string(self, router_instance):
        """tool_input as JSON string is normalized to dict."""
        raw = {
            "tool_name": "read_file",
            "tool_input": '{"path": "/tmp/test.txt"}',
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.tool_input == {"path": "/tmp/test.txt"}
        assert isinstance(ctx.tool_input, dict)

    def test_normalize_input_tool_result_json_string(self, router_instance):
        """tool_result as JSON string is normalized into tool_output."""
        raw = {
            "hook_event_name": "PostToolUse",
            "session_id": "test-123",
            "tool_result": '{"verdict": "PROCEED"}',
        }
        ctx = router_instance.normalize_input(raw)
        # raw_input is unchanged, but tool_output is normalized
        assert ctx.tool_output == {"verdict": "PROCEED"}
        assert isinstance(ctx.tool_output, dict)

    def test_normalize_input_subagent_result_json_string(self, router_instance):
        """subagent_result as JSON string is normalized into tool_output."""
        raw = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-123",
            "subagent_result": '{"output": "done", "status": "ok"}',
        }
        ctx = router_instance.normalize_input(raw)
        # raw_input is unchanged, but tool_output is normalized
        assert ctx.tool_output == {"output": "done", "status": "ok"}
        assert isinstance(ctx.tool_output, dict)


class TestSubagentTypeExtraction:
    """Tests for subagent_type extraction from spawning tools.

    Gemini uses delegate_to_agent(name='...'), Claude uses Task(subagent_type='...').
    Both should correctly extract subagent_type for gate triggers.

    Bug fix: aops-91e4c3f2 - Gemini polecat workers stuck in gate loop
    """

    @pytest.fixture
    def router_instance(self, monkeypatch):
        # Mock get_session_data to avoid reading shared PID session map during xdist tests
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        return HookRouter()

    def test_claude_task_subagent_type(self, router_instance):
        """Claude Task tool with subagent_type extracts correctly."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "Task",
            "tool_input": {"subagent_type": "enforcer", "prompt": "Check compliance"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "enforcer"

    def test_gemini_delegate_to_agent_name(self, router_instance):
        """Gemini delegate_to_agent with name= extracts correctly."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "delegate_to_agent",
            "tool_input": {"name": "enforcer", "query": "Check compliance"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "enforcer"

    def test_gemini_delegate_to_agent_agent_name(self, router_instance):
        """Gemini delegate_to_agent with agent_name= also works."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "delegate_to_agent",
            "tool_input": {"agent_name": "enforcer", "query": "Check compliance"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "enforcer"

    def test_activate_skill_name(self, router_instance):
        """activate_skill with name= extracts correctly."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "activate_skill",
            "tool_input": {"name": "enforcer"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "enforcer"

    def test_activate_skill_handover(self, router_instance):
        """activate_skill with name='handover' extracts correctly."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "activate_skill",
            "tool_input": {"name": "handover"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "handover"

    def test_activate_skill_dump(self, router_instance):
        """activate_skill with name='dump' extracts correctly."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "activate_skill",
            "tool_input": {"name": "dump"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "dump"

    def test_skill_tool_uses_skill_param(self, router_instance):
        """Skill tool extracts from 'skill' param (not 'subagent_type')."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "Skill",
            "tool_input": {"skill": "qa"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "qa"

    def test_skill_tool_ignores_subagent_type_param(self, router_instance):
        """Skill tool does NOT extract from 'subagent_type' — it uses 'skill'."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "Skill",
            "tool_input": {"subagent_type": "qa"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type is None

    def test_subagent_type_from_payload_takes_precedence(self, router_instance):
        """If subagent_type already in payload, tool_input is not used."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "delegate_to_agent",
            "subagent_type": "already-set",
            "tool_input": {"name": "should-not-override"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "already-set"

    def test_aops_prefixed_subagent(self, router_instance):
        """aops-core: prefixed subagent names work correctly."""
        raw = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-123",
            "tool_name": "delegate_to_agent",
            "tool_input": {"name": "aops-core:enforcer", "query": "Check compliance"},
        }
        ctx = router_instance.normalize_input(raw)
        assert ctx.subagent_type == "aops-core:enforcer"


class TestPkbSignatureFix:
    @pytest.fixture
    def router_instance(self, monkeypatch):
        # Mock get_session_data to avoid reading shared PID session map during xdist tests
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        return HookRouter()

    def test_update_task_flattening(self, router_instance):
        raw = {
            "tool_name": "update_task",
            "tool_input": {"id": "task-1", "status": "done", "assignee": "nic"},
            "hook_event_name": "BeforeTool",
        }
        ctx = router_instance.normalize_input(raw, gemini_event="BeforeTool")
        result = CanonicalHookOutput()
        router_instance._run_pkb_signature_fix(ctx, result)

        assert result.updated_input is not None
        import json

        updated = json.loads(result.updated_input)
        assert updated["id"] == "task-1"
        assert updated["updates"] == {"status": "done", "assignee": "nic"}

    def test_update_task_prefixed_flattening(self, router_instance):
        raw = {
            "tool_name": "mcp__pkb__update_task",
            "tool_input": {"id": "task-1", "status": "done"},
            "hook_event_name": "PreToolUse",
        }
        ctx = router_instance.normalize_input(raw)
        result = CanonicalHookOutput()
        router_instance._run_pkb_signature_fix(ctx, result)

        assert result.updated_input is not None
        import json

        updated = json.loads(result.updated_input)
        assert updated["id"] == "task-1"
        assert updated["updates"] == {"status": "done"}

    def test_append_path_alias(self, router_instance):
        raw = {
            "tool_name": "append",
            "tool_input": {"path": "tasks/test.md", "content": "more info"},
            "hook_event_name": "BeforeTool",
        }
        ctx = router_instance.normalize_input(raw, gemini_event="BeforeTool")
        result = CanonicalHookOutput()
        router_instance._run_pkb_signature_fix(ctx, result)

        assert result.updated_input is not None
        import json

        updated = json.loads(result.updated_input)
        assert updated["id"] == "tasks/test.md"
        assert updated["content"] == "more info"

    def test_create_task_title_alias(self, router_instance):
        raw = {
            "tool_name": "create_task",
            "tool_input": {"task_title": "My Task", "project": "aops"},
            "hook_event_name": "BeforeTool",
        }
        ctx = router_instance.normalize_input(raw, gemini_event="BeforeTool")
        result = CanonicalHookOutput()
        router_instance._run_pkb_signature_fix(ctx, result)

        assert result.updated_input is not None
        import json

        updated = json.loads(result.updated_input)
        assert updated["title"] == "My Task"
        assert updated["project"] == "aops"

    def test_get_task_path_alias(self, router_instance):
        raw = {
            "tool_name": "get_task",
            "tool_input": {"path": "tasks/1.md"},
            "hook_event_name": "BeforeTool",
        }
        ctx = router_instance.normalize_input(raw, gemini_event="BeforeTool")
        result = CanonicalHookOutput()
        router_instance._run_pkb_signature_fix(ctx, result)
        import json

        assert json.loads(result.updated_input)["id"] == "tasks/1.md"

    def test_get_document_id_alias(self, router_instance):
        raw = {
            "tool_name": "get_document",
            "tool_input": {"id": "tasks/1.md"},
            "hook_event_name": "BeforeTool",
        }
        ctx = router_instance.normalize_input(raw, gemini_event="BeforeTool")
        result = CanonicalHookOutput()
        router_instance._run_pkb_signature_fix(ctx, result)
        import json

        assert json.loads(result.updated_input)["path"] == "tasks/1.md"

    def test_no_fix_if_already_correct(self, router_instance):
        raw = {
            "tool_name": "update_task",
            "tool_input": {"id": "task-1", "updates": {"status": "done"}},
            "hook_event_name": "BeforeTool",
        }
        ctx = router_instance.normalize_input(raw, gemini_event="BeforeTool")
        result = CanonicalHookOutput()
        router_instance._run_pkb_signature_fix(ctx, result)

        # Should not set updated_input if already has 'updates'
        assert result.updated_input is None
