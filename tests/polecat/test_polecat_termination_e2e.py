#!/usr/bin/env python3
"""End-to-end test for Gemini worker termination after ``release_task``.

Regression harness for issue #521: a Gemini polecat kept running for ~1 hour
after the worker called ``release_task`` with status=done. Unlike Claude,
the Gemini CLI does not emit a Stop hook that polecat can latch onto, so the
supervisor must use a PKB-poll termination watchdog to kill the container
after the task transitions to a terminal status.

This test is gated so it will never run in the default suite:

* ``@pytest.mark.slow`` / ``@pytest.mark.e2e`` — excluded by the default
  ``addopts`` pytest filter (``-m 'not slow and not integration and not demo'``).
* ``POLECAT_E2E=1`` — opt-in env flag.
* Docker + ``aops-crew`` image must be present.
* ``PKB_MCP_URL`` must be set and reachable.
* ``GEMINI_API_KEY`` or equivalent creds must be in the environment.

When all gates are satisfied, the test:

1. Creates a PKB task instructing the worker to call ``release_task`` with
   status=done and a one-line summary, and then stop.
2. Launches ``polecat run -t <id> -p <project> -g`` as a subprocess.
3. Polls PKB until the task transitions to a terminal status (max 10 min).
4. After that transition, asserts the polecat subprocess exits within a
   120-second hard deadline.

Observed failure on current main: polecat's blocking wait on the Gemini
CLI has no upper bound, so the container keeps running past ``release_task``
(ultimately hitting the ``429 MODEL_CAPACITY_EXHAUSTED`` retry loop from
issue #521) and this test times out.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from tests.conftest import _docker_available  # noqa: E402

TERMINAL_STATUSES = {"done", "merge_ready", "blocked", "cancelled"}

# Worker prompt embedded in the task body. Kept minimal so the worker does the
# one thing we care about — call release_task(done) — and then stop. Any
# extra post-release activity is exactly what issue #521 is about.
_WORKER_INSTRUCTION = (
    "Call release_task with status=done and a one-line summary. Then stop. Do nothing else."
)


def _pkb_available() -> bool:
    if not os.environ.get("PKB_MCP_URL"):
        return False
    try:
        from polecat.pkb_bridge import _get_client  # type: ignore

        _get_client()
        return True
    except Exception:
        return False


def _poll_status(task_id: str) -> str | None:
    from polecat.pkb_bridge import get_task as pkb_get_task  # type: ignore

    task = pkb_get_task(task_id)
    if task is None:
        return None
    return task.status


@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("POLECAT_E2E") != "1",
    reason="E2E test — opt in with POLECAT_E2E=1",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker / aops-crew image unavailable")
@pytest.mark.skipif(not _pkb_available(), reason="PKB MCP server unreachable")
def test_gemini_terminates_after_release_task(tmp_path: Path) -> None:
    """Gemini worker container must exit within 120s of PKB terminal status."""
    from polecat.pkb_bridge import (  # type: ignore
        _get_client,
    )

    project = os.environ.get("POLECAT_E2E_PROJECT")
    if not project:
        pytest.fail(
            "POLECAT_E2E_PROJECT must be set explicitly — no silent default. "
            "Set it to the project slug to run against (e.g. POLECAT_E2E_PROJECT=aops)."
        )
    client = _get_client()

    create_result = client.call_tool(
        "create_task",
        {
            "title": "e2e: gemini termination watchdog (#521)",
            "body": _WORKER_INSTRUCTION,
            "project": project,
            "type": "task",
            "status": "ready",
            "tags": ["test", "e2e", "polecat-termination"],
        },
    )
    assert create_result is not None, "PKB create_task returned None"

    task_id: str | None = None
    if isinstance(create_result, dict):
        fm = create_result.get("frontmatter") or {}
        task_id = fm.get("id") or create_result.get("id")
    if not task_id:
        pytest.fail(f"Could not extract task id from PKB create_task response: {create_result!r}")

    transcript_path = (
        Path(os.environ.get("POLECAT_HOME", Path.home() / ".aops"))
        / "polecats"
        / f"{task_id}.jsonl"
    )

    polecat_bin = shutil.which("polecat") or shutil.which("pc")
    if polecat_bin is None:
        # Fall back to ``python polecat/cli.py``
        cli_path = REPO_ROOT / "polecat" / "cli.py"
        cmd = [sys.executable, str(cli_path), "run", "-t", task_id, "-p", project, "-g"]
    else:
        cmd = [polecat_bin, "run", "-t", task_id, "-p", project, "-g"]

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        status_deadline = time.monotonic() + 600.0  # 10 min
        observed_terminal_at: float | None = None
        last_status: str | None = None

        while time.monotonic() < status_deadline:
            if proc.poll() is not None:
                # Process exited before we observed a terminal status — that's
                # fine if it released the task; recheck once and bail.
                last_status = _poll_status(task_id)
                if last_status in TERMINAL_STATUSES:
                    observed_terminal_at = time.monotonic()
                break

            last_status = _poll_status(task_id)
            if last_status in TERMINAL_STATUSES:
                observed_terminal_at = time.monotonic()
                break
            time.sleep(5.0)

        if observed_terminal_at is None:
            proc.kill()
            pytest.fail(
                f"Task {task_id} never reached a terminal status within 10 min "
                f"(last status: {last_status!r}). "
                f"Transcript: {transcript_path}"
            )

        # Now the gauntlet: worker must exit within 120s of terminal status.
        termination_deadline = observed_terminal_at + 120.0
        while time.monotonic() < termination_deadline:
            if proc.poll() is not None:
                return  # Success — worker shut down in time.
            time.sleep(2.0)

        proc.kill()
        pytest.fail(
            f"Polecat worker for task {task_id} did not exit within 120s "
            f"after PKB status={last_status!r}. "
            f"This is the #521 regression. Transcript: {transcript_path}"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
