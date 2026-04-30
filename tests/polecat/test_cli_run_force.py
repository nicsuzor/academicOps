#!/usr/bin/env python3
"""Tests for ``polecat run --force``.

The ``--force`` flag bypasses the status-check guard on ``polecat run -t``,
allowing the command to claim and run a task in any non-terminal status.
Without ``--force``, the existing gating behaviour for terminal/locked
statuses (``done``, ``cancelled``, ``merge_ready``, ``review``, or any
PR-locked task) is preserved.
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


def _make_task(status: str = "queued", task_id: str = "task-1", pr_url=None, pr=None):
    from polecat.pkb_bridge import PkbTask

    fm = {"id": task_id, "status": status, "title": "Test"}
    if pr_url:
        fm["pr_url"] = pr_url
    if pr:
        fm["pr"] = pr
    return PkbTask({"frontmatter": fm, "body": ""})


def _invoke_run(args, mock_manager, task):
    """Run the CLI up to (and including) the claim, then short-circuit by
    making setup_worktree raise so we don't try to spawn docker/claude."""
    mock_manager.get_task.return_value = task
    mock_manager.setup_worktree.side_effect = Exception("setup short-circuit")

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            return runner.invoke(main, args)


# ----------------------------------------------------------------------
# Without --force: existing gating is preserved.
# ----------------------------------------------------------------------


def test_run_without_force_blocks_done_task(mock_manager):
    """A ``done`` task short-circuits with exit 0 and never claims."""
    task = _make_task(status="done", task_id="task-done")
    mock_manager.get_task.return_value = task

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            result = runner.invoke(main, ["run", "-t", "task-done"])

    assert result.exit_code == 0
    assert "already 'done'" in result.output
    mock_manager.update_task.assert_not_called()


def test_run_without_force_blocks_locked_task(mock_manager):
    """A ``merge_ready`` task is locked (exit 2); never claims."""
    task = _make_task(status="merge_ready", task_id="task-locked")
    mock_manager.get_task.return_value = task

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            result = runner.invoke(main, ["run", "-t", "task-locked"])

    assert result.exit_code == 2
    assert "locked" in result.output
    mock_manager.update_task.assert_not_called()


def test_run_without_force_blocks_pr_locked_task(mock_manager):
    """A task with a PR set is locked even at queued status (exit 2)."""
    task = _make_task(
        status="queued",
        task_id="task-pr",
        pr_url="https://github.com/x/y/pull/1",
    )
    mock_manager.get_task.return_value = task

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            result = runner.invoke(main, ["run", "-t", "task-pr"])

    assert result.exit_code == 2
    assert "locked" in result.output
    mock_manager.update_task.assert_not_called()


# ----------------------------------------------------------------------
# With --force: status check is bypassed, task is claimed regardless.
# ----------------------------------------------------------------------


def test_run_force_bypasses_done_status_and_claims(mock_manager):
    """--force on a ``done`` task: claim to in_progress and proceed."""
    task = _make_task(status="done", task_id="task-done")
    result = _invoke_run(["run", "-t", "task-done", "--force"], mock_manager, task)

    # We short-circuit at setup_worktree (Exception), so exit code is 1
    # and rollback runs — that's expected and proves we got past the gate.
    # The warning line goes to stderr; CliRunner mixes streams in result.output.
    assert "[force] Bypassing status check" in result.output
    assert "from status 'done'" in result.output
    # Task was claimed (transition to in_progress).
    claim_calls = [
        c
        for c in mock_manager.update_task.call_args_list
        if c.kwargs.get("status") == "in_progress"
    ]
    assert claim_calls, "expected an update_task(..., status='in_progress') call"
    assert claim_calls[0].args[0] == "task-done"


def test_run_force_bypasses_merge_ready_status_and_claims(mock_manager):
    """--force on a ``merge_ready`` task: claim to in_progress and proceed."""
    task = _make_task(status="merge_ready", task_id="task-mr")
    result = _invoke_run(["run", "-t", "task-mr", "--force"], mock_manager, task)

    assert "[force] Bypassing status check" in result.output
    assert "from status 'merge_ready'" in result.output
    claim_calls = [
        c
        for c in mock_manager.update_task.call_args_list
        if c.kwargs.get("status") == "in_progress"
    ]
    assert claim_calls, "expected a claim to in_progress"


def test_run_force_bypasses_pr_lock_and_claims(mock_manager):
    """--force ignores PR lock and claims the task to in_progress."""
    task = _make_task(
        status="review",
        task_id="task-prforce",
        pr_url="https://github.com/x/y/pull/9",
    )
    result = _invoke_run(["run", "-t", "task-prforce", "--force"], mock_manager, task)

    assert "[force] Bypassing status check" in result.output
    # The "locked … refusing to re-dispatch" message must NOT appear under --force.
    assert "refusing to re-dispatch" not in result.output
    claim_calls = [
        c
        for c in mock_manager.update_task.call_args_list
        if c.kwargs.get("status") == "in_progress"
    ]
    assert claim_calls, "expected a claim to in_progress under --force"


def test_run_force_bypasses_cancelled_status(mock_manager):
    """--force on a ``cancelled`` task: claim to in_progress."""
    task = _make_task(status="cancelled", task_id="task-cancel")
    result = _invoke_run(["run", "-t", "task-cancel", "--force"], mock_manager, task)

    assert "[force] Bypassing status check" in result.output
    assert "from status 'cancelled'" in result.output
    claim_calls = [
        c
        for c in mock_manager.update_task.call_args_list
        if c.kwargs.get("status") == "in_progress"
    ]
    assert claim_calls


# ----------------------------------------------------------------------
# Help text documents --force.
# ----------------------------------------------------------------------


def test_run_help_documents_force_flag():
    """`polecat run --help` mentions --force."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "--force" in result.output
    assert "status check" in result.output.lower()
