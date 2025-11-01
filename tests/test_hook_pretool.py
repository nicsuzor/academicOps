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

from .hooks import parse_hook_output, run_hook

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

    def test_hook_blocks_python_module_without_uv_run(
        self, validate_tool_script: Path, repo_root: Path
    ):
        """Test that 'python -m module' without 'uv run' is blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python -m buttermilk.debug.ws_debug_cli logs"},
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2  # Block
        output = parse_hook_output(stdout)

        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "uv run" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_allows_python_module_with_uv_run(
        self, validate_tool_script: Path, repo_root: Path
    ):
        """Test that 'uv run python -m module' is allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": str(repo_root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "uv run python -m buttermilk.debug.ws_debug_cli logs"
            },
        }

        exit_code, stdout, _stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stdout)

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

        bot_root = Path(os.getenv("ACADEMICOPS"))
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

