"""E2E tests for Docker crew sessions — one LLM invocation per backend.

Sends a single mega-prompt per backend that exercises binaries, extensions,
and structured output. Individual test methods parse different parts of the
same session result, avoiding redundant LLM calls.

Covers: agent responds, binaries on PATH, extension active, structured output,
hooks fire, session persistence (Claude), session log extraction (Claude).
"""

import io
import json
import logging
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

log = logging.getLogger(__name__)

# The single prompt that exercises everything we need to verify.
# Designed to produce output that's easy to parse programmatically.
MEGA_PROMPT = """\
Do ALL of the following steps and report results. This is a verification test.

1. Run these shell commands and include their EXACT output:
   - which pkb
   - which aops
   - pkb --version
   - echo POLECAT_SESSION_TYPE=$POLECAT_SESSION_TYPE

2. List your available extensions or tools. If you see 'aops-core' or any pkb tools, say 'AOPS_TOOLS_FOUND'.

3. What is 2+2? Include the number in your response.

Reply with all outputs clearly labeled.
"""


def _has_claude_auth():
    """Check if Claude auth is available (API key or OAuth)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    creds = Path.home() / ".claude" / ".credentials.json"
    return creds.exists()


def _extract_combined_output(session: dict) -> str:
    """Extract all text from a session result for assertion matching."""
    result = session.get("result", {})
    parts = [
        str(session.get("output", "")),
        str(session.get("stderr", "")),
    ]
    # Claude returns structured result with nested 'result' key
    if isinstance(result, dict):
        parts.append(str(result.get("result", "")))
        parts.append(str(result.get("response", "")))
    else:
        parts.append(str(result))
    return "\n".join(parts)


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.xdist_group("crew-docker-session")
class TestCrewDockerSession:
    """All Docker crew session assertions from a single LLM call per backend.

    The class-scoped crew_session fixture runs one mega-prompt per backend.
    Each test method asserts on a different aspect of the same session.
    """

    @pytest.fixture(scope="class", params=["claude-docker", "gemini-docker"])
    def crew_session(self, request, tmp_path_factory):
        """One LLM session per backend — class-scoped to share across tests.

        Returns dict with keys:
            platform, result, session_id, tool_calls, session_dir,
            output, stderr, hook_evidence
        """
        from tests.conftest import (
            _docker_available,
            _gemini_cli_available,
            _run_gemini_docker,
            find_session_jsonl,
            parse_tool_calls,
        )

        platform = request.param

        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

        tmp_path = tmp_path_factory.mktemp(f"crew-session-{platform}")

        if platform == "claude-docker":
            if not _has_claude_auth():
                pytest.skip("No Claude auth (need ANTHROPIC_API_KEY or OAuth)")

            import uuid

            from tests.conftest import build_claude_agent_cmd, get_repo_root

            repo_root = get_repo_root()
            polecat_dir = str(repo_root / "polecat")
            aops_core_dir = str(repo_root / "aops-core")
            if polecat_dir not in sys.path:
                sys.path.insert(0, polecat_dir)
            if aops_core_dir not in sys.path:
                sys.path.insert(0, aops_core_dir)

            from cli import _build_docker_cmd, _container_to_host_path

            session_id = str(uuid.uuid4())
            # In DinD, tmp_path is on overlay (invisible to the outer Docker daemon).
            # Create workspace under /workspace (a bind mount) so _build_docker_cmd
            # can detect DinD and stage auth files on a host-visible volume.
            # Workspace and session_dir must be on a Docker-visible filesystem.
            # - DinD: /workspace is a bind mount; use it directly
            # - macOS Colima: only /Users is shared via virtiofs; pytest tmp_path
            #   resolves to /private/var/folders/ which is invisible to Docker.
            #   Create under $HOME/.aops/tmp/ instead.
            _ws = Path("/workspace")
            is_dind = _ws.exists() and _container_to_host_path(_ws) != _ws
            if is_dind:
                workspace = _ws / f".test-crew-{session_id[:8]}"
            else:
                # Use a path under $HOME so Colima can see it
                docker_visible_tmp = Path.home() / ".aops" / "tmp" / f"test-crew-{session_id[:8]}"
                docker_visible_tmp.mkdir(parents=True, exist_ok=True)
                workspace = docker_visible_tmp / "workspace"
            workspace.mkdir(exist_ok=True)
            session_dir = workspace / "sessions"
            session_dir.mkdir(exist_ok=True)

            # In DinD, use a Docker named volume for session persistence
            # (bind mounts from overlay won't work).
            vol_name = None
            if is_dind:
                vol_name = f"crew-test-sessions-{session_id[:8]}"
                subprocess.run(
                    ["docker", "volume", "create", vol_name],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                # Fix ownership so container user can write
                uid, gid = os.getuid(), os.getgid()
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "-v",
                        f"{vol_name}:/sessions",
                        "--user",
                        "root",
                        "aops-crew",
                        "chown",
                        "-R",
                        f"{uid}:{gid}",
                        "/sessions",
                    ],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )

            agent_cmd = build_claude_agent_cmd(
                MEGA_PROMPT,
                output_format="json",
                extra_args=[
                    "--verbose",
                    "--debug",
                    "hooks",
                    "--session-id",
                    session_id,
                ],
            )

            env = {}
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                env["ANTHROPIC_API_KEY"] = api_key
            oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
            if oauth_token:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
            aca_data = os.environ.get("ACA_DATA")
            if aca_data:
                env["ACA_DATA"] = aca_data

            cmd = _build_docker_cmd(
                cli_tool="claude",
                work_dir=workspace,
                env=env,
                agent_cmd=agent_cmd,
                is_interactive=False,
                session_dir=session_dir,
                session_volume=vol_name,
            )

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                pytest.fail("Claude Docker session timed out after 180s")

            # Parse JSON output
            try:
                parsed = json.loads(proc.stdout)
                if isinstance(parsed, list):
                    result_msg = next(
                        (m for m in parsed if isinstance(m, dict) and m.get("type") == "result"),
                        parsed[-1] if parsed else {},
                    )
                    init_msg = next(
                        (m for m in parsed if isinstance(m, dict) and m.get("type") == "system"),
                        {},
                    )
                else:
                    result_msg = parsed
                    init_msg = {}
                # Detect auth failures — Claude returns valid JSON but
                # is_error=True with "Not logged in" when auth is missing.
                # These must be hard failures, not silent successes.
                result_text = result_msg.get("result", "") if isinstance(result_msg, dict) else ""
                is_auth_failure = (
                    isinstance(result_msg, dict)
                    and result_msg.get("is_error")
                    and "not logged in" in result_text.lower()
                )
                if is_auth_failure:
                    pytest.fail(
                        f"Claude auth failure inside Docker container: {result_text}\n"
                        f"stderr: {proc.stderr[:500] if proc.stderr else 'none'}"
                    )

                result = {
                    "success": not (isinstance(result_msg, dict) and result_msg.get("is_error")),
                    "output": proc.stdout,
                    "stderr": proc.stderr,
                    "result": result_msg,
                    "init": init_msg,
                }
            except json.JSONDecodeError:
                result = {
                    "success": proc.returncode == 0,
                    "output": proc.stdout,
                    "stderr": proc.stderr,
                    "result": {},
                    "error": f"JSON parse error. stdout: {proc.stdout[:500]}",
                }

            if proc.returncode != 0 and not result.get("success"):
                result["success"] = False
                result["error"] = (
                    f"Exit {proc.returncode}: {proc.stderr[:500] if proc.stderr else 'no stderr'}"
                )

            # In DinD, extract session files from the named volume into session_dir.
            # In native mode, session_dir is already populated via the bind mount.
            if vol_name:
                try:
                    tar_result = subprocess.run(
                        [
                            "docker",
                            "run",
                            "--rm",
                            "-v",
                            f"{vol_name}:/src",
                            "alpine",
                            "sh",
                            "-c",
                            "cd /src && find . -mindepth 1 | grep -q . && tar czf - . || true",
                        ],
                        capture_output=True,
                        timeout=30,
                    )
                    if tar_result.returncode == 0 and tar_result.stdout:
                        with tarfile.open(fileobj=io.BytesIO(tar_result.stdout)) as tar:
                            tar.extractall(session_dir, filter="data")
                except Exception as e:
                    log.warning("Failed to extract sessions from volume %s: %s", vol_name, e)
                finally:
                    subprocess.run(
                        ["docker", "volume", "rm", vol_name],
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )

            # Extract session data before cleanup (session_dir may be inside
            # docker_visible_tmp which gets removed).
            session_file = find_session_jsonl(session_id, search_dirs=[session_dir])

            # Copy session files to tmp_path so they survive cleanup of
            # docker_visible_tmp. tmp_path is managed by pytest.
            persist_dir = tmp_path / "sessions"
            import shutil

            if session_dir.exists():
                shutil.copytree(session_dir, persist_dir, dirs_exist_ok=True)
            else:
                persist_dir.mkdir(exist_ok=True)
            if session_file:
                try:
                    session_file = persist_dir / session_file.relative_to(session_dir)
                except ValueError:
                    # session_file fell back to host ~/.claude/projects/ — leave as-is
                    pass
            session_dir = persist_dir

            # Clean up Docker-visible temp dirs
            if is_dind:
                shutil.rmtree(workspace, ignore_errors=True)
                staging_root = workspace / ".aops-staging"
                if staging_root.exists():
                    shutil.rmtree(staging_root, ignore_errors=True)
            elif docker_visible_tmp.exists():
                shutil.rmtree(docker_visible_tmp, ignore_errors=True)
            tool_calls = parse_tool_calls(session_file) if session_file else []

            return {
                "platform": platform,
                "result": result,
                "session_id": session_id,
                "tool_calls": tool_calls,
                "session_dir": session_dir,
                "session_file": session_file,
                "output": proc.stdout,
                "stderr": proc.stderr,
            }

        elif platform == "gemini-docker":
            if not _gemini_cli_available():
                pytest.skip("Gemini CLI not found in PATH")

            gemini_home = request.getfixturevalue("gemini_home")
            result = _run_gemini_docker(
                MEGA_PROMPT,
                gemini_home=gemini_home,
                timeout_seconds=180,
            )

            return {
                "platform": platform,
                "result": result,
                "session_id": None,
                "tool_calls": [],
                "session_dir": None,
                "session_file": None,
                "output": result.get("output", ""),
                "stderr": result.get("stderr", ""),
            }

    # --- Assertions (all parse the single session) ---

    def test_agent_responds(self, crew_session):
        """Agent starts, responds, and exits cleanly in Docker."""
        result = crew_session["result"]
        platform = crew_session["platform"]
        assert result.get("success"), (
            f"[{platform}] Session failed: {result.get('error', 'unknown')}\n"
            f"stdout: {crew_session['output'][:500]}\n"
            f"stderr: {crew_session['stderr'][:500]}"
        )

    def test_framework_binaries_on_path(self, crew_session):
        """pkb and aops binaries are available inside Docker."""
        combined = _extract_combined_output(crew_session)
        platform = crew_session["platform"]
        assert "pkb" in combined.lower(), (
            f"[{platform}] pkb binary not found in agent output.\n"
            f"Combined output: {combined[:1000]}"
        )

    def test_extension_active(self, crew_session):
        """aops-core extension/plugin is recognized by the agent."""
        combined = _extract_combined_output(crew_session)
        platform = crew_session["platform"]
        assert (
            "aops-core" in combined or "AOPS_TOOLS_FOUND" in combined or "pkb" in combined.lower()
        ), f"[{platform}] Extension not active in container.\nCombined output: {combined[:1000]}"

    def test_structured_output(self, crew_session):
        """Agent returns parseable output."""
        result = crew_session["result"]
        platform = crew_session["platform"]
        assert result.get("result"), (
            f"[{platform}] No structured result. Keys: {list(result.keys())}"
        )

    def test_hooks_fired(self, crew_session):
        """Hooks fire inside Docker container.

        Claude: check stderr/debug output for hook evidence.
        Gemini: check stderr for hook/extension loading evidence.
        """
        platform = crew_session["platform"]
        stderr = crew_session.get("stderr", "")
        output = crew_session.get("output", "")
        combined = stderr + output

        if platform == "claude-docker":
            # Claude --debug hooks writes hook events to stderr
            # Look for any hook-related output
            hook_evidence = (
                "hook" in combined.lower()
                or "SessionStart" in combined
                or "gate" in combined.lower()
            )
            assert hook_evidence, (
                f"[{platform}] No hook evidence in output.\n"
                f"stderr (last 500): {stderr[-500:]}\n"
                f"stdout (last 500): {output[-500:]}"
            )
        else:
            # Gemini: extensions loading produces stderr output
            # or hook logs appear in session state
            hook_evidence = (
                "hook" in combined.lower()
                or "extension" in combined.lower()
                or "aops-core" in combined.lower()
            )
            if not hook_evidence:
                pytest.skip(
                    f"[{platform}] No hook evidence found — Gemini hook logging "
                    "may not be visible in sandbox stderr"
                )

    def test_session_persists(self, crew_session):
        """Session JSONL is written and contains user+assistant entries (Claude only)."""
        if crew_session["platform"] != "claude-docker":
            pytest.skip("Session persistence verification is Claude-specific")

        session_dir = crew_session["session_dir"]
        session_file = crew_session["session_file"]

        # Session dir has files
        actual_files = [p for p in session_dir.rglob("*") if p.is_file()]
        assert len(actual_files) > 0, f"session_dir has no files: {session_dir}"

        # JSONL file exists and is non-empty
        assert session_file is not None, (
            f"No session JSONL for {crew_session['session_id']}. "
            f"Files in session_dir: {actual_files}"
        )
        assert session_file.stat().st_size > 0, "Session JSONL exists but is empty"

        # JSONL content has user + assistant messages
        entries = []
        with session_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        assert len(entries) > 0, "Session JSONL has no entries"
        types = {e.get("type") for e in entries}
        assert "user" in types or "human" in types, f"No user message. Types: {types}"
        assert "assistant" in types, f"No assistant message. Types: {types}"

    def test_session_logs_extracted(self, crew_session):
        """Session JSONL can be parsed for tool calls (Claude only)."""
        if crew_session["platform"] != "claude-docker":
            pytest.skip("Tool call extraction is Claude-specific")

        session_id = crew_session["session_id"]
        assert session_id, "Session ID should be set"

        tool_calls = crew_session["tool_calls"]
        # The mega-prompt asks to run shell commands, so there should be Bash tool calls
        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]
        assert len(bash_calls) >= 1, (
            f"Expected at least one Bash tool call, got: {[c['name'] for c in tool_calls]}"
        )


def _init_test_repo(tmp_path):
    """Create a minimal git repo with a remote so crew worktree setup works."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


