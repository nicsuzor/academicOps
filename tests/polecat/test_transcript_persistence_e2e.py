#!/usr/bin/env python3
"""End-to-end test for real Claude session transcript persistence on the host.

Regression harness for the issue surfaced 2026-04-15: polecat's "Transcript
saved" message points at a 215-byte summary stub stored at
``$POLECAT_HOME/polecats/<task-id>.jsonl``, while the *real* Claude Code
session transcript (~600 KB) is extracted to
``$AOPS_SESSIONS/polecats/<task-id>/<project>/-workspace/<uuid>.jsonl``.
Investigating two max-turns failures was painful because nothing surfaced the
real path and no pytest verified the real transcript made it to the host.

Three test cases:

1. ``test_real_transcript_persists_on_success`` — trivial task completes OK;
   asserts at least one real transcript ≥ 10 KB exists under the session dir.

2. ``test_real_transcript_persists_on_max_turns`` — marked ``xfail`` until
   ``--max-turns N`` CLI passthrough (task-1eae22cb) lands; verifies the real
   transcript survives budget exhaustion.

3. ``test_real_transcript_persists_on_graceful_shutdown`` — SIGTERM sent to
   the polecat subprocess; asserts transcript was extracted before exit.

Gated identically to ``test_polecat_termination_e2e.py``:

* ``@pytest.mark.slow`` / ``@pytest.mark.e2e`` — excluded by the default
  ``addopts`` pytest filter (``-m 'not slow and not integration and not demo'``).
* ``POLECAT_E2E=1`` — opt-in env flag.
* Docker + ``aops-crew`` image must be present.
* ``PKB_MCP_URL`` must be set and reachable.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

_TASK_ID_RE = re.compile(r"(task-[0-9a-f]+|epic-[0-9a-f]+|aops-[0-9a-f]+)")

# Minimum size (bytes) for a "real" Claude session transcript.
# The polecat summary stub is ~215 bytes; a real session is typically 10 KB+.
_MIN_REAL_TRANSCRIPT_BYTES = 10 * 1024  # 10 KB

# Known-stable scratch parent (same as termination e2e).
_DEFAULT_AOPS_SCRATCH_PARENT = "task-0d77545a"

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from tests.conftest import _docker_available  # noqa: E402

# Instruction for the success case: complete trivially so polecat exits cleanly.
_SUCCESS_INSTRUCTION = (
    "Call release_task with status=done and summary='e2e transcript persistence check'."
    " Then stop. Do nothing else."
)

# Instruction for the max-turns case: keep calling tools so the turn budget is
# more likely to exhaust.  With effort=xs the budget is 40 turns; this body
# encourages the agent to loop until cut off.
_MAX_TURNS_INSTRUCTION = (
    "List every Python file under polecat/ one by one using Bash. After each file,"
    " read its first 5 lines. Repeat until you have processed every file. Do NOT"
    " call release_task under any circumstances."
)

# Instruction for the graceful-shutdown (SIGTERM) case.
_SIGTERM_INSTRUCTION = (
    "Search for the string 'transcript' in every Python file under tests/."
    " Report how many matches you find. Do NOT call release_task."
)


def _extract_task_id(resp: object) -> str | None:
    if isinstance(resp, dict):
        fm = resp.get("frontmatter") or {}
        return fm.get("id") or resp.get("id")
    if isinstance(resp, str):
        m = _TASK_ID_RE.search(resp)
        if m:
            return m.group(1)
    return None


def _pkb_available() -> bool:
    if not os.environ.get("PKB_MCP_URL"):
        return False
    try:
        from polecat.pkb_bridge import _get_client  # type: ignore

        _get_client()
        return True
    except Exception:
        return False


def _get_sessions_base() -> Path:
    """Mirror cli._get_sessions_base() without importing the whole CLI."""
    try:
        from lib.paths import get_sessions_repo  # type: ignore

        return get_sessions_repo()
    except ImportError:
        aops_sessions = os.environ.get("AOPS_SESSIONS")
        if aops_sessions:
            return Path(aops_sessions)
        return Path(os.environ.get("POLECAT_HOME", str(Path.home() / ".polecat"))) / "sessions"


def _find_real_transcripts(session_dir: Path) -> list[Path]:
    """Return JSONL files under *session_dir* that exceed the stub threshold.

    The polecat summary stub is saved to a different location
    (``$POLECAT_HOME/polecats/<task-id>.jsonl``); what we look for here are the
    real Claude Code session files extracted from the container to
    ``session_dir/**/*.jsonl``.
    """
    if not session_dir.exists():
        return []
    return [
        p for p in session_dir.rglob("*.jsonl") if p.stat().st_size >= _MIN_REAL_TRANSCRIPT_BYTES
    ]


def _polecat_cmd(task_id: str, project: str) -> list[str]:
    """Build the polecat run command for *task_id*."""
    polecat_bin = shutil.which("polecat") or shutil.which("pc")
    if polecat_bin is None:
        cli_path = REPO_ROOT / "polecat" / "cli.py"
        return [sys.executable, str(cli_path), "run", "-t", task_id, "-p", project]
    return [polecat_bin, "run", "-t", task_id, "-p", project]


def _create_test_task(
    client, project: str, scratch_parent_id: str, title: str, body: str, tags: list[str]
) -> str:
    """Create a PKB task and return its ID, or call pytest.fail."""
    create_result = client.call_tool(
        "create_task",
        {
            "title": title,
            "body": body,
            "parent": scratch_parent_id,
            "tags": tags,
        },
    )
    assert create_result is not None, "PKB create_task returned None"
    task_id = _extract_task_id(create_result)
    if not task_id:
        pytest.fail(f"Could not extract task id from PKB create_task response: {create_result!r}")
    update_resp = client.call_tool(
        "update_task",
        {"id": task_id, "updates": {"project": project, "status": "ready"}},
    )
    if update_resp is None:
        pytest.fail(f"Failed to set project/status on task {task_id}")
    return task_id


def _cleanup_task(client, task_id: str) -> None:
    try:
        client.call_tool("delete", {"id": task_id})
    except Exception as e:  # pragma: no cover — cleanup-only
        print(f"cleanup: failed to delete task {task_id}: {e}", file=sys.stderr)


def _require_project() -> str:
    project = os.environ.get("POLECAT_E2E_PROJECT")
    if not project:
        pytest.fail("POLECAT_E2E_PROJECT must be set explicitly. Example: POLECAT_E2E_PROJECT=aops")
    return project


def _resolve_scratch_parent(project: str) -> str:
    parent_override = os.environ.get("POLECAT_E2E_PARENT")
    if parent_override:
        return parent_override
    if project == "aops":
        return _DEFAULT_AOPS_SCRATCH_PARENT
    pytest.fail(
        f"No default scratch parent for project={project!r}. "
        "Set POLECAT_E2E_PARENT to an existing epic ID under that project."
    )


# ---------------------------------------------------------------------------
# Test 1: success path
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("POLECAT_E2E") != "1",
    reason="E2E test — opt in with POLECAT_E2E=1",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker / aops-crew image unavailable")
@pytest.mark.skipif(not _pkb_available(), reason="PKB MCP server unreachable")
def test_real_transcript_persists_on_success() -> None:
    """Real Claude session transcript must exist and be ≥ 10 KB after a clean run."""
    from polecat.pkb_bridge import _get_client  # type: ignore

    project = _require_project()
    scratch_parent_id = _resolve_scratch_parent(project)
    client = _get_client()

    task_id = _create_test_task(
        client,
        project,
        scratch_parent_id,
        title="e2e: transcript-persistence success",
        body=_SUCCESS_INSTRUCTION,
        tags=["test", "e2e", "transcript-persistence"],
    )

    session_dir = _get_sessions_base() / "polecats" / task_id / project
    cmd = _polecat_cmd(task_id, project)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        print(result.stdout[-4000:] if len(result.stdout) > 4000 else result.stdout)
        if result.stderr:
            print(
                result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
                file=sys.stderr,
            )

        real_transcripts = _find_real_transcripts(session_dir)
        assert real_transcripts, (
            f"No real session transcript found under {session_dir}. "
            f"'Transcript saved' stub is at $POLECAT_HOME/polecats/{task_id}.jsonl — "
            "that is NOT the real transcript. "
            f"polecat exit code: {result.returncode}"
        )

        largest = max(real_transcripts, key=lambda p: p.stat().st_size)
        size = largest.stat().st_size
        assert size >= _MIN_REAL_TRANSCRIPT_BYTES, (
            f"Largest transcript ({largest}) is only {size} bytes — "
            f"expected ≥ {_MIN_REAL_TRANSCRIPT_BYTES} bytes for a real session. "
            "Likely the extraction path is pointing at the summary stub."
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"polecat run timed out after 600s for task {task_id}")
    finally:
        _cleanup_task(client, task_id)


# ---------------------------------------------------------------------------
# Test 2: max-turns path (xfail until task-1eae22cb lands)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("POLECAT_E2E") != "1",
    reason="E2E test — opt in with POLECAT_E2E=1",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker / aops-crew image unavailable")
@pytest.mark.skipif(not _pkb_available(), reason="PKB MCP server unreachable")
@pytest.mark.xfail(
    reason=(
        "Requires --max-turns N CLI passthrough (task-1eae22cb) to set a"
        " deterministically small budget. Without it, budget exhaustion is"
        " non-deterministic and may not trigger during the test window."
    ),
    strict=False,
)
def test_real_transcript_persists_on_max_turns() -> None:
    """Real transcript must be ≥ 10 KB even when the turn budget is exhausted.

    Without ``--max-turns N`` passthrough, polecat derives the budget from the
    task effort field (effort=xs → 40 turns).  This test creates a task that
    encourages the agent to loop, hoping the budget is exhausted before it
    finishes.  It is marked ``xfail`` because budget exhaustion is not
    guaranteed without an explicit ``--max-turns 3``-style CLI override.

    When task-1eae22cb lands (adds ``polecat run --max-turns N``), update this
    test to pass ``--max-turns 3`` so exhaustion is deterministic.
    """
    from polecat.pkb_bridge import _get_client  # type: ignore

    project = _require_project()
    scratch_parent_id = _resolve_scratch_parent(project)
    client = _get_client()

    # effort=xs gives a 40-turn budget via _compute_max_turns; the looping
    # instruction raises the chance the agent hits it.
    task_id = _create_test_task(
        client,
        project,
        scratch_parent_id,
        title="e2e: transcript-persistence max-turns",
        body=_MAX_TURNS_INSTRUCTION,
        tags=["test", "e2e", "transcript-persistence", "effort-xs"],
    )

    # Set effort=xs so _compute_max_turns returns "40".
    client.call_tool(
        "update_task",
        {"id": task_id, "updates": {"effort": "xs"}},
    )

    session_dir = _get_sessions_base() / "polecats" / task_id / project
    cmd = _polecat_cmd(task_id, project)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        combined = (result.stdout or "") + (result.stderr or "")
        budget_hit = "Reached max turns" in combined or "Turn budget exhausted" in combined

        print(result.stdout[-4000:] if len(result.stdout) > 4000 else result.stdout)
        if result.stderr:
            print(
                result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
                file=sys.stderr,
            )

        if not budget_hit:
            pytest.xfail(
                "Turn budget was not exhausted during this run — the agent finished"
                " before hitting the 40-turn limit. This confirms that deterministic"
                " budget-exhaustion testing requires --max-turns N passthrough (task-1eae22cb)."
            )

        real_transcripts = _find_real_transcripts(session_dir)
        assert real_transcripts, (
            f"No real session transcript found under {session_dir} "
            f"after max-turns exhaustion for task {task_id}. "
            "Transcript extraction must survive budget exhaustion."
        )

        largest = max(real_transcripts, key=lambda p: p.stat().st_size)
        size = largest.stat().st_size
        assert size >= _MIN_REAL_TRANSCRIPT_BYTES, (
            f"Largest transcript ({largest}) is only {size} bytes after max-turns — "
            f"expected ≥ {_MIN_REAL_TRANSCRIPT_BYTES} bytes."
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"polecat run timed out after 600s for task {task_id}")
    finally:
        _cleanup_task(client, task_id)


# ---------------------------------------------------------------------------
# Test 3: graceful shutdown (SIGTERM)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("POLECAT_E2E") != "1",
    reason="E2E test — opt in with POLECAT_E2E=1",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker / aops-crew image unavailable")
@pytest.mark.skipif(not _pkb_available(), reason="PKB MCP server unreachable")
def test_real_transcript_persists_on_graceful_shutdown() -> None:
    """Real transcript must be extracted even when polecat receives SIGTERM.

    Sends SIGTERM to the polecat subprocess 30 seconds after launch (giving the
    agent enough time to start a real session but not enough to finish).  The
    transcript extraction happens in ``_run_docker_container`` *after* the
    container stops, so a clean termination path should still produce a real
    transcript on the host.
    """
    from polecat.pkb_bridge import _get_client  # type: ignore

    project = _require_project()
    scratch_parent_id = _resolve_scratch_parent(project)
    client = _get_client()

    task_id = _create_test_task(
        client,
        project,
        scratch_parent_id,
        title="e2e: transcript-persistence sigterm",
        body=_SIGTERM_INSTRUCTION,
        tags=["test", "e2e", "transcript-persistence"],
    )

    session_dir = _get_sessions_base() / "polecats" / task_id / project
    cmd = _polecat_cmd(task_id, project)

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        # Give the agent enough time to start a session and write some turns.
        time.sleep(30)

        if proc.poll() is not None:
            # Process already exited (e.g. task completed or error) — still
            # check for transcript.
            pass
        else:
            # Send SIGTERM and allow polecat time to clean up and extract.
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)

        real_transcripts = _find_real_transcripts(session_dir)
        assert real_transcripts, (
            f"No real session transcript found under {session_dir} "
            f"after SIGTERM for task {task_id}. "
            "Transcript extraction must survive graceful shutdown."
        )

        largest = max(real_transcripts, key=lambda p: p.stat().st_size)
        size = largest.stat().st_size
        assert size >= _MIN_REAL_TRANSCRIPT_BYTES, (
            f"Largest transcript ({largest}) is only {size} bytes after SIGTERM — "
            f"expected ≥ {_MIN_REAL_TRANSCRIPT_BYTES} bytes."
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass

        _cleanup_task(client, task_id)
