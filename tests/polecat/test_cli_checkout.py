#!/usr/bin/env python3
"""Tests for the polecat checkout command's legacy PKB-bridge claim path.

The checkout command has two claim paths:
  1. Storage path (lib.task_model available): uses TaskStatus enum.
  2. PKB-bridge fallback (ImportError): calls pkb_bridge.update_task directly.

Before the taxonomy fix, the PKB-bridge path guarded:
    if task.status in ("queued", "active"):
After the fix it uses the canonical statuses:
    if task.status in ("ready", "queued"):

These tests verify:
  - A task with status "ready" gets claimed via the PKB bridge.
  - A task with status "queued" gets claimed via the PKB bridge.
  - A task already "in_progress" is NOT re-claimed.
  - The legacy "active" status does NOT trigger a claim.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from cli import main
from polecat.pkb_bridge import PkbTask


def _task(status: str, task_id: str = "task-abc123") -> PkbTask:
    return PkbTask(
        {
            "frontmatter": {
                "id": task_id,
                "title": "Test task",
                "status": status,
                "project": "aops",
            },
            "body": "",
        }
    )


def _run_checkout(task: PkbTask, tmp_path: Path):
    """Invoke checkout with storage=None (PKB bridge) and lib.task_model blocked."""
    worktree = tmp_path / "worktrees" / task.id
    worktree.mkdir(parents=True)

    mock_manager = MagicMock()
    mock_manager.storage = None
    mock_manager.setup_worktree.return_value = worktree

    runner = CliRunner()
    with (
        patch("cli.PolecatManager", return_value=mock_manager),
        patch("polecat.pkb_bridge.get_task", return_value=task),
        patch("polecat.pkb_bridge.update_task") as mock_update,
        # Block lib.task_model so the ImportError branch is taken.
        patch.dict("sys.modules", {"lib.task_model": None}),
    ):
        result = runner.invoke(
            main,
            ["--home", str(tmp_path), "checkout", task.id],
            catch_exceptions=False,
        )
    return result, mock_update


class TestCheckoutLegacyClaimPath:
    """PKB-bridge fallback path (lib.task_model unavailable)."""

    def test_ready_task_is_claimed(self, tmp_path):
        """A 'ready' task must be claimed — this is the canonical pre-claim status.

        This is the regression case: before the fix the guard was
        `task.status in ("queued", "active")`, so a "ready" task was silently
        skipped. After the fix `"ready"` is included.
        """
        task = _task("ready")
        result, mock_update = _run_checkout(task, tmp_path)

        mock_update.assert_called_once_with(task.id, status="in_progress", assignee="polecat")
        assert result.exit_code == 0, f"stdout: {result.output!r}"

    def test_queued_task_is_claimed(self, tmp_path):
        """A 'queued' task must also be claimed."""
        task = _task("queued")
        result, mock_update = _run_checkout(task, tmp_path)

        mock_update.assert_called_once_with(task.id, status="in_progress", assignee="polecat")
        assert result.exit_code == 0, f"stdout: {result.output!r}"

    def test_in_progress_task_not_reclaimed(self, tmp_path):
        """A task already 'in_progress' must not trigger a second claim."""
        task = _task("in_progress")
        result, mock_update = _run_checkout(task, tmp_path)

        mock_update.assert_not_called()
        assert result.exit_code == 0, f"stdout: {result.output!r}"

    def test_legacy_active_status_not_claimed(self, tmp_path):
        """The legacy 'active' status must NOT trigger a claim.

        'active' is a non-canonical term that PKB rejects. The pre-fix guard
        `task.status in ("queued", "active")` would have called update_task
        with the non-canonical status, causing a PKB rejection. The fix
        excludes 'active' from the claimable set.
        """
        task = _task("active")
        result, mock_update = _run_checkout(task, tmp_path)

        mock_update.assert_not_called()
        assert result.exit_code == 0, f"stdout: {result.output!r}"
