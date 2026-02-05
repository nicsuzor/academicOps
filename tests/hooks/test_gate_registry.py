from unittest.mock import patch
from hooks import gate_registry
from hooks.gate_registry import GateContext, check_axiom_enforcer_gate
from lib.gate_model import GateVerdict


# Test fixtures: Store violation patterns as constants to avoid triggering
# the axiom enforcer when editing this test file.
# These are intentionally violating patterns used ONLY in tests.
_ENV_GET_VIOLATION = "path = os.environ.get" + '("AOPS", "/home/default")'
_EXCEPT_PASS_VIOLATION = "try:\n    x()\nexcept:\n    pass"
_CLEAN_CODE = 'path = os.environ["AOPS"]  # Fail-fast'
_DICT_GET_NONE = "value = config.get" + '("key", None)'
_ENV_GET_SHORT = "path = os.environ.get" + '("X", "/bad")'


class TestAxiomEnforcerGate:
    """Tests for check_axiom_enforcer_gate (P#8 and P#26 enforcement)."""

    def test_blocks_env_get_with_fallback(self):
        """P#8: Block os.environ.get with hardcoded default."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "content": _ENV_GET_VIOLATION,
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is not None
        assert result.verdict == GateVerdict.DENY
        assert "P#8" in result.context_injection
        assert "env_get_default" in str(result.metadata)

    def test_blocks_except_pass(self):
        """P#8: Block silent exception suppression."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "old_string": "old",
                    "new_string": _EXCEPT_PASS_VIOLATION,
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is not None
        assert result.verdict == GateVerdict.DENY
        assert "P#8" in result.context_injection

    def test_allows_clean_code(self):
        """Allow code without axiom violations."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "content": _CLEAN_CODE,
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None  # No violation, no blocking

    def test_allows_dict_get_with_none_default(self):
        """Allow dict.get with None default (safe pattern)."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "content": _DICT_GET_NONE,
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None  # None default is safe

    def test_ignores_non_pretooluse_events(self):
        """Only run on PreToolUse events."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PostToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {
                    "content": _ENV_GET_SHORT,
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None

    def test_ignores_non_code_tools(self):
        """Only check Write/Edit tools."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/test.py"},
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None


class TestGateRegistry:
    def test_custodiet_build_session_context_string_turns(self):
        # Verify fix for AttributeError: 'str' object has no attribute 'get'
        # caused when conversation turns are strings instead of dicts

        mock_gate_ctx = {"conversation": ["User: hello", "Assistant: hi there"]}

        with patch(
            "hooks.gate_registry.extract_gate_context", return_value=mock_gate_ctx
        ):
            # Should not raise AttributeError anymore
            result = gate_registry._custodiet_build_session_context(
                "/tmp/transcript.json", "sess1"
            )

            assert "[unknown]: User: hello..." in result
            assert "[unknown]: Assistant: hi there..." in result
