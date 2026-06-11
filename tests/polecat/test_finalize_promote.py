"""Tests for the `promote` path in polecat/finalize.py and polecat/cli.py."""

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
            patch("polecat.cli._generate_pr_body", return_value="Dummy PR Body"),
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


def test_promote_shared_no_promote_create(mock_manager_and_env, monkeypatch):
    """(a) shared + no-promote + create -> --draft PRESENT in the gh pr create argv"""
    manager, task = mock_manager_and_env
    result, captured_runs = run_finish_test(
        manager, task, is_shared=True, promote=False, existing_pr=False, monkeypatch=monkeypatch
    )

    assert result.exit_code == 0
    create_call = [args for args in captured_runs if args[:3] == ["gh", "pr", "create"]]
    assert len(create_call) == 1
    assert "--draft" in create_call[0]


def test_promote_shared_promote_create(mock_manager_and_env, monkeypatch):
    """(b) shared + promote + create -> --draft ABSENT"""
    manager, task = mock_manager_and_env
    result, captured_runs = run_finish_test(
        manager, task, is_shared=True, promote=True, existing_pr=False, monkeypatch=monkeypatch
    )

    assert result.exit_code == 0
    create_call = [args for args in captured_runs if args[:3] == ["gh", "pr", "create"]]
    assert len(create_call) == 1
    assert "--draft" not in create_call[0]


def test_promote_existing_pr_promote(mock_manager_and_env, monkeypatch):
    """(c) existing-PR + promote -> a gh pr ready call is made"""
    manager, task = mock_manager_and_env
    result, captured_runs = run_finish_test(
        manager, task, is_shared=True, promote=True, existing_pr=True, monkeypatch=monkeypatch
    )

    assert result.exit_code == 0
    create_calls = [args for args in captured_runs if args[:3] == ["gh", "pr", "create"]]
    assert len(create_calls) == 0

    edit_calls = [args for args in captured_runs if args[:3] == ["gh", "pr", "edit"]]
    assert len(edit_calls) == 1

    ready_calls = [args for args in captured_runs if args[:3] == ["gh", "pr", "ready"]]
    assert len(ready_calls) == 1
    assert ready_calls[0] == ["gh", "pr", "ready", "1770"]


def test_promote_existing_pr_no_promote(mock_manager_and_env, monkeypatch):
    """(d) existing-PR + no-promote -> NO gh pr ready call"""
    manager, task = mock_manager_and_env
    result, captured_runs = run_finish_test(
        manager, task, is_shared=True, promote=False, existing_pr=True, monkeypatch=monkeypatch
    )

    assert result.exit_code == 0
    create_calls = [args for args in captured_runs if args[:3] == ["gh", "pr", "create"]]
    assert len(create_calls) == 0

    edit_calls = [args for args in captured_runs if args[:3] == ["gh", "pr", "edit"]]
    assert len(edit_calls) == 1

    ready_calls = [args for args in captured_runs if args[:3] == ["gh", "pr", "ready"]]
    assert len(ready_calls) == 0


def test_promote_non_shared_create(mock_manager_and_env, monkeypatch):
    """(e) non-shared -> --draft ABSENT (backward-compat)"""
    manager, task = mock_manager_and_env
    result, captured_runs = run_finish_test(
        manager, task, is_shared=False, promote=False, existing_pr=False, monkeypatch=monkeypatch
    )

    assert result.exit_code == 0
    create_calls = [args for args in captured_runs if args[:3] == ["gh", "pr", "create"]]
    assert len(create_calls) == 1
    assert "--draft" not in create_calls[0]
