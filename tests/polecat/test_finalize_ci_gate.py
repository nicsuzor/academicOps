"""Tests for the CI check gate in polecat/finalize.py.

When `polecat finish` is called and the PR has failing CI checks (FAILURE,
ERROR, TIMED_OUT), the task must stay 'in_progress' instead of being released
as 'merge_ready'. This prevents a task with a broken PR from becoming
merge-locked and requiring --force to re-dispatch.

See: aops-deca22c5 — polecat finish marks task merge_ready even when PR CI is red
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from click.testing import CliRunner

from polecat.finalize import finish_cmd

FINALIZE_SRC = (REPO_ROOT / "polecat" / "finalize.py").read_text()


# ---------------------------------------------------------------------------
# Source-level structural assertions
# ---------------------------------------------------------------------------


def test_ci_gate_checks_failing_conclusions():
    """The gate must reject FAILURE, ERROR, and TIMED_OUT conclusions."""
    assert '"FAILURE"' in FINALIZE_SRC
    assert '"ERROR"' in FINALIZE_SRC
    assert '"TIMED_OUT"' in FINALIZE_SRC


def test_ci_gate_uses_status_check_rollup():
    """The gate must query statusCheckRollup from GitHub."""
    assert "statusCheckRollup" in FINALIZE_SRC


def test_ci_gate_sets_in_progress_on_failure():
    """When CI fails, the target status must be in_progress, not merge_ready."""
    assert '"in_progress" if ci_failed_checks else "merge_ready"' in FINALIZE_SRC


def test_ci_gate_uses_update_task_not_release_task():
    """The in_progress path uses update_task (not release_task) since
    release_task only accepts terminal/handoff statuses."""
    assert "pkb_update_status" in FINALIZE_SRC or "update_task as pkb_update_status" in FINALIZE_SRC


def test_ci_gate_prints_re_dispatch_hint():
    """The output for a CI-failing finish must tell the operator how to re-dispatch."""
    assert "polecat run -t" in FINALIZE_SRC


# ---------------------------------------------------------------------------
# Behavioural integration tests (with mocked subprocess)
# ---------------------------------------------------------------------------


def _make_mock_run(existing_pr_number, ci_rollup):
    """Build a mock subprocess.run that returns realistic outputs."""

    def mock_run(args, **kwargs):
        is_text = kwargs.get("text") or kwargs.get("universal_newlines")
        stdout = ""
        stderr = ""
        returncode = 0

        if args == ["git", "status", "--porcelain"]:
            stdout = ""
        elif args[:2] == ["git", "fetch"]:
            stdout = ""
        elif args[:2] == ["git", "diff"] and "--quiet" in args:
            returncode = 1  # changes exist
        elif args[:3] == ["git", "merge-base"]:
            stdout = "abc"
        elif args[:3] == ["git", "rev-parse"]:
            stdout = "abc"
        elif args[:2] == ["git", "push"]:
            stdout = ""
        elif args[:2] == ["git", "branch"] and "--show-current" in args:
            stdout = "polecat/test-task"
        elif args[:3] == ["gh", "pr", "list"] and "--json" in args and "url,number" in args:
            import json

            if existing_pr_number:
                stdout = json.dumps(
                    [
                        {
                            "number": existing_pr_number,
                            "url": f"https://github.com/org/repo/pull/{existing_pr_number}",
                        }
                    ]
                )
            else:
                stdout = "[]"
        elif args[:3] == ["gh", "pr", "list"]:
            import json

            if existing_pr_number:
                stdout = json.dumps(
                    [
                        {
                            "number": existing_pr_number,
                            "url": f"https://github.com/org/repo/pull/{existing_pr_number}",
                        }
                    ]
                )
            else:
                stdout = "[]"
        elif args[:3] == ["gh", "pr", "view"] and "--json" in args and "statusCheckRollup" in args:
            import json

            stdout = json.dumps({"statusCheckRollup": ci_rollup})
        elif args[:2] == ["git", "diff"] and "--shortstat" in args:
            stdout = "1 file changed, 5 insertions(+)"
        elif args[:3] == ["gh", "pr", "edit"]:
            stdout = ""
        elif args[:3] == ["gh", "pr", "create"]:
            stdout = ""

        if not is_text:
            if isinstance(stdout, str):
                stdout = stdout.encode()
            if isinstance(stderr, str):
                stderr = stderr.encode()

        return subprocess.CompletedProcess(args, returncode, stdout, stderr)

    return mock_run


def _base_manager_ctx():
    """Context manager that wires up a minimal PolecatManager mock."""
    mock_mgr_cls = patch("polecat.finalize.PolecatManager")
    mock_check_gh = patch("polecat.cli._check_gh_installed", return_value=True)
    mock_transcript = patch("polecat.cli._read_latest_real_transcript_path", return_value=None)
    mock_pr_body = patch("polecat.cli._generate_pr_body", return_value="PR body")
    mock_release = patch("polecat.pkb_bridge.release_task", return_value=True)
    mock_update = patch("polecat.pkb_bridge.update_task", return_value=True)

    return mock_mgr_cls, mock_check_gh, mock_transcript, mock_pr_body, mock_release, mock_update


def _build_task(task_id="aops-test"):
    task = MagicMock()
    task.id = task_id
    task.title = "Test Task"
    task.body = "body"
    task.project = "aops"
    task.status = "in_progress"
    task.base_branch = "dev"
    task.pr_url = None
    return task


def test_finish_sets_merge_ready_when_ci_passes(monkeypatch):
    """Regression: when all CI checks pass, target status is still merge_ready."""
    ci_rollup = [
        {"name": "build", "status": "COMPLETED", "conclusion": "SUCCESS"},
        {"name": "test", "status": "COMPLETED", "conclusion": "SUCCESS"},
    ]

    (
        mock_mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release,
        mock_update,
    ) = _base_manager_ctx()

    with (
        mock_mgr_cls as mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release as release_mock,
        mock_update as _update_mock,
    ):
        manager = MagicMock()
        mgr_cls.return_value = manager
        manager.polecats_dir = Path("/tmp/polecats")
        manager.home_dir = Path("/tmp/home")
        manager.storage = MagicMock()
        task = _build_task()
        manager.storage.get_task.return_value = task
        manager.resolve_project_alias.return_value = "aops"
        manager.default_branch_for.return_value = "dev"
        manager.resolve_branch_name.return_value = "polecat/aops-test"
        manager.is_shared_branch.return_value = False

        monkeypatch.setattr(subprocess, "run", _make_mock_run(1541, ci_rollup))
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/polecats/aops-test"))

        result = CliRunner().invoke(finish_cmd, [], obj={})

    assert result.exit_code == 0, result.output
    # release_task should have been called (not update_task for in_progress)
    release_mock.assert_called_once()
    call_kwargs = release_mock.call_args
    assert call_kwargs[1].get("status") == "merge_ready" or call_kwargs[0][1] == "merge_ready"


def test_finish_sets_in_progress_when_ci_fails(monkeypatch):
    """Core AC: when the PR has a FAILURE check, task stays in_progress."""
    ci_rollup = [
        {"name": "Enforcer", "status": "COMPLETED", "conclusion": "FAILURE"},
        {"name": "build", "status": "COMPLETED", "conclusion": "SUCCESS"},
    ]

    (
        mock_mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release,
        mock_update,
    ) = _base_manager_ctx()

    with (
        mock_mgr_cls as mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release as release_mock,
        mock_update as update_mock,
    ):
        manager = MagicMock()
        mgr_cls.return_value = manager
        manager.polecats_dir = Path("/tmp/polecats")
        manager.home_dir = Path("/tmp/home")
        manager.storage = MagicMock()
        task = _build_task()
        manager.storage.get_task.return_value = task
        manager.resolve_project_alias.return_value = "aops"
        manager.default_branch_for.return_value = "dev"
        manager.resolve_branch_name.return_value = "polecat/aops-test"
        manager.is_shared_branch.return_value = False

        monkeypatch.setattr(subprocess, "run", _make_mock_run(1541, ci_rollup))
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/polecats/aops-test"))

        result = CliRunner().invoke(finish_cmd, [], obj={})

    assert result.exit_code == 0, result.output
    # release_task must NOT be called — we use update_task for in_progress
    release_mock.assert_not_called()
    update_mock.assert_called_once()
    call_kwargs = update_mock.call_args
    # Should have been called with status="in_progress"
    assert "in_progress" in str(call_kwargs)
    # Task must stay in_progress (not released as merge_ready)
    assert "Task marked as 'merge_ready'" not in result.output


def test_finish_sets_in_progress_when_ci_errors(monkeypatch):
    """ERROR conclusion also triggers in_progress gate."""
    ci_rollup = [
        {"name": "Enforcer", "status": "COMPLETED", "conclusion": "ERROR"},
    ]

    (
        mock_mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release,
        mock_update,
    ) = _base_manager_ctx()

    with (
        mock_mgr_cls as mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release as release_mock,
        mock_update as update_mock,
    ):
        manager = MagicMock()
        mgr_cls.return_value = manager
        manager.polecats_dir = Path("/tmp/polecats")
        manager.home_dir = Path("/tmp/home")
        manager.storage = MagicMock()
        task = _build_task()
        manager.storage.get_task.return_value = task
        manager.resolve_project_alias.return_value = "aops"
        manager.default_branch_for.return_value = "dev"
        manager.resolve_branch_name.return_value = "polecat/aops-test"
        manager.is_shared_branch.return_value = False

        monkeypatch.setattr(subprocess, "run", _make_mock_run(1541, ci_rollup))
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/polecats/aops-test"))

        result = CliRunner().invoke(finish_cmd, [], obj={})

    assert result.exit_code == 0, result.output
    release_mock.assert_not_called()
    update_mock.assert_called_once()


def test_finish_partial_ignores_ci_gate(monkeypatch):
    """--partial must still go through release_task as partial even if CI fails.
    The CI gate only applies to the merge_ready path."""
    ci_rollup = [
        {"name": "Enforcer", "status": "COMPLETED", "conclusion": "FAILURE"},
    ]

    (
        mock_mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release,
        mock_update,
    ) = _base_manager_ctx()

    with (
        mock_mgr_cls as mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release as release_mock,
        mock_update as _update_mock,
    ):
        manager = MagicMock()
        mgr_cls.return_value = manager
        manager.polecats_dir = Path("/tmp/polecats")
        manager.home_dir = Path("/tmp/home")
        manager.storage = MagicMock()
        task = _build_task()
        manager.storage.get_task.return_value = task
        manager.resolve_project_alias.return_value = "aops"
        manager.default_branch_for.return_value = "dev"
        manager.resolve_branch_name.return_value = "polecat/aops-test"
        manager.is_shared_branch.return_value = False

        monkeypatch.setattr(subprocess, "run", _make_mock_run(1541, ci_rollup))
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/polecats/aops-test"))

        result = CliRunner().invoke(finish_cmd, ["--partial"], obj={})

    assert result.exit_code == 0, result.output
    # partial uses release_task with status=partial
    release_mock.assert_called_once()
    call_kwargs = release_mock.call_args
    assert "partial" in str(call_kwargs)


def test_finish_failopen_when_ci_check_query_fails(monkeypatch):
    """If gh pr view fails (e.g. no auth), finish should proceed to merge_ready
    rather than blocking on tooling failure (fail-open)."""

    def mock_run_ci_error(args, **kwargs):
        is_text = kwargs.get("text") or kwargs.get("universal_newlines")
        stdout = ""
        returncode = 0
        stderr = ""

        if args == ["git", "status", "--porcelain"]:
            stdout = ""
        elif args[:2] == ["git", "fetch"]:
            stdout = ""
        elif args[:2] == ["git", "diff"] and "--quiet" in args:
            returncode = 1
        elif args[:3] == ["git", "merge-base"]:
            stdout = "abc"
        elif args[:3] == ["git", "rev-parse"]:
            stdout = "abc"
        elif args[:2] == ["git", "push"]:
            stdout = ""
        elif args[:2] == ["git", "branch"] and "--show-current" in args:
            stdout = "polecat/aops-test"
        elif args[:3] == ["gh", "pr", "list"]:
            import json

            stdout = json.dumps([{"number": 1541, "url": "https://github.com/org/repo/pull/1541"}])
        elif args[:3] == ["gh", "pr", "view"]:
            # Simulate gh failure
            returncode = 1
            stderr = "gh: authentication required"
        elif args[:2] == ["git", "diff"] and "--shortstat" in args:
            stdout = "1 file changed"

        if not is_text:
            if isinstance(stdout, str):
                stdout = stdout.encode()
            if isinstance(stderr, str):
                stderr = stderr.encode()
        return subprocess.CompletedProcess(args, returncode, stdout, stderr)

    (
        mock_mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release,
        mock_update,
    ) = _base_manager_ctx()

    with (
        mock_mgr_cls as mgr_cls,
        mock_check_gh,
        mock_transcript,
        mock_pr_body,
        mock_release as release_mock,
        mock_update as _update_mock,
    ):
        manager = MagicMock()
        mgr_cls.return_value = manager
        manager.polecats_dir = Path("/tmp/polecats")
        manager.home_dir = Path("/tmp/home")
        manager.storage = MagicMock()
        task = _build_task()
        manager.storage.get_task.return_value = task
        manager.resolve_project_alias.return_value = "aops"
        manager.default_branch_for.return_value = "dev"
        manager.resolve_branch_name.return_value = "polecat/aops-test"
        manager.is_shared_branch.return_value = False

        monkeypatch.setattr(subprocess, "run", mock_run_ci_error)
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/polecats/aops-test"))

        result = CliRunner().invoke(finish_cmd, [], obj={})

    assert result.exit_code == 0, result.output
    # Fail-open: should still release as merge_ready
    release_mock.assert_called_once()
    call_kwargs = release_mock.call_args
    assert "merge_ready" in str(call_kwargs)
