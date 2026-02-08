from unittest.mock import patch

from hooks import gate_registry


class TestGateRegistry:
    def test_custodiet_build_session_context_string_turns(self):
        # Verify fix for AttributeError: 'str' object has no attribute 'get'
        # caused when conversation turns are strings instead of dicts

        mock_gate_ctx = {"conversation": ["User: hello", "Assistant: hi there"]}

        with patch("hooks.gate_registry.extract_gate_context", return_value=mock_gate_ctx):
            # Should not raise AttributeError anymore
            result = gate_registry._custodiet_build_session_context("/tmp/transcript.json", "sess1")

            assert "[unknown]: User: hello..." in result
            assert "[unknown]: Assistant: hi there..." in result
