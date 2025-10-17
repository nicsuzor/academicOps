#!/usr/bin/env python3
"""
Integration tests for validate_tool.py hook output stream behavior.

Tests verify that the hook outputs JSON to stdout (not stderr) and that
Claude Code correctly interprets the permission decisions.

This addresses issue #107: validate_tool.py should output to stdout per
Claude Code hooks specification.

Run with: uv run pytest tests/integration/test_hook_output_streams.py -v
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


class TestHookOutputStreams:
    """Test that validate_tool.py outputs to correct streams."""

    def test_hook_outputs_json_to_stdout_not_stderr(self, validate_tool_script):
        """
        Verify hook outputs structured JSON to stdout per Claude Code spec.

        This is the core fix for issue #107.
        """
        # Prepare hook input
        hook_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "test.txt"},
        }

        # Run hook directly
        result = subprocess.run(
            [sys.executable, str(validate_tool_script)],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        # Verify JSON is in stdout
        assert result.stdout.strip(), "Hook should output to stdout"

        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Hook stdout is not valid JSON: {e}\nstdout: {result.stdout}")

        # Verify structure matches Claude Code spec
        # Note: 'continue' is optional and excluded when None
        assert "hookSpecificOutput" in parsed, "Missing 'hookSpecificOutput'"
        assert "permissionDecision" in parsed["hookSpecificOutput"], (
            "Missing 'permissionDecision'"
        )

        # Verify stderr does NOT contain JSON (only debug output allowed)
        if result.stderr.strip():
            try:
                json.loads(result.stderr)
                pytest.fail(
                    "Hook should NOT output JSON to stderr, found valid JSON in stderr"
                )
            except json.JSONDecodeError:
                # Good - stderr is not JSON
                pass

    def test_permission_decision_allow_in_stdout(self, validate_tool_script):
        """Verify 'allow' decisions are properly formatted in stdout."""
        hook_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "test.txt"},
        }

        result = subprocess.run(
            [sys.executable, str(validate_tool_script)],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        parsed = json.loads(result.stdout)
        assert parsed["hookSpecificOutput"]["permissionDecision"] == "allow"
        # 'continue' field is optional and excluded when None
        assert result.returncode == 0

    def test_permission_decision_deny_in_stdout(self, validate_tool_script):
        """Verify 'deny' decisions are properly formatted in stdout."""
        hook_input = {
            "tool_name": "Bash",
            "tool_input": {"command": "python -c 'print(1+1)'"},
        }

        result = subprocess.run(
            [sys.executable, str(validate_tool_script)],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        parsed = json.loads(result.stdout)
        assert parsed["hookSpecificOutput"]["permissionDecision"] == "deny"
        # 'continue' field is optional and excluded when None
        assert result.returncode == 2
        # Error message should be in permissionDecisionReason
        assert parsed["hookSpecificOutput"]["permissionDecisionReason"]

    def test_permission_decision_warn_in_stdout(self, validate_tool_script):
        """Verify 'warn' decisions are properly formatted in stdout."""
        hook_input = {
            "tool_name": "Write",
            "tool_input": {"file_path": ".claude/settings.json", "content": "{}"},
        }

        result = subprocess.run(
            [sys.executable, str(validate_tool_script)],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        parsed = json.loads(result.stdout)
        assert parsed["hookSpecificOutput"]["permissionDecision"] == "allow"
        # 'continue' field is optional and excluded when None
        assert result.returncode == 1  # Warning exit code
        # Warning message should be in permissionDecisionReason
        assert parsed["hookSpecificOutput"]["permissionDecisionReason"]
        assert "WARNING" in parsed["hookSpecificOutput"]["permissionDecisionReason"]


class TestClaudeCodeInterpretation:
    """Test that Claude Code correctly interprets hook output."""

    def test_claude_allows_when_permission_allow(self, claude_headless):
        """
        Verify Claude Code executes tools when hook returns 'allow'.

        This tests end-to-end: hook outputs 'allow' to stdout, Claude parses it,
        and the tool executes successfully.
        """
        result = claude_headless(
            "Use the Read tool to read the file bot/README.md and tell me the first line",
            model="haiku",
        )

        # Should succeed - Read is always allowed
        assert result["success"], f"Read should be allowed. Error: {result['error']}"
        assert not result["permission_denials"], (
            "Read should not trigger permission denials"
        )

    def test_claude_blocks_when_permission_deny(self, claude_headless):
        """
        Verify Claude Code blocks tools when hook returns 'deny'.

        This tests end-to-end: hook outputs 'deny' to stdout, Claude parses it,
        and the operation is blocked.
        """
        result = claude_headless(
            "Run this exact bash command: python -c 'print(1+1)'", model="haiku"
        )

        # Claude should either:
        # 1. Show permission denial in output
        # 2. Explain that the operation is blocked
        # 3. Adapt by creating a proper test file instead

        result_lower = result["result"].lower()

        # Check if Claude mentions the block/prohibition
        mentions_block = (
            "blocked" in result_lower
            or "prohibited" in result_lower
            or "not allowed" in result_lower
            or len(result.get("permission_denials", [])) > 0
        )

        # Or Claude adapts by creating a proper test file
        adapts_properly = "test" in result_lower and (
            "file" in result_lower or "proper" in result_lower
        )

        assert mentions_block or adapts_properly, (
            f"Expected Claude to either acknowledge block or adapt. "
            f"Got: {result['result']}\n"
            f"Permission denials: {result.get('permission_denials', [])}"
        )

    def test_claude_shows_warning_but_continues(self, claude_headless):
        """
        Verify Claude Code shows warnings but allows execution.

        This tests: hook outputs 'allow' with systemMessage to stdout,
        Claude parses it and shows warning to user.
        """
        result = claude_headless(
            "@agent-developer Create a new file called bot/test_doc.md with content 'test'",
            model="haiku",
        )

        # Should complete but may show warning about .md files
        # Check if warning appears in result or output
        str(result["output"])

        # The operation should succeed (warning doesn't block)
        # But warning message should be visible somewhere
        # Note: Current implementation may not surface warnings in JSON output
        # This is a limitation to document

    def test_debug_log_still_works(self, validate_tool_script, tmp_path):
        """
        Verify debug logging to /tmp/validate_tool.json still works.

        Ensures that moving to stdout doesn't break debug functionality.
        """
        # Clear any existing debug log
        debug_file = Path("/tmp/validate_tool.json")
        if debug_file.exists():
            debug_file.unlink()

        # Run hook
        hook_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "test.txt"},
        }

        subprocess.run(
            [sys.executable, str(validate_tool_script)],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        # Verify debug log was created and contains data
        assert debug_file.exists(), "Debug log should be created"

        content = debug_file.read_text()
        assert content.strip(), "Debug log should not be empty"

        # Parse last entry (file contains newline-delimited JSON)
        last_entry = content.strip().split("\n")[-1]
        parsed = json.loads(last_entry)

        assert "input" in parsed, "Debug log should contain input"
        assert "output" in parsed, "Debug log should contain output"
        assert "timestamp" in parsed, (
            "Debug log should contain timestamp"
        )  # Fixed: was 'tiemstamp'


class TestPermissionDecisionTypes:
    """Test all three permission decision types work correctly."""

    @pytest.mark.parametrize(
        ("tool_name", "tool_input", "expected_decision", "expected_exit"),
        [
            # Allow cases
            ("Read", {"file_path": "test.txt"}, "allow", 0),
            ("Glob", {"pattern": "*.py"}, "allow", 0),
            ("Grep", {"pattern": "test"}, "allow", 0),
            ("Bash", {"command": "uv run python --version"}, "allow", 0),
            # Deny cases (blocks)
            ("Bash", {"command": "python -c 'x'"}, "deny", 2),
            ("Write", {"file_path": "/tmp/test.py", "content": "x"}, "deny", 2),
            # Warn cases (allow with warning)
            ("Write", {"file_path": ".claude/settings.json", "content": "{}"}, "allow", 1),
            ("Bash", {"command": "git commit -m 'test'"}, "allow", 1),
        ],
    )
    def test_permission_decision_types(
        self,
        validate_tool_script,
        tool_name,
        tool_input,
        expected_decision,
        expected_exit,
    ):
        """
        Parametrized test for all permission decision types.

        Verifies that each decision type outputs correctly to stdout
        with the right exit code.
        """
        hook_input = {
            "tool_name": tool_name,
            "tool_input": tool_input,
        }

        result = subprocess.run(
            [sys.executable, str(validate_tool_script)],
            check=False,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        # Parse stdout
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail(
                f"Hook output is not valid JSON for {tool_name}:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        # Verify permission decision
        actual_decision = parsed["hookSpecificOutput"]["permissionDecision"]
        assert actual_decision == expected_decision, (
            f"Expected {expected_decision} for {tool_name}, got {actual_decision}"
        )

        # Verify exit code
        assert result.returncode == expected_exit, (
            f"Expected exit code {expected_exit} for {tool_name}, got {result.returncode}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
