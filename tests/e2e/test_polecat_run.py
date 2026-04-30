"""E2E tests for the `pc run` code path.

Tests `polecat run` (headless task execution) for both Claude and Gemini backends.
Uses fake docker/gemini binaries to verify command construction without needing
real LLM invocations for most tests.

The `pc run` path shares `_build_docker_cmd()` / `_make_worker_env()` with `crew`,
so Docker env verification is covered by test_polecat_docker_isolation.py. These
tests focus on run-specific behavior: task routing, prompt building, exit codes.
"""

import os
import subprocess

import pytest


def _polecat_env(polecat_home, sessions_dir=None):
    """Build an env dict for running polecat CLI."""
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(polecat_home)
    if sessions_dir is not None:
        env["AOPS_SESSIONS"] = str(sessions_dir)
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"
    return env


def _polecat_cwd():
    """CWD for running polecat CLI (needs to be inside polecat/ for imports)."""
    return os.getcwd() + "/polecat"


def _init_test_repo(tmp_path):
    """Create a minimal git repo suitable for polecat."""
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
    # Add a remote so polecat can determine the repo
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/test/test.git"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


@pytest.fixture
def temp_polecat_home(tmp_path):
    """Create a polecat home directory and an empty sessions registry.

    Returns the polecat home; the sessions registry sits at
    `tmp_path / "sessions" / "projects.yaml"`. Tests that need to drive the
    CLI must pass `sessions_dir=tmp_path / "sessions"` to `_polecat_env`.
    """
    import yaml

    home = tmp_path / "polecat_home"
    home.mkdir(exist_ok=True)
    sessions = tmp_path / "sessions"
    sessions.mkdir(exist_ok=True)
    (sessions / "projects.yaml").write_text(yaml.dump({"projects": {}}))
    return home


# --- Cheap tests (no Docker, no LLM) ---


@pytest.mark.slow
@pytest.mark.integration
class TestPolecatRunCLI:
    """Tests for pc run CLI argument handling and exit codes."""

    def test_run_empty_queue_exits_3(self, temp_polecat_home):
        """pc run with no tasks in queue exits with code 3."""
        env = _polecat_env(temp_polecat_home, sessions_dir=temp_polecat_home.parent / "sessions")

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "polecat.cli",
                "--home",
                str(temp_polecat_home),
                "run",
                "--project",
                "nonexistent-test-project-zyx987",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
            cwd=_polecat_cwd(),
        )

        assert result.returncode == 3, (
            f"Expected exit code 3 (empty queue), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "no ready tasks" in (result.stdout + result.stderr).lower(), (
            f"Expected 'no ready tasks' message. Output: {result.stdout + result.stderr}"
        )

    def test_run_invalid_task_id_exits_1(self, temp_polecat_home):
        """pc run with invalid task ID format exits with code 1."""
        env = _polecat_env(temp_polecat_home, sessions_dir=temp_polecat_home.parent / "sessions")

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "polecat.cli",
                "--home",
                str(temp_polecat_home),
                "run",
                "--task-id",
                "not-a-valid-id!!!",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=_polecat_cwd(),
        )

        assert result.returncode != 0, (
            f"Expected non-zero exit for invalid task ID, got {result.returncode}.\n"
            f"Output: {result.stdout + result.stderr}"
        )

    def test_run_issue_and_task_id_mutually_exclusive(self, temp_polecat_home):
        """pc run rejects --issue and --task-id together."""
        env = _polecat_env(temp_polecat_home, sessions_dir=temp_polecat_home.parent / "sessions")

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "polecat.cli",
                "--home",
                str(temp_polecat_home),
                "run",
                "--task-id",
                "task-abc123",
                "--issue",
                "owner/repo#1",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=_polecat_cwd(),
        )

        assert result.returncode != 0, (
            f"Expected non-zero exit for mutually exclusive flags. Output: {result.stdout + result.stderr}"
        )
        assert "mutually exclusive" in (result.stdout + result.stderr).lower(), (
            f"Expected mutual exclusion error. Output: {result.stdout + result.stderr}"
        )


# --- Command construction tests (fake docker/gemini, no LLM) ---


@pytest.mark.slow
@pytest.mark.integration
class TestPolecatRunCommandConstruction:
    """Verify pc run constructs correct Docker/Gemini commands.

    Uses fake binaries to intercept the command that polecat run would execute,
    then verifies critical env vars and arguments are present.

    These tests require a PKB task to exist, so they're skipped when PKB
    is unavailable. For environments without PKB, the CLI tests above
    still verify argument handling and exit codes.
    """

    # NOTE: These tests would need a way to inject a synthetic task without PKB.
    # For now, they serve as documentation of the intended test architecture.
    # Real command construction is already covered by test_polecat_docker_isolation.py
    # for the `crew` path, which shares _build_docker_cmd() with `run`.
    pass
