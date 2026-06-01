"""E2E tests for ALL invocation paths: crew and run, Claude and Gemini.

Parameterized over 4 combinations: (crew, run) × (claude, gemini).
Each test exercises the FULL path from CLI entry point through Docker/sandbox
to LLM response, proving:
- Agent responds and produces output
- Agent runs inside a container (sandbox isolation)
- Session transcripts are persisted and extractable
- Required binaries are available

These are the most expensive tests in the suite — each invokes a real LLM
inside a real Docker container. They exist because cheaper tests (fake binaries,
mock Docker) cannot catch real integration failures like the Gemini auth
regression (EAI_AGAIN) that triggered this work.
"""

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

from tests.conftest import (
    _docker_available,
    _gemini_cli_available,
    build_claude_agent_cmd,
    build_gemini_agent_cmd,
    get_repo_root,
)
from tests.polecat.conftest import _DEFAULT_AOPS_SCRATCH_PARENT

# PKB task whose body is the test prompt for `pc run -t`.
# Created in PKB under aops project — DO NOT COMPLETE or ARCHIVE this task.
TEST_FIXTURE_TASK_ID = "e2e-test-fixture"

# Fast/cheap Gemini model for E2E tests. Update here when the recommended
# Flash model changes; the CLI accepts any "gemini-*" literal as a model id.
_GEMINI_TEST_MODEL = "gemini-2.5-flash"

# Mega-prompt for crew paths (passed directly via -p).
# Must match the task body for run paths so assertions work on both.
MEGA_PROMPT_TEMPLATE = """\
Do ALL of the following steps and report results exactly as labeled:

1. SANDBOX CHECK:
   - Run: test -f /.dockerenv && echo "SANDBOX_VERIFIED=true" || echo "SANDBOX_VERIFIED=false"
   - Run: echo "POLECAT_CONTAINER=$AOPS_POLECAT_CONTAINER"
   - Run: hostname

2. BINARY CHECK:
   - Run: which pkb

3. WORKSPACE CHECK:
   - Run: test -d /workspace/.git && echo "WORKSPACE_VERIFIED=true" || echo "WORKSPACE_VERIFIED=false"
   - Run: git -C /workspace rev-parse --abbrev-ref HEAD

4. WORKSPACE WRITE (proves bind-mount, not cp):
   - Run: echo "{sentinel}" > /workspace/{sentinel_name}
   - Run: ls -la /workspace/{sentinel_name}

Reply with ALL outputs clearly labeled. Do NOT skip any step.
Do NOT create any commits or PRs. The single file write in step 4 is required.\
"""


def _make_mega_prompt(sentinel_name: str, sentinel_value: str) -> str:
    return MEGA_PROMPT_TEMPLATE.format(sentinel_name=sentinel_name, sentinel=sentinel_value)


# Back-compat alias for any callers still importing MEGA_PROMPT (no sentinel).
MEGA_PROMPT = _make_mega_prompt(".polecat-bind-mount-sentinel", "ok")


