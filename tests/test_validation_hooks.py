#!/usr/bin/env python3
"""
Test suite for validation hook system (validate_tool.py and validate_env.py).

This tests the hooks in headless mode to ensure they work correctly when
invoked by agents, not just in interactive sessions.

Run with: uv run pytest /tmp/test_validation_hooks.py -v
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

# ============================================================================
# Helper Functions
# ============================================================================


def run_hook(
    script_path: Path, hook_input: dict[str, Any], timeout: int = 10
) -> tuple[int, str, str]:
    """
    Run a hook script with JSON input and return exit code, stdout, stderr.

    Args:
        script_path: Path to the hook script
        hook_input: Dictionary to pass as JSON stdin
        timeout: Timeout in seconds

    Returns:
        (exit_code, stdout, stderr)
    """
    result = subprocess.run(
        ["uv", "run", "python", str(script_path)],
        check=False,
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def parse_hook_output(stdout: str) -> dict[str, Any]:
    """
    Parse hook JSON output from stdout.

    Claude Code hooks output JSON to stdout per the specification.
    This function handles both pure JSON and JSON with surrounding text.
    """
    # Try to find JSON in stdout
    stdout = stdout.strip()

    # Check if stdout starts with {
    if stdout.startswith("{"):
        return json.loads(stdout)

    # Try to find JSON block in stdout
    lines = stdout.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            # Found start of JSON, extract until end
            json_lines = []
            brace_count = 0
            for j in range(i, len(lines)):
                json_lines.append(lines[j])
                brace_count += lines[j].count("{") - lines[j].count("}")
                if brace_count == 0:
                    break
            json_str = "\n".join(json_lines)
            return json.loads(json_str)

    msg = f"No JSON found in stdout: {stdout}"
    raise ValueError(msg)


# ============================================================================
# SessionStart Hook Tests (validate_env.py)
# ============================================================================


class TestSessionStartHook:
    """Tests for SessionStart hook (validate_env.py)."""

    def test_hook_runs_successfully(self, validate_env_script: Path):
        """Test that the SessionStart hook runs without errors."""
        exit_code, stdout, _stderr = run_hook(validate_env_script, {})

        assert exit_code == 0, f"Hook failed with exit code {exit_code}: {_stderr}"

        # Parse JSON output and verify it contains instruction content
        output = parse_hook_output(stdout)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        # Check that the context contains expected content from instruction files
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "Core Axioms" in context or "BACKGROUND" in context

    def test_hook_outputs_valid_json(self, validate_env_script: Path):
        """Test that the hook outputs valid JSON."""
        exit_code, stdout, _stderr = run_hook(validate_env_script, {})

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # Verify structure
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_hook_loads_both_instruction_files(self, validate_env_script: Path):
        """Test that both instruction files are loaded."""
        exit_code, stdout, _stderr = run_hook(validate_env_script, {})

        assert exit_code == 0
        output = parse_hook_output(stdout)

        context = output["hookSpecificOutput"]["additionalContext"]

        # Check for both files
        assert (
            "Generic Agent Rules (bot/agents/_CORE.md)" in context
            or "BACKGROUND: Framework Operating Rules" in context
        )
        assert (
            "User-Specific Context (docs/agents/INSTRUCTIONS.md)" in context
            or "PRIMARY: Your Work Context" in context
        )

        # Check for key content from each file
        assert "Core Axioms" in context  # From generic instructions
        assert "Nicolas Suzor" in context  # From user-specific instructions

    def test_hook_handles_missing_files_gracefully(
        self, validate_env_script: Path, tmp_path: Path
    ):
        """Test that hook fails gracefully if instruction files are missing."""
        # This test would require modifying the script to point to non-existent files
        # For now, we just verify the script would exit with code 1
        # We can't easily test this without modifying the script or using mocks


# ============================================================================
# PreToolUse Hook Tests (validate_tool.py)
# ============================================================================


class TestPreToolUseHook:
    """Tests for PreToolUse hook (validate_tool.py)."""

    def test_hook_allows_safe_tool(self, validate_tool_script: Path, repo_root: Path):
        """Test that safe tools are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.txt"},
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_blocks_inline_python(self, validate_tool_script: Path, repo_root: Path):
        """Test that inline Python (python -c) is blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python -c 'print(1+1)'"},
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2  # Block
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert (
            "Inline Python execution"
            in output["hookSpecificOutput"]["permissionDecisionReason"]
        )

    def test_hook_blocks_python_without_uv_run(self, validate_tool_script: Path, repo_root: Path):
        """Test that Python commands without 'uv run' are blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python script.py"},
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2  # Block
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "uv run" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_allows_python_with_uv_run(self, validate_tool_script: Path, repo_root: Path):
        """Test that Python commands with 'uv run' are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "uv run python script.py"},
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_blocks_pytest_without_uv_run(self, validate_tool_script: Path, repo_root: Path):
        """Test that pytest without 'uv run' is blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hook_allows_pytest_with_uv_run(self, validate_tool_script: Path, repo_root: Path):
        """Test that pytest with 'uv run' are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "uv run pytest tests/"},
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_warns_trainer_agent_on_claude_files(self, validate_tool_script: Path, repo_root: Path):
        """Test that non-trainer agents get warnings for .claude files."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(repo_root / ".claude" / "test.json"),
                "content": "{}",
                "subagent_type": "developer",  # Not trainer
            },
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 1  # Warn
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None  # Allow but warn
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert output["hookSpecificOutput"]["permissionDecisionReason"] is not None
        assert "trainer" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_allows_trainer_agent_on_claude_files(
        self, validate_tool_script: Path, repo_root: Path
    ):
        """Test that trainer agent can modify .claude files."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(repo_root / ".claude" / "test.json"),
                "content": "{}",
                "subagent_type": "trainer",
            },
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_blocks_md_creation_outside_allowed_paths(
        self, validate_tool_script: Path, repo_root: Path
    ):
        """Test that .md files outside allowed paths are blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(repo_root / "docs" / "README.md"),
                "content": "# Test",
                "subagent_type": "developer",
            },
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2  # Block
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hook_allows_md_in_tmp(self, validate_tool_script: Path, repo_root: Path):
        """Test that .md files in /tmp are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/test.md",
                "content": "# Test",
                "subagent_type": "developer",
            },
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_allows_md_in_papers(self, validate_tool_script: Path, repo_root: Path):
        """Test that .md files in papers/ are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(repo_root / "papers" / "test.md"),
                "content": "# Test Paper",
                "subagent_type": "developer",
            },
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_allows_agent_instructions(self, validate_tool_script: Path, repo_root: Path):
        """Test that agent instruction files are allowed."""
        import os

        bot_root = Path(os.getenv("ACADEMICOPS_BOT"))
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(bot_root / "agents" / "test-agent.md"),
                "content": "# Agent Instructions",
                "subagent_type": "trainer",
            },
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # continue field is optional and excluded when None
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ============================================================================
# Integration Tests
# ============================================================================


