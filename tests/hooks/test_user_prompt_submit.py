#!/usr/bin/env python3
"""Tests for user_prompt_submit.py hook.

Tests hydration triggering logic, skip conditions, temp file creation, and context structure.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the functions we're testing
import sys

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from user_prompt_submit import (
    build_hydration_instruction,
    cleanup_old_temp_files,
    load_template,
    should_skip_hydration,
    write_temp_file,
)


@pytest.fixture
def temp_hydrator_dir(monkeypatch):
    """Create temporary hydrator directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "claude-hydrator"
        temp_path.mkdir(parents=True)

        # Mock the get_hydration_temp_dir function
        with patch("user_prompt_submit.get_hydration_temp_dir", return_value=temp_path):
            yield temp_path


@pytest.fixture
def mock_session_state():
    """Mock session state functions."""
    with (
        patch("user_prompt_submit.set_hydration_pending") as mock_set,
        patch("user_prompt_submit.clear_hydration_pending") as mock_clear,
    ):
        yield {"set": mock_set, "clear": mock_clear}


class TestSkipConditions:
    """Test should_skip_hydration logic."""

    def test_skip_slash_command(self):
        """Test that prompts starting with / are skipped (slash commands)."""
        assert should_skip_hydration("/commit") is True
        assert should_skip_hydration("/help") is True
        assert should_skip_hydration("/ test") is True

    def test_skip_expanded_slash_command(self):
        """Test that expanded slash commands (starting with # /) are skipped."""
        assert should_skip_hydration("# /pull - Pull task") is True
        assert should_skip_hydration("# /test - Test command") is True

    def test_skip_dot_prefix(self):
        """Test that prompts starting with . are skipped (user ignore shortcut)."""
        assert should_skip_hydration(".test") is True
        assert should_skip_hydration(". ignore this") is True

    def test_skip_agent_notification(self):
        """Test that agent notifications are skipped."""
        assert should_skip_hydration("<agent-notification>Task completed") is True

    def test_skip_task_notification(self):
        """Test that task notifications are skipped."""
        assert should_skip_hydration("<task-notification>Build finished") is True

    def test_normal_prompt_not_skipped(self):
        """Test that normal prompts are not skipped."""
        assert should_skip_hydration("fix the bug in login") is False
        assert should_skip_hydration("help me implement feature X") is False
        assert should_skip_hydration("what does this code do?") is False

    def test_skip_with_whitespace(self):
        """Test that skip logic handles leading whitespace."""
        assert should_skip_hydration("  /commit") is True
        assert should_skip_hydration("\n.test") is True
        assert should_skip_hydration("\t<agent-notification>") is True


class TestTempFileCreation:
    """Test temp file creation and cleanup."""

    def test_write_temp_file_creates_file(self, temp_hydrator_dir):
        """Test that write_temp_file creates a file in correct location."""
        content = "Test content for hydration"
        temp_path = write_temp_file(content)

        # Verify file was created
        assert temp_path.exists()
        assert temp_path.parent == temp_hydrator_dir
        assert temp_path.name.startswith("hydrate_")
        assert temp_path.suffix == ".md"

        # Verify content
        assert temp_path.read_text() == content

    def test_write_temp_file_unique_names(self, temp_hydrator_dir):
        """Test that multiple temp files get unique names."""
        path1 = write_temp_file("content 1")
        path2 = write_temp_file("content 2")

        assert path1 != path2
        assert path1.exists()
        assert path2.exists()

    def test_cleanup_old_temp_files(self, temp_hydrator_dir):
        """Test that old temp files are cleaned up."""
        # Create an old file (simulate by modifying mtime)
        old_file = temp_hydrator_dir / "hydrate_old.md"
        old_file.write_text("old content")

        # Set modification time to 2 hours ago
        two_hours_ago = time.time() - (2 * 60 * 60)
        os.utime(old_file, (two_hours_ago, two_hours_ago))

        # Create a recent file
        recent_file = temp_hydrator_dir / "hydrate_recent.md"
        recent_file.write_text("recent content")

        # Run cleanup
        cleanup_old_temp_files()

        # Old file should be deleted, recent file should remain
        assert not old_file.exists(), "Old file should be deleted"
        assert recent_file.exists(), "Recent file should remain"

    def test_cleanup_handles_missing_dir(self):
        """Test that cleanup handles missing temp directory gracefully."""
        with patch(
            "user_prompt_submit.get_hydration_temp_dir",
            return_value=Path("/nonexistent/path"),
        ):
            # Should not raise
            cleanup_old_temp_files()

    def test_cleanup_handles_permission_errors(self, temp_hydrator_dir):
        """Test that cleanup ignores files that can't be deleted."""
        test_file = temp_hydrator_dir / "hydrate_locked.md"
        test_file.write_text("content")

        # Set mtime to old
        old_time = time.time() - (2 * 60 * 60)
        os.utime(test_file, (old_time, old_time))

        # Mock unlink to raise OSError
        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            # Should not raise - cleanup errors are ignored
            cleanup_old_temp_files()


