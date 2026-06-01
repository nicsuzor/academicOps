"""Subprocess integration — JSON format per platform.

Tests that the router executes correctly as a subprocess and produces
correct JSON for Claude Code and Gemini CLI.
"""

import uuid

import pytest

from tests.hooks.gate_helpers import run_router_claude, run_router_gemini


class TestRouterClaudeFormat:
    """Claude Code output format from subprocess invocation."""

    def test_session_start_output_format(self, monkeypatch) -> None:
        # SessionStart emits a systemMessage for polecat-container sessions.
        # Establish that explicitly via the resolved dispatcher signal rather
        # than depending on ambient container env (aops-b368109a): the harness
        # inherits os.environ, so set the signal it needs and scrub the removed
        # label so the result is independent of which launcher created the host.
        monkeypatch.setenv("AOPS_POLECAT_CONTAINER", "1")
        monkeypatch.delenv("POLECAT_SESSION_TYPE", raising=False)
        input_data = {
            "hook_event_name": "SessionStart",
            "session_id": "test-session-123",
        }
        output, stderr = run_router_claude(input_data)
        assert "hookSpecificOutput" not in output, (
            f"SessionStart emitted hookSpecificOutput — Claude Code will reject. Output: {output}"
        )
        assert "systemMessage" in output

    def test_pretooluse_output_format(self) -> None:
        input_data = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session-123",
            "tool_name": "Read",
            "tool_input": {"file_path": "/etc/hostname"},
        }
        output, stderr = run_router_claude(input_data)
        if not output:
            pytest.fail(f"Empty output from router. stderr: {stderr}")
        assert "hookSpecificOutput" in output, (
            f"Missing hookSpecificOutput. Output: {output}, stderr: {stderr}"
        )
        hso = output["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert "permissionDecision" in hso
        assert hso["permissionDecision"] in ["allow", "deny", "ask"]

    def test_stop_output_format(self) -> None:
        input_data = {
            "hook_event_name": "Stop",
            "session_id": "test-session-123",
        }
        output, stderr = run_router_claude(input_data)
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["approve", "block"]

    def test_session_end_output_format(self) -> None:
        input_data = {
            "hook_event_name": "SessionEnd",
            "session_id": f"test-{uuid.uuid4()}",
        }
        output, stderr = run_router_claude(input_data)
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["approve", "block"]


class TestRouterGeminiFormat:
    """Gemini CLI output format from subprocess invocation."""

    def test_session_start_output_format(self) -> None:
        input_data = {}
        output, stderr = run_router_gemini(input_data, "SessionStart")
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["allow", "deny"]

    def test_before_tool_output_format(self) -> None:
        input_data = {
            "tool_name": "shell",
            "tool_input": {"command": "ls"},
            "session_id": f"test-{uuid.uuid4()}",
        }
        output, stderr = run_router_gemini(input_data, "BeforeTool")
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["allow", "deny"]
        assert output["decision"] == "allow", f"Expected allow. Output: {output}, Stderr: {stderr}"

    def test_after_tool_output_format(self) -> None:
        input_data = {
            "tool_name": "shell",
            "tool_input": {"command": "ls"},
            "tool_output": "file1 file2",
        }
        output, stderr = run_router_gemini(input_data, "AfterTool")
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["allow", "deny"]

    def test_session_end_output_format(self) -> None:
        input_data = {}
        output, stderr = run_router_gemini(input_data, "SessionEnd")
        assert "decision" in output, f"Missing decision. Output: {output}"
        assert output["decision"] in ["allow", "deny"]


class TestRouterEventMapping:
    """Gemini to Claude event mapping."""

    def test_before_tool_maps_to_pretooluse(self) -> None:
        input_data = {
            "tool_name": "read_file",
            "tool_input": {"path": "test.txt"},
            "session_id": f"test-{uuid.uuid4()}",
        }
        output, stderr = run_router_gemini(input_data, "BeforeTool")
        assert output["decision"] == "allow", f"Expected allow. Output: {output}, Stderr: {stderr}"

    def test_session_end_maps_to_stop(self) -> None:
        input_data = {}
        output, stderr = run_router_gemini(input_data, "SessionEnd")
        assert "decision" in output


class TestRouterStdoutIntegrity:
    """Stdout from the router must be a single JSON object — no raw text leakage."""

    def test_router_subprocess_does_not_print_advisory_outside_json(self, tmp_path):
        payload = {
            "hook_event_name": "Stop",
            "session_id": "test-stop-envelope-d10e7db6",
            "transcript_path": str(tmp_path / "transcript.jsonl"),
            "cwd": str(tmp_path),
        }
        (tmp_path / "transcript.jsonl").write_text("")

        # run_router_claude raises JSONDecodeError if stdout is not clean JSON
        run_router_claude(payload)
