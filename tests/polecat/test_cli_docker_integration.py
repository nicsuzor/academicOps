#!/usr/bin/env python3
"""Integration tests for Docker container end-state.

Unlike test_cli_docker.py (which checks command flag strings), these tests
actually spin up containers via the production _build_docker_cmd() +
_run_docker_container() pipeline and verify the resulting state inside the
container.

Motivation: the WSL2 workspace bug went undetected because a unit test
checked for ``-v /workspace`` in the command list — which passed while
``/workspace`` was empty inside the actual container.

These tests require Docker and the ``aops-crew`` image to be available.
They skip gracefully when either is missing.
"""

import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from cli import _build_docker_cmd, _run_docker_container  # noqa: E402

from tests.conftest import _docker_available  # noqa: E402


def _parse_kv_output(stdout: str) -> dict[str, str]:
    """Parse KEY=VALUE lines from container stdout into a dict."""
    results = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            results[key.strip()] = value.strip()
    return results


# ---------------------------------------------------------------------------
# Container 1: Environment variables, git identity, credentials, UID
# ---------------------------------------------------------------------------

_ENV_SCRIPT = r"""
echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
echo "CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN"
echo "GEMINI_API_KEY=$GEMINI_API_KEY"
echo "GOOGLE_API_KEY=$GOOGLE_API_KEY"
echo "POLECAT_SESSION_TYPE=$POLECAT_SESSION_TYPE"
echo "POLECAT_CREW_NAME=$POLECAT_CREW_NAME"
echo "MY_SECRET=$MY_SECRET"
echo "DATABASE_URL=$DATABASE_URL"
echo "CUSTODIET_GATE_MODE=$CUSTODIET_GATE_MODE"
echo "HANDOVER_GATE_MODE=$HANDOVER_GATE_MODE"
echo "QA_GATE_MODE=$QA_GATE_MODE"
echo "CUSTODIET_TOOL_CALL_THRESHOLD=$CUSTODIET_TOOL_CALL_THRESHOLD"
echo "AOPS_SESSIONS=$AOPS_SESSIONS"
echo "AOPS_CUSTOM_VAR=$AOPS_CUSTOM_VAR"
echo "TZ_VAL=$TZ"
echo "GIT_AUTHOR_NAME=$GIT_AUTHOR_NAME"
echo "GIT_AUTHOR_EMAIL=$GIT_AUTHOR_EMAIL"
echo "GIT_COMMITTER_NAME=$GIT_COMMITTER_NAME"
echo "GIT_COMMITTER_EMAIL=$GIT_COMMITTER_EMAIL"
echo "SSH_AUTH_SOCK_VAL=$SSH_AUTH_SOCK"
echo "GIT_SSH_COMMAND=$GIT_SSH_COMMAND"
echo "GIT_TERMINAL_PROMPT=$GIT_TERMINAL_PROMPT"
echo "GH_TOKEN_VAL=$GH_TOKEN"
echo "AOPS_BOT_GH_TOKEN=$AOPS_BOT_GH_TOKEN"
echo "GIT_ASKPASS=$GIT_ASKPASS"
echo "PKB_MCP_URL=$PKB_MCP_URL"
echo "CONTAINER_UID=$(id -u)"
echo "CONTAINER_GID=$(id -g)"
echo "GIT_CONFIG_NAME=$(git config --global user.name 2>/dev/null || echo UNSET)"
echo "GIT_CONFIG_EMAIL=$(git config --global user.email 2>/dev/null || echo UNSET)"
echo "CRED_PASSWORD=$(printf 'protocol=https\nhost=github.com\n' | git credential fill 2>/dev/null | grep password || echo NONE)"
echo "GIT_URL_REWRITE=$(git config --global --get url.https://github.com/.insteadOf 2>/dev/null || echo NONE)"
""".strip()


