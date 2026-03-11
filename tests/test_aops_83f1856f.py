#!/usr/bin/env python3
"""
Test for aops-83f1856f: Truncate long user prompts in transcript.py abridged output.

Verifies that:
- User prompts > 500 chars are truncated in abridged mode
- Truncation is indicated with '... [truncated]' suffix
- Full mode still shows complete content
"""

import sys
from pathlib import Path

import pytest

# Add framework root to sys.path for imports
PROJECT_ROOT = Path(__file__).parent.parent
AOPS_CORE_ROOT = PROJECT_ROOT / "aops-core"
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.transcript_parser import Entry, SessionProcessor, SessionSummary


class TestUserPromptTruncation:
    @pytest.fixture
    def processor(self):
        return SessionProcessor()

    @pytest.fixture
    def session_summary(self):
        """Create a minimal session summary for testing."""
        return SessionSummary(
            uuid="test-session-123",
            summary="Test Session",
            artifact_type="test",
        )

    def test_truncate_long_user_prompt_abridged(self, processor, session_summary):
        """User prompts > 500 chars are truncated in abridged output with '... [truncated]' suffix."""
        long_message = "A" * 600
        entries = [
            Entry(type="user", message={"role": "user", "content": long_message}),
            Entry(type="assistant", message={"role": "assistant", "content": "Hello"}),
        ]

        # Abridged mode
        markdown = processor.format_session_as_markdown(
            session_summary,
            entries,
            variant="abridged",
        )

        # Should be truncated to 500 chars + suffix
        assert len(long_message) > 500
        assert "A" * 500 + "... [truncated]" in markdown
        assert "A" * 600 not in markdown

    def test_full_user_prompt_full_mode(self, processor, session_summary):
        """Full mode still shows complete content even if > 500 chars."""
        long_message = "A" * 600
        entries = [
            Entry(type="user", message={"role": "user", "content": long_message}),
            Entry(type="assistant", message={"role": "assistant", "content": "Hello"}),
        ]

        # Full mode
        markdown = processor.format_session_as_markdown(
            session_summary,
            entries,
            variant="full",
        )

        assert "A" * 600 in markdown
        assert "... [truncated]" not in markdown

    def test_truncate_meta_message_abridged(self, processor, session_summary):
        """Meta messages are truncated in abridged mode with '... [truncated]' suffix."""
        long_meta = "<command>aops</command>\n" + "B" * 600
        entries = [
            Entry(
                type="user",
                message={"role": "user", "content": long_meta},
                is_meta=True,
            ),
            Entry(type="assistant", message={"role": "assistant", "content": "Done"}),
        ]

        markdown = processor.format_session_as_markdown(
            session_summary,
            entries,
            variant="abridged",
        )

        # Should contain truncated content
        assert "... [truncated]" in markdown
        # Should NOT have the old format
        assert "\n... (truncated)" not in markdown

    def test_full_meta_message_full_mode(self, processor, session_summary):
        """Meta messages are not truncated in full mode."""
        long_meta = "<command>aops</command>\n" + "B" * 600
        entries = [
            Entry(
                type="user",
                message={"role": "user", "content": long_meta},
                is_meta=True,
            ),
            Entry(type="assistant", message={"role": "assistant", "content": "Done"}),
        ]

        markdown = processor.format_session_as_markdown(
            session_summary,
            entries,
            variant="full",
        )

        assert long_meta in markdown
        assert "... [truncated]" not in markdown

    def test_short_user_prompt_not_truncated(self, processor, session_summary):
        """Short user prompts (< 500 chars) should not be truncated in any mode."""
        short_message = "This is a short message"
        entries = [
            Entry(type="user", message={"role": "user", "content": short_message}),
            Entry(type="assistant", message={"role": "assistant", "content": "Hello"}),
        ]

        # Test both modes
        for variant in ["abridged", "full"]:
            markdown = processor.format_session_as_markdown(
                session_summary,
                entries,
                variant=variant,
            )
            assert short_message in markdown
            assert "... [truncated]" not in markdown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