def _check_fixture_task():
    """Verify the test fixture task exists in PKB and is runnable."""
    try:
        result = subprocess.run(
            ["pkb", "show", TEST_FIXTURE_TASK_ID],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0 and TEST_FIXTURE_TASK_ID in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


_RESOLVED_FIXTURE_ID_CACHE: str | None = None


def _resolve_fixture_task_id() -> str:
    """Resolve the fixture task's canonical ID via PKB MCP, once per session.

    ``TEST_FIXTURE_TASK_ID`` is the alias (filename stem). Polecat creates
    worktrees and branches under the task's ``id`` frontmatter field, which
    differs from the alias (e.g. ``e2e-test-85fabbbf``). Use this for any
    path/branch derivation that needs to match polecat's view of the task.

    Caches the resolved id for the lifetime of the test process — the
    fixture task's id never changes, and each polecat invocation triggers
    PKB writes (status updates, release) that can race read-after-write
    consistency on the MCP server, occasionally returning HTTP 404 for a
    handful of seconds. Caching avoids that race entirely after the first
    successful resolve.

    Fails loud if PKB is unreachable on the very first call: a silent
    fallback to the alias would point worktree/session-dir lookups at a
    non-existent path, producing opaque "file not found"/"no session"
    failures that wrongly look like bind-mount or auth bugs. Retries the
    initial resolve a few times to ride out transient post-write 404s.
    """
    global _RESOLVED_FIXTURE_ID_CACHE
    if _RESOLVED_FIXTURE_ID_CACHE is not None:
        return _RESOLVED_FIXTURE_ID_CACHE

    from polecat.pkb_bridge import get_task

    last_err: Exception | None = None
    for _attempt in range(5):
        try:
            task = get_task(TEST_FIXTURE_TASK_ID)
            if task and task.id:
                _RESOLVED_FIXTURE_ID_CACHE = task.id
                return task.id
            last_err = RuntimeError(f"PKB returned no task for {TEST_FIXTURE_TASK_ID!r}")
        except Exception as e:  # noqa: BLE001 — surface any error after retries
            last_err = e
        time.sleep(1.0)

    raise RuntimeError(
        f"PKB MCP did not return a canonical id for fixture task "
        f"'{TEST_FIXTURE_TASK_ID}' after 5 attempts (last error: {last_err!r}). "
        f"The test cannot proceed without it — worktree paths and session-dir "
        f"lookups depend on the resolved id matching what polecat uses."
    )


def _cleanup_run_worktree():
    """Delete the remote branch and local worktree created by pc run for the fixture task.

    pc run creates polecat/<task-id> on origin and a local clone under ~/.aops/worktrees/.
    Without cleanup, subsequent runs fail with "stale unmerged branch" from polecat's guard.
    """
    resolved_id = _resolve_fixture_task_id()
    for tid in {TEST_FIXTURE_TASK_ID, resolved_id}:
        subprocess.run(
            ["git", "push", "origin", "--delete", f"polecat/{tid}"],
            capture_output=True,
            check=False,
        )
        worktree = Path.home() / ".aops" / "worktrees" / tid
        if worktree.exists():
            import shutil

            shutil.rmtree(worktree, ignore_errors=True)


def _reset_fixture_task():
    """Reset the test fixture task to active status so it can be re-run.

    PKB MCP is the source of truth for ``pc run``: an autonomous polecat
    worker calls ``release_task`` at the end of each successful run, leaving
    the fixture task with status ``done``. The next test must flip it back
    to ``queued`` before launching polecat or polecat refuses ("already
    done"). Both the PKB write and a read-back verification are required;
    transient PKB errors are retried (read-after-write consistency on the
    MCP server can briefly miss a fresh write under load).

    Fails loud if the reset can't be confirmed — silently moving on would
    let polecat see stale ``done`` and produce an opaque "already done"
    failure that masquerades as an agent/auth bug.
    """
    from polecat.pkb_bridge import get_task, update_task

    last_err: Exception | None = None
    for _attempt in range(5):
        try:
            update_task(
                TEST_FIXTURE_TASK_ID,
                status="queued",
                assignee="polecat",
                project="aops",
            )
            task = get_task(TEST_FIXTURE_TASK_ID)
            if task and task.status == "queued":
                break
            last_err = RuntimeError(
                f"after update_task, PKB read-back returned status="
                f"{task.status if task else None!r} (expected 'queued')"
            )
        except Exception as e:  # noqa: BLE001 — surface after retries
            last_err = e
        time.sleep(1.0)
    else:
        raise RuntimeError(
            f"Could not reset fixture task '{TEST_FIXTURE_TASK_ID}' to 'queued' "
            f"after 5 attempts (last error: {last_err!r}). Polecat will refuse "
            f"to run a 'done' task; the test cannot proceed without a successful "
            f"reset."
        )

    # Sync the local file to PKB so `_check_fixture_task` and any local PKB
    # reads see the same status. This is best-effort — PKB is authoritative.
    aca_data = os.environ.get("ACA_DATA", str(Path.home() / "brain"))
    task_file = Path(aca_data) / "tasks" / f"{TEST_FIXTURE_TASK_ID}.md"
    if not task_file.exists():
        return
    content = task_file.read_text()
    content = re.sub(r"(?m)^status:\s+\S+", "status: queued", content, count=1)
    # Strip any "Completion Evidence" or "Outcome" sections appended by previous
    # runs — agents see these and triage ("prior work") instead of executing.
    content = re.sub(r"\n## Completion Evidence.*", "", content, flags=re.DOTALL)
    content = re.sub(r"\n  ## Outcome.*?(?=\n\w)", "\n", content, flags=re.DOTALL)
    task_file.write_text(content)


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.xdist_group("invocation-paths")
class TestAllInvocationPaths:
    """Full CLI-to-response tests across all 4 invocation paths.

    Parameterized: (crew, run) x (claude, gemini). Each param runs one LLM
    call; all test methods parse the same output.
    """

    @pytest.fixture(
        scope="class",
        params=[
            "crew-claude",
            "crew-gemini",
            "run-claude",
            "run-gemini",
        ],
    )
    def session(self, request, tmp_path_factory):
        """Run one agent session per (path, backend) combination."""
        param = request.param
        path_type, backend = param.split("-")

        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

        if backend == "gemini" and not _gemini_cli_available():
            pytest.skip("Gemini CLI not found in PATH")

        tmp_path = tmp_path_factory.mktemp(f"invocation-{param}")

        if path_type == "crew":
            result = self._run_crew(tmp_path, backend)
        else:
            result = self._run_polecat(tmp_path, backend)

        # Skip Gemini paths when Google's API has rate-limited us. The CLI
        # exits cleanly with QUOTA_EXHAUSTED on stderr; without this guard
        # all downstream assertions fail with no signal that the cause was
        # external quota, not a code regression.
        if backend == "gemini":
            stderr = result.get("stderr", "")
            combined = result.get("combined", "")
            for needle in ("QUOTA_EXHAUSTED", "TerminalQuotaError", "exhausted your capacity"):
                if needle in stderr or needle in combined:
                    pytest.skip(f"Gemini API quota exhausted ({needle}) — retry after reset")

        return result

    @staticmethod
    def _is_hook_file(f: Path) -> bool:
        """Return True if the file is a hook log, not a session transcript."""
        return f.name.endswith("-hooks.jsonl") or f.name.startswith("cc_hooks_")

    @staticmethod
    def _is_session_file(f: Path) -> bool:
        """Return True if the file looks like a session transcript.

        Three concrete shapes (all line-delimited or single JSON):
        - Claude transcript: ``<uuid>.jsonl`` written under the agent's
          ``$CLAUDE_CONFIG_DIR/projects/...`` and exfiltrated under
          ``$AOPS_SESSIONS/{crew,polecats}/.../<uuid>.jsonl``. NOT under a
          ``chats/`` directory.
        - Gemini chat: ``chats/session-*.jsonl`` written by gemini-cli into
          ``$GEMINI_CLI_HOME/.gemini/tmp/<projectHash>/chats/`` and bind-
          mounted out under ``$AOPS_SESSIONS/.../workspace/chats/``. This is
          where the actual conversation + tool calls live.
        - Per-session aops wrapper (``*-{backend}-session.json``) is metadata
          only — gate state, hooks log path — and is NOT treated as a
          transcript.

        Hook logs (``*-hooks.jsonl``) are excluded explicitly.
        """
        if TestAllInvocationPaths._is_hook_file(f):
            return False
        if f.suffix != ".jsonl":
            return False
        # Gemini chat: chats/session-*.jsonl
        if f.parent.name == "chats" and f.name.startswith("session-"):
            return True
        # Claude transcript: any *.jsonl outside chats/ that isn't a hook log
        if f.parent.name != "chats":
            return True
        return False

    @staticmethod
    def _find_latest_session_logs(
        started_after: float = 0,
        crew_name: str | None = None,
        backend: str | None = None,
        session_dir: Path | None = None,
    ):
        """Discover the session file and hook log produced by THIS test run.

        Args:
            started_after: Unix timestamp — only consider files modified after
                this time. Prevents picking up stale files from unrelated sessions.
            crew_name: Optional crew name embedded in hook log filenames (e.g.
                "test-claude").  When set, filters hook files to those whose
                filename contains the crew name, avoiding cross-session races
                where a concurrent session's hook log is created in the same
                time window.
            backend: "claude" or "gemini". When set, filters session files by
                location (claude lives at the top of the per-session dir;
                gemini lives one level deeper under ``chats/``).
            session_dir: Required for race-free discovery. Polecat writes the
                test agent's artefacts under ``$AOPS_SESSIONS/{crew,polecats}/
                {name_or_task}/{project}/`` — passing this dir scopes the
                rglob to that subtree only. Without it, a concurrent polecat
                run on an unrelated task (e.g. somebody actively working on
                another epic on the same machine) wins on mtime and produces
                an opaque "wrong-session" failure.

        Returns:
            (hook_files_content, session_file, tool_calls)
        """
        from lib.paths import get_sessions_repo

        from tests.conftest import parse_tool_calls

        aops_sessions = get_sessions_repo()
        # Scope to the per-test session_dir when provided (the only honest
        # source of truth for "this test's session"). Fall back to a global
        # search only if the caller didn't pass it — we keep the fallback so
        # legacy callers don't silently break, but in-tree callers should
        # always pass session_dir.
        search_root = session_dir if session_dir is not None else aops_sessions

        def _hook_birthtime(f: Path) -> float:
            st = f.stat()
            # st_birthtime is macOS/BSD; fall back to st_ctime on Linux
            return getattr(st, "st_birthtime", st.st_ctime)

        hook_files = (
            sorted(search_root.rglob("*-hooks.jsonl"), key=_hook_birthtime)
            if search_root.exists()
            else []
        )
        if started_after:
            hook_files = [f for f in hook_files if _hook_birthtime(f) >= started_after]
        if crew_name:
            # Filenames sanitize crew names with allow_dashes=False: "test-claude" → "testclaude"
            sanitized_crew = crew_name.replace("-", "")
            hook_files = [f for f in hook_files if sanitized_crew in f.name]
        hook_file = hook_files[-1] if hook_files else None
        if hook_file:
            raw = hook_file.read_text()
            # run-claude and run-gemini share the same session dir (same task+project),
            # so they may append to the same hook log. Filter entries by client_type so
            # each backend only sees its own hooks.
            if backend in ("claude", "gemini"):
                filtered_lines = []
                for line in raw.splitlines():
                    try:
                        entry = json.loads(line)
                        ct = entry.get("client_type")
                        if ct is None or ct == backend:
                            filtered_lines.append(line)
                    except json.JSONDecodeError:
                        filtered_lines.append(line)
                hook_files_content = "\n".join(filtered_lines)
            else:
                hook_files_content = raw
        else:
            hook_files_content = ""

        # Search the per-test session_dir only — never ~/.claude/projects/
        # (would match the developer's concurrent host Claude sessions) and
        # never the global $AOPS_SESSIONS (would match any other polecat run
        # currently active on this machine, which is common during dev). The
        # only sessions we care about are the ones polecat writes into the
        # per-test subtree under $AOPS_SESSIONS/{crew|polecats}/{name}/...
        is_session = TestAllInvocationPaths._is_session_file
        session_files: list[Path] = []
        if search_root.exists():
            for f in search_root.rglob("*"):
                if f.is_file() and is_session(f):
                    session_files.append(f)

        # Filter by modification time to avoid picking up unrelated sessions
        if started_after:
            session_files = [f for f in session_files if f.stat().st_mtime >= started_after]

        # Filter by expected file location for the backend to prevent cross-
        # backend contamination when Claude and Gemini sessions sit side by
        # side under $AOPS_SESSIONS. Claude lives at the top of the per-session
        # dir; Gemini lives one level deeper under chats/.
        if backend == "claude":
            session_files = [f for f in session_files if f.parent.name != "chats"]
        elif backend == "gemini":
            session_files = [
                f
                for f in session_files
                if f.parent.name == "chats" and f.name.startswith("session-")
            ]

        session_files = sorted(session_files, key=os.path.getmtime)
        session_file = session_files[-1] if session_files else None
        tool_calls = parse_tool_calls(session_file) if session_file else []
        return hook_files_content, session_file, tool_calls

    def _run_crew(self, tmp_path, backend, timeout=None):
        """Run pc crew repo <path> -- -p <mega-prompt>."""
        if timeout is None:
            timeout = 600 if backend == "gemini" else 300

        repo = get_repo_root()
        crew_name = f"test-{backend}"

        # Unique sentinel per invocation — the agent writes this into /workspace
        # so we can later assert the file appears on the host's bind-mounted
        # worktree (proves bind-mount, since cp never reverse-extracts /workspace).
        sentinel_name = f".polecat-bind-mount-sentinel-{backend}-{uuid.uuid4().hex[:8]}"
        sentinel_value = f"crew-{backend}-{uuid.uuid4().hex[:8]}"
        prompt = _make_mega_prompt(sentinel_name, sentinel_value)

        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "polecat.cli",
            "crew",
            "repo",
            str(repo),
            "-n",
            crew_name,
        ]
        if backend == "gemini":
            cmd.extend(["--model", _GEMINI_TEST_MODEL])

        cmd.append("--")
        if backend == "gemini":
            cmd.extend(build_gemini_agent_cmd(prompt, include_binary=False))
        else:
            cmd.extend(build_claude_agent_cmd(prompt, output_format="text", include_binary=False))

        env = os.environ.copy()
        cwd = os.getcwd()
        env["PYTHONPATH"] = os.pathsep.join(
            [
                cwd,
                os.path.join(cwd, "polecat"),
                os.path.join(cwd, "aops-core"),
            ]
        )
        for key in [
            "AOPS_SESSION_ID",
            "CLAUDE_ENV_FILE",
            "AOPS_SESSION_STATE_DIR",
            "AOPS_HOOK_LOG_PATH",
        ]:
            env.pop(key, None)

        # Always clean up any previous run first
        subprocess.run(
            ["uv", "run", "python", "-m", "polecat.cli", "nuke", crew_name, "--force"],
            capture_output=True,
            check=False,
            env=env,
            cwd=cwd,
        )
        started_at = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(f"crew-{backend} timed out after {timeout}s")

        combined = proc.stdout + proc.stderr
        # Mirror polecat's session_dir construction (see polecat/cli.py around
        # line 3493) so we scope discovery to THIS test run's subtree.
        from lib.paths import get_sessions_repo as _get_sessions_repo

        crew_session_dir = _get_sessions_repo() / "crew" / crew_name / "repo"
        hook_files_content, session_file, tool_calls = self._find_latest_session_logs(
            started_after=started_at,
            crew_name=crew_name,
            backend=backend,
            session_dir=crew_session_dir,
        )

        return {
            "param": f"crew-{backend}",
            "path_type": "crew",
            "backend": backend,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "combined": combined,
            "hook_files_content": hook_files_content,
            "session_file": session_file,
            "tool_calls": tool_calls,
            "sentinel_name": sentinel_name,
            "sentinel_value": sentinel_value,
            "started_at": started_at,
        }

    def _run_polecat(self, tmp_path, backend, timeout=None):
        """Run pc run -t <task_id> for the given backend."""
        if timeout is None:
            timeout = 600 if backend == "gemini" else 300
        if not _check_fixture_task():
            pytest.skip(
                f"Test fixture task '{TEST_FIXTURE_TASK_ID}' not found in PKB "
                "(missing, or pkb binary not available)"
            )

        # Defensive: ensure no stale worktree from a prior aborted invocation.
        # Polecat (correctly) refuses to overwrite a worktree that has
        # uncommitted changes, which can leave us stuck if a previous run-*
        # test was interrupted before its post-run cleanup. Cleanup also runs
        # at-end via the post-process block; doing it at-start guarantees
        # clean state regardless of what any prior session left behind.
        _cleanup_run_worktree()
        _reset_fixture_task()

        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "polecat.cli",
            "run",
            "-t",
            TEST_FIXTURE_TASK_ID,
            "--no-auto-finish",
        ]
        if backend == "gemini":
            cmd.extend(["--model", _GEMINI_TEST_MODEL])

        env = os.environ.copy()
        cwd = os.getcwd()
        env["PYTHONPATH"] = os.pathsep.join(
            [
                cwd,
                os.path.join(cwd, "polecat"),
                os.path.join(cwd, "aops-core"),
            ]
        )
        for key in [
            "AOPS_SESSION_ID",
            "CLAUDE_ENV_FILE",
            "AOPS_SESSION_STATE_DIR",
            "AOPS_HOOK_LOG_PATH",
        ]:
            env.pop(key, None)

        # Static sentinel the fixture task always writes to /workspace
        sentinel_name = ".polecat-bind-mount-sentinel"
        sentinel_value = "ok"

        started_at = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(f"run-{backend} timed out after {timeout}s")
        finally:
            _reset_fixture_task()

        # --no-auto-finish leaves the worktree in place; capture the sentinel
        # before _cleanup_run_worktree() deletes the worktree directory.
        # Polecat names the worktree by the task's resolved id (frontmatter),
        # not by the alias used to look it up.
        resolved_task_id = _resolve_fixture_task_id()
        worktree = Path.home() / ".aops" / "worktrees" / resolved_task_id
        sentinel_file = worktree / sentinel_name
        sentinel_on_host = sentinel_file.exists()
        sentinel_content = sentinel_file.read_text().strip() if sentinel_on_host else ""
        _cleanup_run_worktree()

        combined = proc.stdout + proc.stderr
        # Mirror polecat's run_session_dir construction (see polecat/cli.py
        # around line 4202) so we scope discovery to THIS test run's subtree.
        # The fixture task is project=aops; its resolved id is what polecat
        # names the per-task subdir.
        from lib.paths import get_sessions_repo as _get_sessions_repo

        run_session_dir = _get_sessions_repo() / "polecats" / resolved_task_id / "aops"
        hook_files_content, session_file, tool_calls = self._find_latest_session_logs(
            started_after=started_at,
            backend=backend,
            session_dir=run_session_dir,
        )

        return {
            "param": f"run-{backend}",
            "path_type": "run",
            "backend": backend,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "combined": combined,
            "hook_files_content": hook_files_content,
            "session_file": session_file,
            "tool_calls": tool_calls,
            "sentinel_name": sentinel_name,
            "sentinel_value": sentinel_value,
            "sentinel_on_host": sentinel_on_host,
            "sentinel_content": sentinel_content,
            "started_at": started_at,
        }

    # --- Assertions (all parse the shared session result) ---

    def test_agent_responds(self, session):
        """Agent started, ran to completion, and persisted a transcript.

        Hard requirement: the agent's session transcript exists and is
        non-empty. Polecat's stdout/stderr alone is NOT evidence the agent
        ran — polecat prints setup logs even when the in-container agent
        never authenticates or never starts. The transcript is the only
        artifact that proves the LLM produced output.
        """
        session_file = session.get("session_file")
        assert session_file is not None and session_file.exists(), (
            f"[{session['param']}] No session transcript was produced. The agent "
            f"either never started, never authenticated, or never logged anything. "
            f"This is the failure mode where polecat reports success but the "
            f"in-container agent silently failed.\n"
            f"stdout (last 500): {session['stdout'][-500:]}\n"
            f"stderr (last 500): {session['stderr'][-500:]}"
        )
        assert session_file.stat().st_size > 0, (
            f"[{session['param']}] Session transcript exists at {session_file} "
            f"but is empty — agent started but produced no output."
        )

    def test_sandbox_isolation(self, session):
        """Agent ran INSIDE the container and reported it via the transcript.

        The bash check ``test -f /.dockerenv && echo SANDBOX_VERIFIED=true``
        in the MEGA_PROMPT only emits ``SANDBOX_VERIFIED=true`` when executed
        inside a Docker container. Asserting on the agent's session transcript
        (not stdout/stderr) is the only honest signal that the agent actually
        ran inside the sandbox.

        Stdout/stderr include polecat CLI's own setup logs — they mention
        ``aops-crew``, ``/workspace/``, ``docker run``, and the sentinel
        filename as part of normal staging output, so substring-matching on
        ``combined`` would pass the test even when the in-container agent
        never executed a single bash command (e.g. auth failure).
        """
        session_file = session.get("session_file")
        assert session_file is not None and session_file.exists(), (
            f"[{session['param']}] No session transcript — agent did not run. "
            f"See test_agent_responds for the underlying diagnosis."
        )
        raw_log = session_file.read_text()

        # Hard requirement: the agent emitted SANDBOX_VERIFIED=true into its
        # transcript. This string only appears when the agent (a) was alive,
        # (b) executed our bash command, and (c) the file /.dockerenv existed
        # — which only happens inside the Docker container.
        assert "SANDBOX_VERIFIED=true" in raw_log, (
            f"[{session['param']}] Agent transcript does not contain "
            f"'SANDBOX_VERIFIED=true'. Either the agent never executed the "
            f"bash check from MEGA_PROMPT step 1, or the check ran outside "
            f"the container (no /.dockerenv).\n"
            f"Transcript path: {session_file}\n"
            f"Transcript tail (last 1500 chars):\n{raw_log[-1500:]}"
        )

    def test_hooks_fired(self, session):
        """Hook JSONL is written with valid structure for all invocation paths.

        Validates every line is valid JSON with required fields, SessionStart
        is first, and client_type is logged correctly.
        """
        import json

        hook_content = session.get("hook_files_content", "")
        assert hook_content.strip(), (
            f"[{session['param']}] No hook JSONL content found.\n"
            f"stderr (last 500): {session['stderr'][-500:]}"
        )

        # Parse every line as valid JSON
        entries = []
        for line in hook_content.strip().splitlines():
            entry = json.loads(line)  # fail if any line is invalid JSON
            entries.append(entry)

        assert len(entries) >= 1, f"[{session['param']}] Hook JSONL has no entries"

        # Every entry must have core fields
        for i, entry in enumerate(entries):
            assert "hook_event" in entry, f"Entry {i} missing hook_event"
            assert "session_id" in entry, f"Entry {i} missing session_id"
            assert "logged_at" in entry, f"Entry {i} missing logged_at"

        # SessionStart must be the first event
        assert entries[0]["hook_event"] == "SessionStart", (
            f"[{session['param']}] First hook event is "
            f"{entries[0]['hook_event']!r}, expected 'SessionStart'"
        )

        ct = entries[0].get("client_type")
        assert ct == session["backend"], (
            f"[{session['param']}] client_type={ct!r}, expected {session['backend']!r}"
        )

    def test_hook_transcript_roundtrip(self, session, tmp_path):
        """Transcript parser correctly reads hook JSONL output fields.

        Proves the full chain: logger writes -> parser reads -> verdict survives.
        Uses the hook content already captured by the session fixture (avoids
        rglob discovery mismatches between host and container paths).
        """
        import json

        hook_content = session.get("hook_files_content", "")
        if not hook_content.strip():
            pytest.skip("No hook content (covered by test_hooks_fired)")

        # Write captured content to a temp file for the parser to read
        hook_file = tmp_path / "test-hooks.jsonl"
        hook_file.write_text(hook_content)

        # Use the transcript parser to load entries
        from lib.transcript_parser import SessionProcessor

        processor = SessionProcessor()
        parsed_entries = processor._load_hook_entries(hook_file)
        assert len(parsed_entries) >= 1, (
            f"[{session['param']}] Transcript parser returned no entries from hook JSONL"
        )

        # Every raw entry must have a parsed counterpart with hook_event_name
        raw_entries = [json.loads(line) for line in hook_content.strip().splitlines()]
        assert len(parsed_entries) == len(raw_entries), (
            f"[{session['param']}] Parser returned {len(parsed_entries)} entries, "
            f"expected {len(raw_entries)}"
        )

        # For entries with gate output, verdict must survive parsing (match by index)
        for i, raw in enumerate(raw_entries):
            if (
                raw.get("output")
                and isinstance(raw["output"], dict)
                and raw["output"].get("verdict")
            ):
                parsed = parsed_entries[i]
                assert parsed.hook_verdict == raw["output"]["verdict"], (
                    f"[{session['param']}] Verdict lost in parsing at entry {i} "
                    f"({raw.get('hook_event')}): "
                    f"raw={raw['output']['verdict']!r}, "
                    f"parsed={parsed.hook_verdict!r}"
                )

    def test_workspace_writes_visible_on_host(self, session):
        """Bind-mount only: a file the agent wrote inside /workspace appears on
        the host's clone of the worktree.

        Under docker-cp staging this FAILS because cp only goes host→container
        at start; in-container writes are discarded by `docker rm -f`. Under
        bind-mount staging the write lands directly on the host filesystem.

        crew path: worktree persists after the run, so we search polecat_home
        for the sentinel file (unique per invocation to avoid stale matches).
        run path: worktree is captured before _cleanup_run_worktree() deletes
        it; the result is stored in the session dict.
        """
        sentinel_name = session["sentinel_name"]
        sentinel_value = session["sentinel_value"]

        if session["path_type"] == "run":
            assert session["sentinel_on_host"], (
                f"[{session['param']}] Agent wrote /workspace/{sentinel_name} inside "
                f"the container, but the file was not found on the host worktree at "
                f"~/.aops/worktrees/{TEST_FIXTURE_TASK_ID}/{sentinel_name}. "
                f"This proves the worktree was NOT bind-mounted "
                f"(cp-only staging discards in-container writes)."
            )
            assert sentinel_value in session["sentinel_content"], (
                f"[{session['param']}] Sentinel found but content "
                f"{session['sentinel_content']!r} does not contain {sentinel_value!r}."
            )
        else:
            started_at = session["started_at"]
            polecat_home = Path(os.environ.get("POLECAT_HOME", str(Path.home() / ".polecat")))
            matches = [
                p
                for p in polecat_home.rglob(sentinel_name)
                if p.is_file() and p.stat().st_mtime >= started_at
            ]
            assert matches, (
                f"[{session['param']}] Agent wrote /workspace/{sentinel_name} inside "
                f"the container, but no file by that name appears on the host under "
                f"{polecat_home}. This proves the worktree was NOT bind-mounted "
                f"(cp-only staging discards in-container writes)."
            )
            content = matches[0].read_text().strip()
            assert sentinel_value in content, (
                f"[{session['param']}] Sentinel found at {matches[0]} but content "
                f"{content!r} does not contain expected {sentinel_value!r}."
            )

    def test_workspace_available_in_container(self, session):
        """Repo worktree is mounted at /workspace inside the container.

        Two verification strategies depending on path type:

        - crew path: the bind-mount target is on the host, so we locate the
          worktree via the sentinel file (same lookup as
          test_workspace_writes_visible_on_host) and assert `.git` is a
          directory there.  A git-worktree-add would leave a `.git` FILE; a
          proper git clone leaves a `.git` DIRECTORY.  Since `/workspace` is
          a bind-mount of that host path, what we see on the host is exactly
          what the agent sees inside the container.

        - run path: the agent must emit WORKSPACE_VERIFIED=true into its
          session transcript by executing the bash check from MEGA_PROMPT
          step 3. We assert ONLY against the transcript — polecat's
          stdout/stderr can echo the prompt template (which contains the
          literal "WORKSPACE_VERIFIED=true" inside an echo command), so
          matching ``combined`` would pass even when the bash never ran.
        """
        if session["path_type"] == "crew":
            # Host-side verification: find the worktree via sentinel file and
            # check that .git is a directory (proves the mount points at a
            # proper full clone, not a git-worktree-add file).
            sentinel_name = session["sentinel_name"]
            started_at = session["started_at"]
            polecat_home = Path(os.environ.get("POLECAT_HOME", str(Path.home() / ".polecat")))
            sentinel_matches = [
                p
                for p in polecat_home.rglob(sentinel_name)
                if p.is_file() and p.stat().st_mtime >= started_at
            ]
            assert sentinel_matches, (
                f"[{session['param']}] Sentinel file '{sentinel_name}' not found "
                f"under {polecat_home}. The agent never wrote it inside /workspace, "
                f"so we cannot locate the worktree to verify the bind-mount. "
                f"This is the same failure as test_workspace_writes_visible_on_host "
                f"and indicates the agent did not run inside the container."
            )
            worktree_path = sentinel_matches[0].parent
            git_dir = worktree_path / ".git"
            assert git_dir.is_dir(), (
                f"[{session['param']}] Worktree at {worktree_path} has "
                f"{'a .git file' if git_dir.is_file() else 'no .git entry'} "
                "— agent saw a git-worktree-add mount, not a full clone."
            )
        else:
            session_file = session.get("session_file")
            assert session_file is not None and session_file.exists(), (
                f"[{session['param']}] No session transcript — agent did not run."
            )
            raw_log = session_file.read_text()
            assert "WORKSPACE_VERIFIED=true" in raw_log, (
                f"[{session['param']}] Agent transcript does not contain "
                f"'WORKSPACE_VERIFIED=true'. The agent did not execute the "
                f"bash check from MEGA_PROMPT step 3, so /workspace mounting "
                f"cannot be verified.\n"
                f"Transcript path: {session_file}\n"
                f"Transcript tail (last 1000 chars):\n{raw_log[-1000:]}"
            )

    def test_session_persists(self, session):
        """Session file is written and contains user+assistant entries."""
        session_file = session.get("session_file")

        assert session_file is not None, f"No session file found for {session['param']}."
        assert session_file.stat().st_size > 0, "Session file exists but is empty"

        import json

        # Handle both Claude JSONL (one entry per line) and Gemini JSON (single object)
        if session_file.suffix == ".json":
            # Gemini: {"messages": [{"type": "user"|"gemini", ...}]}
            data = json.loads(session_file.read_text())
            entries = data.get("messages", [])
        else:
            # Claude: one JSON object per line
            entries = []
            with session_file.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))

        assert len(entries) > 0, "Session file has no entries"
        types = {e.get("type") for e in entries}
        assert "user" in types or "human" in types, f"No user message. Types: {types}"
        assert "assistant" in types or "model" in types or "gemini" in types, (
            f"No assistant/model message. Types: {types}"
        )

    def test_session_logs_extracted(self, session):
        """Session file can be parsed for tool calls."""
        tool_calls = session.get("tool_calls", [])
        # The agent should make at least one tool call (any type — the specific
        # tools used depend on hooks, prompt hydration, and LLM behavior)
        assert len(tool_calls) >= 1, (
            f"Expected at least one tool call, got none. "
            f"Session file: {session.get('session_file')}"
        )


