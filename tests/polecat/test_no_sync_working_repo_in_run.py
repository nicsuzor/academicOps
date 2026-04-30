"""Regression test: ``polecat run`` must not invoke ``_sync_working_repo``.

The dispatch path (run pipeline) intentionally does not perform a working-repo
sync — that responsibility belongs to ``polecat sync``. This test locks in
that boundary so the call cannot be re-introduced into ``run`` without an
explicit decision.

Step 2 of the Polecat v2 module split (epic-4234682b) — see commit log.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import click.testing

# Mirror the path setup used by other polecat tests (test_cli_revert.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "polecat"))
if str(REPO_ROOT / "aops-core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# Run command lives in polecat.cli; import via the module alias used by the CLI.
from polecat import cli as polecat_cli  # noqa: E402


def _abort_after_pkb_check(*_args, **_kwargs):
    """Stand-in for ``_require_pkb_url_or_exit`` that aborts ``run`` early.

    We don't need the rest of the dispatch pipeline to execute — we only
    need to assert that, in any path the CLI takes, ``_sync_working_repo``
    is never invoked. Aborting via SystemExit before any I/O keeps the test
    hermetic.
    """
    raise SystemExit(99)


def test_run_does_not_call_sync_working_repo():
    """Invoking ``polecat run`` must never reach ``_sync_working_repo``."""
    runner = click.testing.CliRunner()

    with (
        patch.object(polecat_cli, "_sync_working_repo") as mock_sync,
        patch.object(polecat_cli, "_require_pkb_url_or_exit", _abort_after_pkb_check),
    ):
        # The exact exit code is irrelevant — we only assert that the patched
        # ``_sync_working_repo`` was never called.
        runner.invoke(polecat_cli.main, ["run", "-p", "aops"])
        assert mock_sync.call_count == 0, (
            "polecat run must not call _sync_working_repo "
            f"(was called {mock_sync.call_count} times)"
        )


def test_run_with_task_id_does_not_call_sync_working_repo():
    """Same invariant for the explicit --task-id branch of ``run``."""
    runner = click.testing.CliRunner()

    with (
        patch.object(polecat_cli, "_sync_working_repo") as mock_sync,
        patch.object(polecat_cli, "_require_pkb_url_or_exit", _abort_after_pkb_check),
    ):
        runner.invoke(polecat_cli.main, ["run", "-t", "aops-deadbeef"])
        assert mock_sync.call_count == 0, (
            "polecat run -t TASK_ID must not call _sync_working_repo "
            f"(was called {mock_sync.call_count} times)"
        )


def test_run_with_issue_does_not_call_sync_working_repo():
    """Same invariant for the --issue branch of ``run``."""
    runner = click.testing.CliRunner()

    with (
        patch.object(polecat_cli, "_sync_working_repo") as mock_sync,
        patch.object(polecat_cli, "_require_pkb_url_or_exit", _abort_after_pkb_check),
    ):
        runner.invoke(polecat_cli.main, ["run", "--issue", "owner/repo#1"])
        assert mock_sync.call_count == 0, (
            "polecat run --issue must not call _sync_working_repo "
            f"(was called {mock_sync.call_count} times)"
        )
