#!/usr/bin/env python3
"""End-to-end test: Gemini polecat persists non-PR task result to PKB.

Regression harness for the 2026-04-28 silent-data-loss incident (PR #784):
a Gemini spike polecat completed its investigation but could not call
release_task because gemini-extension.json was missing PKB_MCP_URL in the
pkb MCP server env block. The result was lost — the supervisor had to
manually transcribe the worker's stdout.

Failure mode: the Gemini session starts with zero PKB tools. The worker
reports "I do not have direct access to the remote task management tools"
and exits without calling release_task. The task stays in-progress
indefinitely (or until the supervisor notices). Status never transitions
to a terminal value, so this test fails after a timeout — loudly, not
silently.

The static config tests in test_gemini_extension_validation.py::
TestSourceManifestMcpConfig catch this regression without any LLM call.
This E2E test catches it in the running system — useful when the config
is correct on paper but something in the wiring still breaks at runtime.

Gating (all must pass to run):

* ``@pytest.mark.slow`` / ``@pytest.mark.e2e`` — excluded by the default
  ``addopts`` filter.
* ``POLECAT_E2E=1`` — opt-in env flag.
* Docker + ``aops-crew`` image must be present.
* ``PKB_MCP_URL`` must be set and reachable.
* Gemini credentials (``GEMINI_API_KEY`` or equivalent) in the environment.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

_TASK_ID_RE = re.compile(r"(task-[0-9a-f]+|epic-[0-9a-f]+|aops-[0-9a-f]+)")


def _extract_task_id(resp: object) -> str | None:
    if isinstance(resp, dict):
        fm = resp.get("frontmatter") or {}
        return fm.get("id")
    if isinstance(resp, str):
        m = _TASK_ID_RE.search(resp)
        if m:
            return m.group(1)
    return None


from tests.polecat.conftest import _DEFAULT_AOPS_SCRATCH_PARENT  # noqa: E402

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from tests.conftest import _docker_available  # noqa: E402

TERMINAL_STATUSES = {"done", "merge_ready", "blocked", "cancelled"}

# Worker prompt: minimal spike-style task. The key assertion is that the worker
# can call release_task at all — which requires working PKB MCP access.
# Type is explicitly "spike" to mirror the production failure mode.
_WORKER_INSTRUCTION = (
    "This is a spike validation task. "
    "Confirm you have PKB MCP tool access, then call release_task with "
    "status=done and a one-sentence summary confirming whether PKB MCP worked. "
    "Then stop. Do nothing else."
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


def _poll_task(task_id: str):
    from polecat.pkb_bridge import get_task as pkb_get_task  # type: ignore

    return pkb_get_task(task_id)


@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("POLECAT_E2E") != "1",
    reason="E2E test — opt in with POLECAT_E2E=1",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker / aops-crew image unavailable")
@pytest.mark.skipif(not _pkb_available(), reason="PKB MCP server unreachable")
def test_gemini_polecat_persists_non_pr_result(tmp_path: Path) -> None:
    """Gemini polecat must call release_task for a non-PR (spike) task.

    This is the regression test for the 2026-04-28 incident: a Gemini spike
    polecat had no PKB tools and its result was silently lost. Without PKB MCP
    access the task never reaches a terminal status and this test fails.
    """
    from polecat.pkb_bridge import _get_client  # type: ignore

    project = os.environ.get("POLECAT_E2E_PROJECT")
    if not project:
        pytest.fail(
            "POLECAT_E2E_PROJECT must be set explicitly. "
            "Set it to the project slug (e.g. POLECAT_E2E_PROJECT=aops)."
        )
    client = _get_client()

    parent_override = os.environ.get("POLECAT_E2E_PARENT")
    if parent_override:
        scratch_parent_id = parent_override
    elif project == "aops":
        scratch_parent_id = _DEFAULT_AOPS_SCRATCH_PARENT
    else:
        pytest.fail(
            f"No default scratch parent for project={project!r}. "
            "Set POLECAT_E2E_PARENT to an existing epic ID under that project."
        )

    create_result = client.call_tool(
        "create_task",
        {
            "title": "e2e: gemini PKB persistence (#784 regression)",
            "body": _WORKER_INSTRUCTION,
            "parent": scratch_parent_id,
            "tags": ["test", "e2e", "gemini-pkb-persistence"],
            "project": project,
            "status": "ready",
            "type": "spike",
        },
    )
    assert create_result is not None, "PKB create_task returned None"

    task_id = _extract_task_id(create_result)
    if not task_id:
        pytest.fail(f"Could not extract task id from PKB create_task response: {create_result!r}")

    transcript_path = (
        Path(os.environ.get("POLECAT_HOME", Path.home() / ".aops"))
        / "polecats"
        / f"{task_id}.jsonl"
    )

    polecat_bin = shutil.which("polecat") or shutil.which("pc")
    if polecat_bin is None:
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
        # Allow up to 10 min for the worker to call release_task.
        deadline = time.monotonic() + 600.0
        last_status: str | None = None

        while time.monotonic() < deadline:
            if proc.poll() is not None:
                last_status = getattr(_poll_task(task_id), "status", None)
                break

            task = _poll_task(task_id)
            last_status = task.status if task else None
            if last_status in TERMINAL_STATUSES:
                break
            time.sleep(5.0)

        if last_status not in TERMINAL_STATUSES:
            proc.kill()
            pytest.fail(
                f"Task {task_id} never reached a terminal status within 10 min "
                f"(last status: {last_status!r}). "
                "This means the Gemini worker could not call release_task — "
                "likely missing PKB MCP access. "
                f"Transcript: {transcript_path}. "
                "Check gemini-extension.json: PKB_MCP_URL must be in the pkb "
                "MCP server env block. Regression ledger: PR #784 (2026-04-28)."
            )

        # Verify the task has a non-empty body (summary written by the worker).
        task = _poll_task(task_id)
        assert task is not None, f"Could not retrieve task {task_id} after terminal status"
        # The worker writes its summary into the task body via release_task.
        # An empty body means release_task was never called with a summary, or
        # something silently swallowed the update. Both are failures.
        assert task.body and task.body.strip(), (
            f"Task {task_id} reached terminal status {task.status!r} but body is empty. "
            "The Gemini worker may have called release_task without a summary, or "
            f"the PKB update was silently lost. Transcript: {transcript_path}"
        )

    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass

        if task_id:
            try:
                client.call_tool("delete", {"id": task_id})
            except Exception as e:  # pragma: no cover — cleanup-only
                print(f"cleanup: failed to delete task {task_id}: {e}", file=sys.stderr)
