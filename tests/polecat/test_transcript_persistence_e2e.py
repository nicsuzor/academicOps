#!/usr/bin/env python3
"""End-to-end tests for polecat real-transcript persistence on the host.

Polecat produces two artifacts per run:

1. A **summary stub** at ``$POLECAT_HOME/polecats/<task-id>.jsonl`` (~215 bytes,
   recording only ``{timestamp, task_id, agent, session_type, exit_code,
   success, stdout, stderr}``). This is what polecat advertises in its
   "Transcript saved: …" exit message.
2. The **real Claude Code session transcript** at
   ``$AOPS_SESSIONS/polecats/<task-id>/<project>/-workspace/<uuid>.jsonl``
   (~hundreds of KB, containing per-turn tool calls, reads, edits — the only
   artifact useful for post-mortem). This path is never surfaced by polecat.

These tests assert that (2) lands on the host across the failure modes we
care about operationally: success and max-turns exhaustion. See follow-ups
for graceful shutdown, container-SIGKILL, and Gemini paths.

Gated identically to ``test_polecat_termination_e2e.py`` — will not run in
the default suite:

* ``@pytest.mark.slow`` / ``@pytest.mark.e2e`` — excluded by the default
  ``addopts`` pytest filter.
* ``POLECAT_E2E=1`` — opt-in env flag.
* ``POLECAT_E2E_PROJECT`` — project slug required, no silent default.
* Docker + ``aops-crew`` image must be present.
* ``PKB_MCP_URL`` must be set and reachable.

Task:  task-5ddb64df.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

_TASK_ID_RE = re.compile(r"(task-[0-9a-f]+|epic-[0-9a-f]+|aops-[0-9a-f]+)")

from tests.polecat.conftest import _DEFAULT_AOPS_SCRATCH_PARENT  # noqa: E402

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from tests.conftest import _docker_available  # noqa: E402

TERMINAL_STATUSES = {"done", "merge_ready", "blocked", "cancelled"}


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


def _poll_status(task_id: str) -> str | None:
    from polecat.pkb_bridge import get_task as pkb_get_task  # type: ignore

    task = pkb_get_task(task_id)
    if task is None:
        return None
    return task.status


def _sessions_base() -> Path:
    """Resolve the sessions base directory the same way polecat does."""
    from polecat.cli import _get_sessions_base  # type: ignore

    return _get_sessions_base()


def _polecat_home() -> Path:
    return Path(os.environ.get("POLECAT_HOME", Path.home() / ".aops"))


def _assert_real_transcript(task_id: str, project: str, min_bytes: int) -> Path:
    """Glob the per-run session dir and assert a non-stub jsonl landed.

    The UUID filename is chosen by Claude Code itself and polecat doesn't
    record it, so we glob. On re-runs there may be multiple jsonls; take
    the newest by mtime.
    """
    workspace = _sessions_base() / "polecats" / task_id / project / "-workspace"
    assert workspace.is_dir(), f"Missing session dir: {workspace}"
    jsonls = list(workspace.glob("*.jsonl"))
    assert jsonls, f"No transcript found under {workspace}"
    path = max(jsonls, key=lambda p: p.stat().st_mtime)
    size = path.stat().st_size
    assert size >= min_bytes, (
        f"Transcript {path} is {size}B, expected ≥{min_bytes}B (probably a stub or truncated)"
    )
    # Smoke-parse last non-empty line so a truncated/partial write fails loudly.
    with path.open() as f:
        lines = [ln for ln in f if ln.strip()]
    assert lines, f"Transcript {path} is empty"
    last = json.loads(lines[-1])
    assert isinstance(last, dict), f"Last line of {path} is not a JSON object"
    return path


def _assert_stub(task_id: str) -> Path:
    """Assert the 215-byte summary stub also landed. Documents current behaviour.

    If follow-up task-b0928ed2 ("stub records real transcript path") lands,
    update the size bound.
    """
    stub = _polecat_home() / "polecats" / f"{task_id}.jsonl"
    assert stub.is_file(), f"Missing stub: {stub}"
    size = stub.stat().st_size
    # Current stub is ~215 bytes; allow generous headroom so we don't
    # re-break this assertion every time the stub schema gains a field.
    assert 100 <= size <= 5_000, (
        f"Stub at {stub} is {size}B — outside expected 100–5000B range. "
        f"If the stub schema changed intentionally, update this bound."
    )
    return stub


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


def _create_test_task(title: str, body: str, project: str, tags: list[str]) -> tuple[str, object]:
    """Create a PKB test task, set project + ready status. Returns (task_id, client)."""
    from polecat.pkb_bridge import _get_client  # type: ignore

    client = _get_client()
    scratch_parent_id = _resolve_scratch_parent(project)

    # PKB create_task now accepts project/status directly.
    create_result = client.call_tool(
        "create_task",
        {
            "title": title,
            "body": body,
            "parent": scratch_parent_id,
            "tags": tags,
            "project": project,
            "status": "ready",
        },
    )
    assert create_result is not None, "PKB create_task returned None"

    task_id = _extract_task_id(create_result)
    if not task_id:
        pytest.fail(f"Could not extract task id from PKB create_task response: {create_result!r}")

    return task_id, client


def _polecat_cmd(task_id: str, project: str) -> list[str]:
    polecat_bin = shutil.which("polecat") or shutil.which("pc")
    if polecat_bin is None:
        cli_path = REPO_ROOT / "polecat" / "cli.py"
        return [sys.executable, str(cli_path), "run", "-t", task_id, "-p", project]
    return [polecat_bin, "run", "-t", task_id, "-p", project]


def _cleanup(proc: subprocess.Popen | None, client: object | None, task_id: str | None) -> None:
    if proc is not None and proc.poll() is None:
        try:
            # Kill the process group to clean up Docker children (relevant when
            # start_new_session=True makes proc.pid the process group leader).
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, AttributeError):
            proc.kill()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
    if client is not None and task_id:
        try:
            client.call_tool("delete", {"id": task_id})  # type: ignore[attr-defined]
        except Exception as e:  # pragma: no cover — cleanup-only
            print(f"cleanup: failed to delete task {task_id}: {e}", file=sys.stderr)


def _require_project() -> str:
    project = os.environ.get("POLECAT_E2E_PROJECT")
    if not project:
        pytest.fail(
            "POLECAT_E2E_PROJECT must be set explicitly — no silent default. "
            "Set it to the project slug to run against (e.g. POLECAT_E2E_PROJECT=aops)."
        )
    return project


_GATES = [
    pytest.mark.slow,
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("POLECAT_E2E") != "1",
        reason="E2E test — opt in with POLECAT_E2E=1",
    ),
    pytest.mark.skipif(not _docker_available(), reason="Docker / aops-crew image unavailable"),
    pytest.mark.skipif(not _pkb_available(), reason="PKB MCP server unreachable"),
]


def _apply_gates(fn):
    for m in reversed(_GATES):
        fn = m(fn)
    return fn


@pytest.fixture
def shared_sessions_dir(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override conftest's AOPS_SESSIONS redirect with a Docker-visible location.

    The repo-level autouse fixture ``tests/conftest.py::ensure_test_environment``
    points AOPS_SESSIONS at pytest's ``tmp_path`` (under ``/var/folders/...``),
    which colima's virtiofs share does NOT expose to the VM. Bind-mounts of
    those paths appear empty on the host — the container writes disappear.

    We need a path under a colima-shared root (``/Users/...``) so the
    polecat subprocess's bind-mount of the session dir is actually visible
    on the host after container exit. ``~/.aops/test-sessions-<uuid>/`` is
    a natural fit: same volume as the real sessions dir, isolated per-test,
    cleaned up on teardown.
    """
    base = _polecat_home() / "test-sessions" / f"e2e-{uuid.uuid4().hex[:8]}"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_SESSIONS", str(base))
    try:
        yield base
    finally:
        shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------------------
