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
SCRIPT_PATH = Path(__file__).parent.parent / "aops-core" / "scripts" / "transcript.py"


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
        assert (
            "Convert Claude Code JSONL" in result.stdout
            or "transcript" in result.stdout.lower()
        )
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

    def test_generate_session_slug_basic(self, transcript_module) -> None:
        """generate_session_slug extracts meaningful words from user message."""
        from lib.transcript_parser import Entry, SessionProcessor

        processor = SessionProcessor()
        entries = [
            Entry(
                type="user", message={"content": "Fix the authentication bug in login"}
            ),
        ]
        slug = processor.generate_session_slug(entries)
        assert (
            "fix" in slug
            or "authentication" in slug
            or "bug" in slug
            or "login" in slug
        )

    def test_generate_session_slug_skips_commands(self, transcript_module) -> None:
        """generate_session_slug skips command invocations."""
        from lib.transcript_parser import Entry, SessionProcessor

        processor = SessionProcessor()
        entries = [
            Entry(
                type="user", message={"content": "<command-name>/commit</command-name>"}
            ),
            Entry(
                type="user", message={"content": "Update the session storage module"}
            ),
        ]
        slug = processor.generate_session_slug(entries)
        # Should skip the command and use the second message
        assert (
            "session" in slug
            or "storage" in slug
            or "update" in slug
            or "module" in slug
        )

    def test_generate_session_slug_fallback(self, transcript_module) -> None:
        """generate_session_slug returns 'session' when no meaningful content."""
        from lib.transcript_parser import SessionProcessor

        processor = SessionProcessor()
        entries = []
        slug = processor.generate_session_slug(entries)
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

        from lib.transcript_parser import SessionProcessor

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
        import os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Existing Transcript\n\nContent here")
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), temp_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=os.environ,
            )
            # Exit code 2 means skipped (no meaningful content)
            # This is expected behavior for non-JSONL files
            assert result.returncode in (0, 2)
            # Should indicate skipping or processing
            assert "Processing" in result.stdout or "Skip" in result.stdout
        finally:
            Path(temp_path).unlink()


class TestOutputPathHandling:
    """Test -o flag output path handling."""

    def test_output_directory_generates_filename(self) -> None:
        """When -o is a directory, should auto-generate filename in that directory."""
        import os
        # Create a minimal valid JSONL session
        session_content = """{"type":"user","message":{"content":"Hello world"}}
{"type":"assistant","message":{"content":"Hi there! How can I help?"}}
{"type":"user","message":{"content":"Fix the bug please"}}
{"type":"assistant","message":{"content":"I'll fix that bug now."}}
"""
        with tempfile.TemporaryDirectory() as output_dir:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".jsonl", delete=False
            ) as f:
                f.write(session_content)
                session_path = f.name

            try:
                result = subprocess.run(
                    [sys.executable, str(SCRIPT_PATH), session_path, "-o", output_dir],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=os.environ,
                )

                # Should succeed
                assert result.returncode == 0, f"Failed: {result.stderr}"

                # Should create files in the output directory
                output_files = list(Path(output_dir).glob("*.md"))
                assert len(output_files) >= 1, (
                    f"No output files in {output_dir}. "
                    f"stdout: {result.stdout}, stderr: {result.stderr}"
                )

                # Files should have proper names (not just "-full.md")
                for f in output_files:
                    assert not f.name.startswith("-"), (
                        f"File {f.name} starts with dash - missing filename prefix"
                    )
            finally:
                Path(session_path).unlink(missing_ok=True)


