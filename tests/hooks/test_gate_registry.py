from unittest.mock import patch

from hooks import gate_registry


class TestGateRegistry:
    def test_custodiet_build_session_context_string_turns(self):
        # Verify fix for AttributeError: 'str' object has no attribute 'get'
        # caused when conversation turns are strings instead of dicts

        mock_gate_ctx = {"conversation": ["User: hello", "Assistant: hi there"]}

        # Patch build_rich_session_context since logic moved to session_reader
        with patch("hooks.gate_registry.build_rich_session_context") as mock_build:
            mock_build.return_value = "[unknown]: User: hello...\n[unknown]: Assistant: hi there..."
            result = gate_registry._custodiet_build_session_context("/tmp/transcript.json", "sess1")

            assert "[unknown]: User: hello..." in result
            assert "[unknown]: Assistant: hi there..." in result