class TestTemplateLoading:
    """Test template loading logic (uses shared lib.template_loader)."""

    def test_load_template_extracts_content(self):
        """Test that load_template extracts content after YAML frontmatter."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            # YAML frontmatter format: starts with ---, ends with ---
            f.write("---\nname: test\n---\nActual content here")
            temp_path = Path(f.name)

        try:
            content = load_template(temp_path)
            assert content == "Actual content here"
        finally:
            temp_path.unlink()

    def test_load_template_no_separator(self):
        """Test that load_template returns full content if no separator."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Just content, no separator")
            temp_path = Path(f.name)

        try:
            content = load_template(temp_path)
            assert content == "Just content, no separator"
        finally:
            temp_path.unlink()

    def test_load_template_missing_file(self):
        """Test that load_template raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_template(Path("/nonexistent/template.md"))


class TestHydrationContext:
    """Test hydration context building."""

    def test_build_hydration_instruction_creates_temp_file(
        self, temp_hydrator_dir, mock_session_state
    ):
        """Test that build_hydration_instruction creates temp file."""
        session_id = "test-session-abc123"
        prompt = "Fix the authentication bug"

        # Mock template loading and framework paths
        with (
            patch("user_prompt_submit.load_template") as mock_load,
            patch(
                "user_prompt_submit.load_framework_paths", return_value="# Paths\n..."
            ),
            patch("user_prompt_submit.get_task_work_state", return_value=""),
        ):
            # Set up template mocks
            mock_load.side_effect = [
                "Context: {prompt}\n{session_context}\n{framework_paths}\n{task_state}",
                "Instruction: {prompt_preview}\nFile: {temp_path}",
            ]

            instruction = build_hydration_instruction(session_id, prompt)

            # Verify temp file was created
            files = list(temp_hydrator_dir.glob("hydrate_*.md"))
            assert len(files) == 1, "Should create one temp file"

            # Verify instruction contains temp file path
            assert str(temp_hydrator_dir) in instruction
            assert "Fix the authentication bug" in instruction

            # Verify hydration state was set
            mock_session_state["set"].assert_called_once_with(session_id, prompt)

    def test_build_hydration_instruction_truncates_long_prompt(
        self, temp_hydrator_dir, mock_session_state
    ):
        """Test that long prompts are truncated in instruction preview."""
        session_id = "test-session-long"
        long_prompt = "a" * 100  # 100 chars, should be truncated to 80

        with (
            patch("user_prompt_submit.load_template") as mock_load,
            patch("user_prompt_submit.load_framework_paths", return_value=""),
            patch("user_prompt_submit.get_task_work_state", return_value=""),
        ):
            mock_load.side_effect = [
                "{prompt}\n{session_context}\n{framework_paths}\n{task_state}",
                "{prompt_preview}\n{temp_path}",
            ]

            instruction = build_hydration_instruction(session_id, long_prompt)

            # Check that truncation happened (80 chars + "...")
            assert "..." in instruction
            # The preview should be in the instruction (check via template call)
            template_calls = mock_load.return_value.format.call_args_list
            if template_calls:
                assert len(template_calls[-1][1]["prompt_preview"]) <= 83  # 80 + "..."

    def test_build_hydration_instruction_includes_session_context(
        self, temp_hydrator_dir, mock_session_state
    ):
        """Test that session context is extracted and included."""
        session_id = "test-context-session"
        prompt = "Test prompt"

        # Create a mock transcript file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"test": "data"}\n')
            transcript_path = f.name

        try:
            with (
                patch("user_prompt_submit.load_template") as mock_load,
                patch(
                    "user_prompt_submit.load_framework_paths", return_value="# Paths"
                ),
                patch(
                    "user_prompt_submit.get_task_work_state", return_value="# BD State"
                ),
                patch(
                    "user_prompt_submit.extract_router_context",
                    return_value="## Session Context\nRecent activity...",
                ),
            ):
                mock_load.side_effect = [
                    "Prompt: {prompt}\nContext: {session_context}\nPaths: {framework_paths}\nBD: {task_state}",
                    "Preview: {prompt_preview}\nFile: {temp_path}",
                ]

                instruction = build_hydration_instruction(
                    session_id, prompt, transcript_path
                )

                # Verify context was included in temp file
                temp_files = list(temp_hydrator_dir.glob("hydrate_*.md"))
                assert len(temp_files) == 1
                content = temp_files[0].read_text()

                # Verify session context was included in the temp file content
                assert "Recent activity" in content, (
                    "Session context should be in temp file"
                )
                assert "Test prompt" in content, "Prompt should be in temp file"

        finally:
            Path(transcript_path).unlink()

    def test_build_hydration_instruction_graceful_context_failure(
        self, temp_hydrator_dir, mock_session_state
    ):
        """Test that context extraction failure doesn't break hydration."""
        session_id = "test-graceful"
        prompt = "Test prompt"

        with (
            patch("user_prompt_submit.load_template") as mock_load,
            patch("user_prompt_submit.load_framework_paths", return_value=""),
            patch("user_prompt_submit.get_task_work_state", return_value=""),
            patch(
                "user_prompt_submit.extract_router_context",
                side_effect=Exception("Context extraction failed"),
            ),
        ):
            mock_load.side_effect = [
                "{prompt}{session_context}{framework_paths}{task_state}",
                "{prompt_preview}\n{temp_path}",
            ]

            # Should not raise - graceful degradation
            instruction = build_hydration_instruction(
                session_id, prompt, "/fake/transcript"
            )

            # Should still create temp file and instruction
            assert len(list(temp_hydrator_dir.glob("hydrate_*.md"))) == 1

    def test_build_hydration_instruction_io_error_propagates(
        self, temp_hydrator_dir, mock_session_state
    ):
        """Test that IOError during temp file write propagates (fail-fast)."""
        session_id = "test-io-error"
        prompt = "Test prompt"

        with (
            patch("user_prompt_submit.load_template") as mock_load,
            patch("user_prompt_submit.load_framework_paths", return_value=""),
            patch("user_prompt_submit.get_task_work_state", return_value=""),
            patch(
                "user_prompt_submit.write_temp_file", side_effect=IOError("Disk full")
            ),
        ):
            mock_load.side_effect = [
                "{prompt}{session_context}{framework_paths}{task_state}",
                "{prompt_preview}\n{temp_path}",
            ]

            # Should propagate IOError for fail-fast behavior
            with pytest.raises(IOError, match="Disk full"):
                build_hydration_instruction(session_id, prompt)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
