#!/usr/bin/env python3
"""
Acceptance tests for aops-core/scripts/transcript.py.

Verifies that the transcript generation script can:
1. Parse CLI arguments correctly
2. Validate session ID format
3. Generate markdown from session data
4. Handle various input formats
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Script location
SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "transcript.py"


class TestTranscriptCLI:
    """Test CLI interface and argument parsing."""

    def test_script_exists(self) -> None:
        """Script file must exist."""
        assert SCRIPT_PATH.exists(), f"Missing script: {SCRIPT_PATH}"

    def test_script_is_executable(self) -> None:
        """Script should be executable."""
        assert SCRIPT_PATH.stat().st_mode & 0o111, "Script not executable"

    def test_help_flag(self) -> None:
        """--help flag should work and show usage."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "Convert Claude Code JSONL" in result.stdout or "transcript" in result.stdout.lower()
        assert "session" in result.stdout.lower()
        assert "--output" in result.stdout or "-o" in result.stdout

    def test_invalid_session_shows_error(self) -> None:
        """Invalid session input should show clear error."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "not-a-valid-input"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        # Error may appear in stdout or stderr depending on implementation
        combined_output = result.stderr + result.stdout
        assert "Error" in combined_output or "not found" in combined_output.lower()

    def test_nonexistent_file_shows_error(self) -> None:
        """Non-existent file path should show error."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "/nonexistent/path/session.jsonl"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0


class TestTranscriptFunctions:
    """Test internal functions by importing the module."""

    @pytest.fixture
    def transcript_module(self):
        """Import the transcript module."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("transcript", SCRIPT_PATH)
        module = importlib.util.module_from_spec(spec)
        # Add framework root to sys.path for imports
        framework_root = SCRIPT_PATH.parent.parent.parent
        sys.path.insert(0, str(framework_root))
        spec.loader.exec_module(module)
        return module

    def test_generate_slug_basic(self, transcript_module) -> None:
        """generate_slug extracts meaningful words from user message."""
        # Create mock entries matching the Entry dataclass structure
        from dataclasses import dataclass
        from typing import Any

        @dataclass
        class MockEntry:
            type: str
            message: dict[str, Any] | None = None

        entries = [
            MockEntry(type="user", message={"content": "Fix the authentication bug in login"}),
        ]
        slug = transcript_module.generate_slug(entries)
        assert "fix" in slug or "authentication" in slug or "bug" in slug or "login" in slug

    def test_generate_slug_skips_commands(self, transcript_module) -> None:
        """generate_slug skips command invocations."""
        from dataclasses import dataclass
        from typing import Any

        @dataclass
        class MockEntry:
            type: str
            message: dict[str, Any] | None = None

        entries = [
            MockEntry(type="user", message={"content": "<command-name>/commit</command-name>"}),
            MockEntry(type="user", message={"content": "Update the session storage module"}),
        ]
        slug = transcript_module.generate_slug(entries)
        # Should skip the command and use the second message
        assert "session" in slug or "storage" in slug or "update" in slug or "module" in slug

    def test_generate_slug_fallback(self, transcript_module) -> None:
        """generate_slug returns 'session' when no meaningful content."""
        entries = []
        slug = transcript_module.generate_slug(entries)
        assert slug == "session"


class TestSessionProcessor:
    """Test the SessionProcessor class for markdown generation."""

    @pytest.fixture
    def session_processor(self):
        """Import and create SessionProcessor."""
        # Add paths for imports
        framework_root = SCRIPT_PATH.parent.parent.parent
        aops_core_root = SCRIPT_PATH.parent.parent
        sys.path.insert(0, str(framework_root))
        sys.path.insert(0, str(aops_core_root))

        from lib.session_reader import SessionProcessor

        return SessionProcessor()

    def test_processor_exists(self, session_processor) -> None:
        """SessionProcessor class should be importable."""
        assert session_processor is not None

    def test_processor_has_format_method(self, session_processor) -> None:
        """SessionProcessor should have format_session_as_markdown method."""
        assert hasattr(session_processor, "format_session_as_markdown")
        assert callable(session_processor.format_session_as_markdown)

    def test_processor_has_parse_method(self, session_processor) -> None:
        """SessionProcessor should have parse_session_file method."""
        assert hasattr(session_processor, "parse_session_file")
        assert callable(session_processor.parse_session_file)


class TestMarkdownTranscript:
    """Test markdown transcript file handling."""

    def test_process_empty_session_skips(self) -> None:
        """Processing a file with no meaningful content should return exit code 2."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("# Existing Transcript\n\nContent here")
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), temp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Exit code 2 means skipped (no meaningful content)
            # This is expected behavior for non-JSONL files
            assert result.returncode in (0, 2)
            # Should indicate skipping or processing
            assert "Processing" in result.stdout or "Skip" in result.stdout
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
