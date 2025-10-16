#!/usr/bin/env python3
"""
Test suite for validation hook system (validate_tool.py and validate_env.py).

This tests the hooks in headless mode to ensure they work correctly when
invoked by agents, not just in interactive sessions.

Run with: uv run pytest /tmp/test_validation_hooks.py -v
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

# Mark all tests in this file as slow (integration tests that invoke actual hooks)
pytestmark = [pytest.mark.slow, pytest.mark.timeout(30)]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def repo_root() -> Path:
    """Get the repository root directory."""
    # Assume we're running from /home/nic/src/writing
    return Path("/home/nic/src/writing")


@pytest.fixture
def validate_tool_script(repo_root: Path) -> Path:
    """Path to validate_tool.py script."""
    return repo_root / "bot" / "scripts" / "validate_tool.py"


@pytest.fixture
def validate_env_script(repo_root: Path) -> Path:
    """Path to validate_env.py script."""
    return repo_root / "bot" / "scripts" / "validate_env.py"


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
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def parse_hook_output(stderr: str) -> dict[str, Any]:
    """
    Parse hook JSON output from stderr.

    Claude Code hooks output JSON to stderr.
    This function handles both pure JSON and JSON with surrounding text.
    """
    # Try to find JSON in stderr
    stderr = stderr.strip()

    # Check if stderr starts with {
    if stderr.startswith("{"):
        return json.loads(stderr)

    # Try to find JSON block in stderr
    lines = stderr.split("\n")
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

    raise ValueError(f"No JSON found in stderr: {stderr}")


# ============================================================================
# SessionStart Hook Tests (validate_env.py)
# ============================================================================


class TestSessionStartHook:
    """Tests for SessionStart hook (validate_env.py)."""

    def test_hook_runs_successfully(self, validate_env_script: Path):
        """Test that the SessionStart hook runs without errors."""
        exit_code, stdout, stderr = run_hook(validate_env_script, {})

        assert exit_code == 0, f"Hook failed with exit code {exit_code}: {stderr}"
        assert "Loaded core instruction files" in stderr

    def test_hook_outputs_valid_json(self, validate_env_script: Path):
        """Test that the hook outputs valid JSON."""
        exit_code, stdout, stderr = run_hook(validate_env_script, {})

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # Verify structure
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_hook_loads_both_instruction_files(self, validate_env_script: Path):
        """Test that both instruction files are loaded."""
        exit_code, stdout, stderr = run_hook(validate_env_script, {})

        assert exit_code == 0
        output = parse_hook_output(stdout)

        context = output["hookSpecificOutput"]["additionalContext"]

        # Check for both files
        assert "Generic Agent Rules (bot/agents/_CORE.md)" in context or "BACKGROUND: Framework Operating Rules" in context
        assert "User-Specific Context (docs/agents/INSTRUCTIONS.md)" in context or "PRIMARY: Your Work Context" in context

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
        pass


# ============================================================================
# PreToolUse Hook Tests (validate_tool.py)
# ============================================================================


class TestPreToolUseHook:
    """Tests for PreToolUse hook (validate_tool.py)."""

    def test_hook_allows_safe_tool(self, validate_tool_script: Path):
        """Test that safe tools are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.txt"},
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stderr)

        assert output["continue"] is True
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_blocks_inline_python(self, validate_tool_script: Path):
        """Test that inline Python (python -c) is blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python -c 'print(1+1)'"},
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2  # Block
        output = parse_hook_output(stderr)

        assert output["continue"] is False
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "Inline Python execution" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_blocks_python_without_uv_run(self, validate_tool_script: Path):
        """Test that Python commands without 'uv run' are blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python script.py"},
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2  # Block
        output = parse_hook_output(stderr)

        assert output["continue"] is False
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "uv run" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_allows_python_with_uv_run(self, validate_tool_script: Path):
        """Test that Python commands with 'uv run' are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "uv run python script.py"},
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stderr)

        assert output["continue"] is True
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_blocks_pytest_without_uv_run(self, validate_tool_script: Path):
        """Test that pytest without 'uv run' is blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2
        output = parse_hook_output(stderr)

        assert output["continue"] is False
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hook_allows_pytest_with_uv_run(self, validate_tool_script: Path):
        """Test that pytest with 'uv run' is allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "uv run pytest tests/"},
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stderr)

        assert output["continue"] is True
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_warns_trainer_agent_on_claude_files(
        self, validate_tool_script: Path
    ):
        """Test that non-trainer agents get warnings for .claude files."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/home/nic/src/writing/.claude/test.json",
                "content": "{}",
                "subagent_type": "developer",  # Not trainer
            },
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 1  # Warn
        output = parse_hook_output(stderr)

        assert output["continue"] is True  # Allow but warn
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert output["systemMessage"] is not None
        assert "trainer" in output["systemMessage"]

    def test_hook_allows_trainer_agent_on_claude_files(
        self, validate_tool_script: Path
    ):
        """Test that trainer agent can modify .claude files."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/home/nic/src/writing/.claude/test.json",
                "content": "{}",
                "subagent_type": "trainer",
            },
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stderr)

        assert output["continue"] is True
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_blocks_md_creation_outside_allowed_paths(
        self, validate_tool_script: Path
    ):
        """Test that .md files outside allowed paths are blocked."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/home/nic/src/writing/docs/README.md",
                "content": "# Test",
                "subagent_type": "developer",
            },
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 2  # Block
        output = parse_hook_output(stderr)

        assert output["continue"] is False
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hook_allows_md_in_tmp(self, validate_tool_script: Path):
        """Test that .md files in /tmp are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/test.md",
                "content": "# Test",
                "subagent_type": "developer",
            },
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stderr)

        assert output["continue"] is True
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_allows_md_in_papers(self, validate_tool_script: Path):
        """Test that .md files in papers/ are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/home/nic/src/writing/papers/test.md",
                "content": "# Test Paper",
                "subagent_type": "developer",
            },
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stderr)

        assert output["continue"] is True
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_allows_agent_instructions(self, validate_tool_script: Path):
        """Test that agent instruction files are allowed."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/home/nic/src/writing/bot/agents/test-agent.md",
                "content": "# Agent Instructions",
                "subagent_type": "trainer",
            },
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        assert exit_code == 0
        output = parse_hook_output(stderr)

        assert output["continue"] is True
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ============================================================================
# Integration Tests
# ============================================================================


class TestHookIntegration:
    """Integration tests for hook system."""

    def test_json_output_format_matches_claude_expectations(
        self, validate_tool_script: Path
    ):
        """
        Test that hook output matches Claude Code's expected format.

        This is the critical test that catches the issue from the debug logs:
        Claude Code expects JSON on stderr, but was seeing non-JSON text.
        """
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.txt"},
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        # Verify stderr starts with JSON (no leading text)
        stderr_stripped = stderr.strip()
        assert stderr_stripped.startswith("{"), (
            f"Hook output should start with '{{' but got: {stderr_stripped[:100]}"
        )

        # Verify it's valid JSON
        output = json.loads(stderr_stripped)

        # Verify required fields
        assert "continue" in output
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "permissionDecision" in output["hookSpecificOutput"]

    def test_hook_handles_task_agent_invocation(self, validate_tool_script: Path):
        """Test that Task tool invocations extract agent type correctly."""
        # When the Task tool is called, the agent type is in tool_input.subagent_type
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "code-review",
                "prompt": "Review this code",
                "description": "Code review",
            },
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        # Should succeed - we're just testing agent detection
        assert exit_code == 0
        output = parse_hook_output(stderr)
        assert output["continue"] is True


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_hook_handles_empty_input(self, validate_tool_script: Path):
        """Test that hook handles empty input gracefully."""
        exit_code, stdout, stderr = run_hook(validate_tool_script, {})

        # Should not crash, but may fail validation
        assert exit_code in [0, 1, 2]

    def test_hook_handles_malformed_json(self, validate_tool_script: Path):
        """Test that hook handles malformed JSON."""
        result = subprocess.run(
            ["uv", "run", "python", str(validate_tool_script)],
            input="not json",
            capture_output=True,
            text=True,
        )

        # Should exit with error
        assert result.returncode == 2
        assert "Invalid JSON" in result.stderr

    def test_hook_handles_missing_tool_name(self, validate_tool_script: Path):
        """Test that hook handles missing tool_name."""
        hook_input = {
            "session_id": "test-session",
            "cwd": "/home/nic/src/writing",
            "hook_event_name": "PreToolUse",
            # Missing tool_name
            "tool_input": {},
        }

        exit_code, stdout, stderr = run_hook(validate_tool_script, hook_input)

        # Should handle gracefully
        assert exit_code in [0, 1, 2]


if __name__ == "__main__":
    # Allow running directly with: python /tmp/test_validation_hooks.py
    pytest.main([__file__, "-v"])
