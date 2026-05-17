#!/usr/bin/env python3
"""End-to-end tests for polecat real-transcript persistence on the host.

Polecat produces two artifacts per run:

1. A **summary stub** at ``$POLECAT_HOME/polecats/<task-id>.jsonl`` (~215 bytes,
   recording only ``{timestamp, task_id, agent, session_type, exit_code,
   success, stdout, stderr}``). This is what polecat advertises in its
   "Transcript saved: …" exit message.
2. The **real session transcript** — shape depends on the CLI tool:

   * Claude:  ``$AOPS_SESSIONS/polecats/<task-id>/<project>/-workspace/<uuid>.jsonl``
     (~hundreds of KB, per-turn tool calls).
   * Gemini:  ``$AOPS_SESSIONS/polecats/<task-id>/<project>/<hash>/chats/session-*.json``
     (Gemini CLI's own session-log format, written under
     ``$GEMINI_CLI_HOME/.gemini/tmp/<workdir-hash>/chats/`` inside the
     container then ``docker cp``'d to the host).

   Neither path is surfaced by polecat; the stub points to (Claude only) the
   host transcript via ``real_transcript_path``.

These tests assert that (2) lands on the host across the failure modes we
care about operationally — for both Claude and Gemini dispatch paths.

Gated identically to ``test_polecat_termination_e2e.py`` — will not run in
the default suite:

* ``@pytest.mark.slow`` / ``@pytest.mark.e2e`` — excluded by the default
  ``addopts`` pytest filter.
* ``POLECAT_E2E=1`` — opt-in env flag.
* ``POLECAT_E2E_PROJECT`` — project slug required, no silent default.
* Docker + ``aops-crew`` image must be present.
* ``PKB_MCP_URL`` must be set and reachable.
* For the Gemini parameter only: ``GEMINI_API_KEY`` must be set so the
  in-container Gemini CLI can authenticate (host ``~/.gemini/oauth_creds.json``
  rarely round-trips into the container on WSL2 / Docker Desktop).

Tasks: task-5ddb64df (Claude), task-743da695 (Gemini variant).
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
        return fm.get("id")
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


def _assert_gemini_transcript(task_id: str, project: str, min_bytes: int) -> Path:
    """Assert a Gemini ``session-*.json`` file landed on the host.

    Gemini CLI writes session logs to
    ``$GEMINI_CLI_HOME/.gemini/tmp/<sha256-of-workdir>/chats/session-*.json``
    inside the container, and polecat ``docker cp``s the contents of
    ``/home/worker/.gemini/tmp`` to ``run_session_dir`` on the host. The
    final layout is therefore::

        $AOPS_SESSIONS/polecats/<task_id>/<project>/<hash>/chats/session-*.json

    On re-runs there may be multiple session files; take the newest by mtime.
    """
    run_dir = _sessions_base() / "polecats" / task_id / project
    assert run_dir.is_dir(), f"Missing run dir: {run_dir}"
    sessions = list(run_dir.rglob("session-*.json"))
    assert sessions, (
        f"No Gemini session-*.json found under {run_dir}. "
        f"Existing tree: {[str(p) for p in run_dir.rglob('*') if p.is_file()][:20]}"
    )
    path = max(sessions, key=lambda p: p.stat().st_mtime)
    size = path.stat().st_size
    assert size >= min_bytes, (
        f"Gemini transcript {path} is {size}B, expected ≥{min_bytes}B (probably truncated)"
    )
    # Smoke-parse: Gemini session files are a single JSON object/array, not
    # JSONL. Parse the whole file rather than line-by-line.
    with path.open() as f:
        payload = json.load(f)
    assert payload, f"Gemini transcript {path} parsed but is empty"
    return path


def _assert_stub(task_id: str, expect_real_path: bool = True) -> Path:
    """Assert the summary stub landed and optionally references the real transcript."""
    stub = _polecat_home() / "polecats" / f"{task_id}.jsonl"
    assert stub.is_file(), f"Missing stub: {stub}"
    size = stub.stat().st_size
    # Stub now includes real_transcript_path/size fields; allow generous headroom.
    assert 100 <= size <= 5_000, (
        f"Stub at {stub} is {size}B — outside expected 100–5000B range. "
        f"If the stub schema changed intentionally, update this bound."
    )

    if expect_real_path:
        last_line = stub.read_text().strip().split("\n")[-1]
        entry = json.loads(last_line)
        assert entry.get("real_transcript_path"), (
            f"Stub at {stub} is missing real_transcript_path. Entry: {entry}"
        )
        real_path = Path(entry["real_transcript_path"])
        assert real_path.exists(), (
            f"real_transcript_path in stub points to non-existent file: {real_path}"
        )
        assert entry.get("real_transcript_size_bytes", 0) > 0, (
            f"real_transcript_size_bytes should be > 0, got {entry.get('real_transcript_size_bytes')}"
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


def _polecat_cmd(task_id: str, project: str, cli_tool: str = "claude") -> list[str]:
    """Build a ``polecat run`` invocation for the requested CLI tool.

    ``cli_tool`` selects the dispatch flag: ``"claude"`` runs the default
    Claude path; ``"gemini"`` adds ``-g`` so polecat dispatches via the
    Gemini CLI inside the container.
    """
    if cli_tool not in ("claude", "gemini"):
        raise ValueError(f"unsupported cli_tool: {cli_tool!r}")

    polecat_bin = shutil.which("polecat") or shutil.which("pc")
    if polecat_bin is None:
        base = [sys.executable, str(REPO_ROOT / "polecat" / "cli.py")]
    else:
        base = [polecat_bin]

    cmd = [*base, "run", "-t", task_id, "-p", project]
    if cli_tool == "gemini":
        cmd.append("-g")
    return cmd


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


# Parametrisation across CLI tools. Per the "no per-mode duplicate tests"
# memory rule we hoist the dispatch tool to a parameter rather than copying
# each test. Gemini is gated separately on GEMINI_API_KEY because the host
# ~/.gemini/oauth_creds.json doesn't reliably round-trip into the container
# on WSL2 / Docker Desktop, so an API key is the only auth we can rely on
# in CI-equivalent environments.
_CLI_TOOL_PARAMS = [
    pytest.param("claude", id="claude"),
    pytest.param(
        "gemini",
        marks=pytest.mark.skipif(
            not os.environ.get("GEMINI_API_KEY"),
            reason="GEMINI_API_KEY not set — Gemini variant requires API-key auth",
        ),
        id="gemini",
    ),
]


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
@pytest.mark.parametrize("cli_tool", _CLI_TOOL_PARAMS)
def test_real_transcript_persists_on_success(shared_sessions_dir: Path, cli_tool: str) -> None:
    """A normal successful polecat run leaves a fat transcript on the host.

    Runs once per supported CLI tool (Claude, Gemini). The Gemini parameter
    is skipped at collection time when ``GEMINI_API_KEY`` is unset — see
    ``_CLI_TOOL_PARAMS``.
    """
    project = _require_project()
    task_id, client = _create_test_task(
        title=f"e2e: transcript-persistence success {cli_tool} (task-743da695)",
        body=_TRIVIAL_INSTRUCTION,
        project=project,
        tags=["test", "e2e", "transcript-persistence", cli_tool],
    )

    proc: subprocess.Popen | None = None
    try:
        cmd = _polecat_cmd(task_id, project, cli_tool=cli_tool)
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

        if cli_tool == "gemini":
            # Gemini writes a single-JSON session file (not JSONL) and the
            # stub doesn't yet record real_transcript_path for the gemini
            # path — the docker-cp landing point is what we verify here.
            _assert_gemini_transcript(task_id, project, min_bytes=1_000)
            _assert_stub(task_id, expect_real_path=False)
        else:
            _assert_real_transcript(task_id, project, min_bytes=10_000)
            _assert_stub(task_id)
    finally:
        _cleanup(proc, client, task_id)


# ---------------------------------------------------------------------------
# Case 2: max-turns (deterministic budget-exhaustion)
# ---------------------------------------------------------------------------

_EXHAUSTIVE_INSTRUCTION = (
    "Explore this worktree exhaustively. Read every Python file under polecat/. "
    "For each file, also grep for its imports across the repo. Do not call "
    "release_task. Do not write a plan. Just keep reading and grepping."
)


@_apply_gates
def test_real_transcript_persists_on_max_turns(shared_sessions_dir: Path) -> None:
    """A max-turns failure still leaves a real transcript on the host."""
    project = _require_project()
    task_id, client = _create_test_task(
        title="e2e: transcript-persistence max-turns (task-5ddb64df)",
        body=_EXHAUSTIVE_INSTRUCTION,
        project=project,
        tags=["test", "e2e", "transcript-persistence", "effort-xs"],
    )

    proc: subprocess.Popen | None = None
    try:
        cmd = _polecat_cmd(task_id, project) + ["--max-turns", "2"]
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
        _assert_real_transcript(task_id, project, min_bytes=1_000)

        # Deterministic check
        assert proc.returncode != 0, f"expected non-zero exit, got {proc.returncode}"
        assert "Reached max turns" in (stdout or ""), (
            "Expected 'Reached max turns' in output. This is the flaky part: "
            "without --max-turns override, the agent may terminate cleanly."
        )
    finally:
        _cleanup(proc, client, task_id)


# ---------------------------------------------------------------------------
# Case 3: graceful shutdown (SIGTERM)
# ---------------------------------------------------------------------------

# Instruction for SIGTERM: keep the agent occupied with a real (multi-turn)
# task so it accumulates transcript bytes before we interrupt. Must NOT call
# release_task — we want polecat still running when we signal.
_SIGTERM_INSTRUCTION = (
    "Search for the string 'transcript' in every Python file under tests/ "
    "and report how many matches you find per file. Take your time — examine "
    "each file carefully. Do NOT call release_task under any circumstances."
)


@_apply_gates
@pytest.mark.parametrize("cli_tool", _CLI_TOOL_PARAMS)
def test_real_transcript_persists_on_graceful_shutdown(
    shared_sessions_dir: Path, cli_tool: str
) -> None:
    """A polecat run interrupted by SIGTERM still leaves a real transcript on the host.

    Verifies the SIGTERM path: polecat signal handler → ``docker stop`` →
    container shutdown → ``docker cp`` (or bind-mount flush) → host. Without
    a SIGTERM handler in ``pc run``, Python's default action terminates the
    process before extraction `finally` blocks fire and the transcript is
    lost. See task-11de7b21.

    Runs once per supported CLI tool. The polecat-side SIGTERM handler is
    CLI-tool-agnostic — it converts SIGTERM to KeyboardInterrupt and the
    same ``finally`` blocks fire for both extract paths
    (``/home/worker/.claude/projects`` and ``/home/worker/.gemini/tmp``),
    so the assertion shape is symmetric.
    """
    project = _require_project()
    task_id, client = _create_test_task(
        title=f"e2e: transcript-persistence sigterm {cli_tool} (task-743da695)",
        body=_SIGTERM_INSTRUCTION,
        project=project,
        tags=["test", "e2e", "transcript-persistence", "sigterm", cli_tool],
    )

    proc: subprocess.Popen | None = None
    try:
        cmd = _polecat_cmd(task_id, project, cli_tool=cli_tool)
        # NOTE: do NOT pass start_new_session=True — we want SIGTERM to hit
        # only the polecat process so its handler runs, rather than blasting
        # the whole process group (which would kill docker children before
        # polecat could `docker stop` them gracefully).
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Give the agent enough time to start a session and write turns.
        # 45s is empirically enough for Claude to hydrate, read the prompt,
        # and emit several tool calls.
        time.sleep(45)

        if proc.poll() is None:
            # Send SIGTERM and allow polecat time to docker-stop the
            # container, extract, and exit. The container itself gets up to
            # 10s in `docker stop --time 10` plus extraction overhead, so
            # 90s is generous but bounded.
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=90)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
                pytest.fail(
                    f"polecat did not exit within 90s of SIGTERM for {task_id} "
                    "— SIGTERM handler may be missing or extraction blocked."
                )
        # If proc already exited (unlikely with this prompt), still verify
        # transcript landed.

        if cli_tool == "gemini":
            # Gemini's first session-*.json write happens after a few
            # turns; 45s of search-and-grep against tests/ is normally
            # enough. Min bytes is lower than Claude's because Gemini's
            # session log is denser per turn.
            _assert_gemini_transcript(task_id, project, min_bytes=1_000)
        else:
            _assert_real_transcript(task_id, project, min_bytes=10_000)
    finally:
        _cleanup(proc, client, task_id)
