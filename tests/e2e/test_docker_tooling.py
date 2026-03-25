"""Tests for Docker container tooling (Node.js, Rust).

Verifies that Node.js and Rust (cargo) are correctly installed and
available on PATH inside the aops-crew Docker image.
"""

import pytest


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.xdist_group("gemini-docker")
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
