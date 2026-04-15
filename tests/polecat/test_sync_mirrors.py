#!/usr/bin/env python3
"""Regression tests for sync_all_mirrors() delegating to safe_sync_mirror().

Before this fix, sync_all_mirrors() called raw ``git fetch --all --prune``
directly, bypassing the worktree-aware exclusion logic in safe_sync_mirror().
This caused git to fail when a branch was checked out in a worktree — the
exact scenario that safe_sync_mirror() was designed to handle.

These tests call the real sync_all_mirrors() and FAIL if it bypasses
safe_sync_mirror() (e.g. by reverting to raw subprocess calls).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import yaml

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import PolecatManager  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_manager(tmp_path: Path, projects: dict | None = None):
    """Create a PolecatManager backed by tmp dirs and an optional project map."""
    if projects is None:
        projects = {"myproject": {"path": str(tmp_path / "repo"), "default_branch": "main"}}

    home_dir = tmp_path / "polecat_home"
    home_dir.mkdir(exist_ok=True)
    config = {
        "projects": projects,
        "crew_names": ["worker"],
        "git_identity": {},
    }
    (home_dir / "polecat.yaml").write_text(yaml.dump(config))

    aca_data = tmp_path / "aca_data"
    aca_data.mkdir(exist_ok=True)

    with patch.dict("os.environ", {"ACA_DATA": str(aca_data)}):
        return PolecatManager(home_dir=home_dir)


# ---------------------------------------------------------------------------
# Tests: sync_all_mirrors() delegates to safe_sync_mirror()
# ---------------------------------------------------------------------------


class TestSyncAllMirrorsDelegation:
    """sync_all_mirrors() must call safe_sync_mirror(), not raw git fetch.

    The regression condition: replacing ``self.safe_sync_mirror(project)``
    with a direct subprocess call would bypass worktree-aware exclusion.
    These tests catch that by verifying safe_sync_mirror is called.
    """

    def test_delegates_to_safe_sync_mirror_for_existing_mirror(self, tmp_path):
        """sync_all_mirrors calls safe_sync_mirror for each project with a mirror."""
        manager = _make_manager(tmp_path)
        mirror_path = manager.repos_dir / "myproject.git"
        mirror_path.mkdir(parents=True)

        with patch.object(manager, "safe_sync_mirror", return_value=True) as mock_sync:
            results = manager.sync_all_mirrors()

        mock_sync.assert_called_once_with("myproject")
        assert results == {"myproject": True}

    def test_delegates_to_safe_sync_mirror_failure_path(self, tmp_path):
        """sync_all_mirrors propagates False from safe_sync_mirror correctly."""
        manager = _make_manager(tmp_path)
        mirror_path = manager.repos_dir / "myproject.git"
        mirror_path.mkdir(parents=True)

        with patch.object(manager, "safe_sync_mirror", return_value=False) as mock_sync:
            results = manager.sync_all_mirrors()

        mock_sync.assert_called_once_with("myproject")
        assert results == {"myproject": False}

    def test_skips_project_with_no_mirror(self, tmp_path):
        """sync_all_mirrors returns False and skips safe_sync_mirror when no mirror exists."""
        manager = _make_manager(tmp_path)
        # Mirror directory intentionally NOT created.

        with patch.object(manager, "safe_sync_mirror") as mock_sync:
            results = manager.sync_all_mirrors()

        mock_sync.assert_not_called()
        assert results == {"myproject": False}

    def test_multiple_projects_each_get_safe_sync_called(self, tmp_path):
        """Each project with a mirror gets its own safe_sync_mirror call."""
        projects = {
            "alpha": {"path": str(tmp_path / "alpha"), "default_branch": "main"},
            "beta": {"path": str(tmp_path / "beta"), "default_branch": "main"},
            "gamma": {"path": str(tmp_path / "gamma"), "default_branch": "main"},
        }
        manager = _make_manager(tmp_path, projects=projects)

        # Only alpha and gamma have mirrors; beta does not.
        (manager.repos_dir / "alpha.git").mkdir(parents=True)
        (manager.repos_dir / "gamma.git").mkdir(parents=True)

        with patch.object(manager, "safe_sync_mirror", return_value=True) as mock_sync:
            results = manager.sync_all_mirrors()

        called_with = {call.args[0] for call in mock_sync.call_args_list}
        assert called_with == {"alpha", "gamma"}, (
            "safe_sync_mirror must be called for projects with mirrors only"
        )
        assert results["alpha"] is True
        assert results["beta"] is False  # no mirror
        assert results["gamma"] is True
