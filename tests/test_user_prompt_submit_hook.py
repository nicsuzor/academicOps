"""Tests for UserPromptSubmit hook with temp file approach.

Tests the prompt hydration hook behavior:
- Writes context to temp file (not inline embedding)
- Returns short instruction with file path
- Cleans up old temp files
- Falls back to inline on temp file failure
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Temp directory used by the hook
TEMP_DIR = Path("/tmp/claude-hydrator")


class TestTempFileApproach:
    """Tests for temp file creation and management."""

    def test_creates_temp_file_with_context(self, tmp_path: Path) -> None:
        """Hook should write full context to temp file, not embed inline.

        The temp file should contain:
        - User prompt
        - Session context
        - Hydrator template/instructions
        """
        from hooks.user_prompt_submit import build_hydration_instruction

        prompt = "Help me fix this bug in the authentication module"

        # Create a mock transcript file
        transcript = tmp_path / "session.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"content": [{"type": "text", "text": "previous prompt"}]}}\n'
        )

        instruction = build_hydration_instruction(prompt, str(transcript))

        # Instruction should contain a temp file path
        assert "/tmp/claude-hydrator/" in instruction, "Should reference temp file path"
        assert "hydrate_" in instruction, "Should use hydrate_ prefix for temp files"

        # Instruction should be SHORT (not contain full context)
        assert (
            len(instruction) < 500
        ), f"Instruction should be short (<500 chars), got {len(instruction)}"

        # The full prompt context (session context, hydrator instructions) should NOT be in instruction
        # Note: The preview in description is OK, but session context should be in temp file
        assert (
            "previous prompt" not in instruction
        ), "Session context should be in temp file, not instruction"

    def test_temp_file_contains_full_context(self, tmp_path: Path) -> None:
        """Temp file should contain the full context for subagent to read."""
        from hooks.user_prompt_submit import build_hydration_instruction

        prompt = "Implement the new caching layer for API responses"

        transcript = tmp_path / "session.jsonl"
        transcript.write_text(
            '{"type": "user", "message": {"content": [{"type": "text", "text": "prior context"}]}}\n'
        )

        instruction = build_hydration_instruction(prompt, str(transcript))

        # Extract temp file path from instruction (path ends at backtick, comma, or whitespace)
        import re

        match = re.search(r"/tmp/claude-hydrator/hydrate_[a-z0-9_]+\.md", instruction)
        assert match, f"Should find temp file path in instruction: {instruction[:200]}"

        temp_path = Path(match.group())
        assert temp_path.exists(), f"Temp file should exist: {temp_path}"

        content = temp_path.read_text()

        # Temp file should contain the full prompt
        assert (
            "caching layer" in content.lower()
        ), "Temp file should contain user prompt"

        # Temp file should contain session context (if available)
        # This depends on extract_router_context working

    def test_instruction_tells_subagent_to_use_read_tool(self) -> None:
        """Instruction should explicitly tell subagent to use Read tool."""
        from hooks.user_prompt_submit import build_hydration_instruction

        prompt = "Simple test prompt"
        instruction = build_hydration_instruction(prompt)

        # Should mention Read tool since subagents need it
        assert (
            "Read" in instruction or "read" in instruction.lower()
        ), "Should tell subagent to read the temp file"

    def test_temp_file_uses_unique_names(self) -> None:
        """Each invocation should create a uniquely named temp file."""
        from hooks.user_prompt_submit import build_hydration_instruction

        instruction1 = build_hydration_instruction("First prompt")
        instruction2 = build_hydration_instruction("Second prompt")

        import re

        path1 = re.search(r"/tmp/claude-hydrator/[^\s\"]+", instruction1)
        path2 = re.search(r"/tmp/claude-hydrator/[^\s\"]+", instruction2)

        assert path1 and path2, "Both instructions should have temp file paths"
        assert (
            path1.group() != path2.group()
        ), "Each call should create unique temp file"


class TestTempFileCleanup:
    """Tests for temp file cleanup mechanism."""

    def test_cleans_old_temp_files_on_invocation(self, tmp_path: Path) -> None:
        """Hook should delete temp files older than 1 hour."""
        from hooks.user_prompt_submit import cleanup_old_temp_files

        # Create temp directory
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        # Create an "old" file (simulate by setting mtime)
        old_file = TEMP_DIR / "hydrate_old_test.md"
        old_file.write_text("old content")

        # Set modification time to 2 hours ago
        old_time = time.time() - (2 * 60 * 60)
        os.utime(old_file, (old_time, old_time))

        # Create a "new" file
        new_file = TEMP_DIR / "hydrate_new_test.md"
        new_file.write_text("new content")

        # Run cleanup
        cleanup_old_temp_files()

        # Old file should be deleted
        assert not old_file.exists(), "Files older than 1 hour should be deleted"

        # New file should remain
        assert new_file.exists(), "Recent files should not be deleted"

        # Cleanup test files
        if new_file.exists():
            new_file.unlink()


class TestFailFastBehavior:
    """Tests for fail-fast on infrastructure errors (AXIOM #7)."""

    def test_raises_on_write_failure(self, tmp_path: Path) -> None:
        """If temp file write fails, should raise exception (fail-fast)."""
        from hooks.user_prompt_submit import build_hydration_instruction

        prompt = "Test prompt for fail-fast behavior"

        # Patch write_temp_file to simulate failure
        with patch("hooks.user_prompt_submit.write_temp_file") as mock_write:
            mock_write.side_effect = IOError("Disk full")

            # Should raise, not silently fall back
            with pytest.raises(IOError):
                build_hydration_instruction(prompt)


class TestInstructionFormat:
    """Tests for the instruction format returned to main agent."""

    def test_instruction_spawns_prompt_hydrator_subagent(self) -> None:
        """Instruction should tell main agent to spawn prompt-hydrator."""
        from hooks.user_prompt_submit import build_hydration_instruction

        instruction = build_hydration_instruction("Test prompt")

        assert (
            "prompt-hydrator" in instruction
        ), "Should reference prompt-hydrator subagent"
        assert (
            "Task(" in instruction or "subagent" in instruction.lower()
        ), "Should instruct to spawn subagent"

    def test_instruction_uses_haiku_model(self) -> None:
        """Instruction should specify haiku model for cost efficiency."""
        from hooks.user_prompt_submit import build_hydration_instruction

        instruction = build_hydration_instruction("Test prompt")

        assert "haiku" in instruction.lower(), "Should specify haiku model"

    def test_instruction_token_budget(self) -> None:
        """Instruction should be under 150 tokens (~600 chars)."""
        from hooks.user_prompt_submit import build_hydration_instruction

        # Use a realistic long prompt
        long_prompt = "Please help me refactor the authentication module to use JWT tokens instead of session cookies. The current implementation has security vulnerabilities and we need to improve it."

        instruction = build_hydration_instruction(long_prompt)

        # Rough estimate: 4 chars per token
        estimated_tokens = len(instruction) / 4

        assert (
            estimated_tokens < 150
        ), f"Instruction should be <150 tokens, estimated {estimated_tokens:.0f}"


class TestHookIntegration:
    """Integration tests for the full hook behavior."""

    def test_hook_returns_valid_json_output(self, tmp_path: Path) -> None:
        """Hook should return properly formatted JSON with additionalContext."""
        from hooks.user_prompt_submit import main
        import io
        import sys

        # Prepare input
        input_data = {
            "prompt": "Test the full hook integration",
            "transcript_path": None,
        }

        # Capture stdout
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(json.dumps(input_data))
            sys.stdout = io.StringIO()

            # Run hook (catches SystemExit)
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0, "Hook should exit with code 0"

            output = sys.stdout.getvalue()
            result = json.loads(output)

            # Verify structure
            assert "hookSpecificOutput" in result
            assert "additionalContext" in result["hookSpecificOutput"]

            context = result["hookSpecificOutput"]["additionalContext"]
            assert (
                "/tmp/claude-hydrator/" in context
            ), "additionalContext should reference temp file"

        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_hook_handles_empty_prompt(self) -> None:
        """Hook should handle empty prompt gracefully."""
        from hooks.user_prompt_submit import build_hydration_instruction

        instruction = build_hydration_instruction("")

        # Empty prompt should still produce some instruction
        # or return empty string - either is acceptable
        assert isinstance(instruction, str)


class TestSkipHydration:
    """Tests for skipping hydration on certain prompts."""

    def test_skips_agent_notification(self) -> None:
        """Agent completion notifications should skip hydration."""
        from hooks.user_prompt_submit import should_skip_hydration

        notification = """<agent-notification>
<agent-id>abc123</agent-id>
<output-file>/tmp/output.txt</output-file>
<status>completed</status>
<summary>Agent completed.</summary>
</agent-notification>"""

        assert should_skip_hydration(notification) is True

    def test_skips_agent_notification_with_whitespace(self) -> None:
        """Agent notifications with leading whitespace should still be detected."""
        from hooks.user_prompt_submit import should_skip_hydration

        notification = "  \n<agent-notification>test</agent-notification>"
        assert should_skip_hydration(notification) is True

    def test_skips_skill_invocations(self) -> None:
        """Prompts starting with / should skip hydration (skill invocations)."""
        from hooks.user_prompt_submit import should_skip_hydration

        skill_prompts = [
            "/commit",
            "/do fix this bug",
            "/aops",
            "  /meta question",  # with leading whitespace
        ]

        for prompt in skill_prompts:
            assert (
                should_skip_hydration(prompt) is True
            ), f"'{prompt}' should skip hydration"

    def test_skips_user_ignore_shortcut(self) -> None:
        """Prompts starting with . should skip hydration (user ignore shortcut)."""
        from hooks.user_prompt_submit import should_skip_hydration

        ignore_prompts = [
            ".ignore this",
            ".",
            "  .also ignored",  # with leading whitespace
        ]

        for prompt in ignore_prompts:
            assert (
                should_skip_hydration(prompt) is True
            ), f"'{prompt}' should skip hydration"

    def test_allows_normal_prompts(self) -> None:
        """Normal user prompts should NOT skip hydration."""
        from hooks.user_prompt_submit import should_skip_hydration

        prompts = [
            "Help me fix this bug",
            "can you refactor the authentication module?",
            "What does this code do?",
            "prove it with pytests",
        ]

        for prompt in prompts:
            assert (
                should_skip_hydration(prompt) is False
            ), f"'{prompt}' should not skip hydration"

    def test_allows_empty_prompt(self) -> None:
        """Empty prompts should not skip hydration."""
        from hooks.user_prompt_submit import should_skip_hydration

        assert should_skip_hydration("") is False
        assert should_skip_hydration("   ") is False

    def test_hook_skips_hydration_for_agent_notification(self) -> None:
        """Full hook should return empty additionalContext for agent notifications."""
        from hooks.user_prompt_submit import main
        import io
        import sys

        notification = (
            "<agent-notification><status>completed</status></agent-notification>"
        )
        input_data = {"prompt": notification, "transcript_path": None}

        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(json.dumps(input_data))
            sys.stdout = io.StringIO()

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0, "Hook should exit with code 0"

            output = sys.stdout.getvalue()
            result = json.loads(output)

            # Should have empty additionalContext (no hydration)
            context = result["hookSpecificOutput"]["additionalContext"]
            assert context == "", f"Should skip hydration, got: {context[:100]}"

        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Clean up any temp files created during tests."""
    yield

    # Cleanup after test
    if TEMP_DIR.exists():
        for f in TEMP_DIR.glob("hydrate_*test*.md"):
            try:
                f.unlink()
            except Exception:
                pass
