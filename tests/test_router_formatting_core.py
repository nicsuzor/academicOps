"""Tests for GateResult model and HookRouter formatting logic."""

from lib.gate_model import GateResult, GateVerdict
from hooks.router import HookRouter
from hooks.schemas import CanonicalHookOutput


class TestGateModel:
    """Tests for GateResult dataclass."""

    def test_gate_result_json_serialization(self):
        result = GateResult(
            verdict=GateVerdict.DENY,
            system_message="Access Denied",
            context_injection="Do this instead",
            metadata={"rule": "compliance"},
        )
        json_out = result.to_json()
        assert json_out["verdict"] == "deny"
        assert json_out["system_message"] == "Access Denied"
        assert json_out["context_injection"] == "Do this instead"
        assert json_out["metadata"]["rule"] == "compliance"


class TestRouterFormatting:
    """Tests for HookRouter.output_for_gemini and output_for_claude."""

    def setup_method(self):
        self.router = HookRouter()

    def test_format_for_gemini_deny(self):
        canonical = CanonicalHookOutput(
            verdict="deny",
            system_message="Blocked",
            context_injection="Reasoning here",
        )
        output = self.router.output_for_gemini(canonical, "BeforeTool")
        assert output.decision == "deny"
        assert output.systemMessage == "Blocked"
        assert output.reason == "Reasoning here"

    def test_format_for_gemini_allow_with_context(self):
        canonical = CanonicalHookOutput(verdict="allow", context_injection="Info")
        output = self.router.output_for_gemini(canonical, "BeforeTool")
        assert output.decision == "allow"
        # For allow verdicts, context goes to hookSpecificOutput.additionalContext, not reason
        assert output.hookSpecificOutput.additionalContext == "Info"

    def test_format_for_claude_deny(self):
        canonical = CanonicalHookOutput(
            verdict="deny",
            system_message="Blocked",
            context_injection="Reasoning here",
        )
        output = self.router.output_for_claude(canonical, "PreToolUse")
        assert output.systemMessage == "Blocked"
        assert output.hookSpecificOutput.permissionDecision == "deny"
        assert output.hookSpecificOutput.additionalContext == "Reasoning here"

    def test_format_for_claude_updated_input(self):
        canonical = CanonicalHookOutput(
            verdict="allow",
            updated_input='{"arg": "value"}',
        )
        output = self.router.output_for_claude(canonical, "PreToolUse")
        assert output.hookSpecificOutput.permissionDecision == "allow"
        assert output.hookSpecificOutput.updatedInput == '{"arg": "value"}'

    def test_format_for_claude_stop_event_deny(self):
        """Stop events use decision/reason/stopReason, NOT hookSpecificOutput."""
        canonical = CanonicalHookOutput(
            verdict="deny",
            system_message="Uncommitted changes detected",
            context_injection="Please commit before stopping",
        )
        output = self.router.output_for_claude(canonical, "Stop")

        # Stop hooks use decision/reason/stopReason format
        assert output.decision == "block"
        assert output.reason == "Please commit before stopping"
        assert output.stopReason == "Uncommitted changes detected"
        assert output.systemMessage == "Uncommitted changes detected"

    def test_format_for_claude_stop_event_allow(self):
        """Stop event with allow verdict."""
        canonical = CanonicalHookOutput(
            verdict="allow",
            system_message="Session ending normally",
        )
        output = self.router.output_for_claude(canonical, "Stop")

        assert output.decision == "approve"
        assert output.stopReason == "Session ending normally"

    def test_format_for_gemini_updated_input(self):
        canonical = CanonicalHookOutput(
            verdict="allow",
            updated_input='{"arg": "value"}',
        )
        output = self.router.output_for_gemini(canonical, "BeforeTool")
        assert output.updatedInput == '{"arg": "value"}'


class TestRouterMerge:
    """Tests for HookRouter._merge_result logic."""

    def setup_method(self):
        self.router = HookRouter()

    def test_merge_metadata(self):
        target = CanonicalHookOutput(
            verdict="allow",
            metadata={"updated_input": {"a": 1}},
        )
        source = CanonicalHookOutput(
            verdict="warn",
            context_injection="Warning",
            metadata={"other": "value"},
        )

        self.router._merge_result(target, source)

        # Verdict: warn > allow
        assert target.verdict == "warn"
        assert target.context_injection == "Warning"
        assert target.metadata["updated_input"] == {"a": 1}
        assert target.metadata["other"] == "value"

    def test_merge_deny_takes_precedence(self):
        target = CanonicalHookOutput(verdict="allow")
        source = CanonicalHookOutput(verdict="deny", system_message="Blocked")

        self.router._merge_result(target, source)

        assert target.verdict == "deny"
        assert target.system_message == "Blocked"

    def test_merge_context_concatenates(self):
        target = CanonicalHookOutput(
            verdict="allow",
            context_injection="First message",
        )
        source = CanonicalHookOutput(
            verdict="allow",
            context_injection="Second message",
        )

        self.router._merge_result(target, source)

        assert "First message" in target.context_injection
        assert "Second message" in target.context_injection
