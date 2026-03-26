"""Tests for Docker container tooling (Node.js, Rust, git credentials).

Verifies that Node.js, Rust (cargo), and git credential helpers are correctly
installed and available on PATH inside the aops-crew Docker image.

These tests run `docker run` directly — no LLM invocation needed.
"""

import subprocess

import pytest

from tests.conftest import _docker_available


@pytest.mark.slow
@pytest.mark.integration
class TestDockerTooling:
    """Node.js, Rust, and git credentials are available in the Docker environment."""

    @pytest.fixture(autouse=True)
    def _require_docker(self):
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

    def _docker_run(self, *cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a command inside the aops-crew Docker image."""
        return subprocess.run(
            ["docker", "run", "--rm", "aops-crew", *cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def test_node_available(self):
        """Verify Node.js and npm are on PATH."""
        result = self._docker_run("node", "--version")
        assert result.returncode == 0, f"node --version failed: {result.stderr}"
        assert result.stdout.strip().startswith("v"), f"Unexpected node output: {result.stdout}"

        result = self._docker_run("npm", "--version")
        assert result.returncode == 0, f"npm --version failed: {result.stderr}"

    def test_rust_available(self):
        """Verify Rust (cargo/rustc) is on PATH."""
        result = self._docker_run("cargo", "--version")
        assert result.returncode == 0, f"cargo --version failed: {result.stderr}"
        assert "cargo" in result.stdout.lower(), f"Unexpected cargo output: {result.stdout}"

        result = self._docker_run("rustc", "--version")
        assert result.returncode == 0, f"rustc --version failed: {result.stderr}"

    def test_git_available(self):
        """Verify git is installed in the Docker image."""
        result = self._docker_run("git", "--version")
        assert result.returncode == 0, f"git --version failed: {result.stderr}"

    def test_python_available(self):
        """Verify Python 3 is on PATH."""
        result = self._docker_run("python3", "--version")
        assert result.returncode == 0, f"python3 --version failed: {result.stderr}"
        assert "Python 3" in result.stdout, f"Unexpected python output: {result.stdout}"
