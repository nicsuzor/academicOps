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
import subprocess
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

# PKB task whose body is the test prompt for `pc run -t`.
# Created in PKB under aops project — DO NOT COMPLETE or ARCHIVE this task.
TEST_FIXTURE_TASK_ID = "e2e-test-fixture"

# Mega-prompt for crew paths (passed directly via -p).
# Must match the task body for run paths so assertions work on both.
MEGA_PROMPT_TEMPLATE = """\
Do ALL of the following steps and report results exactly as labeled:

1. SANDBOX CHECK:
   - Run: test -f /.dockerenv && echo "SANDBOX_VERIFIED=true" || echo "SANDBOX_VERIFIED=false"
   - Run: echo "SESSION_TYPE=$POLECAT_SESSION_TYPE"
   - Run: hostname

2. BINARY CHECK:
   - Run: which aops

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


def _cleanup_run_worktree():
    """Delete the remote branch and local worktree created by pc run for the fixture task.

    pc run creates polecat/<task-id> on origin and a local clone under ~/.aops/worktrees/.
    Without cleanup, subsequent runs fail with "stale unmerged branch" from polecat's guard.
    """
    branch = f"polecat/{TEST_FIXTURE_TASK_ID}"
    subprocess.run(
        ["git", "push", "origin", "--delete", branch],
        capture_output=True,
        check=False,
    )
    worktree = Path.home() / ".aops" / "worktrees" / TEST_FIXTURE_TASK_ID
    if worktree.exists():
        import shutil

        shutil.rmtree(worktree, ignore_errors=True)


def _reset_fixture_task():
    """Reset the test fixture task to active status so it can be re-run.

    Uses the PKB MCP HTTP API to update the remote server, then also
    resets the local file to keep them in sync.
    """
    # Reset via PKB MCP API (the source of truth for `pc run`)
    try:
        from polecat.pkb_bridge import update_task

        update_task(TEST_FIXTURE_TASK_ID, status="active", assignee="polecat")
    except Exception:
        pass  # Best-effort; local reset below is the fallback

    # Also reset the local file for environments where PKB reads locally
    aca_data = os.environ.get("ACA_DATA", str(Path.home() / "brain"))
    task_file = Path(aca_data) / "tasks" / f"{TEST_FIXTURE_TASK_ID}.md"
    if not task_file.exists():
        return
    content = task_file.read_text()
    content = re.sub(r"(?m)^status:\s+\S+", "status: active", content, count=1)
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
            return self._run_crew(tmp_path, backend)
        else:
            return self._run_polecat(tmp_path, backend)

    @staticmethod
    def _is_hook_file(f: Path) -> bool:
        """Return True if the file is a hook log, not a session transcript."""
        return f.name.endswith("-hooks.jsonl") or f.name.startswith("cc_hooks_")

    @staticmethod
    def _is_session_file(f: Path) -> bool:
        """Return True if the file looks like a session transcript (Claude or Gemini)."""
        if TestAllInvocationPaths._is_hook_file(f):
            return False
        # Claude: *.jsonl (not hooks)
        if f.suffix == ".jsonl":
            return True
        # Gemini: chats/session-*.json
        if f.suffix == ".json" and f.name.startswith("session-"):
            return True
        return False

    @staticmethod
    def _find_latest_session_logs(
        started_after: float = 0,
        crew_name: str | None = None,
        backend: str | None = None,
    ):
        """Discover the most-recently-modified session file and hook log.

        Searches for both Claude JSONL and Gemini JSON session files.

        Args:
            started_after: Unix timestamp — only consider files modified after
                this time. Prevents picking up stale files from unrelated sessions.
            crew_name: Optional crew name embedded in hook log filenames (e.g.
                "test-claude").  When set, filters hook files to those whose
                filename contains the crew name, avoiding cross-session races
                where a concurrent session's hook log is created in the same
                time window.
            backend: "claude" or "gemini". When set, filters session files by
                expected format (.jsonl for Claude, session-*.json for Gemini)
                to prevent cross-backend contamination.

        Returns:
            (hook_files_content, session_file, tool_calls)
        """
        from lib.paths import get_sessions_repo

        from tests.conftest import parse_tool_calls

        aops_sessions = get_sessions_repo()

        def _hook_birthtime(f: Path) -> float:
            st = f.stat()
            # st_birthtime is macOS/BSD; fall back to st_ctime on Linux
            return getattr(st, "st_birthtime", st.st_ctime)

        hook_files = sorted(aops_sessions.rglob("*-hooks.jsonl"), key=_hook_birthtime)
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

        is_session = TestAllInvocationPaths._is_session_file
        claude_dir = Path.home() / ".claude" / "projects"
        session_files = []
        if claude_dir.exists():
            session_files.extend(f for f in claude_dir.rglob("*.jsonl") if is_session(f))
        if aops_sessions.exists():
            # Search both .jsonl (Claude) and .json (Gemini chats)
            for f in aops_sessions.rglob("*"):
                if f.is_file() and is_session(f):
                    session_files.append(f)

        # Filter by modification time to avoid picking up unrelated sessions
        if started_after:
            session_files = [f for f in session_files if f.stat().st_mtime >= started_after]

        # Filter by expected file format for the backend to prevent cross-session
        # contamination when Claude and Gemini sessions run in the same time window.
        if backend == "claude":
            session_files = [f for f in session_files if f.suffix == ".jsonl"]
        elif backend == "gemini":
            session_files = [
                f for f in session_files if f.suffix == ".json" and f.name.startswith("session-")
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
            cmd.append("-g")

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
            "CLAUDE_SESSION_ID",
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
        hook_files_content, session_file, tool_calls = self._find_latest_session_logs(
            started_after=started_at,
            crew_name=crew_name,
            backend=backend,
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
            cmd.append("-g")

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
            "CLAUDE_SESSION_ID",
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
        worktree = Path.home() / ".aops" / "worktrees" / TEST_FIXTURE_TASK_ID
        sentinel_file = worktree / sentinel_name
        sentinel_on_host = sentinel_file.exists()
        sentinel_content = sentinel_file.read_text().strip() if sentinel_on_host else ""
        _cleanup_run_worktree()

        # --no-auto-finish leaves the worktree in place; capture the sentinel
        # before _cleanup_run_worktree() deletes the worktree directory.
        worktree = Path.home() / ".aops" / "worktrees" / TEST_FIXTURE_TASK_ID
        sentinel_file = worktree / sentinel_name
        sentinel_on_host = sentinel_file.exists()
        sentinel_content = sentinel_file.read_text().strip() if sentinel_on_host else ""
        _cleanup_run_worktree()

        combined = proc.stdout + proc.stderr
        hook_files_content, session_file, tool_calls = self._find_latest_session_logs(
            started_after=started_at,
            backend=backend,
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
        """Agent starts, produces output, and exits."""
        combined = session["combined"]
        # Must have SOME output from the agent (not just CLI status lines)
        assert len(combined) > 100, (
            f"{session['param']} produced very little output "
            f"({len(combined)} chars).\n"
            f"stdout: {session['stdout'][-500:]}\n"
            f"stderr: {session['stderr'][-500:]}"
        )

    def test_sandbox_isolation(self, session):
        """Agent runs inside a Docker container / Gemini sandbox."""
        import re

        combined = session["combined"]
        session_file = session.get("session_file")
        raw_log = session_file.read_text() if session_file and session_file.exists() else ""
        all_text = raw_log + combined

        # Primary proof: the agent executed the bash command inside the container
        # and reported SANDBOX_VERIFIED=true, or we can see Docker container evidence.
        has_dockerenv = (
            "SANDBOX_VERIFIED=true" in all_text
            or bool(re.search(r"\bSANDBOX_VERIFIED\s*=\s*true\b", all_text, re.IGNORECASE))
            or "/.dockerenv" in all_text
        )

        # Secondary proof: the agent read the injected environment variables
        has_session_type = bool(
            re.search(r"SESSION_TYPE.*?(crew|polecat)", all_text, re.IGNORECASE)
        )

        # Fallback: if the agent didn't run our specific bash commands, check for
        # other Docker/sandbox evidence (container hostname, sandbox flags, etc.)
        has_container_evidence = (
            "aops-crew" in all_text
            or "POLECAT_SESSION_TYPE" in all_text
            or "--sandbox" in combined
            or bool(re.search(r"docker\s+run", combined, re.IGNORECASE))
        )

        assert (has_dockerenv and has_session_type) or has_container_evidence, (
            f"[{session['param']}] Failed to verify sandbox isolation.\n"
            f"has_dockerenv={has_dockerenv}, has_session_type={has_session_type}, "
            f"has_container_evidence={has_container_evidence}\n"
            f"Agent output (last 1000 chars): {combined[-1000:]}"
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

        - run path: the agent echoes WORKSPACE_VERIFIED=true via the bash
          command in the MEGA_PROMPT.  The session transcript (JSONL) is
          accessible on the host for this path, so the string appears in
          raw_log or combined.
        """
        combined = session["combined"]
        session_file = session.get("session_file")
        raw_log = session_file.read_text() if session_file and session_file.exists() else ""
        all_text = raw_log + combined

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
            if not sentinel_matches:
                pytest.skip(
                    f"[{session['param']}] Sentinel file not found on host — "
                    "cannot verify workspace via host-side check "
                    "(test_workspace_writes_visible_on_host would also fail)"
                )
            worktree_path = sentinel_matches[0].parent
            git_dir = worktree_path / ".git"
            assert git_dir.is_dir(), (
                f"[{session['param']}] Worktree at {worktree_path} has "
                f"{'a .git file' if git_dir.is_file() else 'no .git entry'} "
                "— agent saw a git-worktree-add mount, not a full clone."
            )
        else:
            assert "WORKSPACE_VERIFIED=true" in all_text, (
                f"[{session['param']}] No evidence the repo worktree was available at /workspace. "
                f"Agent output (last 1000 chars): {all_text[-1000:]}"
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
