#!/usr/bin/env python3
import sys
from pathlib import Path
import pytest

# Add framework root to sys.path for imports
PROJECT_ROOT = Path(__file__).parent.parent
AOPS_CORE_ROOT = PROJECT_ROOT / "aops-core"
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.transcript_parser import SessionProcessor, ConversationTurn

class TestUserPromptTruncation:
    @pytest.fixture
    def processor(self):
        return SessionProcessor()

    def test_truncate_long_user_prompt_abridged(self, processor):
        """User prompts > 500 chars are truncated in abridged output with '... [truncated]' suffix."""
        long_message = "A" * 600
        turns = [
            ConversationTurn(
                turn_number=1,
                user_message=long_message,
                assistant_message="Hello",
                is_meta=False
            )
        ]
        
        # Abridged mode (variant="abridged")
        markdown = processor.format_session_as_markdown(turns, variant="abridged")
        
        # Should be truncated to 500 chars + suffix
        assert len(long_message) > 500
        assert "A" * 500 + "... [truncated]" in markdown
        assert long_message not in markdown

    def test_full_user_prompt_full_mode(self, processor):
        """Full mode still shows complete content even if > 500 chars."""
        long_message = "A" * 600
        turns = [
            ConversationTurn(
                turn_number=1,
                user_message=long_message,
                assistant_message="Hello",
                is_meta=False
            )
        ]
        
        # Full mode (variant="full")
        markdown = processor.format_session_as_markdown(turns, variant="full")
        
        assert long_message in markdown
        assert "... [truncated]" not in markdown

    def test_truncate_meta_message_abridged(self, processor):
        """Meta messages are truncated in abridged mode with '... [truncated]' suffix."""
        long_meta = "<command>aops</command>\\n" + "B" * 600
        turns = [
            ConversationTurn(
                turn_number=1,
                user_message=long_meta,
                assistant_message="Done",
                is_meta=True
            )
        ]
        
        markdown = processor.format_session_as_markdown(turns, variant="abridged")
        
        assert "B" * 400 in markdown # Should contain part of it
        assert "... [truncated]" in markdown
        assert "\\n... (truncated)" not in markdown

    def test_full_meta_message_full_mode(self, processor):
        """Meta messages are not truncated in full mode."""
        long_meta = "<command>aops</command>\\n" + "B" * 600
        turns = [
            ConversationTurn(
                turn_number=1,
                user_message=long_meta,
                assistant_message="Done",
                is_meta=True
            )
        ]
        
        markdown = processor.format_session_as_markdown(turns, variant="full")
        
        assert long_meta in markdown
        assert "... [truncated]" not in markdown

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
