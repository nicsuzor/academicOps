try:
    import pytest
except ImportError:
    # mock pytest.mark for standalone runs
    class mock_mark:
        def parametrize(self, *args, **kwargs):
            return lambda f: f

    class mock_pytest:
        mark = mock_mark()

    pytest = mock_pytest()

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add framework roots for imports
SCRIPT_DIR = Path(__file__).parent.resolve()
ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(ROOT / "aops-core" / "lib"))
sys.path.insert(0, str(ROOT / "aops-core"))

import importlib.util

# Import aops-core scripts by file path to avoid shadowing root scripts/ package
def _import_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

transcript = _import_from_path("transcript", ROOT / "aops-core" / "scripts" / "transcript.py")
insights_generator = _import_from_path("insights_generator", ROOT / "aops-core" / "lib" / "insights_generator.py")


class TestTranscriptNamingIntegration:
    """Tests for transcript and insights naming integration."""

    def test_generate_transcript_filename_uses_naming_module(self):
        """Test that transcript.py's _generate_transcript_filename uses session_naming."""
        session_path = Path(
            "/home/worker/.claude/projects/-home-worker-src-aops/session-uuid.jsonl"
        )
        entries = []  # Mock entries

        # We need to mock aops-core directory layout
        os.environ["CLAUDE_PROJECT_DIR"] = "/home/worker/src/aops"

        # Fixed timestamp
        ts = datetime(2026, 4, 11, 14, 30, 0, tzinfo=UTC)

        # Mock mtime if no entries
        class MockStat:
            st_mtime = ts.timestamp()
            st_mode = 0o100644  # Regular file

        def mock_stat():
            return MockStat()

        import unittest.mock as mock

        with mock.patch.object(Path, "stat", side_effect=mock_stat):
            filename, date_str, short_project, session_id, slug = (
                transcript._generate_transcript_filename(session_path, entries, slug="test-slug")
            )

            # Should match session_naming.generate_base_name format
            # {YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}
            import re

            pattern = r"^\d{8}-\d{4}-[0-9a-f]{8}-.*-test-slug$"
            assert re.match(pattern, filename), (
                f"Filename {filename} does not match pattern {pattern}"
            )
            assert short_project == "aops"
            assert slug == "test-slug"

    def test_insights_file_path_matches_transcript(self):
        """Test that insights JSON filename matches transcript base name."""
        session_id = "a1b2c3d4"
        date = "2026-04-11"
        project = "my-project"
        slug = "fix-bugs"
        hour = "17"

        # Expected base from naming module
        # Note: machine and provider might vary in CI, so we check for components
        path = insights_generator.get_insights_file_path(
            date=date, session_id=session_id, slug=slug, project=project, hour=hour
        )

        filename = path.name
        assert filename.startswith("20260411-1700-a1b2c3d4-")
        assert "my-project" in filename
        assert "fix-bugs.json" in filename

    def test_find_existing_transcripts_backward_compat(self, tmp_path):
        """Test that existing transcripts in old formats are still found."""
        session_id = "abc12345"

        # Old v3.7.0 format (HH)
        old_path = tmp_path / "20260411-14-project-abc12345-slug-full.md"
        old_path.touch()

        # New v4.0.0 format (HHMM)
        new_path = tmp_path / "20260411-1430-abc12345-repo-machine-claude-slug-full.md"
        new_path.touch()

        # Very old format
        v_old_path = tmp_path / "20260411-abc12345-full.md"
        v_old_path.touch()

        matches = transcript._find_existing_transcripts(tmp_path, session_id)
        match_names = {p.name for p in matches}

        assert old_path.name in match_names
        assert new_path.name in match_names
        assert v_old_path.name in match_names
        assert len(matches) == 3

    def test_find_existing_insights_backward_compat(self, tmp_path):
        """Test that existing insights in old formats are still found."""
        session_id = "a1b2c3d4"
        date = "2026-04-11"

        # Mock summaries dir
        import unittest.mock as mock

        with mock.patch("lib.insights_generator.get_summaries_dir", return_value=tmp_path):
            # Old v3.7.0 format (HH)
            old_path = tmp_path / "20260411-17-project-a1b2c3d4-slug.json"
            old_path.touch()

            # New v4.0.0 format (HHMM)
            new_path = tmp_path / "20260411-1730-a1b2c3d4-repo-machine-claude-slug.json"
            new_path.touch()

            # Should find at least one (glob returns list)
            found = insights_generator.find_existing_insights(date, session_id)
            assert found is not None
            # The pattern list in find_existing_insights ensures we check new then old
            assert found.name == new_path.name
            print("✓ find_existing_insights_backward_compat passed")
