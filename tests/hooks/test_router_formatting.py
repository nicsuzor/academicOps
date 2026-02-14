import sys
from pathlib import Path

import pytest

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import CanonicalHookOutput, HookRouter


class TestRouterFormatting:
    @pytest.fixture
    def router_instance(self):
        return HookRouter()

    def test_format_for_claude_stop_event_deny(self, router_instance):
        """Verify Stop hook deny verdict maps to 'block' decision and correct fields."""
        canonical_output = CanonicalHookOutput(
            verdict="deny",
            context_injection="Please create a framework reflection.",
            system_message="Session blocked: Reflection required.",
        )
        event_name = "Stop"

        result = router_instance.output_for_claude(canonical_output, event_name)

        assert result.decision == "block"
        assert result.reason == "Please create a framework reflection."
        assert result.stopReason == "Session blocked: Reflection required."

    def test_format_for_claude_stop_event_allow(self, router_instance):
        """Verify Stop hook allow verdict maps to 'approve' decision."""
        canonical_output = CanonicalHookOutput(
            verdict="allow", system_message="Session ending normally."
        )
        event_name = "Stop"

        result = router_instance.output_for_claude(canonical_output, event_name)

        assert result.decision == "approve"
        assert result.stopReason == "Session ending normally."

    def test_format_for_claude_standard_event(self, router_instance):
        """Verify non-Stop events still use hookSpecificOutput."""
        canonical_output = CanonicalHookOutput(
            verdict="deny",
            context_injection="Access denied.",
            system_message="Blocked.",
        )
        event_name = "PreToolUse"

        result = router_instance.output_for_claude(canonical_output, event_name)

        assert result.systemMessage == "Blocked."
        assert result.hookSpecificOutput is not None
        assert result.hookSpecificOutput.permissionDecision == "deny"
        assert result.hookSpecificOutput.additionalContext == "Access denied."