# ---------------------------------------------------------------------------
# PKB write-back regression tests (run-claude × run-gemini)
# ---------------------------------------------------------------------------

TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "merge_ready", "blocked", "cancelled"})
_TASK_ID_RE = re.compile(r"(task-[0-9a-f]+|epic-[0-9a-f]+|aops-[0-9a-f]+)")

_PKB_WORKER_INSTRUCTION = (
    "This is a spike validation task. "
    "Confirm you have PKB MCP tool access, then call release_task with "
    "status=done and a one-sentence summary confirming PKB MCP worked. "
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


def _extract_task_id(resp: object) -> str | None:
    if isinstance(resp, dict):
        fm = resp.get("frontmatter") or {}
        return fm.get("id")
    if isinstance(resp, str):
        m = _TASK_ID_RE.search(resp)
        if m:
            return m.group(1)
    return None


def _poll_task(task_id: str):
    from polecat.pkb_bridge import get_task as _get_task  # type: ignore

    return _get_task(task_id)


def _require_e2e_project() -> str:
    project = os.environ.get("POLECAT_E2E_PROJECT")
    if not project:
        pytest.fail(
            "POLECAT_E2E_PROJECT must be set explicitly — no silent default. "
            "Set it to the project slug (e.g. POLECAT_E2E_PROJECT=aops)."
        )
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


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.xdist_group("pkb-persistence")
class TestPkbPersistence:
    """Regression tests: PKB MCP write-back works for run-claude and run-gemini.

    Parameterized over (run-claude, run-gemini) — the two backends where a
    polecat worker must call release_task to persist its result. crew-* paths
    have no PKB task to close and are out of scope.

    Catches regressions where the agent's PKB MCP server is misconfigured and
    release_task silently fails — e.g., the 2026-04-28 incident (PR #784) where
    gemini-extension.json was missing PKB_MCP_URL in the pkb MCP server env
    block, leaving every Gemini polecat with zero PKB tools.

    Gated: POLECAT_E2E=1, Docker + aops-crew image, PKB MCP reachable.
    """

    @pytest.fixture(
        scope="class",
        params=["run-claude", "run-gemini"],
    )
    def pkb_run(self, request, tmp_path_factory):
        """Create a fresh PKB spike task, run polecat against it, yield result info."""
        _, backend = request.param.split("-")

        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")
        if backend == "gemini" and not _gemini_cli_available():
            pytest.skip("Gemini CLI not found in PATH")
        if not _pkb_available():
            pytest.skip("PKB MCP server unreachable")
        if os.environ.get("POLECAT_E2E") != "1":
            pytest.skip("E2E test — opt in with POLECAT_E2E=1")

        project = _require_e2e_project()
        from polecat.pkb_bridge import _get_client  # type: ignore

        client = _get_client()
        scratch_parent_id = _resolve_scratch_parent(project)

        task_id: str | None = None
        proc: subprocess.Popen | None = None
        try:
            create_result = client.call_tool(
                "create_task",
                {
                    "title": f"e2e: PKB persistence {backend} (PR #784 regression)",
                    "body": _PKB_WORKER_INSTRUCTION,
                    "parent": scratch_parent_id,
                    "tags": ["test", "e2e", "pkb-persistence"],
                    "project": project,
                    "status": "ready",
                    "type": "spike",
                },
            )
            assert create_result is not None, "PKB create_task returned None"
            task_id = _extract_task_id(create_result)
            if not task_id:
                pytest.fail(
                    f"Could not extract task id from create_task response: {create_result!r}"
                )

            repo = get_repo_root()
            polecat_bin = shutil.which("polecat") or shutil.which("pc")
            if polecat_bin is None:
                cmd = [
                    sys.executable,
                    str(repo / "polecat" / "cli.py"),
                    "run",
                    "-t",
                    task_id,
                    "-p",
                    project,
                ]
            else:
                cmd = [polecat_bin, "run", "-t", task_id, "-p", project]
            if backend == "gemini":
                cmd.extend(["--model", _GEMINI_TEST_MODEL])

            proc = subprocess.Popen(
                cmd,
                cwd=str(repo),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
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

            final_task = _poll_task(task_id)
            yield {
                "param": request.param,
                "backend": backend,
                "task_id": task_id,
                "last_status": last_status,
                "task_body": (final_task.body if final_task else None),
            }
        finally:
            if proc is not None and proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError, AttributeError):
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

    def test_pkb_persistence(self, pkb_run):
        """Agent must call release_task — confirms PKB MCP write-back works end-to-end."""
        last_status = pkb_run["last_status"]
        task_id = pkb_run["task_id"]
        backend = pkb_run["backend"]
        assert last_status in TERMINAL_STATUSES, (
            f"[{pkb_run['param']}] Task {task_id} never reached terminal status "
            f"(last={last_status!r}). {backend} agent could not call release_task — "
            "likely missing PKB MCP access. Regression: PR #784 (2026-04-28)."
        )
        assert pkb_run["task_body"] and pkb_run["task_body"].strip(), (
            f"[{pkb_run['param']}] Task {task_id} reached terminal status but body is empty. "
            "Agent may have called release_task without a summary, or the PKB update "
            "was silently lost."
        )
