"""Tests for Docker-containerised agent sessions.

Verifies that agents run correctly inside Docker containers and that
session logs can be reliably extracted for test assertions.

Uses cli_headless fixture which is parameterized across:
  claude, gemini, claude-docker, gemini-docker
"""

import pytest


@pytest.mark.slow
@pytest.mark.integration
class TestDockerAgentResponds:
    """Agent responds correctly across all Docker backends."""

    @pytest.fixture(
        params=["claude-docker", "gemini-docker"],
    )
    def docker_headless(self, request, tmp_path):
        """Filter to Docker backends only. No gemini_home needed — uses system gemini."""
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

    def test_agent_responds(self, docker_headless):
        """Agent starts, responds, and exits cleanly in Docker.

        This verifies that the basic agent infrastructure is working.
        """
        runner, platform = docker_headless
        result, session_id, tool_calls = runner("What is 2+2? Answer with just the number.")
        assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"

    def test_framework_binaries_on_path(self, docker_headless):
        """Verify that pkb and aops binaries are available on PATH inside Docker."""
        runner, platform = docker_headless
        # Ask the agent to check for the binaries using their tool-use capabilities (Bash/run_shell_command)
        prompt = "Run 'which pkb' and 'which aops' and 'pkb --version'. If they all work, reply with 'BINARIES_OK'."
        result, session_id, tool_calls = runner(prompt)
        assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"

        # Check output for confirmation
        output = str(result.get("output", "")) + str(result.get("stderr", ""))
        print(
            f"\n--- RAW AGENT RESPONSE [{platform}] ---\n{result.get('result', {}).get('response', output)}\n-----------------------------"
        )
        assert "BINARIES_OK" in output or "pkb" in output.lower(), (
            f"[{platform}] Framework binaries missing or not working in container. Output: {output}"
        )

    def test_extension_active_in_docker(self, docker_headless):
        """Verify that aops-core extension is active and recognized in Docker."""
        runner, platform = docker_headless
        # For Gemini, we can check if it's listed in 'gemini extensions list'
        # For Claude, we can check if its tools are available or if it's in verbose output
        prompt = "List your available extensions or tools. Reply with 'AOPS_ACTIVE' if you see 'aops-core' or pkb tools."
        result, session_id, tool_calls = runner(prompt)
        assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"

        output = str(result.get("output", "")) + str(result.get("stderr", ""))
        print(
            f"\n--- RAW AGENT RESPONSE [{platform}] ---\n{result.get('result', {}).get('response', output)}\n-----------------------------"
        )
        # For Gemini, the verbose output (from conftest) should show "Loading extension: aops-core"
        assert "aops-core" in output or "AOPS_ACTIVE" in output or "pkb" in output, (
            f"[{platform}] Extension not active in container. Output: {output}"
        )

    def test_agent_returns_structured_output(self, docker_headless):
        """Agent returns parseable structured output from Docker."""
        runner, platform = docker_headless
        result, session_id, tool_calls = runner("What is 2+2? Reply with just the number.")
        assert result["success"], f"[{platform}] Execution failed: {result.get('error')}"
        assert result["result"], f"[{platform}] Result should have parsed JSON/output"


@pytest.mark.slow
@pytest.mark.integration
class TestDockerSessionTracking:
    """Agent Docker session log extraction."""

    def test_session_logs_extracted(self, cli_headless):
        """Session logs are written and can be parsed."""
        runner, platform = cli_headless
        if "docker" not in platform:
            pytest.skip("Test requires docker backend")

        result, session_id, tool_calls = runner(
            "Use the Bash tool to run: echo hello-from-docker",
            timeout_seconds=60,
        )
        assert result["success"], f"Session failed: {result.get('error')}"
        assert session_id, "Session ID should be set"
        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]
        assert len(bash_calls) >= 1, (
            f"Expected Bash tool call, got: {[c['name'] for c in tool_calls]}"
        )
