"""Tests for transcript parsing and reflection extraction."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestReflectionExtraction:
    """Test extracting Framework Reflections from transcript."""

    @pytest.fixture
    def parser_module(self):
        """Import the transcript parser module."""
        import lib.transcript_parser as parser

        return parser

    def test_parse_framework_reflection_basic(self, parser_module) -> None:
        """Test parsing a simple Framework Reflection."""
        content = """
Some conversation...

## Framework Reflection

**Prompts**: Used strict prompting.

**Guidance Received**: None.

**Followed**: Yes.

**Outcome**: Success.

**Accomplishments**:
- Fixed the bug.

**Friction Points**: None.

**Root Cause**: Typo.

**Proposed Changes**: None.

**Next Step**: Merge.
"""
        reflection = parser_module.parse_framework_reflection(content)
        assert reflection is not None
        assert reflection.get("prompts") == "Used strict prompting."
        assert reflection.get("outcome") == "Success."
        # accomplishments is a list, check membership loosely or exactly
        accomplishments = reflection.get("accomplishments", [])
        assert any("Fixed the bug" in acc for acc in accomplishments)

    def test_parse_framework_reflection_partial(self, parser_module) -> None:
        """Test parsing with missing fields."""
        content = """
## Framework Reflection

**Outcome**: Partial success.

**Next Step**: Retry.
"""
        reflection = parser_module.parse_framework_reflection(content)
        assert reflection is not None
        assert reflection.get("outcome") == "Partial success."
        assert reflection.get("next_step") == "Retry."
        assert reflection.get("prompts") is None

    def test_parse_framework_reflection_no_header(self, parser_module) -> None:
        """Should return None if header missing."""
        content = "Just some text."
        reflection = parser_module.parse_framework_reflection(content)
        assert reflection is None

    def test_extract_reflection_from_live_logs(self, parser_module) -> None:
        """CRITICAL: Verify extraction works on actual live session logs.

        This test finds recent session logs that contain reflections and
        verifies the extraction pipeline works end-to-end.
        """
        from pathlib import Path

        # Find session transcripts with Framework Reflections
        sessions_dir = Path.home() / "writing" / "sessions" / "claude"
        reflection_files = []

        if sessions_dir.exists():
            for md_file in sessions_dir.glob("*-full.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if (
                        "## Framework Reflection" in content
                        or "## framework reflection" in content.lower()
                    ):
                        reflection_files.append(md_file)
                        if len(reflection_files) >= 3:
                            break
                except Exception:
                    continue

        # We must have at least one session with a reflection to test against
        if len(reflection_files) == 0:
            import pytest
            pytest.skip(
                f"No live session logs with Framework Reflections found in {sessions_dir}. "
                "Skipping live log extraction test."
            )

        # Test extraction on each found file
        successful_extractions = 0
        for md_file in reflection_files:
            content = md_file.read_text(encoding="utf-8")
            reflection = parser_module.parse_framework_reflection(content)

            if reflection and (
                reflection.get("outcome")
                or reflection.get("accomplishments")
                or reflection.get("next_step")
            ):
                successful_extractions += 1
            else:
                print(f"Failed to extract from {md_file.name}")

        assert successful_extractions > 0, "Failed to extract meaningful data from any live log"
