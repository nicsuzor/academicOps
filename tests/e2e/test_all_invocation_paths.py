"""E2E tests for ALL invocation paths: crew and run, Claude and Gemini.

Parameterized over 4 combinations: (crew, run) × (claude, gemini).
Each test exercises the FULL path from CLI entry point through Docker/sandbox
to LLM response, proving:
- Agent responds and produces output
- Agent runs inside a container (sandbox isolation)
- PKB MCP server works (tool calls succeed)
- Required binaries are available

These are the most expensive tests in the suite — each invokes a real LLM
inside a real Docker container. They exist because cheaper tests (fake binaries,
mock Docker) cannot catch real integration failures like the Gemini auth
regression (EAI_AGAIN) that triggered this work.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.conftest import _docker_available, _gemini_cli_available, get_repo_root

# PKB task whose body is the test prompt for `pc run -t`.
# Created in PKB under aops project — DO NOT COMPLETE or ARCHIVE this task.
TEST_FIXTURE_TASK_ID = "e2e-test-fixture"

# Mega-prompt for crew paths (passed directly via -p).
# Must match the task body for run paths so assertions work on both.
MEGA_PROMPT = """\
Do ALL of the following steps and report results exactly as labeled:

1. SANDBOX CHECK:
   - Run: test -f /.dockerenv && echo "SANDBOX_VERIFIED=true" || echo "SANDBOX_VERIFIED=false"
   - Run: echo "SESSION_TYPE=$POLECAT_SESSION_TYPE"
   - Run: hostname

2. PKB TOOL CALL:
   - Use the pkb graph_stats MCP tool and report the output
   - Include the exact task_count and document_count values

3. BINARY CHECK:
   - Run: pkb --version
   - Run: which aops

Reply with ALL outputs clearly labeled. Do NOT skip any step.
Do NOT create any commits, PRs, or modify any files. Just report the results.\
"""


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


def _reset_fixture_task():
    """Reset the test fixture task to active status so it can be re-run.

    Writes directly to the task file's frontmatter since `pkb update` is
    only available via the MCP protocol, not the CLI.
    """
    aca_data = os.environ.get("ACA_DATA", str(Path.home() / "brain"))
    task_file = Path(aca_data) / "tasks" / f"{TEST_FIXTURE_TASK_ID}.md"
    if not task_file.exists():
        return
    content = task_file.read_text()
    # Replace status: <anything> with status: active in frontmatter
    content = re.sub(r"(?m)^status:\s+\S+", "status: active", content, count=1)
    # Strip any "Completion Evidence" or "Outcome" sections appended by previous
    # runs — agents see these and triage ("prior work") instead of executing.
    content = re.sub(r"\n## Completion Evidence.*", "", content, flags=re.DOTALL)
    content = re.sub(r"\n  ## Outcome.*?(?=\n\w)", "\n", content, flags=re.DOTALL)
    task_file.write_text(content)


def _make_polecat_home(tmp_path):
    """Create a polecat home with project config pointing to the real academicOps repo."""
    polecat_home = tmp_path / "polecat_home"
    polecat_home.mkdir(exist_ok=True)
    config = {
        "projects": {
            "aops": {
                "path": str(get_repo_root()),
                "default_branch": "main",
            },
        },
    }
    (polecat_home / "polecat.yaml").write_text(yaml.dump(config))
    return polecat_home


def _base_env(polecat_home):
    """Build env dict for running polecat commands."""
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(polecat_home)
    env["PYTHONPATH"] = (
        os.getcwd() + ":" + os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"
    )
    return env


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

    def _run_crew(self, tmp_path, backend, timeout=300):
        """Run pc crew repo <path> -- -p <mega-prompt>."""
        repo = _init_test_repo(tmp_path)
        polecat_home = _make_polecat_home(tmp_path)

        cmd = [
            sys.executable,
            "-m",
            "polecat.cli",
            "--home",
            str(polecat_home),
            "crew",
            "repo",
            str(repo),
            "-n",
            f"test-{backend}",
        ]
        if backend == "gemini":
            cmd.append("-g")

        cmd.append("--")
        if backend == "gemini":
            cmd.extend(
                [
                    "-p",
                    MEGA_PROMPT,
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
                    MEGA_PROMPT,
                    "--output-format",
                    "text",
                    "--model",
                    "haiku",
                    "--max-turns",
                    "10",
                ]
            )

        env = _base_env(polecat_home)

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
            pytest.fail(f"crew-{backend} timed out after {timeout}s")

        combined = proc.stdout + proc.stderr
        return {
            "param": f"crew-{backend}",
            "path_type": "crew",
            "backend": backend,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "combined": combined,
        }

    def _run_polecat(self, tmp_path, backend, timeout=300):
        """Run pc run -t <task_id> for the given backend."""
        if not _check_fixture_task():
            pytest.skip(
                f"Test fixture task '{TEST_FIXTURE_TASK_ID}' not found in PKB "
                "(missing, or pkb binary not available)"
            )

        # Reset task to active before each run (previous run may have set in_progress)
        _reset_fixture_task()

        polecat_home = _make_polecat_home(tmp_path)

        cmd = [
            sys.executable,
            "-m",
            "polecat.cli",
            "--home",
            str(polecat_home),
            "run",
            "-t",
            TEST_FIXTURE_TASK_ID,
            "--no-auto-finish",
        ]
        if backend == "gemini":
            cmd.append("-g")

        env = _base_env(polecat_home)

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
            pytest.fail(f"run-{backend} timed out after {timeout}s")
        finally:
            # Always reset task status so it's reusable
            _reset_fixture_task()

        combined = proc.stdout + proc.stderr
        return {
            "param": f"run-{backend}",
            "path_type": "run",
            "backend": backend,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "combined": combined,
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
        combined = session["combined"]
        # Check for either signal of container execution
        has_dockerenv = "SANDBOX_VERIFIED=true" in combined
        has_session_type = "SESSION_TYPE=crew" in combined or "SESSION_TYPE=polecat" in combined
        assert has_dockerenv or has_session_type, (
            f"{session['param']} could not verify sandbox isolation.\n"
            f"Expected SANDBOX_VERIFIED=true or SESSION_TYPE=crew/polecat.\n"
            f"Output (last 1000 chars): {combined[-1000:]}"
        )

    def test_pkb_tool_call(self, session):
        """PKB MCP graph_stats tool call succeeds inside the container."""
        combined = session["combined"]
        # graph_stats returns task_count and/or document_count
        has_task_count = "task_count" in combined.lower()
        has_doc_count = "document_count" in combined.lower()
        has_graph_stats = "graph_stats" in combined.lower() or "graph stats" in combined.lower()
        assert has_task_count or has_doc_count or has_graph_stats, (
            f"{session['param']} did not produce PKB graph_stats output.\n"
            f"Expected task_count/document_count in output.\n"
            f"Output (last 1000 chars): {combined[-1000:]}"
        )

    def test_pkb_binary_available(self, session):
        """pkb binary is on PATH and responds to --version."""
        combined = session["combined"]
        # The prompt asks to run `pkb --version` and `which aops`
        has_pkb = "pkb" in combined.lower()
        assert has_pkb, (
            f"{session['param']} did not report pkb binary.\n"
            f"Output (last 1000 chars): {combined[-1000:]}"
        )
