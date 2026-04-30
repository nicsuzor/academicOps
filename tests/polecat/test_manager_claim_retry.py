#!/usr/bin/env python3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from manager import PolecatManager


@pytest.fixture
def manager():
    with patch("manager.load_config", return_value={"projects": {}, "crew_names": []}):
        with patch("manager.load_projects", return_value={}):
            m = PolecatManager(home_dir=Path("/tmp/polecat"))
            m.storage = None  # Force PKB bridge
            return m


def test_claim_next_task_pkb_timeout_verify_success(manager, capsys):
    from polecat.pkb_bridge import PkbTask

    mock_task = PkbTask({"frontmatter": {"id": "task-1", "status": "ready"}, "body": ""})
    mock_verified = PkbTask(
        {"frontmatter": {"id": "task-1", "status": "in_progress", "assignee": "bot"}, "body": ""}
    )

    with patch("polecat.pkb_bridge.get_ready_tasks", return_value=[mock_task]):
        with patch("polecat.pkb_bridge.get_task", side_effect=[mock_task, mock_verified]):
            with patch("polecat.pkb_bridge.update_task", side_effect=TimeoutError("timed out")):
                result = manager._claim_next_task_pkb("bot")

                assert result.id == "task-1"
                assert result.status == "in_progress"
                assert result.assignee == "bot"

                captured = capsys.readouterr()
                assert "⚠️  PKB claim timeout for task-1" in captured.err
                assert "✅ Verified: claim succeeded" in captured.err


def test_claim_next_task_pkb_timeout_verify_fail(manager, capsys):
    from polecat.pkb_bridge import PkbTask

    mock_task = PkbTask({"frontmatter": {"id": "task-1", "status": "ready"}, "body": ""})

    with patch("polecat.pkb_bridge.get_ready_tasks", return_value=[mock_task]):
        with patch("polecat.pkb_bridge.get_task", return_value=mock_task):
            with patch("polecat.pkb_bridge.update_task", side_effect=TimeoutError("timed out")):
                with pytest.raises(TimeoutError):
                    manager._claim_next_task_pkb("bot")

                captured = capsys.readouterr()
                assert "⚠️  PKB claim timeout for task-1" in captured.err
                assert "Task task-1 may be stranded in_progress" in captured.err
                assert "polecat reset-stalled" in captured.err
