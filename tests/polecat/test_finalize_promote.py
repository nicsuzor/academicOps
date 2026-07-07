"""Tests for the `promote` path in polecat/finalize.py and polecat/cli.py.

`finish` never files or edits a PR itself (the agent does that from within
its own session, per `polecat/prompt_template.py`); `--promote` only marks an
*already-filed* PR ready for review via `gh pr ready`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from click.testing import CliRunner

from polecat.cli import run
from polecat.finalize import finish_cmd


def _option_names(command) -> set[str]:
    names: set[str] = set()
    for param in command.params:
        names.update(param.opts)
        names.update(param.secondary_opts)
    return names


def test_promote_flag_is_registered_on_finish():
    """`finish` must expose a `--promote` option."""
    assert "--promote" in _option_names(finish_cmd)


def test_promote_flag_is_registered_on_run():
    """`run` must expose a `--promote` option."""
    assert "--promote" in _option_names(run)


def test_help_documents_promote():
    """`finish --help` and `run --help` must document the promote behaviour."""
    finish_result = CliRunner().invoke(finish_cmd, ["--help"])
    assert finish_result.exit_code == 0
    assert "--promote" in finish_result.output
    assert "promotion" in finish_result.output.lower()

    run_result = CliRunner().invoke(run, ["--help"])
    assert run_result.exit_code == 0
    assert "--promote" in run_result.output
    assert "promotion" in run_result.output.lower()


@pytest.fixture
def mock_manager_and_env():
    # Setup mocks for PolecatManager, git environment, and helpers
    with patch("polecat.finalize.PolecatManager") as mock_mgr_cls:
        manager = MagicMock()
        mock_mgr_cls.return_value = manager

        manager.polecats_dir = Path("/tmp/polecat/polecats")
        manager.home_dir = Path("/tmp/polecat/home")

        # Mock storage and task
        mock_storage = MagicMock()
        manager.storage = mock_storage

        task = MagicMock()
        task.id = "task-1"
        task.title = "Test Task"
        task.body = "Test task body"
        task.project = "aops"
        task.status = "in_progress"
        task.base_branch = "dev"
        mock_storage.get_task.return_value = task

        manager.resolve_project_alias.return_value = "aops"
        manager.default_branch_for.return_value = "dev"
        manager.resolve_branch_name.return_value = "test-branch"
        manager.is_shared_branch.return_value = False

        # Mock other dependencies that are dynamically imported
        with (
            patch("polecat.cli._check_gh_installed", return_value=True),
            patch("polecat.cli._read_latest_real_transcript_path", return_value=None),
            patch("polecat.pkb_bridge.release_task", return_value=True),
            patch("os.path.exists", return_value=True),
        ):
            yield manager, task


def run_finish_test(manager, task, is_shared, promote, existing_pr, monkeypatch):
    manager.is_shared_branch.return_value = is_shared

    captured_runs = []

    def mock_run(args, **kwargs):
        captured_runs.append(args)
        is_text = kwargs.get("text") or kwargs.get("universal_newlines")

        # Default mock behavior
        stdout = ""
        stderr = ""
        returncode = 0

        if args == ["git", "status", "--porcelain"]:
            stdout = ""
        elif args[:2] == ["git", "fetch"]:
            stdout = ""
        elif args[:2] == ["git", "diff"] and "--quiet" in args:
            returncode = 1  # changes exist
        elif args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            stdout = "test-branch"
        elif args[:3] == ["git", "merge-base"]:
            stdout = "base-commit-hash"
        elif args[:3] == ["git", "rev-parse"]:
            stdout = "base-commit-hash"
        elif args[:2] == ["git", "ls-remote"]:
            if is_shared:
                stdout = "hash\trefs/heads/test-branch"
            else:
                stdout = ""
        elif args[:2] == ["git", "push"]:
            stdout = ""
        elif args[:3] == ["gh", "pr", "list"]:
            if existing_pr:
                stdout = (
                    '[{"number": 1770, "url": "https://github.com/nicsuzor/academicOps/pull/1770"}]'
                )
            else:
                stdout = "[]"
        elif args[:2] == ["git", "diff"] and "--shortstat" in args:
            stdout = "1 file changed, 1 insertion(+)"

        if not is_text:
            if isinstance(stdout, str):
                stdout = stdout.encode()
            if isinstance(stderr, str):
                stderr = stderr.encode()
        else:
            if isinstance(stdout, bytes):
                stdout = stdout.decode()
            if isinstance(stderr, bytes):
                stderr = stderr.decode()

        return subprocess.CompletedProcess(args, returncode, stdout, stderr)

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/polecat/polecats/task-1"))

    # Run the click command
    args = []
    if promote:
        args.append("--promote")

    result = CliRunner().invoke(finish_cmd, args, obj={})
    return result, captured_runs


def test_promote_existing_pr_promote(mock_manager_and_env, monkeypatch):
    """--promote + an existing open PR -> a gh pr ready call is made; finish
    never creates or edits the PR body itself."""
    manager, task = mock_manager_and_env
    result, captured_runs = run_finish_test(
        manager, task, is_shared=True, promote=True, existing_pr=True, monkeypatch=monkeypatch
    )

    assert result.exit_code == 0
    assert not [args for args in captured_runs if args[:3] == ["gh", "pr", "create"]]
    assert not [args for args in captured_runs if args[:3] == ["gh", "pr", "edit"]]

    ready_calls = [args for args in captured_runs if args[:3] == ["gh", "pr", "ready"]]
    assert len(ready_calls) == 1
    assert ready_calls[0] == ["gh", "pr", "ready", "1770"]


def test_promote_existing_pr_no_promote(mock_manager_and_env, monkeypatch):
    """No --promote -> no gh pr ready call, even with an existing open PR."""
    manager, task = mock_manager_and_env
    result, captured_runs = run_finish_test(
        manager, task, is_shared=True, promote=False, existing_pr=True, monkeypatch=monkeypatch
    )

    assert result.exit_code == 0
    assert not [args for args in captured_runs if args[:3] == ["gh", "pr", "create"]]
    assert not [args for args in captured_runs if args[:3] == ["gh", "pr", "edit"]]
    assert not [args for args in captured_runs if args[:3] == ["gh", "pr", "ready"]]


def test_promote_no_existing_pr(mock_manager_and_env, monkeypatch):
    """--promote with no PR filed yet -> nothing to promote, no ready call,
    and finish does not fall back to creating one."""
    manager, task = mock_manager_and_env
    result, captured_runs = run_finish_test(
        manager, task, is_shared=True, promote=True, existing_pr=False, monkeypatch=monkeypatch
    )

    assert result.exit_code == 0
    assert not [args for args in captured_runs if args[:3] == ["gh", "pr", "create"]]
    assert not [args for args in captured_runs if args[:3] == ["gh", "pr", "ready"]]