class TestReflectionExtraction:
    """Test Framework Reflection extraction from session logs.

    CRITICAL: These tests verify transcript.py can find and parse reflections.
    They must pass BEFORE making changes to the reflection format.
    """

    @pytest.fixture
    def parser_module(self):
        """Import the transcript_parser module."""
        framework_root = SCRIPT_PATH.parent.parent.parent
        aops_core_root = SCRIPT_PATH.parent.parent
        sys.path.insert(0, str(framework_root))
        sys.path.insert(0, str(aops_core_root))
        from lib import transcript_parser
        return transcript_parser

    def test_parse_framework_reflection_basic(self, parser_module) -> None:
        """parse_framework_reflection extracts fields from valid reflection."""
        text = """
## Framework Reflection

**Prompts**: Fix the authentication bug
**Guidance received**: N/A
**Followed**: Yes
**Outcome**: success
**Accomplishments**: Fixed the bug, added tests
**Friction points**: none
**Root cause** (if not success): N/A
**Proposed changes**: none
**Next step**: Deploy to production
**Workflow improvements**: none
**JIT context needed**: none
**Context distractions**: none
**User tone**: 0.5
"""
        result = parser_module.parse_framework_reflection(text)
        assert result is not None, "Failed to parse valid reflection"
        assert result.get("outcome") == "success"
        assert "Fix the authentication bug" in result.get("prompts", "")
        assert "Deploy to production" in result.get("next_step", "")

    def test_parse_framework_reflection_with_lists(self, parser_module) -> None:
        """parse_framework_reflection handles bullet-list fields."""
        text = """
## Framework Reflection

**Prompts**: Multiple prompts here
**Outcome**: partial
**Accomplishments**:
- Completed task A
- Completed task B
- Started task C
**Friction points**:
- Issue with API
- Slow build times
**Next step**: Continue work tomorrow
"""
        result = parser_module.parse_framework_reflection(text)
        assert result is not None
        assert len(result.get("accomplishments", [])) == 3
        assert len(result.get("friction_points", [])) == 2
        assert "Completed task A" in result["accomplishments"]

    def test_parse_framework_reflection_missing_returns_none(self, parser_module) -> None:
        """parse_framework_reflection returns None for text without reflection."""
        text = """
# Regular Session Content

This is just normal session content with no reflection section.

## Some Other Header

More content here.
"""
        result = parser_module.parse_framework_reflection(text)
        assert result is None, "Should return None when no reflection present"

    def test_parse_framework_reflection_case_insensitive(self, parser_module) -> None:
        """Reflection header matching is case-insensitive."""
        text = """
## framework reflection

**Outcome**: success
**Accomplishments**: Did the thing
"""
        result = parser_module.parse_framework_reflection(text)
        assert result is not None, "Should match case-insensitive header"
        assert result.get("outcome") == "success"

    def test_extract_reflection_from_live_logs(self, parser_module) -> None:
        """CRITICAL: Verify extraction works on actual live session logs.

        This test finds recent session logs that contain reflections and
        verifies the extraction pipeline works end-to-end.
        """
        import glob
        from pathlib import Path

        # Find session transcripts with Framework Reflections
        sessions_dir = Path.home() / "writing" / "sessions" / "claude"
        reflection_files = []

        if sessions_dir.exists():
            for md_file in sessions_dir.glob("*-full.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if "## Framework Reflection" in content or "## framework reflection" in content.lower():
                        reflection_files.append(md_file)
                        if len(reflection_files) >= 3:
                            break
                except Exception:
                    continue

        # We must have at least one session with a reflection to test against
        assert len(reflection_files) > 0, (
            "CRITICAL: No live session logs with Framework Reflections found! "
            f"Searched in {sessions_dir}. "
            "Cannot verify extraction works on real data."
        )

        # Test extraction on each found file
        successful_extractions = 0
        extraction_details = []
        for md_file in reflection_files:
            content = md_file.read_text(encoding="utf-8")
            result = parser_module.parse_framework_reflection(content)
            if result is not None and len(result) > 0:
                successful_extractions += 1
                extraction_details.append(
                    f"{md_file.name}: extracted {len(result)} fields ({list(result.keys())})"
                )

        assert successful_extractions > 0, (
            f"Found {len(reflection_files)} files with reflection headers but "
            "failed to extract any reflections. Parser may be broken."
        )
        # Log what we found for visibility
        print(f"\n✅ Successfully extracted reflections from {successful_extractions} live logs:")
        for detail in extraction_details:
            print(f"   {detail}")


class TestReflectionToInsights:
    """Test reflection_to_insights produces schema-compliant output.

    Verifies that the output matches specs/session-insights-prompt.md schema:
    - Required fields: session_id, date, project, summary, outcome, accomplishments
    - Framework Reflection data nested in framework_reflections array
    """

    @pytest.fixture
    def parser_module(self):
        """Import transcript_parser module."""
        framework_root = SCRIPT_PATH.parent.parent.parent
        aops_core_root = SCRIPT_PATH.parent.parent
        sys.path.insert(0, str(framework_root))
        sys.path.insert(0, str(aops_core_root))
        from lib import transcript_parser
        return transcript_parser

    @pytest.fixture
    def insights_module(self):
        """Import insights_generator module."""
        framework_root = SCRIPT_PATH.parent.parent.parent
        aops_core_root = SCRIPT_PATH.parent.parent
        sys.path.insert(0, str(framework_root))
        sys.path.insert(0, str(aops_core_root))
        from lib import insights_generator
        return insights_generator

    def test_reflection_to_insights_has_required_fields(self, parser_module) -> None:
        """reflection_to_insights output has all required fields."""
        reflection = {
            "prompts": "Fix authentication bug",
            "outcome": "success",
            "accomplishments": ["Fixed the bug", "Added tests"],
            "friction_points": ["API was slow"],
            "proposed_changes": ["Add caching"],
        }

        result = parser_module.reflection_to_insights(
            reflection,
            session_id="abc12345",
            date="2026-01-30",
            project="test-project",
        )

        # Required fields
        assert "session_id" in result
        assert "date" in result
        assert "project" in result
        assert "summary" in result
        assert "outcome" in result
        assert "accomplishments" in result

    def test_reflection_to_insights_framework_reflections_nested(self, parser_module) -> None:
        """Framework Reflection data is nested in framework_reflections array."""
        reflection = {
            "prompts": "Implement feature X",
            "guidance_received": "Use TDD workflow",
            "followed": True,
            "outcome": "partial",
            "accomplishments": ["Created tests"],
            "friction_points": ["Build was slow"],
            "root_cause": "Missing dependency",
            "proposed_changes": ["Add build cache"],
            "next_step": "Continue tomorrow",
        }

        result = parser_module.reflection_to_insights(
            reflection,
            session_id="def67890",
            date="2026-01-31",
            project="feature-project",
        )

        # Must have framework_reflections as array
        assert "framework_reflections" in result
        assert isinstance(result["framework_reflections"], list)
        assert len(result["framework_reflections"]) == 1

        # Check nested reflection content
        nested = result["framework_reflections"][0]
        assert nested["prompts"] == "Implement feature X"
        assert nested["guidance_received"] == "Use TDD workflow"
        assert nested["followed"] is True
        assert nested["outcome"] == "partial"
        assert nested["accomplishments"] == ["Created tests"]
        assert nested["friction_points"] == ["Build was slow"]
        assert nested["root_cause"] == "Missing dependency"
        assert nested["proposed_changes"] == ["Add build cache"]
        assert nested["next_step"] == "Continue tomorrow"

    def test_reflection_to_insights_no_top_level_reflection_fields(self, parser_module) -> None:
        """Top-level should NOT have reflection-specific fields."""
        reflection = {
            "prompts": "Test prompt",
            "guidance_received": "Some guidance",
            "followed": True,
            "outcome": "success",
            "accomplishments": ["Done"],
            "root_cause": None,
            "next_step": "Nothing",
        }

        result = parser_module.reflection_to_insights(
            reflection,
            session_id="ghi11111",
            date="2026-02-01",
            project="clean-project",
        )

        # These should NOT be at top level (only in framework_reflections)
        assert "prompts" not in result
        assert "guidance_received" not in result
        assert "followed" not in result
        assert "root_cause" not in result
        assert "next_step" not in result

    def test_reflection_to_insights_validates_against_schema(
        self, parser_module, insights_module
    ) -> None:
        """reflection_to_insights output passes schema validation."""
        reflection = {
            "prompts": "Full workflow test",
            "guidance_received": "Hydrator suggested audit",
            "followed": True,
            "outcome": "success",
            "accomplishments": ["Implemented feature", "Ran tests"],
            "friction_points": [],
            "proposed_changes": [],
            "root_cause": None,
            "next_step": None,
        }

        result = parser_module.reflection_to_insights(
            reflection,
            session_id="jkl22222",
            date="2026-02-02",
            project="validated-project",
        )

        # This should NOT raise InsightsValidationError
        insights_module.validate_insights_schema(result)


class TestExitCodeExtraction:
    """Test exit code extraction from Bash tool results.

    Verifies that exit codes are properly extracted from tool results
    and displayed in transcripts.
    """

    @pytest.fixture
    def parser_module(self):
        """Import transcript_parser module."""
        framework_root = SCRIPT_PATH.parent.parent.parent
        aops_core_root = SCRIPT_PATH.parent.parent
        sys.path.insert(0, str(framework_root))
        sys.path.insert(0, str(aops_core_root))

        from lib import transcript_parser

        return transcript_parser

    def test_extract_exit_code_from_success(self, parser_module) -> None:
        """Successful commands should return exit code 0."""
        exit_code = parser_module._extract_exit_code_from_content(
            "Output from successful command", is_error=False
        )
        assert exit_code == 0

    def test_extract_exit_code_from_error_with_prefix(self, parser_module) -> None:
        """Error messages with 'Exit code N' prefix should be parsed."""
        exit_code = parser_module._extract_exit_code_from_content(
            "Exit code 1\nCommand failed", is_error=True
        )
        assert exit_code == 1

    def test_extract_exit_code_from_error_no_prefix(self, parser_module) -> None:
        """Error messages without exit code prefix should default to 1."""
        exit_code = parser_module._extract_exit_code_from_content(
            "Some error message", is_error=True
        )
        assert exit_code == 1  # Default for errors without explicit code

    def test_extract_exit_code_various_codes(self, parser_module) -> None:
        """Should correctly parse various exit codes."""
        test_cases = [
            ("Exit code 0\nSuccess", True, 0),
            ("Exit code 127\nCommand not found", True, 127),
            ("Exit code 255\nFatal error", True, 255),
            ("Exit code 2\nMisuse of command", True, 2),
        ]

        for content, is_error, expected_code in test_cases:
            result = parser_module._extract_exit_code_from_content(content, is_error)
            assert result == expected_code, (
                f"Failed for content: {content[:50]}, "
                f"expected {expected_code}, got {result}"
            )

    def test_tool_result_info_includes_exit_code(self, parser_module) -> None:
        """_get_tool_result_info should include exit code in result."""
        from lib.transcript_parser import Entry, SessionProcessor

        processor = SessionProcessor()

        # Create mock entries with tool_use and tool_result
        tool_id = "test_tool_123"
        entries = [
            Entry(
                type="assistant",
                message={
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": "Bash",
                            "input": {"command": "ls /nonexistent"},
                        }
                    ]
                },
            ),
            Entry(
                type="user",
                message={
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "is_error": True,
                            "content": "Exit code 2\nls: cannot access '/nonexistent': No such file or directory",
                        }
                    ]
                },
            ),
        ]

        result_info = processor._get_tool_result_info(tool_id, entries)

        assert result_info is not None
        assert result_info["is_error"] is True
        assert result_info["exit_code"] == 2
        assert "cannot access" in result_info["content"]

    def test_extract_sidechain_deduplicates(self, parser_module) -> None:
        """_extract_sidechain should not show duplicate text content."""
        from lib.transcript_parser import Entry, SessionProcessor

        processor = SessionProcessor()

        # Create entries with duplicate text
        entries = [
            Entry(
                type="assistant",
                message={
                    "content": [
                        {"type": "text", "text": "Processing task..."},
                    ]
                },
            ),
            Entry(
                type="assistant",
                message={
                    "content": [
                        {"type": "text", "text": "Processing task..."},  # Duplicate
                    ]
                },
            ),
            Entry(
                type="assistant",
                message={
                    "content": [
                        {"type": "text", "text": "Task completed."},
                    ]
                },
            ),
        ]

        result = processor._extract_sidechain(entries)

        # Should only contain "Processing task..." once, not twice
        assert result.count("Processing task...") == 1
        assert "Task completed." in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