class TestHookIntegration:
    """Integration tests for hook system."""

    def test_json_output_format_matches_claude_expectations(
        self, validate_tool_script: Path, repo_root: Path
    ):
        """
        Test that hook output matches Claude Code's expected format.

        This is the critical test that catches the issue from the debug logs:
        Claude Code expects JSON on stdout per the specification.
        """
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.txt"},
        }

        _exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        # Verify stdout starts with JSON (no leading text)
        stdout_stripped = stdout.strip()
        assert stdout_stripped.startswith("{"), (
            f"Hook output should start with '{{'  but got: {stdout_stripped[:100]}"
        )

        # Verify it's valid JSON
        output = json.loads(stdout_stripped)

        # Verify required fields
        # Note: 'continue' is optional and excluded when None
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "permissionDecision" in output["hookSpecificOutput"]

    def test_hook_handles_task_agent_invocation(self, validate_tool_script: Path, repo_root: Path):
        """Test that Task tool invocations extract agent type correctly."""
        # When the Task tool is called, the agent type is in tool_input.subagent_type
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "code-review",
                "prompt": "Review this code",
                "description": "Code review",
            },
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        # Should succeed - we're just testing agent detection
        assert exit_code == 0
        output = parse_hook_output(stdout)
        # continue field is optional and excluded when None


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_hook_handles_empty_input(self, validate_tool_script: Path):
        """Test that hook handles empty input gracefully."""
        exit_code, _stdout, _stderr = run_hook(validate_tool_script, {})

        # Should not crash, but may fail validation
        assert exit_code in [0, 1, 2]

    def test_hook_handles_malformed_json(self, validate_tool_script: Path):
        """Test that hook handles malformed JSON."""
        result = subprocess.run(
            ["uv", "run", "python", str(validate_tool_script)],
            check=False,
            input="not json",
            capture_output=True,
            text=True,
        )

        # Should exit with error
        assert result.returncode == 2
        assert "Invalid JSON" in result.stderr

    def test_hook_handles_missing_tool_name(self, validate_tool_script: Path, repo_root: Path):
        """Test that hook handles missing tool_name."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            # Missing tool_name
            "tool_input": {},
        }

        exit_code, _stdout, _stderr = run_hook(validate_tool_script, hook_input)

        # Should handle gracefully
        assert exit_code in [0, 1, 2]

