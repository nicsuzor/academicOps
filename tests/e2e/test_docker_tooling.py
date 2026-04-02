"""Tests for Docker container tooling (Node.js, Rust, Docker socket).

Verifies that Node.js, Rust (cargo), and Docker are correctly installed and
available inside the aops-crew Docker image.
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.slow
@pytest.mark.integration
class TestDockerSocket:
    """Docker socket is accessible and images can be built inside the container."""

    @pytest.fixture(autouse=True)
    def require_crew_container(self):
        """Skip unless running inside an aops-crew container."""
        if os.environ.get("HOSTNAME") != "aops-crew":
            pytest.skip("Not running inside an aops-crew container")

    def test_docker_socket_accessible(self):
        """Docker socket exists and docker info succeeds."""
        assert Path("/var/run/docker.sock").is_socket(), (
            "Docker socket not found at /var/run/docker.sock — DinD not running?"
        )
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"docker info failed:\n{result.stderr}"

    def test_can_build_dockerfile(self):
        """docker build . succeeds from the workspace root."""
        repo_root = Path(__file__).parents[2]
        tag = "aops-crew-ci-test"
        try:
            result = subprocess.run(
                ["docker", "build", "-t", tag, str(repo_root)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            assert result.returncode == 0, (
                f"docker build failed:\n"
                f"STDOUT: {result.stdout[-3000:]}\n"
                f"STDERR: {result.stderr[-3000:]}"
            )
        finally:
            subprocess.run(["docker", "rmi", tag], capture_output=True)


@pytest.mark.slow
@pytest.mark.integration
class TestDockerTooling:
    """Node.js and Rust are available in the Docker environment."""

    @pytest.fixture(
        params=["claude-docker", "gemini-docker"],
    )
    def docker_headless(self, request, tmp_path):
        """Filter to Docker backends only."""
        import os
        from pathlib import Path

        from tests.conftest import (
            _docker_available,
            _gemini_cli_available,
            _make_failing_wrapper,
            _run_claude_docker_simple,
            _run_gemini_docker,
        )

        platform = request.param

        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

        if platform == "claude-docker":
            has_oauth = (Path.home() / ".claude" / ".credentials.json").exists()
            if not os.environ.get("ANTHROPIC_API_KEY") and not has_oauth:
                pytest.skip("No Claude auth for Docker")

            def _run(prompt, **kwargs):
                return _run_claude_docker_simple(prompt, tmp_path=tmp_path, **kwargs)

            return _make_failing_wrapper(_run), "claude-docker"

        elif platform == "gemini-docker":
            if not _gemini_cli_available():
                pytest.skip("gemini CLI not found in PATH")

            def _run(prompt, **kwargs):
                return _run_gemini_docker(prompt, **kwargs)

            return _make_failing_wrapper(_run), "gemini-docker"

    def test_node_available(self, docker_headless):
        """Verify Node.js and npm are on PATH."""
        runner, platform = docker_headless
        prompt = "Run 'node --version' and 'npm --version'. If both work, reply with 'NODE_OK'."
        result = runner(prompt)
        assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"
        output = str(result.get("output", "")) + str(result.get("stderr", ""))
        assert "NODE_OK" in output or "v22" in output, (
            f"[{platform}] Node.js not working in container. Output: {output}"
        )

    def test_rust_available(self, docker_headless):
        """Verify Rust (cargo/rustc) is on PATH."""
        runner, platform = docker_headless
        prompt = "Run 'cargo --version' and 'rustc --version'. If both work, reply with 'RUST_OK'."
        result = runner(prompt)
        assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"
        output = str(result.get("output", "")) + str(result.get("stderr", ""))
        assert "RUST_OK" in output or "cargo" in output.lower(), (
            f"[{platform}] Rust not working in container. Output: {output}"
        )
