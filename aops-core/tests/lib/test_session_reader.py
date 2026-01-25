#!/usr/bin/env python3
"""
Tests for aops-core/lib/session_reader.py.

Tests router context extraction, particularly:
- Question extraction from agent responses (known limitations documented)
- Truncation behavior for short vs long user prompts
"""

import sys
from pathlib import Path

import pytest

# Add framework root for imports
FRAMEWORK_ROOT = Path(__file__).parent.parent.parent.parent
AOPS_CORE_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.session_reader import _extract_questions_from_text


class TestQuestionExtraction:
    """Test _extract_questions_from_text function.

    NOTE: The regex-based approach has known limitations with file paths
    and URLs containing periods. These tests document the current behavior
    and known limitations (P#78 violation - this is fundamentally an LLM task).
    """

    @pytest.mark.xfail(reason="Regex breaks on periods in file paths - known limitation per P#78")
    def test_question_extraction_file_path(self) -> None:
        """Questions containing file paths should not be truncated at the period."""
        text = "Do you want me to remove hooks from `settings.json` to eliminate duplication?"
        questions = _extract_questions_from_text(text)
        assert len(questions) == 1
        assert "settings.json" in questions[0]
        assert "eliminate duplication" in questions[0]

    @pytest.mark.xfail(reason="Regex breaks on periods in URLs - known limitation per P#78")
    def test_question_extraction_url(self) -> None:
        """Questions containing URLs should not be truncated at periods."""
        text = "Should I fetch data from https://api.example.com/v2/users?"
        questions = _extract_questions_from_text(text)
        # Should find the question
        assert len(questions) >= 1
        # Should preserve the URL intact
        assert any("https://api.example.com" in q for q in questions)

    def test_question_extraction_multiple(self) -> None:
        """Multiple questions in one response."""
        text = "Should I proceed? Also, do you want verbose output?"
        questions = _extract_questions_from_text(text)
        assert len(questions) == 2

    def test_question_extraction_code_block(self) -> None:
        """Questions after code blocks with periods."""
        text = "Here's the fix:\n```python\nprint('hello.world')\n```\nDoes this look right?"
        questions = _extract_questions_from_text(text)
        # Should find the question after the code block
        assert any("Does this look right" in q for q in questions)

    def test_question_extraction_empty_text(self) -> None:
        """Empty text should return empty list."""
        assert _extract_questions_from_text("") == []
        assert _extract_questions_from_text(None) == []

    def test_question_extraction_no_questions(self) -> None:
        """Text without questions should return empty list."""
        text = "I've completed the task. The fix is ready."
        questions = _extract_questions_from_text(text)
        assert len(questions) == 0

    def test_question_extraction_deduplicates(self) -> None:
        """Duplicate questions should be removed."""
        text = "Should I continue? Should I continue? Different question?"
        questions = _extract_questions_from_text(text)
        # Count occurrences of "Should I continue"
        continue_count = sum(1 for q in questions if "Should I continue" in q)
        assert continue_count == 1


