import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import CanonicalHookOutput, HookRouter
from hooks.schemas import GeminiHookOutput, HookContext


class TestUniversalRouter:
    @pytest.fixture
    def router_instance(self):
        return HookRouter()

    def test_normalize_input_basic(self, router_instance):
        raw = {
            "tool_name": "read_file",
            "tool_input": {"path": "test.txt"},
            "hook_event_name": "BeforeTool",
        }
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

        @patch("hooks.router.subprocess.run")
        def test_execute_hooks_dispatch(self, mock_run, router_instance):
            # Mock successful hook execution
            # PreToolUse runs 2 hooks (logger + gates)
            # We'll make them return same output, so they merge
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"verdict": "allow", "system_message": "Allowed"}),
                stderr="",
            )

            ctx = HookContext(session_id="test", hook_event="PreToolUse", raw_input={})
            result = router_instance.execute_hooks(ctx)

            assert isinstance(result, CanonicalHookOutput)
            assert result.verdict == "allow"
            # Expect merged messages from 2 hooks
            assert result.system_message == "Allowed\nAllowed"
            assert mock_run.called

    @patch("hooks.router.GATE_CHECKS")
    def test_block_behavior(self, mock_gate_checks, router_instance):
        """Test that a gate returning deny verdict propagates correctly."""
        from lib.gate_model import GateResult, GateVerdict

        # Mock a gate that returns deny
        # Signature must match (ctx, state)
        def mock_deny_gate(ctx, state):
            return GateResult(verdict=GateVerdict.DENY, system_message="Blocked")

        # Replace gate checks with our mock
        mock_gate_checks.get.return_value = mock_deny_gate

        # Mock SessionState.load to avoid I/O
        with patch("hooks.router.SessionState.load") as mock_load:
            mock_load.return_value = MagicMock()
            ctx = HookContext(session_id="test", hook_event="PreToolUse", raw_input={})
            result = router_instance.execute_hooks(ctx)

            assert result.verdict == "deny"

    def test_output_for_gemini(self, router_instance):
        canonical = CanonicalHookOutput(
            verdict="deny", context_injection="Reason", system_message="Msg"
        )
        out = router_instance.output_for_gemini(canonical, "BeforeTool")

        assert isinstance(out, GeminiHookOutput)
        assert out.decision == "deny"
        assert out.reason == "Reason"
        assert out.systemMessage == "Msg"

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
    def router_instance(self):
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
