#!/usr/bin/env python3
"""Tests for `polecat list` — container-liveness detection.

Verifies that list_polecats labels worktrees as [ACTIVE], [STALE], or [UNKNOWN]
based on whether a matching polecat-<task_id> Docker container is running.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from cli import _get_running_polecat_containers, main

# ---------------------------------------------------------------------------
# _get_running_polecat_containers unit tests
# ---------------------------------------------------------------------------


class TestGetRunningPolecatContainers:
    def test_returns_task_ids_from_named_containers(self):
        mock_result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="polecat-task-abc12345\nnginx\npolecat-framework-def67890\n",
        )
        with (
            patch("cli._is_remote_daemon", return_value=False),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _get_running_polecat_containers()
        assert result == {"task-abc12345", "framework-def67890"}

    def test_returns_empty_set_when_no_polecat_containers(self):
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="nginx\nredis\n")
        with (
            patch("cli._is_remote_daemon", return_value=False),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _get_running_polecat_containers()
        assert result == set()

    def test_returns_none_when_docker_not_found(self):
        with (
            patch("cli._is_remote_daemon", return_value=False),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            result = _get_running_polecat_containers()
        assert result is None

    def test_returns_none_on_timeout(self):
        with (
            patch("cli._is_remote_daemon", return_value=False),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=5)),
        ):
            result = _get_running_polecat_containers()
        assert result is None

    def test_returns_none_when_docker_returns_nonzero(self):
        mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="")
        with (
            patch("cli._is_remote_daemon", return_value=False),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _get_running_polecat_containers()
        assert result is None

    def test_handles_empty_output(self):
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with (
            patch("cli._is_remote_daemon", return_value=False),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _get_running_polecat_containers()
        assert result == set()

    def test_returns_none_when_remote_daemon(self):
        with patch("cli._is_remote_daemon", return_value=True):
            result = _get_running_polecat_containers()
        assert result is None


# ---------------------------------------------------------------------------
# list command integration tests
# ---------------------------------------------------------------------------


class TestListCommand:
    def _setup_worktrees(self, tmp_path: Path, task_ids: list[str]) -> Path:
        worktrees = tmp_path / "worktrees"
        worktrees.mkdir()
        for tid in task_ids:
            (worktrees / tid).mkdir()
        return tmp_path

    def test_active_worktree_labelled_active(self, tmp_path):
        home = self._setup_worktrees(tmp_path, ["task-abc12345"])
        runner = CliRunner()

        with patch("cli._get_running_polecat_containers", return_value={"task-abc12345"}):
            result = runner.invoke(main, ["--home", str(home), "list"])

        assert result.exit_code == 0
        assert "[ACTIVE]" in result.output
        assert "task-abc12345" in result.output
        assert "[STALE]" not in result.output

    def test_stale_worktree_labelled_stale(self, tmp_path):
        home = self._setup_worktrees(tmp_path, ["task-abc12345"])
        runner = CliRunner()

        with patch("cli._get_running_polecat_containers", return_value=set()):
            result = runner.invoke(main, ["--home", str(home), "list"])

        assert result.exit_code == 0
        assert "[STALE]" in result.output
        assert "task-abc12345" in result.output
        assert "[ACTIVE]" not in result.output

    def test_mixed_active_and_stale(self, tmp_path):
        home = self._setup_worktrees(tmp_path, ["task-abc12345", "task-def67890"])
        runner = CliRunner()

        with patch("cli._get_running_polecat_containers", return_value={"task-abc12345"}):
            result = runner.invoke(main, ["--home", str(home), "list"])

        assert result.exit_code == 0
        assert "[ACTIVE]" in result.output
        assert "[STALE]" in result.output

    def test_docker_unavailable_shows_unknown(self, tmp_path):
        home = self._setup_worktrees(tmp_path, ["task-abc12345"])
        # CliRunner merges stderr into output by default
        runner = CliRunner()

        with patch("cli._get_running_polecat_containers", return_value=None):
            result = runner.invoke(main, ["--home", str(home), "list"])

        assert result.exit_code == 0
        assert "[UNKNOWN]" in result.output
        assert "Docker unavailable" in result.output

    def test_no_worktrees_prints_no_active(self, tmp_path):
        home = tmp_path / "polecat_home"
        home.mkdir()
        (home / "worktrees").mkdir()
        runner = CliRunner()

        with patch("cli._get_running_polecat_containers", return_value=set()):
            result = runner.invoke(main, ["--home", str(home), "list"])

        assert result.exit_code == 0
        assert "No active polecats" in result.output

    def test_no_worktrees_dir_prints_no_active(self, tmp_path):
        home = tmp_path / "polecat_home"
        home.mkdir()
        runner = CliRunner()

        with patch("cli._get_running_polecat_containers", return_value=set()):
            result = runner.invoke(main, ["--home", str(home), "list"])

        assert result.exit_code == 0
        assert "No active polecats" in result.output

    def test_hidden_directories_ignored(self, tmp_path):
        home = self._setup_worktrees(tmp_path, [])
        (tmp_path / "worktrees" / ".worktree_creation.lock").mkdir()
        runner = CliRunner()

        with patch("cli._get_running_polecat_containers", return_value=set()):
            result = runner.invoke(main, ["--home", str(home), "list"])

        assert result.exit_code == 0
        assert "No active polecats" in result.output
