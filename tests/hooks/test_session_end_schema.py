import pytest
import sys
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import HookRouter, CanonicalHookOutput, ClaudeStopHookOutput, ClaudeGeneralHookOutput

class TestSessionEndSchema:
    @pytest.fixture
    def router_instance(self):
        return HookRouter()

    def test_session_end_uses_stop_schema(self, router_instance):
        """Verify SessionEnd event uses ClaudeStopHookOutput schema, not hookSpecificOutput."""
        canonical_output = CanonicalHookOutput(
            verdict="allow",
            system_message="Session ending."
        )
        event_name = "SessionEnd"

        result = router_instance.output_for_claude(canonical_output, event_name)

        # It must be a ClaudeStopHookOutput
        assert isinstance(result, ClaudeStopHookOutput)
        assert not isinstance(result, ClaudeGeneralHookOutput)
        
        # It must NOT have hookSpecificOutput
        assert not hasattr(result, "hookSpecificOutput")
        
        # Check expected fields
        assert result.decision == "approve"
        assert result.stopReason == "Session ending."

    def test_session_end_block(self, router_instance):
        """Verify SessionEnd event uses ClaudeStopHookOutput schema for blocks."""
        canonical_output = CanonicalHookOutput(
            verdict="deny",
            system_message="Blocked for reason.",
            context_injection="Reason details"
        )
        event_name = "SessionEnd"

        result = router_instance.output_for_claude(canonical_output, event_name)

        assert isinstance(result, ClaudeStopHookOutput)
        assert result.decision == "block"
        assert result.stopReason == "Blocked for reason."
        assert result.reason == "Reason details"
