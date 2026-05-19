#!/usr/bin/env python3
"""Tests for polecat dispatch rollback semantics.

When ``polecat run`` / ``polecat start`` claims a task and worktree setup
then fails, the task must be reverted to a *canonical* PKB status (per
``aops-core/skills/remember/references/TAXONOMY.md``). Historically this
code wrote ``"active"``, which PKB rejects as ``Invalid status``, leaving
the task stranded in ``in_progress``. The fix is to capture the prior
status before claiming and restore it on failure (falling back to
``"queued"`` when no prior status was captured).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from polecat.cli import main


@pytest.fixture
def mock_manager():
    with patch("polecat.cli.PolecatManager") as mock:
        manager = MagicMock()
        mock.return_value = manager
        yield manager


def _make_task(status: str = "queued", task_id: str = "task-1"):
    """Build a PkbTask with a captured prior status, mimicking what
    ``PolecatManager.claim_next_task`` returns after a successful claim."""
    from polecat.pkb_bridge import PkbTask

    # After a real claim the task carries status="in_progress" and a
    # ``_prior_status`` annotation recording what it was before.
    task = PkbTask(
        {
            "frontmatter": {"id": task_id, "status": "in_progress", "title": "Test"},
            "body": "",
        }
    )
    task._prior_status = status
    return task


def test_run_revert_restores_prior_queued_status(mock_manager):
    """run -p: rollback uses the captured prior status (``queued``), not ``active``."""
    task = _make_task(status="queued", task_id="task-1")
    mock_manager.claim_next_task.return_value = task
    mock_manager.setup_worktree.side_effect = Exception("Setup failed")

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            with patch("polecat.cli._require_claude_oauth_or_exit", return_value=None):
                result = runner.invoke(main, ["run", "-p", "aops"])

    assert result.exit_code == 1
    assert "Error setting up worktree: Setup failed" in result.output
    assert "Reverting task task-1 to queued..." in result.output
    # MUST NOT write the non-canonical "active" status — PKB rejects it.
    assert "to active" not in result.output

    mock_manager.update_task.assert_called_with("task-1", status="queued", assignee=None)
    # Negative assertion: the legacy bug would call status="active".
    for call in mock_manager.update_task.call_args_list:
        assert call.kwargs.get("status") != "active"


def test_run_revert_restores_prior_ready_status(mock_manager):
    """If the prior status was ``ready``, the rollback restores ``ready``."""
    task = _make_task(status="ready", task_id="task-2")
    mock_manager.claim_next_task.return_value = task
    mock_manager.setup_worktree.side_effect = Exception("Setup failed")

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            with patch("polecat.cli._require_claude_oauth_or_exit", return_value=None):
                result = runner.invoke(main, ["run", "-p", "aops"])

    assert result.exit_code == 1
    assert "Reverting task task-2 to ready..." in result.output
    mock_manager.update_task.assert_called_with("task-2", status="ready", assignee=None)


def test_run_revert_falls_back_to_queued_when_prior_missing(mock_manager):
    """If no ``_prior_status`` annotation is present, fall back to canonical ``queued``."""
    from polecat.pkb_bridge import PkbTask

    task = PkbTask(
        {
            "frontmatter": {"id": "task-3", "status": "in_progress", "title": "Test"},
            "body": "",
        }
    )
    # Deliberately do NOT set task._prior_status.
    mock_manager.claim_next_task.return_value = task
    mock_manager.setup_worktree.side_effect = Exception("Setup failed")

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            with patch("polecat.cli._require_claude_oauth_or_exit", return_value=None):
                result = runner.invoke(main, ["run", "-p", "aops"])

    assert result.exit_code == 1
    assert "Reverting task task-3 to queued..." in result.output
    mock_manager.update_task.assert_called_with("task-3", status="queued", assignee=None)


def test_run_revert_never_passes_invalid_status_to_pkb(mock_manager):
    """Regression: PKB MCP must never receive ``status="active"`` from rollback.

    PKB rejects ``active`` with ``Invalid status: active``. Asserts that even
    if a stale ``_prior_status="active"`` somehow leaks through (e.g. from a
    legacy task object), the rollback coerces it to canonical ``queued``.
    """
    from polecat.pkb_bridge import PkbTask

    task = PkbTask(
        {
            "frontmatter": {"id": "task-4", "status": "in_progress", "title": "Test"},
            "body": "",
        }
    )
    task._prior_status = "active"  # legacy non-canonical value
    mock_manager.claim_next_task.return_value = task
    mock_manager.setup_worktree.side_effect = Exception("Setup failed")

    # Simulate the PKB MCP behaviour: reject "active".
    def update_task_side_effect(task_id, **kwargs):
        if kwargs.get("status") == "active":
            raise RuntimeError("PKB MCP error -32603: Invalid status: active")
        return True

    mock_manager.update_task.side_effect = update_task_side_effect

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            with patch("polecat.cli._require_claude_oauth_or_exit", return_value=None):
                result = runner.invoke(main, ["run", "-p", "aops"])

    assert result.exit_code == 1
    # The rollback must NOT have raised "Invalid status".
    assert "Invalid status" not in result.output
    # The rollback must have been called with a canonical value.
    statuses = [c.kwargs.get("status") for c in mock_manager.update_task.call_args_list]
    assert "active" not in statuses
    assert "queued" in statuses


def test_start_revert_restores_prior_queued_status(mock_manager):
    """start: rollback uses the captured prior status, not ``active``."""
    task = _make_task(status="queued", task_id="task-1")
    mock_manager.claim_next_task.return_value = task
    mock_manager.setup_worktree.side_effect = Exception("Setup failed")

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            with patch("polecat.cli._require_claude_oauth_or_exit", return_value=None):
                result = runner.invoke(main, ["start", "-p", "aops"])

    assert result.exit_code == 1
    assert "Error setting up worktree: Setup failed" in result.output
    assert "Reverting task task-1 to queued..." in result.output
    assert "to active" not in result.output

    mock_manager.update_task.assert_called_with("task-1", status="queued", assignee=None)
