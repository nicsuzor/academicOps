#!/usr/bin/env python3
"""
Unit tests for validate_tool.py PreToolUse hook.

Tests verify:
1. JSON output goes to stdout (not stderr)
2. Permission decisions work correctly (allow/deny/ask)
3. Exit codes match Claude Code specification
4. Hook respects validation rules
"""

import contextlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the hook script
HOOK_SCRIPT = Path(__file__).parent.parent / "scripts" / "validate_tool.py"


def run_hook(tool_name: str, tool_input: dict) -> dict:
    """
    Run the validate_tool.py hook with given input and capture output.

    Returns:
        dict with keys: stdout, stderr, exit_code, parsed_json
    """
    hook_input = {
        "tool_name": tool_name,
        "tool_input": tool_input,
    }

    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        check=False,
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
    )

    # Try to parse JSON from stdout
    parsed_json = None
    if result.stdout.strip():
        with contextlib.suppress(json.JSONDecodeError):
            parsed_json = json.loads(result.stdout)

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
        "parsed_json": parsed_json,
    }


class TestHookOutputStreams:
    """Test that hook outputs to correct streams per Claude Code spec."""

    def test_json_output_goes_to_stdout_not_stderr(self):
        """Verify JSON response is written to stdout, not stderr."""
        result = run_hook("Read", {"file_path": "test.txt"})

        # JSON should be in stdout
        assert result["parsed_json"] is not None, (
            "Hook should output valid JSON to stdout"
        )

        # stderr should be empty (or only contain debug messages)
        # Note: We allow stderr to have content from logging, but no JSON
        if result["stderr"]:
            with pytest.raises(json.JSONDecodeError):
                json.loads(result["stderr"])

    def test_allowed_operation_returns_exit_0(self):
        """Verify allowed operations return exit code 0."""
        result = run_hook("Read", {"file_path": "test.txt"})

        assert result["exit_code"] == 0
        assert (
            result["parsed_json"]["hookSpecificOutput"]["permissionDecision"] == "allow"
        )


class TestPermissionDecisions:
    """Test different permission decision types."""

    def test_allow_decision(self):
        """Test 'allow' permission decision."""
        # Read operations should always be allowed
        result = run_hook("Read", {"file_path": "test.txt"})

        json_output = result["parsed_json"]
        assert json_output["hookSpecificOutput"]["permissionDecision"] == "allow"
        # permissionDecisionReason is None, so it should be excluded from output
        assert "permissionDecisionReason" not in json_output["hookSpecificOutput"]

    def test_warn_decision(self):
        """Test 'warn' permission decision (allow with warning)."""
        # Git commits trigger warnings for non-code-review agents
        result = run_hook("Bash", {"command": "git commit -m 'test'"})

        json_output = result["parsed_json"]
        assert json_output["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert json_output["hookSpecificOutput"]["permissionDecisionReason"] is not None
        assert (
            "code-review"
            in json_output["hookSpecificOutput"]["permissionDecisionReason"].lower()
        )
        assert result["exit_code"] == 1

    def test_deny_decision(self):
        """Test 'deny' permission decision (block)."""
        # Python inline execution should be blocked
        result = run_hook("Bash", {"command": "python -c 'print(1+1)'"})

        json_output = result["parsed_json"]
        assert json_output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert json_output["hookSpecificOutput"]["permissionDecisionReason"] is not None
        assert result["exit_code"] == 2


class TestValidationRules:
    """Test specific validation rules."""

    def test_uv_run_requirement(self):
        """Test that Python commands require 'uv run' prefix."""
        # Without uv run - should block
        result = run_hook("Bash", {"command": "python script.py"})
        assert (
            result["parsed_json"]["hookSpecificOutput"]["permissionDecision"] == "deny"
        )
        # For deny decisions, message is in permissionDecisionReason
        assert (
            "uv run"
            in result["parsed_json"]["hookSpecificOutput"]["permissionDecisionReason"]
        )

        # With uv run - should allow
        result = run_hook("Bash", {"command": "uv run python script.py"})
        assert (
            result["parsed_json"]["hookSpecificOutput"]["permissionDecision"] == "allow"
        )

    def test_tmp_file_prohibition(self):
        """Test that /tmp test files are blocked."""
        result = run_hook(
            "Write", {"file_path": "/tmp/test_something.py", "content": "test"}
        )

        json_output = result["parsed_json"]
        assert json_output["hookSpecificOutput"]["permissionDecision"] == "deny"
        # For deny decisions, message is in permissionDecisionReason
        reason = json_output["hookSpecificOutput"]["permissionDecisionReason"]
        assert "/tmp" in reason
        assert "axiom #5" in reason.lower()

    def test_inline_python_prohibition(self):
        """Test that python -c commands are blocked."""
        result = run_hook("Bash", {"command": "python -c 'print(123)'"})

        json_output = result["parsed_json"]
        assert json_output["hookSpecificOutput"]["permissionDecision"] == "deny"
        # For deny decisions, message is in permissionDecisionReason
        assert (
            "inline python"
            in json_output["hookSpecificOutput"]["permissionDecisionReason"].lower()
        )

    def test_git_commit_warning(self):
        """Test that git commits trigger warnings (for non-code-review agents)."""
        result = run_hook("Bash", {"command": "git commit -m 'test commit'"})

        json_output = result["parsed_json"]
        # Should warn (allow but with message)
        assert json_output["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert json_output["hookSpecificOutput"]["permissionDecisionReason"] is not None
        assert (
            "code-review"
            in json_output["hookSpecificOutput"]["permissionDecisionReason"].lower()
        )


class TestHookStructure:
    """Test the overall hook output structure matches Claude Code spec."""

    def test_required_fields_present(self):
        """Verify all required fields are in hook response."""
        result = run_hook("Read", {"file_path": "test.txt"})
        json_output = result["parsed_json"]

        # Top-level field (required)
        assert "hookSpecificOutput" in json_output

        # Hook-specific fields (required)
        hook_output = json_output["hookSpecificOutput"]
        assert "hookEventName" in hook_output
        assert "permissionDecision" in hook_output
        # permissionDecisionReason is optional and excluded when None

        assert hook_output["hookEventName"] == "PreToolUse"

    def test_permission_decision_values(self):
        """Verify permissionDecision uses valid values."""
        valid_decisions = {"allow", "deny", "ask"}

        # Test a few different operations
        test_cases = [
            ("Read", {"file_path": "test.txt"}),
            ("Write", {"file_path": "/tmp/test.py", "content": "x"}),
            ("Bash", {"command": "python -c 'x'"}),
        ]

        for tool_name, tool_input in test_cases:
            result = run_hook(tool_name, tool_input)
            decision = result["parsed_json"]["hookSpecificOutput"]["permissionDecision"]
            assert decision in valid_decisions, (
                f"Invalid decision '{decision}' for {tool_name}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
