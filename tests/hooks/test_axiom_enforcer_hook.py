"""Tests for the Axiom Enforcer Gate."""

import sys
from pathlib import Path
import pytest

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

# Ensure lib is also in path
LIB_DIR = AOPS_CORE_DIR / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from hooks.gate_registry import GateContext, check_axiom_enforcer_gate


class TestAxiomEnforcerGate:
    """Test the Axiom Enforcer Gate logic."""

    @pytest.fixture
    def gate_context_factory(self):
        def _make_context(tool_name, tool_input, session_id="sess-1", event_name="PreToolUse"):
            return GateContext(
                session_id=session_id,
                event_name=event_name,
                input_data={
                    "hook_event_name": event_name,
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "session_id": session_id,
                },
            )
        return _make_context

    def test_axiom_enforcer_blocks_fallback(self, gate_context_factory):
        """Should block code with P#8 violation (fallback pattern)."""
        code = 'val = os.environ.get("VAR", "default")'
        ctx = gate_context_factory("Edit", {"new_string": code})

        result = check_axiom_enforcer_gate(ctx)

        assert result is not None
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "AXIOM ENFORCEMENT BLOCKED" in result["hookSpecificOutput"]["additionalContext"]
        assert "P#8" in result["hookSpecificOutput"]["additionalContext"]

    def test_axiom_enforcer_allows_clean_code(self, gate_context_factory):
        """Should allow code without violations."""
        code = 'val = os.environ["VAR"]'
        ctx = gate_context_factory("Edit", {"new_string": code})

        result = check_axiom_enforcer_gate(ctx)

        assert result is None

    def test_axiom_enforcer_handles_write_tool(self, gate_context_factory):
        """Should check 'content' for Write tool."""
        code = 'try:\n    pass\nexcept:\n    pass'
        ctx = gate_context_factory("Write", {"content": code})

        result = check_axiom_enforcer_gate(ctx)

        assert result is not None
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "Silent exception suppression" in result["hookSpecificOutput"]["additionalContext"]

    def test_axiom_enforcer_handles_gemini_tools(self, gate_context_factory):
        """Should check Gemini-specific tool names."""
        code = 'config.get("key", "hardcoded")'
        
        # replace_file_content
        ctx1 = gate_context_factory("replace_file_content", {"new_string": code})
        assert check_axiom_enforcer_gate(ctx1) is not None

        # write_to_file
        ctx2 = gate_context_factory("write_to_file", {"content": code})
        assert check_axiom_enforcer_gate(ctx2) is not None

    def test_axiom_enforcer_handles_multi_replace(self, gate_context_factory):
        """Should check all replacements in multi_replace_file_content."""
        ctx = gate_context_factory("multi_replace_file_content", {
            "replacements": [
                {"new_string": "x = 1"},
                {"new_string": "y = z or 'fallback'"}
            ]
        })

        result = check_axiom_enforcer_gate(ctx)
        assert result is not None
        assert "Value fallback using 'or default'" in result["hookSpecificOutput"]["additionalContext"]

