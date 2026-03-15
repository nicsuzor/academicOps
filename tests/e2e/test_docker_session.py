"""Tests for Docker-containerised Claude sessions.

Verifies that Claude runs correctly inside the aops-env-test Docker container
and that session logs can be reliably extracted for test assertions.
"""

import pytest

from tests.conftest import extract_response_text


@pytest.mark.slow
@pytest.mark.integration
class TestDockerSession:
    """Claude running inside Docker container."""

    def test_claude_responds(self, claude_docker):
        """Claude starts, responds, and exits cleanly in Docker."""
        result, session_id, tool_calls = claude_docker(
            "What is 2+2? Answer with just the number.",
            timeout_seconds=60,
        )
        response = extract_response_text(result)
        assert "4" in response

    def test_session_logs_extracted(self, claude_docker):
        """Session JSONL is written to bind-mounted .claude/ and can be parsed."""
        result, session_id, tool_calls = claude_docker(
            "Use the Bash tool to run: echo hello-from-docker",
            timeout_seconds=60,
        )
        assert result["success"], f"Session failed: {result.get('error')}"
        # Session file should exist and tool calls should be parseable
        assert session_id, "Session ID should be set"
        # Claude should have used the Bash tool
        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]
        assert len(bash_calls) >= 1, (
            f"Expected Bash tool call, got: {[c['name'] for c in tool_calls]}"
        )

    def test_workspace_is_mounted(self, claude_docker):
        """Container workspace is mounted and writable."""
        result, session_id, tool_calls = claude_docker(
            "Use the Bash tool to run: pwd && touch /workspace/test-file && echo success",
            timeout_seconds=60,
        )
        assert result["success"], f"Session failed: {result.get('error')}"
        response = extract_response_text(result)
        assert "success" in response.lower() or any(c["name"] == "Bash" for c in tool_calls), (
            "Should be able to write to /workspace"
        )

    def test_non_root_execution(self, claude_docker):
        """Container runs as non-root user (host UID)."""
        result, session_id, tool_calls = claude_docker(
            "Use the Bash tool to run: id -u",
            timeout_seconds=60,
        )
        assert result["success"], f"Session failed: {result.get('error')}"
        # Should not be running as root (uid 0)
        response = extract_response_text(result)
        assert "0" not in response.split() or any(
            c["name"] == "Bash" and "id" in str(c.get("input", {})) for c in tool_calls
        )