class TestShortPromptTruncation:
    """Test that short user prompts preserve more context.

    When user sends a short response like "yes" or "all", the truncation
    limit should be higher (2000 chars) to preserve the full agent response
    context, ensuring the question being answered is visible.
    """

    def test_short_prompt_preserves_full_response(self) -> None:
        """Short prompts (≤10 chars) should preserve up to 2000 chars of agent response.

        This is the key fix for hydrator context - when user says "yes", we need
        to preserve enough context to see what they're confirming.
        """
        import json
        import tempfile
        from lib.session_reader import extract_router_context

        # Create a response that's >500 chars but <2000 chars
        # This would be truncated at 500 normally, but should be preserved for short prompts
        long_response = (
            "I've analyzed your hook configuration and found several issues. "
            "First, there are duplicate entries in both user.json and project.json. "
            "Second, the session-start hook has conflicting parameters. "
            "Third, some hooks reference paths that no longer exist. "
            "I recommend consolidating all hooks into a single configuration file. "
            "This would involve: 1) Backing up current configs, 2) Merging entries, "
            "3) Removing duplicates, 4) Updating path references, 5) Testing the result. "
            "The main file to modify would be `settings.json` in your project root. "
            "Do you want me to proceed with this consolidation and remove the "
            "redundant hook from `settings.json` to eliminate this duplication? "
            "MARKER_END_OF_QUESTION"  # Marker to verify full response preserved
        )

        session_data = [
            {"type": "user", "message": {"content": "check hooks"}},
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": long_response}]
                },
            },
            {"type": "user", "message": {"content": "yes"}},  # Short response (≤10 chars)
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for entry in session_data:
                f.write(json.dumps(entry) + "\n")
            temp_path = Path(f.name)

        try:
            context = extract_router_context(temp_path)

            # With short prompt, the full response (including the marker) should be preserved
            assert "MARKER_END_OF_QUESTION" in context, (
                f"Response was truncated for short prompt. Full response should be preserved.\n"
                f"Response length: {len(long_response)} chars\n"
                f"Context:\n{context}"
            )
        finally:
            temp_path.unlink()

    def test_normal_prompt_uses_standard_truncation(self) -> None:
        """Normal-length prompts (>10 chars) should use standard 500 char truncation."""
        import json
        import tempfile
        from lib.session_reader import extract_router_context

        # Create a response >500 chars with a marker at the end
        long_agent_response = "A" * 600 + "MARKER_SHOULD_BE_TRUNCATED"

        session_data = [
            {"type": "user", "message": {"content": "Please explain the authentication flow in detail"}},
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": long_agent_response}]
                },
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for entry in session_data:
                f.write(json.dumps(entry) + "\n")
            temp_path = Path(f.name)

        try:
            context = extract_router_context(temp_path)

            # With normal prompt, response should be truncated at ~500 chars
            # The marker at the end should NOT be present
            assert "MARKER_SHOULD_BE_TRUNCATED" not in context, (
                f"Response was not truncated for normal prompt. Context:\n{context}"
            )
            # Should show truncation indicator
            assert "..." in context
        finally:
            temp_path.unlink()

    def test_boundary_prompt_length(self) -> None:
        """Prompts of exactly 10 chars should trigger extended context."""
        import json
        import tempfile
        from lib.session_reader import extract_router_context

        long_response = "A" * 600 + "MARKER_PRESERVED"

        session_data = [
            {"type": "user", "message": {"content": "initial"}},
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": long_response}]
                },
            },
            {"type": "user", "message": {"content": "1234567890"}},  # Exactly 10 chars
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for entry in session_data:
                f.write(json.dumps(entry) + "\n")
            temp_path = Path(f.name)

        try:
            context = extract_router_context(temp_path)

            # 10 chars should trigger extended context (≤10)
            assert "MARKER_PRESERVED" in context, (
                f"10-char prompt should trigger extended context. Context:\n{context}"
            )
        finally:
            temp_path.unlink()

    def test_11_char_prompt_uses_standard_truncation(self) -> None:
        """Prompts of 11 chars should use standard truncation."""
        import json
        import tempfile
        from lib.session_reader import extract_router_context

        long_response = "A" * 600 + "MARKER_SHOULD_BE_TRUNCATED"

        session_data = [
            {"type": "user", "message": {"content": "initial"}},
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": long_response}]
                },
            },
            {"type": "user", "message": {"content": "12345678901"}},  # 11 chars
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for entry in session_data:
                f.write(json.dumps(entry) + "\n")
            temp_path = Path(f.name)

        try:
            context = extract_router_context(temp_path)

            # 11 chars is > 10, should use standard truncation
            assert "MARKER_SHOULD_BE_TRUNCATED" not in context, (
                f"11-char prompt should use standard truncation. Context:\n{context}"
            )
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
