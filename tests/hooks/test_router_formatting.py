import sys
from pathlib import Path
import pytest

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks import router

class TestRouterFormatting:
    def test_format_for_claude_stop_event_deny(self):
        """Verify Stop hook deny verdict maps to 'block' decision and correct fields."""
        canonical_output = {
            "verdict": "deny",
            "context_injection": "Please create a framework reflection.",
            "system_message": "Session blocked: Reflection required."
        }
        event_name = "Stop"

        result = router.format_for_claude(canonical_output, event_name)

        # Stop hook output format:
        # decision: "block" (mapped from deny)
        # reason: "Please create a framework reflection." (shown to agent)
        # stopReason: "Session blocked: Reflection required." (shown to user)
        # systemMessage: "Session blocked: Reflection required." (shown to user)
        
        assert result["decision"] == "block"
        assert result["reason"] == "Please create a framework reflection."
        assert result["stopReason"] == "Session blocked: Reflection required."
        assert result["systemMessage"] == "Session blocked: Reflection required."
        
        # Verify hookSpecificOutput is NOT present for Stop events
        assert "hookSpecificOutput" not in result

    def test_format_for_claude_stop_event_allow(self):
        """Verify Stop hook allow verdict maps to 'allow' decision."""
        canonical_output = {
            "verdict": "allow",
            # context_injection might be missing if allowed, or present as info
            "system_message": "Session ending normally."
        }
        event_name = "Stop"

        result = router.format_for_claude(canonical_output, event_name)

        assert result["decision"] == "allow"
        assert result["stopReason"] == "Session ending normally."
        assert "reason" not in result
        assert "hookSpecificOutput" not in result

    def test_format_for_claude_standard_event(self):
        """Verify non-Stop events still use hookSpecificOutput."""
        canonical_output = {
            "verdict": "deny",
            "context_injection": "Access denied.",
            "system_message": "Blocked."
        }
        event_name = "PreToolUse"

        result = router.format_for_claude(canonical_output, event_name)

        assert "decision" not in result
        assert "hookSpecificOutput" in result
        hso = result["hookSpecificOutput"]
        assert hso["permissionDecision"] == "deny"
        assert hso["additionalContext"] == "Access denied."
        assert result["systemMessage"] == "Blocked."
