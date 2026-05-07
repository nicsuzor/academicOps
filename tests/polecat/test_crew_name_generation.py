#!/usr/bin/env python3
"""Tests for crew name generation and list_crew() staleness handling.

Covers:
- generate_crew_name() returns pool names when pool has slots available.
- generate_crew_name() falls back to <name>_<hex4> suffix when all pool
  names are taken, rather than raising RuntimeError.
- list_crew() skips empty directories (partially-cleaned remnants) and
  removes them as a side effect.
"""

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import PolecatManager  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager(tmp_path: Path) -> PolecatManager:
    """Return a minimal PolecatManager backed by a temp directory."""
    # Patch load_config / load_projects / load_crew_names to avoid needing
    # a real polecat.yaml on disk.
    with (
        patch("manager.load_config", return_value={}),
        patch("manager.load_projects", return_value={}),
        patch("manager.load_project_aliases", return_value={}),
        patch("manager.load_crew_names", return_value=["weasel", "badger", "ferret"]),
    ):
        m = PolecatManager(home_dir=tmp_path)
    m.crew_dir = tmp_path / "crew"
    m.crew_dir.mkdir(parents=True, exist_ok=True)
    return m


# ---------------------------------------------------------------------------
# list_crew() tests
# ---------------------------------------------------------------------------


class TestListCrew:
    def test_returns_empty_when_no_crew_dir(self, tmp_path):
        m = _make_manager(tmp_path)
        m.crew_dir = tmp_path / "nonexistent"
        assert m.list_crew() == []

    def test_returns_dirs_with_content(self, tmp_path):
        m = _make_manager(tmp_path)
        crew_dir = m.crew_dir
        # Create a crew dir with a project subdir inside it
        (crew_dir / "weasel" / "aops").mkdir(parents=True)
        assert m.list_crew() == ["weasel"]

    def test_skips_empty_dirs(self, tmp_path):
        m = _make_manager(tmp_path)
        crew_dir = m.crew_dir
        # Empty dir — should be treated as stale remnant
        (crew_dir / "badger").mkdir()
        assert m.list_crew() == []

    def test_removes_empty_dirs(self, tmp_path):
        m = _make_manager(tmp_path)
        crew_dir = m.crew_dir
        empty = crew_dir / "badger"
        empty.mkdir()
        m.list_crew()
        # Empty dir should have been removed as a side effect
        assert not empty.exists()

    def test_mixed_empty_and_nonempty(self, tmp_path):
        m = _make_manager(tmp_path)
        crew_dir = m.crew_dir
        (crew_dir / "weasel" / "aops").mkdir(parents=True)  # non-empty
        (crew_dir / "badger").mkdir()  # empty stale dir
        result = m.list_crew()
        assert result == ["weasel"]
        assert not (crew_dir / "badger").exists()


# ---------------------------------------------------------------------------
# generate_crew_name() tests
# ---------------------------------------------------------------------------


class TestGenerateCrewName:
    def test_picks_from_pool_when_available(self, tmp_path):
        m = _make_manager(tmp_path)
        # No active crew
        name = m.generate_crew_name()
        assert name in m.crew_names

    def test_avoids_active_crew_names(self, tmp_path):
        m = _make_manager(tmp_path)
        crew_dir = m.crew_dir
        # Mark weasel and badger as "in use" by creating dirs with content
        (crew_dir / "weasel" / "aops").mkdir(parents=True)
        (crew_dir / "badger" / "aops").mkdir(parents=True)
        # Only ferret remains
        name = m.generate_crew_name()
        assert name == "ferret"

    def test_fallback_suffix_when_pool_exhausted(self, tmp_path):
        m = _make_manager(tmp_path)
        crew_dir = m.crew_dir
        # Occupy all three pool names
        for n in ["weasel", "badger", "ferret"]:
            (crew_dir / n / "aops").mkdir(parents=True)

        # Should NOT raise; instead returns a suffixed name
        name = m.generate_crew_name()
        parts = name.rsplit("_", 1)
        assert len(parts) == 2, f"Expected base_suffix format, got: {name!r}"
        base, suffix = parts
        assert base in m.crew_names
        assert len(suffix) == 4
        # suffix is 4 hex chars
        int(suffix, 16)

    def test_fallback_name_not_in_active_crew(self, tmp_path):
        m = _make_manager(tmp_path)
        crew_dir = m.crew_dir
        # Exhaust pool
        for n in ["weasel", "badger", "ferret"]:
            (crew_dir / n / "aops").mkdir(parents=True)
        # Also mark a specific suffixed name as taken
        (crew_dir / "weasel_ab12" / "aops").mkdir(parents=True)

        name = m.generate_crew_name()
        # generate_crew_name() must not return any of the exhausted pool names,
        # and must not return the specifically pre-occupied suffixed name.
        assert name not in {"weasel", "badger", "ferret", "weasel_ab12"}
