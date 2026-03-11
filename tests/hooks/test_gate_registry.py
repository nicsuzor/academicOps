from unittest.mock import patch

from lib.session_reader import build_rich_session_context


class TestGateRegistry:
    def test_build_rich_session_context_with_no_transcript(self):
        # Verify that a missing transcript returns a fallback message
        result = build_rich_session_context("/nonexistent/path.json")
        assert "(No transcript path available)" in result

    def test_build_rich_session_context_string_turns(self):
        # Verify fix for AttributeError: 'str' object has no attribute 'get'
        # caused when conversation turns are strings instead of dicts.
        # The logic that was in _custodiet_build_session_context is now
        # inlined in _custodiet_build_audit_instruction.
        with patch("lib.session_reader.extract_gate_context") as mock_extract:
            mock_extract.return_value = {
                "conversation": ["User: hello", "Assistant: hi there"],
                "prompts": [],
                "tools": [],
                "files": [],
                "errors": [],
            }
            result = build_rich_session_context("/tmp/transcript.json")
            # Should not crash on string conversation turns
            assert isinstance(result, str)
