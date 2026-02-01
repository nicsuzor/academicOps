"""Integration tests for router.py subprocess invocation.

Tests verify that the router:
- Executes correctly as a subprocess (how it's invoked by CLI tools)
- Outputs correct JSON format for Claude Code
- Outputs correct JSON format for Gemini CLI
- Correctly maps Gemini events to internal events
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
ROUTER_PATH = AOPS_CORE_DIR / "hooks" / "router.py"


def run_router_claude(
    input_data: dict,
    timeout: int = 30,
) -> tuple[dict, str]:
    """Run router in Claude Code mode (no event arg).

    Args:
        input_data: JSON input to send to router
        timeout: Subprocess timeout in seconds

    Returns:
        Tuple of (parsed output dict, stderr string)
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AOPS_CORE_DIR)

    result = subprocess.run(
        [sys.executable, str(ROUTER_PATH), "--client", "claude"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(AOPS_CORE_DIR),  # Run from aops-core, not hooks/
    )

    output = {}
    if result.stdout.strip():
        output = json.loads(result.stdout)

    return output, result.stderr


def run_router_gemini(
    input_data: dict,
    event: str,
    timeout: int = 30,
) -> tuple[dict, str]:
    """Run router in Gemini CLI mode (with event arg).

    Args:
        input_data: JSON input to send to router
        event: Gemini event name (BeforeTool, AfterTool, etc.)
        timeout: Subprocess timeout in seconds

    Returns:
        Tuple of (parsed output dict, stderr string)
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AOPS_CORE_DIR)

    result = subprocess.run(
        [sys.executable, str(ROUTER_PATH), "--client", "gemini", event],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(AOPS_CORE_DIR),  # Run from aops-core, not hooks/
    )

    output = {}
    if result.stdout.strip():
        output = json.loads(result.stdout)

    return output, result.stderr


class TestRouterClaudeFormat:
    """Tests for Claude Code output format."""

    def test_session_start_output_format(self) -> None:
        """SessionStart returns correct Claude format with hookSpecificOutput."""
        input_data = {
            "hook_event_name": "SessionStart",
            "session_id": "test-session-123",
        }

        output, stderr = run_router_claude(input_data)

        # Claude SessionStart should have hookSpecificOutput structure
        assert "hookSpecificOutput" in output, f"Missing hookSpecificOutput. Output: {output}"
        hso = output["hookSpecificOutput"]
        assert hso["hookEventName"] == "SessionStart"
        assert "permissionDecision" in hso

    def test_pretooluse_output_format(self) -> None:
        """PreToolUse returns correct Claude format with hookSpecificOutput."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session-123",
            "tool_name": "Read",
            "tool_input": {"file_path": "/etc/hostname"},
        }

        output, stderr = run_router_claude(input_data)

        # Debug output for failure case
        if not output:
            pytest.fail(
                f"Empty output from router. stderr: {stderr}"
            )

        # Claude PreToolUse should have hookSpecificOutput structure
        assert "hookSpecificOutput" in output, f"Missing hookSpecificOutput. Output: {output}, stderr: {stderr}"
        hso = output["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        # Should have permissionDecision (allow or deny)
        assert "permissionDecision" in hso
        assert hso["permissionDecision"] in ["allow", "deny", "ask"]

    def test_stop_output_format(self) -> None:
        """Stop returns correct Claude format with top-level fields."""
        input_data = {
            "hook_event_name": "Stop",
            "session_id": "test-session-123",
        }

        output, stderr = run_router_claude(input_data)

        # Claude Stop uses different format - top-level decision
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["approve", "block"]


class TestRouterGeminiFormat:
    """Tests for Gemini CLI output format."""

    def test_session_start_output_format(self) -> None:
        """SessionStart returns correct Gemini format."""
        input_data = {}

        output, stderr = run_router_gemini(input_data, "SessionStart")

        # Gemini format has top-level decision
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["allow", "deny"]

    def test_before_tool_output_format(self) -> None:
        """BeforeTool returns correct Gemini format with deny for unhydrated."""
        input_data = {
            "tool_name": "shell",
            "tool_input": {"command": "ls"},
        }

        # Force block mode for hydration gate
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("HYDRATION_MODE", "block")
            # We need to set this in the actual OS environ because run_router_gemini copies it
            os.environ["HYDRATION_MODE"] = "block"
            try:
                output, stderr = run_router_gemini(input_data, "BeforeTool")
            finally:
                del os.environ["HYDRATION_MODE"]

        # Gemini format has top-level decision
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["allow", "deny"]
        # Should be denied due to hydration gate
        assert output["decision"] == "deny", f"Expected deny due to hydration gate. Output: {output}, Stderr: {stderr}"
        assert "reason" in output, "Should have reason for deny"

    def test_after_tool_output_format(self) -> None:
        """AfterTool returns correct Gemini format."""
        input_data = {
            "tool_name": "shell",
            "tool_input": {"command": "ls"},
            "tool_output": "file1 file2",
        }

        output, stderr = run_router_gemini(input_data, "AfterTool")

        # Gemini format has top-level decision
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["allow", "deny"]

    def test_session_end_output_format(self) -> None:
        """SessionEnd returns correct Gemini format."""
        input_data = {}

        output, stderr = run_router_gemini(input_data, "SessionEnd")

        # Gemini format has top-level decision
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["allow", "deny"]


class TestRouterEventMapping:
    """Tests for Gemini to Claude event mapping."""

    def test_before_tool_maps_to_pretooluse(self) -> None:
        """Gemini BeforeTool maps to internal PreToolUse."""
        input_data = {
            "tool_name": "read_file",
            "tool_input": {"path": "test.txt"},
        }

        # Force block mode for hydration gate
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("HYDRATION_MODE", "block")
            os.environ["HYDRATION_MODE"] = "block"
            try:
                output, stderr = run_router_gemini(input_data, "BeforeTool")
            finally:
                del os.environ["HYDRATION_MODE"]

        # The gate messages should reference PreToolUse behavior
        # Hydration gate blocks read operations on unhydrated sessions
        assert output["decision"] == "deny", f"Expected deny. Output: {output}, Stderr: {stderr}"

    def test_session_end_maps_to_stop(self) -> None:
        """Gemini SessionEnd maps to internal Stop event."""
        input_data = {}

        output, stderr = run_router_gemini(input_data, "SessionEnd")

        # Stop gates run for SessionEnd
        assert "decision" in output
