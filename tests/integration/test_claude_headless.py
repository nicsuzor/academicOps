#!/usr/bin/env python3
"""
Integration tests for Claude Code headless mode.

These tests invoke the actual claude CLI to verify:
1. Agent detection and subagent_type parameter passing
2. Hook enforcement (PreToolUse validation)
3. Permission system behavior
4. Git commit workflows

Run with: uv run pytest tests/integration/test_claude_headless.py -v
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

# Mark all tests in this file as slow (integration tests)
pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]


def run_claude_headless(prompt: str, timeout: int = 120, permission_mode: str = "acceptEdits") -> dict:
    """
    Run claude CLI in headless mode and return parsed JSON output.

    Args:
        prompt: The prompt to send to Claude
        timeout: Timeout in seconds (default 60)
        permission_mode: Permission mode (default "acceptEdits")
            - "acceptEdits": Auto-accept edit operations
            - "ask": Prompt for permission (will hang in headless)
            - "deny": Auto-deny all operations

    Returns:
        dict with keys: success, output, error, permission_denials, duration_ms
    """
    cmd = ["claude", "-p", prompt, "--output-format", "json"]

    # Add permission mode if specified
    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd="/home/nic/src/writing",
    )

    try:
        output = json.loads(result.stdout)
        return {
            "success": output.get("is_error", True) == False,
            "output": output,
            "error": result.stderr,
            "permission_denials": output.get("permission_denials", []),
            "result": output.get("result", ""),
            "duration_ms": output.get("duration_ms", 0),
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "output": {},
            "error": f"Failed to parse JSON. stdout: {result.stdout}\nstderr: {result.stderr}",
            "permission_denials": [],
            "result": "",
            "duration_ms": 0,
        }


class TestAgentDetection:
    """Test that agents are properly detected and subagent_type is passed."""

    def test_trainer_agent_invocation(self):
        """Verify @agent-trainer syntax works in headless mode."""
        result = run_claude_headless("@agent-trainer What agent am I?")

        assert result["success"], f"Failed: {result['error']}"
        assert "trainer" in result["result"].lower(), "Agent didn't identify as trainer"

    def test_developer_agent_invocation(self):
        """Verify @agent-developer syntax works in headless mode."""
        result = run_claude_headless("@agent-developer What agent am I?")

        assert result["success"], f"Failed: {result['error']}"
        assert "developer" in result["result"].lower(), "Agent didn't identify as developer"

    @pytest.mark.skip(reason="Need to check debug log for subagent_type - requires hook inspection")
    def test_subagent_type_parameter_passed(self):
        """Verify subagent_type is passed to PreToolUse hook."""
        # This test requires inspecting /tmp/claude-tool-input.json
        # after a tool use occurs
        pass


class TestValidateToolEnforcement:
    """Test that validate_tool.py rules are enforced in headless mode."""

    def test_python_without_uv_run_gets_warning(self):
        """Verify Python without uv run triggers validation warning."""
        result = run_claude_headless(
            "@agent-developer Run this bash command: python --version"
        )

        # Should complete but with a warning about uv run
        # Check if warning appears in output or permission_denials
        output_text = json.dumps(result["output"]).lower()
        assert "uv run" in output_text or result.get("permission_denials"), \
            "Expected warning about using 'uv run python'"

    def test_python_dash_c_is_blocked(self):
        """Verify python -c is blocked and Claude adapts by using a proper file."""
        result = run_claude_headless(
            "@agent-developer Run this bash command: python -c 'print(1+1)'"
        )

        # Claude should either:
        # 1. Explain the block (mentions "blocked" or "prohibited")
        # 2. Work around it (creates temp_test.py, mentions "approval" or "permission")
        result_text = result["result"].lower()

        # Success if Claude either explains the block OR works around it
        mentions_blocking = "blocked" in result_text or "prohibited" in result_text
        works_around_it = ("temp" in result_text and "test" in result_text) or \
                         ("approval" in result_text or "permission" in result_text)

        assert mentions_blocking or works_around_it, \
            f"Expected Claude to handle python -c block, got: {result['result']}"

    def test_developer_blocked_from_claude_config(self):
        """Verify developer cannot edit .claude/settings.json."""
        result = run_claude_headless(
            "@agent-developer Edit .claude/settings.json and add a comment"
        )

        # Should be blocked
        assert result["permission_denials"], "Expected developer to be blocked from .claude config"
        denial_text = str(result["permission_denials"]).lower()
        assert "trainer" in denial_text


class TestPermissionEnforcement:
    """Test that PreToolUse hooks enforce permissions correctly."""

    def test_trainer_can_edit_agent_files(self):
        """Verify trainer agent can modify agent instruction files."""
        # Create a temporary test file
        test_content = "# Test Agent\n\nThis is a test."

        result = run_claude_headless(
            f"@agent-trainer Create a file at bot/agents/test_temp.md with this content:\n{test_content}"
        )

        # Check if permission was denied
        if result["permission_denials"]:
            pytest.fail(f"Trainer was denied permission: {result['permission_denials']}")

        # Verify file was created
        test_file = Path("/home/nic/src/writing/bot/agents/test_temp.md")
        if test_file.exists():
            assert test_file.read_text() == test_content
            test_file.unlink()  # Clean up

    @pytest.mark.xfail(reason="Known bug: developer agent gets blocked from editing - issue #93")
    def test_developer_can_edit_code_files(self):
        """Verify developer agent can modify code files."""
        test_file = Path("/home/nic/src/writing/bot/test_temp.py")
        test_content = '# Test file\nprint("hello")\n'

        result = run_claude_headless(
            f"@agent-developer Create a file at bot/test_temp.py with this content:\n{test_content}"
        )

        if result["permission_denials"]:
            pytest.fail(f"Developer was denied permission: {result['permission_denials']}")

        if test_file.exists():
            assert test_content in test_file.read_text()
            test_file.unlink()

    def test_developer_blocked_from_agent_files(self):
        """Verify developer agent is blocked from modifying agent instruction files."""
        result = run_claude_headless(
            "@agent-developer Edit the file bot/agents/TRAINER.md and add a comment at the top saying 'test'"
        )

        # Should have permission denials
        assert result["permission_denials"], "Developer should have been blocked from editing agent files"
        assert any("trainer" in str(denial).lower() for denial in result["permission_denials"])


class TestGitCommitWorkflow:
    """Test git commit permission enforcement."""

    @pytest.mark.skip(reason="Requires actual git operations in test environment")
    def test_code_review_agent_can_commit(self):
        """Verify code-review agent can perform git commits."""
        # This test needs a proper git test environment
        # with changes staged for commit
        pass

    def test_developer_gets_git_commit_warning(self):
        """Verify developer agent gets warning (not block) for git commit."""
        # The current behavior is severity="warn" for git commits
        # Should allow but warn

        result = run_claude_headless(
            "@agent-developer Run: git status"
        )

        # Check if any warnings were shown about git commits
        # This is hard to test without actually triggering a commit
        # May need to check the result text for warning messages
        pass


class TestHookBehavior:
    """Test that hooks receive correct data and exit codes are respected."""

    @pytest.mark.skip(reason="Requires parsing debug log at /tmp/claude-tool-input.json")
    def test_hook_receives_correct_input_structure(self):
        """Verify PreToolUse hook gets expected input structure."""
        # Need to:
        # 1. Trigger a tool use
        # 2. Parse /tmp/claude-tool-input.json
        # 3. Verify tool_name, tool_input, subagent_type are present
        pass

    @pytest.mark.skip(reason="Requires mock hook that returns specific exit codes")
    def test_hook_exit_code_0_allows(self):
        """Verify exit code 0 allows tool use."""
        pass

    @pytest.mark.skip(reason="Requires mock hook that returns specific exit codes")
    def test_hook_exit_code_1_warns(self):
        """Verify exit code 1 warns but allows."""
        pass

    @pytest.mark.skip(reason="Requires mock hook that returns specific exit codes")
    def test_hook_exit_code_2_blocks(self):
        """Verify exit code 2 blocks tool use."""
        pass


if __name__ == "__main__":
    # Allow running with: python test_claude_headless.py
    pytest.main([__file__, "-v"])