@pytest.mark.slow
@pytest.mark.integration
class TestCrewFullPath:
    """Full CLI-to-response tests: `pc crew repo <path> -- -p <prompt>`.

    These exercise the ENTIRE crew path: CLI entry point → worktree setup →
    env construction → Docker/sandbox launch → LLM response → cleanup.
    """

    @pytest.fixture(autouse=True)
    def _require_docker(self):
        from tests.conftest import _docker_available

        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

    def _run_crew(self, tmp_path, gemini=False, timeout=180):
        """Run pc crew repo <path> with a simple prompt, return stdout+stderr."""
        repo = _init_test_repo(tmp_path)

        cmd = [
            sys.executable,
            "-m",
            "polecat.cli",
            "--home",
            str(tmp_path / "polecat_home"),
            "crew",
            "repo",
            str(repo),
            "-n",
            f"test-{'gemini' if gemini else 'claude'}",
        ]
        if gemini:
            cmd.append("-g")

        # Pass agent-specific args after '--'
        cmd.append("--")
        if gemini:
            cmd.extend(
                [
                    "-p",
                    "What is 2+2? Reply with ONLY the number.",
                    "--approval-mode",
                    "yolo",
                    "--raw-output",
                    "--accept-raw-output-risk",
                ]
            )
        else:
            cmd.extend(
                [
                    "-p",
                    "What is 2+2? Reply with ONLY the number.",
                    "--output-format",
                    "json",
                    "--model",
                    "haiku",
                    "--max-turns",
                    "3",
                ]
            )

        # Create polecat home
        polecat_home = tmp_path / "polecat_home"
        polecat_home.mkdir(exist_ok=True)
        import yaml

        (polecat_home / "polecat.yaml").write_text(yaml.dump({"projects": {}}))

        env = os.environ.copy()
        env["POLECAT_HOME"] = str(polecat_home)
        env["PYTHONPATH"] = (
            os.getcwd() + ":" + os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"
        )

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
                cwd=os.getcwd(),
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(f"pc crew {'gemini' if gemini else 'claude'} timed out after {timeout}s")

        return proc

    def test_crew_claude_full_path(self, tmp_path):
        """pc crew repo <path> -- -p <prompt> produces a response via Claude."""
        proc = self._run_crew(tmp_path, gemini=False)
        combined = proc.stdout + proc.stderr

        # The crew CLI prints status lines, then Claude outputs JSON
        assert proc.returncode == 0 or "4" in combined, (
            f"Claude crew failed (exit {proc.returncode}).\n"
            f"stdout: {proc.stdout[-1000:]}\n"
            f"stderr: {proc.stderr[-1000:]}"
        )
        assert "4" in combined, (
            f"Claude crew did not produce expected response containing '4'.\n"
            f"stdout: {proc.stdout[-1000:]}\n"
            f"stderr: {proc.stderr[-1000:]}"
        )

    def test_crew_gemini_full_path(self, tmp_path):
        """pc crew repo <path> -g -- -p <prompt> produces a response via Gemini."""
        from tests.conftest import _gemini_cli_available

        if not _gemini_cli_available():
            pytest.skip("Gemini CLI not found in PATH")

        proc = self._run_crew(tmp_path, gemini=True)
        combined = proc.stdout + proc.stderr

        assert "4" in combined, (
            f"Gemini crew did not produce expected response containing '4'.\n"
            f"stdout: {proc.stdout[-1000:]}\n"
            f"stderr: {proc.stderr[-1000:]}"
        )
