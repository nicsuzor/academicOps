import json
import sys
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import HookRouter, CanonicalHookOutput
from hooks.schemas import HookContext, GeminiHookOutput

class TestUniversalRouter:
    @pytest.fixture
    def router_instance(self):
        return HookRouter()

    def test_normalize_input_basic(self, router_instance):
        raw = {"tool_name": "read_file", "tool_input": {"path": "test.txt"}, "hook_event_name": "BeforeTool"}
        ctx = router_instance.normalize_input(raw, gemini_event="BeforeTool")
        
        assert ctx.hook_event == "PreToolUse"
        assert ctx.tool_name == "read_file"
        assert ctx.session_id.startswith("gemini-") or ctx.session_id.startswith("unknown-")

    def test_normalize_input_claude(self, router_instance):
        raw = {"tool_name": "Read", "tool_input": {"path": "test.txt"}, "hook_event_name": "PreToolUse", "session_id": "claude-1"}
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
                stderr=""
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
        def mock_deny_gate(ctx):
            return GateResult(verdict=GateVerdict.DENY, system_message="Blocked")

        # Replace gate checks with our mock
        mock_gate_checks.get.return_value = mock_deny_gate

        ctx = HookContext(session_id="test", hook_event="PreToolUse", raw_input={})
        result = router_instance.execute_hooks(ctx)

        assert result.verdict == "deny"

    def test_output_for_gemini(self, router_instance):
        canonical = CanonicalHookOutput(verdict="deny", context_injection="Reason", system_message="Msg")
        out = router_instance.output_for_gemini(canonical, "BeforeTool")
        
        assert isinstance(out, GeminiHookOutput)
        assert out.decision == "deny"
        assert out.reason == "Reason"
        assert out.systemMessage == "Msg"

    def test_output_for_claude_stop(self, router_instance):
        canonical = CanonicalHookOutput(verdict="deny", context_injection="Stop Reason", system_message="User Msg")
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