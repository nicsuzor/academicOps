#!/usr/bin/env python3
"""Regression test for gh-1195: polecat nuke <crew-name> fails with ValueError.

When a crew worker's directory exists but nuke_worktree is called directly
(bypassing the CLI's crew_path.exists() guard), it should delegate to
nuke_crew rather than failing with a confusing "task lookup failed" error.

Also covers: nuke_worktree called with a crew name when crew dir is gone
raises ValueError (not an unhandled traceback).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import PolecatManager  # noqa: E402


def _make_manager(tmp_path: Path) -> PolecatManager:
    with (
        patch("manager.load_config", return_value={}),
        patch("manager.load_projects", return_value={}),
        patch("manager.load_project_aliases", return_value={}),
        patch("manager.load_crew_names", return_value=["smoketest-claude"]),
    ):
        m = PolecatManager(home_dir=tmp_path)
    m.crew_dir = tmp_path / "crew"
    m.crew_dir.mkdir(parents=True, exist_ok=True)
    m.polecats_dir = tmp_path / "worktrees"
    m.polecats_dir.mkdir(parents=True, exist_ok=True)
    return m


class TestNukeCrewByName:
    def test_nuke_worktree_delegates_to_nuke_crew_when_crew_dir_exists(self, tmp_path):
        """nuke_worktree with a crew name delegates to nuke_crew if crew dir exists."""
        m = _make_manager(tmp_path)
        crew_name = "smoketest-claude"
        crew_path = m.crew_dir / crew_name
        crew_path.mkdir(parents=True)
        # Put a harmless file in the crew dir so shutil.rmtree has something to remove
        (crew_path / "placeholder").write_text("crew sentinel")

        nuke_crew_calls = []

        def capturing_nuke_crew(name, force=False):
            nuke_crew_calls.append((name, force))
            # Simulate successful crew removal
            import shutil

            shutil.rmtree(m.crew_dir / name, ignore_errors=True)

        m.nuke_crew = capturing_nuke_crew

        # Should NOT raise — should delegate to nuke_crew
        m.nuke_worktree(crew_name, force=False)

        assert nuke_crew_calls == [(crew_name, False)], (
            "nuke_worktree must delegate to nuke_crew when crew dir exists"
        )

    def test_nuke_worktree_passes_force_to_nuke_crew(self, tmp_path):
        """force=True is forwarded to nuke_crew so --force skips branch safety checks."""
        m = _make_manager(tmp_path)
        crew_name = "smoketest-claude"
        (m.crew_dir / crew_name).mkdir(parents=True)

        nuke_crew_calls = []

        def capturing_nuke_crew(name, force=False):
            nuke_crew_calls.append((name, force))
            import shutil

            shutil.rmtree(m.crew_dir / name, ignore_errors=True)

        m.nuke_crew = capturing_nuke_crew

        m.nuke_worktree(crew_name, force=True)

        assert nuke_crew_calls == [(crew_name, True)]

    def test_nuke_worktree_raises_value_error_when_crew_dir_absent(self, tmp_path):
        """When crew dir is gone (auto-nuked) and target isn't a task, raise ValueError."""
        m = _make_manager(tmp_path)
        crew_name = "smoketest-claude"
        # crew dir deliberately absent — simulates post-auto-nuke state

        with pytest.raises(ValueError, match="Cannot nuke worktree"):
            m.nuke_worktree(crew_name)

    def test_crew_dir_takes_priority_over_task_lookup(self, tmp_path):
        """Crew dir check runs before PKB lookup so task-less crews are always handled."""
        m = _make_manager(tmp_path)
        crew_name = "smoketest-claude"
        crew_path = m.crew_dir / crew_name
        crew_path.mkdir(parents=True)
        (crew_path / "placeholder").write_text("crew sentinel")

        task_lookup_called = []

        def capturing_nuke_crew(name, force=False):
            import shutil

            shutil.rmtree(m.crew_dir / name, ignore_errors=True)

        m.nuke_crew = capturing_nuke_crew

        # Patch PKB bridge so any accidental task lookup would raise — proving
        # that the crew-dir check fires before task lookup is attempted.
        def fail_if_called(*args, **kwargs):
            task_lookup_called.append(args)
            raise RuntimeError("task lookup must not be reached when crew dir exists")

        with patch("polecat.pkb_bridge.get_task", fail_if_called, create=True):
            m.nuke_worktree(crew_name, force=False)

        assert not crew_path.exists(), "crew dir must be removed"
        assert not task_lookup_called, "task lookup must not be reached when crew dir exists"