@pytest.mark.slow
@pytest.mark.integration
class TestDockerEndState:
    """End-state tests: verify _build_docker_cmd flags produce correct container state.

    Container 1 (env_results) batches 14 checks into one container.
    Container 2 (workspace_results) verifies workspace docker cp.
    """

    @pytest.fixture(autouse=True)
    def _require_docker(self):
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

    @pytest.fixture(scope="class")
    def env_results(self, tmp_path_factory) -> dict[str, str]:
        """Single container checking all env vars, git config, and credentials."""
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

        work_dir = tmp_path_factory.mktemp("env-test")
        (work_dir / "placeholder").write_text("x")

        env = {
            "ANTHROPIC_API_KEY": "sk-test-integration-123",
            "CLAUDE_CODE_OAUTH_TOKEN": "oauth-integration-token",
            "GEMINI_API_KEY": "gemini-should-not-appear",
            "GOOGLE_API_KEY": "google-should-not-appear",
            "POLECAT_SESSION_TYPE": "crew",
            "POLECAT_CREW_NAME": "integration-test",
            "MY_SECRET": "should-not-leak",
            "DATABASE_URL": "postgres://should-not-leak",
            "CUSTODIET_GATE_MODE": "block",
            "HANDOVER_GATE_MODE": "warn",
            "QA_GATE_MODE": "warn",
            "CUSTODIET_TOOL_CALL_THRESHOLD": "50",
            "AOPS_SESSIONS": "/tmp/test-sessions",
            "AOPS_CUSTOM_VAR": "custom-value",
            "GIT_AUTHOR_NAME": "integration-bot",
            "GIT_AUTHOR_EMAIL": "integration@test.example",
            "GH_TOKEN": "ghp_integration_test_token",
            "PKB_MCP_URL": "http://host:8026/mcp",
        }

        tmp_files: list[Path] = []
        # _build_docker_cmd reads TZ from os.environ — patch it so the container
        # gets a known timezone regardless of the host's POLECAT_DOCKER_IMAGE value.
        with patch.dict(os.environ, {"TZ": "US/Eastern"}):
            docker_cmd = _build_docker_cmd(
                cli_tool="claude",
                work_dir=work_dir,
                env=env,
                agent_cmd=["bash", "-c", _ENV_SCRIPT],
                is_interactive=False,
                tmp_files=tmp_files,
            )
        patched_cmd = docker_cmd

        try:
            result = _run_docker_container(
                patched_cmd,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"Container exited {result.returncode}:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            return _parse_kv_output(result.stdout)
        finally:
            for f in tmp_files:
                if f.is_dir():
                    shutil.rmtree(f, ignore_errors=True)
                else:
                    f.unlink(missing_ok=True)

    @pytest.fixture(scope="class")
    def workspace_results(self, tmp_path_factory) -> dict[str, str]:
        """Container verifying workspace files arrived via docker cp."""
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

        work_dir = tmp_path_factory.mktemp("ws-test")
        (work_dir / "test-file.txt").write_text("hello-workspace")
        (work_dir / "subdir").mkdir()
        (work_dir / "subdir" / "nested.txt").write_text("nested-content")

        script = (
            'echo "WS_FILE_COUNT=$(find /workspace -type f | wc -l)"\n'
            'echo "WS_CONTENT=$(cat /workspace/test-file.txt 2>/dev/null || echo MISSING)"\n'
            'echo "WS_NESTED=$(cat /workspace/subdir/nested.txt 2>/dev/null || echo MISSING)"\n'
            'echo "WS_CWD=$(pwd)"\n'
        )

        tmp_files: list[Path] = []
        docker_cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=work_dir,
            env={},
            agent_cmd=["bash", "-c", script],
            is_interactive=False,
            tmp_files=tmp_files,
        )

        try:
            result = _run_docker_container(
                docker_cmd,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"Container exited {result.returncode}:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            return _parse_kv_output(result.stdout)
        finally:
            for f in tmp_files:
                if f.is_dir():
                    shutil.rmtree(f, ignore_errors=True)
                else:
                    f.unlink(missing_ok=True)

    # --- Group 1: Environment variable forwarding ---

    def test_anthropic_api_key_reaches_container(self, env_results):
        """ANTHROPIC_API_KEY is available inside the container."""
        assert env_results["ANTHROPIC_API_KEY"] == "sk-test-integration-123"

    def test_oauth_token_reaches_container(self, env_results):
        """CLAUDE_CODE_OAUTH_TOKEN is available inside the container."""
        assert env_results["CLAUDE_CODE_OAUTH_TOKEN"] == "oauth-integration-token"

    def test_gemini_keys_blocked_from_container(self, env_results):
        """GEMINI_API_KEY and GOOGLE_API_KEY must NOT reach the container."""
        assert env_results.get("GEMINI_API_KEY", "") == ""
        assert env_results.get("GOOGLE_API_KEY", "") == ""

    def test_polecat_prefixed_env_reaches_container(self, env_results):
        """POLECAT_* env vars are forwarded."""
        assert env_results["POLECAT_SESSION_TYPE"] == "crew"
        assert env_results["POLECAT_CREW_NAME"] == "integration-test"

    def test_arbitrary_env_blocked_from_container(self, env_results):
        """Arbitrary env vars (MY_SECRET, DATABASE_URL) must NOT leak."""
        assert env_results.get("MY_SECRET", "") == ""
        assert env_results.get("DATABASE_URL", "") == ""

    def test_gate_mode_vars_reach_container(self, env_results):
        """Gate mode variables reach the container for hook enforcement."""
        assert env_results["CUSTODIET_GATE_MODE"] == "block"
        assert env_results["HANDOVER_GATE_MODE"] == "warn"
        assert env_results["QA_GATE_MODE"] == "warn"
        assert env_results["CUSTODIET_TOOL_CALL_THRESHOLD"] == "50"

    def test_aops_prefixed_env_reaches_container(self, env_results):
        """AOPS_* env vars are forwarded."""
        assert env_results["AOPS_SESSIONS"] == "/tmp/test-sessions"
        assert env_results["AOPS_CUSTOM_VAR"] == "custom-value"

    def test_timezone_reaches_container(self, env_results):
        """TZ is set correctly inside the container."""
        assert env_results["TZ_VAL"] == "US/Eastern"

    def test_pkb_url_reaches_container(self, env_results):
        """PKB_MCP_URL is forwarded to the container."""
        assert env_results["PKB_MCP_URL"] == "http://host:8026/mcp"

    # --- Group 2: Git identity and credentials ---

    def test_git_identity_configured_in_container(self, env_results):
        """Git author/committer identity is set inside the container."""
        assert env_results["GIT_AUTHOR_NAME"] == "integration-bot"
        assert env_results["GIT_AUTHOR_EMAIL"] == "integration@test.example"
        assert env_results["GIT_COMMITTER_NAME"] == "integration-bot"
        assert env_results["GIT_COMMITTER_EMAIL"] == "integration@test.example"
        # Also verify git config was applied by the entrypoint
        assert env_results["GIT_CONFIG_NAME"] == "integration-bot"
        assert env_results["GIT_CONFIG_EMAIL"] == "integration@test.example"

    def test_ssh_isolation_enforced_in_container(self, env_results):
        """SSH is fully blocked inside the container."""
        assert env_results["SSH_AUTH_SOCK_VAL"] == ""
        assert env_results["GIT_SSH_COMMAND"] == "false"
        assert env_results["GIT_TERMINAL_PROMPT"] == "0"

    def test_git_credential_helper_resolves_token(self, env_results):
        """GH_TOKEN reaches the container and the credential helper resolves it."""
        assert env_results["GH_TOKEN_VAL"] == "ghp_integration_test_token"
        assert env_results["AOPS_BOT_GH_TOKEN"] == "ghp_integration_test_token"
        assert "password=ghp_integration_test_token" in env_results.get("CRED_PASSWORD", "")

    # --- Group 3: Container configuration ---

    def test_runs_as_current_uid(self, env_results):
        """Container runs as the current user's UID/GID."""
        assert env_results["CONTAINER_UID"] == str(os.getuid())
        assert env_results["CONTAINER_GID"] == str(os.getgid())

    # --- Group 4: Workspace ---

    def test_workspace_files_present(self, workspace_results):
        """Workspace files arrive in /workspace via docker cp."""
        assert workspace_results["WS_CONTENT"] == "hello-workspace"

    def test_workspace_nested_files_present(self, workspace_results):
        """Nested workspace files are preserved."""
        assert workspace_results["WS_NESTED"] == "nested-content"

    def test_workspace_cwd_is_workspace(self, workspace_results):
        """Working directory inside the container is /workspace."""
        assert workspace_results["WS_CWD"] == "/workspace"

    def test_workspace_has_files(self, workspace_results):
        """Workspace is not empty (file count > 0)."""
        count = int(workspace_results["WS_FILE_COUNT"])
        assert count >= 2, f"Expected at least 2 files in /workspace, got {count}"


# ---------------------------------------------------------------------------
# Container 3: Docker socket mount (conditional)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.integration
class TestDockerSocketEndState:
    """Verify Docker socket is accessible from inside the container (DooD)."""

    @pytest.fixture(autouse=True)
    def _require_docker_and_socket(self):
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")
        if not Path("/var/run/docker.sock").exists():
            pytest.skip("Docker socket not present")

    def test_docker_accessible_from_container(self, tmp_path):
        """docker info succeeds inside the container when socket is mounted."""
        env = {"DOCKER_HOST": "unix:///var/run/docker.sock"}
        work_dir = tmp_path / "socket-test"
        work_dir.mkdir()
        (work_dir / "placeholder").write_text("x")

        docker_cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=work_dir,
            env=env,
            agent_cmd=[
                "bash",
                "-c",
                "docker info > /dev/null 2>&1 && echo DOCKER_OK=true || echo DOCKER_OK=false",
            ],
            is_interactive=False,
        )

        result = _run_docker_container(
            docker_cmd,
            capture_output=True,
            text=True,
        )
        parsed = _parse_kv_output(result.stdout)
        assert parsed.get("DOCKER_OK") == "true", (
            f"docker info failed inside container:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