# Case 1: success path
# ---------------------------------------------------------------------------

_TRIVIAL_INSTRUCTION = (
    "Read the top-level README.md in this worktree. Then call release_task "
    "with status=done and a one-line summary of what the README describes. "
    "Do nothing else."
)


@_apply_gates
def test_real_transcript_persists_on_success(shared_sessions_dir: Path) -> None:
    """A normal successful polecat run leaves a fat transcript on the host."""
    project = _require_project()
    task_id, client = _create_test_task(
        title="e2e: transcript-persistence success (task-5ddb64df)",
        body=_TRIVIAL_INSTRUCTION,
        project=project,
        tags=["test", "e2e", "transcript-persistence"],
    )

    proc: subprocess.Popen | None = None
    try:
        cmd = _polecat_cmd(task_id, project)
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + 300.0  # 5 min
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            if _poll_status(task_id) in TERMINAL_STATUSES:
                break
            time.sleep(5.0)
        else:
            pytest.fail(f"polecat run for task {task_id} did not finish within 5 min")

        # Drain subprocess even if PKB is already terminal.
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail(f"polecat subprocess did not exit 60s after PKB terminal for {task_id}")

        _assert_real_transcript(task_id, project, min_bytes=10_000)
        _assert_stub(task_id)
    finally:
        _cleanup(proc, client, task_id)


