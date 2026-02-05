#!/usr/bin/env python3
"""Tests for hook_utils.py temp path resolution.

Specifically tests that Gemini CLI temp paths are correctly resolved when:
- transcript_path contains .gemini but hook's cwd is different
- GEMINI_CLI env var is not set
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.hook_utils import get_hook_temp_dir


class TestGeminiTempPathFromTranscript:
    """Test that transcript_path containing .gemini triggers Gemini path resolution."""

    def test_gemini_path_detected_from_transcript_path(self, tmp_path):
        """Test that .gemini in transcript_path is detected even without GEMINI_CLI env."""
        # Simulate Gemini temp structure: ~/.gemini/tmp/<hash>/chats/session.json
        gemini_tmp = tmp_path / ".gemini" / "tmp" / "abc123hash"
        chats_dir = gemini_tmp / "chats"
        chats_dir.mkdir(parents=True)
        transcript_file = chats_dir / "session-2026-01-28.json"
        transcript_file.write_text("{}")

        input_data = {"transcript_path": str(transcript_file)}

        # Ensure GEMINI_CLI is NOT set and cwd doesn't have .gemini
        with patch.dict(os.environ, {}, clear=True):
            # Clear any GEMINI_CLI or TMPDIR that might be set
            os.environ.pop("GEMINI_CLI", None)
            os.environ.pop("TMPDIR", None)
            os.environ.pop("AOPS_GEMINI_TEMP_ROOT", None)

            # Mock cwd to NOT have .gemini
            with patch(
                "lib.hook_utils.Path.cwd", return_value=Path("/some/other/path")
            ):
                result = get_hook_temp_dir("hydrator", input_data)

        # Should resolve to gemini_tmp/hydrator, NOT Claude's path
        assert ".gemini" in str(result), f"Expected .gemini in path, got: {result}"
        assert result == gemini_tmp / "hydrator"
        assert result.exists()

    def test_gemini_path_with_jsonl_transcript(self, tmp_path):
        """Test that .jsonl transcript files also work."""
        gemini_tmp = tmp_path / ".gemini" / "tmp" / "def456hash"
        logs_dir = gemini_tmp / "logs"
        logs_dir.mkdir(parents=True)
        transcript_file = logs_dir / "session.jsonl"
        transcript_file.write_text("{}\n")

        input_data = {"transcript_path": str(transcript_file)}

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_CLI", None)
            os.environ.pop("TMPDIR", None)
            os.environ.pop("AOPS_GEMINI_TEMP_ROOT", None)

            with patch("lib.hook_utils.Path.cwd", return_value=Path("/other/cwd")):
                result = get_hook_temp_dir("hydrator", input_data)

        assert ".gemini" in str(result)
        assert result == gemini_tmp / "hydrator"

    def test_claude_fallback_when_no_gemini_in_transcript(self, tmp_path):
        """Test that Claude path is used when transcript_path doesn't contain .gemini."""
        # Create a Claude-style transcript path
        claude_tmp = tmp_path / ".claude" / "projects" / "test-project"
        claude_tmp.mkdir(parents=True)
        transcript_file = claude_tmp / "transcript.json"
        transcript_file.write_text("{}")

        input_data = {"transcript_path": str(transcript_file)}

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_CLI", None)
            os.environ.pop("TMPDIR", None)
            os.environ.pop("AOPS_GEMINI_TEMP_ROOT", None)

            # Mock cwd to not have .gemini and mock get_claude_project_folder
            with patch("lib.hook_utils.Path.cwd", return_value=Path("/some/path")):
                with patch(
                    "lib.hook_utils.get_claude_project_folder",
                    return_value="-some-path",
                ):
                    result = get_hook_temp_dir("hydrator", input_data)

        # Should fall through to Claude default
        assert ".claude" in str(result)

    def test_tmpdir_env_takes_priority(self, tmp_path):
        """Test that TMPDIR env var takes priority over transcript_path detection."""
        # Set up both Gemini transcript and TMPDIR
        gemini_tmp = tmp_path / ".gemini" / "tmp" / "hash123"
        chats_dir = gemini_tmp / "chats"
        chats_dir.mkdir(parents=True)
        transcript_file = chats_dir / "session.json"
        transcript_file.write_text("{}")

        custom_tmp = tmp_path / "custom_tmp"
        custom_tmp.mkdir()

        input_data = {"transcript_path": str(transcript_file)}

        with patch.dict(os.environ, {"TMPDIR": str(custom_tmp)}, clear=True):
            result = get_hook_temp_dir("hydrator", input_data)

        # TMPDIR should take priority
        assert result == custom_tmp / "hydrator"

    def test_aops_gemini_temp_root_takes_priority(self, tmp_path):
        """Test that AOPS_GEMINI_TEMP_ROOT takes priority over transcript detection."""
        gemini_tmp = tmp_path / ".gemini" / "tmp" / "hash123"
        chats_dir = gemini_tmp / "chats"
        chats_dir.mkdir(parents=True)
        transcript_file = chats_dir / "session.json"
        transcript_file.write_text("{}")

        explicit_root = tmp_path / "explicit_gemini_root"
        explicit_root.mkdir()

        input_data = {"transcript_path": str(transcript_file)}

        with patch.dict(
            os.environ, {"AOPS_GEMINI_TEMP_ROOT": str(explicit_root)}, clear=True
        ):
            result = get_hook_temp_dir("hydrator", input_data)

        # Explicit root should take priority
        assert result == explicit_root / "hydrator"


class TestGeminiTempPathEdgeCases:
    """Edge cases for Gemini temp path resolution."""

    def test_nonexistent_transcript_parent_fails_fast(self, tmp_path):
        """Test that nonexistent transcript parent directory raises RuntimeError.

        FAIL-FAST: When Gemini provides a transcript_path with .gemini,
        the hash directory MUST exist. If it doesn't, fail immediately -
        no fallback to Claude paths, no silent directory creation.
        """
        # Transcript path where hash dir doesn't exist
        fake_path = (
            tmp_path / ".gemini" / "tmp" / "nonexistent" / "chats" / "session.json"
        )

        input_data = {"transcript_path": str(fake_path)}

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_CLI", None)
            os.environ.pop("TMPDIR", None)
            os.environ.pop("AOPS_GEMINI_TEMP_ROOT", None)

            with pytest.raises(RuntimeError) as exc_info:
                get_hook_temp_dir("hydrator", input_data)

        # Should fail with clear error message
        assert "hash directory missing" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_no_input_data_falls_through(self):
        """Test that None input_data falls through to Claude default."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_CLI", None)
            os.environ.pop("TMPDIR", None)
            os.environ.pop("AOPS_GEMINI_TEMP_ROOT", None)

            with patch("lib.hook_utils.Path.cwd", return_value=Path("/some/path")):
                with patch(
                    "lib.hook_utils.get_claude_project_folder",
                    return_value="-some-path",
                ):
                    result = get_hook_temp_dir("hydrator", None)

        assert ".claude" in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
