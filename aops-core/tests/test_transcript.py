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
        assert "Generate session transcript" in result.stdout
        assert "session" in result.stdout
        assert "--format" in result.stdout

    def test_invalid_session_shows_error(self) -> None:
        """Invalid session input should show clear error."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "not-a-valid-input"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "Error" in result.stderr or "Invalid" in result.stderr

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

    def test_is_session_id_valid_ids(self, transcript_module) -> None:
        """Valid session IDs should be recognized."""
        assert transcript_module.is_session_id("a5234d3e")
        assert transcript_module.is_session_id("017c6ae7-c910-4fa8-b033-633c7866370e")
        assert transcript_module.is_session_id("ABCDEF12")
        assert transcript_module.is_session_id("abcdef1234567890")

    def test_is_session_id_invalid_ids(self, transcript_module) -> None:
        """Invalid session IDs should be rejected."""
        assert not transcript_module.is_session_id("abc")  # too short
        assert not transcript_module.is_session_id("not-hex-chars")
        assert not transcript_module.is_session_id("12345zz8")  # contains 'z'

    def test_extract_workflow_markers(self, transcript_module) -> None:
        """Workflow markers should be extracted from content."""
        content = "**Workflow**: tdd\nWith require_acceptance_test guardrail"
        markers = transcript_module.extract_workflow_markers(content)
        assert "Workflow: tdd" in markers
        assert "require_acceptance_test" in markers

    def test_extract_workflow_markers_empty(self, transcript_module) -> None:
        """No markers in plain content."""
        content = "Just some regular text without markers"
        markers = transcript_module.extract_workflow_markers(content)
        assert len(markers) == 0


class TestGenerateFrameworkSummary:
    """Test the core markdown generation function."""

    @pytest.fixture
    def transcript_module(self):
        """Import the transcript module."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("transcript", SCRIPT_PATH)
        module = importlib.util.module_from_spec(spec)
        framework_root = SCRIPT_PATH.parent.parent.parent
        sys.path.insert(0, str(framework_root))
        spec.loader.exec_module(module)
        return module

    def test_generate_framework_summary_basic(self, transcript_module) -> None:
        """Generate markdown from mock session data."""
        from dataclasses import dataclass, field
        from typing import Any

        @dataclass
        class MockEntry:
            type: str
            message: dict[str, Any] | None = None
            content: str | None = None

        @dataclass
        class MockSessionSummary:
            uuid: str = "abc12345-test"
            summary: str = "Test Session"
            artifact_type: str = "test"
            created_at: str = ""
            edited_files: list[str] = field(default_factory=list)
            details: dict = field(default_factory=dict)

        # Create mock entries simulating a simple session
        entries = [
            MockEntry(type="user", message={"content": "Please fix the bug"}),
            MockEntry(
                type="assistant",
                message={
                    "content": [
                        {"type": "text", "text": "I'll fix that bug now."},
                        {"type": "tool_use", "name": "Edit"},
                    ]
                },
            ),
        ]
        session = MockSessionSummary(edited_files=["src/main.py"])

        # Generate markdown
        markdown = transcript_module.generate_framework_summary(
            entries, session, format_type="full"
        )

        # Verify structure
        assert "# Session Transcript: abc12345" in markdown
        assert "Test Session" in markdown
        assert "## User (Turn 1)" in markdown
        assert "fix the bug" in markdown
        assert "## Assistant (Turn 1)" in markdown
        assert "I'll fix that bug" in markdown
        assert "Edit" in markdown  # Tool name
        assert "Files edited" in markdown
        assert "main.py" in markdown

    def test_generate_framework_summary_abridged(self, transcript_module) -> None:
        """Abridged format should truncate long content."""
        from dataclasses import dataclass, field
        from typing import Any

        @dataclass
        class MockEntry:
            type: str
            message: dict[str, Any] | None = None

        @dataclass
        class MockSessionSummary:
            uuid: str = "abc12345"
            summary: str = "Test"
            artifact_type: str = "test"
            created_at: str = ""
            edited_files: list[str] = field(default_factory=list)
            details: dict = field(default_factory=dict)

        # Create entry with very long content
        long_content = "x" * 1500
        entries = [
            MockEntry(type="assistant", message={"content": long_content}),
        ]
        session = MockSessionSummary()

        # Abridged should truncate
        markdown = transcript_module.generate_framework_summary(
            entries, session, format_type="abridged"
        )

        # Should be truncated with "..."
        assert "..." in markdown
        assert len(markdown) < len(long_content) + 500  # Much shorter


class TestMarkdownTranscript:
    """Test markdown transcript file handling."""

    def test_copy_existing_markdown(self) -> None:
        """Reading an existing markdown file should just return it."""
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
            assert result.returncode == 0
            assert "Existing Transcript" in result.stdout
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
