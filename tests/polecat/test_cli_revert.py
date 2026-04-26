#!/usr/bin/env python3
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


def test_run_revert_on_setup_failure(mock_manager):
    from polecat.pkb_bridge import PkbTask

    task = PkbTask(
        {"frontmatter": {"id": "task-1", "status": "active", "title": "Test"}, "body": ""}
    )
    mock_manager.claim_next_task.return_value = task
    mock_manager.setup_worktree.side_effect = Exception("Setup failed")

    runner = CliRunner()
    # Mocking bootstrap and pkb_url checks
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            result = runner.invoke(main, ["run", "-p", "aops"])

    assert result.exit_code == 1
    assert "Error setting up worktree: Setup failed" in result.output
    assert "Reverting task task-1 to active..." in result.output

    # Verify manager.update_task was called to revert
    mock_manager.update_task.assert_called_with("task-1", status="active", assignee=None)


def test_start_revert_on_setup_failure(mock_manager):
    from polecat.pkb_bridge import PkbTask

    task = PkbTask(
        {"frontmatter": {"id": "task-1", "status": "active", "title": "Test"}, "body": ""}
    )
    mock_manager.claim_next_task.return_value = task
    mock_manager.setup_worktree.side_effect = Exception("Setup failed")

    runner = CliRunner()
    with patch("polecat.cli._require_pkb_url_or_exit", return_value=None):
        with patch("polecat.cli._bootstrap_or_exit", return_value=None):
            result = runner.invoke(main, ["start", "-p", "aops"])

    assert result.exit_code == 1
    assert "Error setting up worktree: Setup failed" in result.output
    assert "Reverting task task-1 to active..." in result.output

    mock_manager.update_task.assert_called_with("task-1", status="active", assignee=None)