# ---------------------------------------------------------------------------
# Case 2: max-turns (xfail until task-1eae22cb lands)
# ---------------------------------------------------------------------------

_EXHAUSTIVE_INSTRUCTION = (
    "Explore this worktree exhaustively. Read every Python file under polecat/. "
    "For each file, also grep for its imports across the repo. Do not call "
    "release_task. Do not write a plan. Just keep reading and grepping."
)


@_apply_gates
@pytest.mark.xfail(
    strict=False,
    reason=(
        "Busting max_turns via prompt engineering is a behavioral oracle, "
        "not deterministic. Remove xfail once task-1eae22cb (--max-turns CLI "
        "passthrough) lands and this test can force the budget."
    ),
)
def test_real_transcript_persists_on_max_turns(shared_sessions_dir: Path) -> None:
    """A max-turns failure still leaves a real transcript on the host."""
    project = _require_project()
    task_id, client = _create_test_task(
        title="e2e: transcript-persistence max-turns (task-5ddb64df)",
        body=_EXHAUSTIVE_INSTRUCTION,
        project=project,
        tags=["test", "e2e", "transcript-persistence", "effort-xs"],
    )
    # Smallest effort tier (post-#565: 40 turns) to maximise chance of
    # hitting budget before the agent self-terminates.
    client.call_tool("update_task", {"id": task_id, "updates": {"effort": "xs"}})

    proc: subprocess.Popen | None = None
    try:
        cmd = _polecat_cmd(task_id, project)
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        # 10 min deadline — xs-budget runs usually complete (or bust) in <5.
        try:
            stdout, _ = proc.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, _ = proc.communicate()
            pytest.fail(f"polecat run for task {task_id} exceeded 10 min")

        # Non-xfail property: transcript must exist regardless of exit code.
        # If this assert survives but the one below fails, xfail marks the test
        # as XPASS — which strict=False tolerates — documenting that the
        # weak signal is passing.
        _assert_real_transcript(task_id, project, min_bytes=10_000)

        # xfail-only property (deterministic only with follow-up task-1eae22cb):
        assert proc.returncode != 0, f"expected non-zero exit, got {proc.returncode}"
        assert "Reached max turns" in (stdout or ""), (
            "Expected 'Reached max turns' in output. This is the flaky part: "
            "without --max-turns override, the agent may terminate cleanly."
        )
    finally:
        _cleanup(proc, client, task_id)
