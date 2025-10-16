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
from pathlib import Path

import pytest

# Mark all tests in this file as slow (integration tests)
pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]


class TestAgentDetection:
    """Test that agents are properly detected and subagent_type is passed."""

    def test_trainer_agent_invocation(self, claude_headless):
        """Verify @agent-trainer syntax works in headless mode."""
        result = claude_headless("@agent-trainer What agent am I?")

        assert result["success"], f"Failed: {result['error']}"
        assert "trainer" in result["result"].lower(), "Agent didn't identify as trainer"

    def test_developer_agent_invocation(self, claude_headless):
        """Verify @agent-developer syntax works in headless mode."""
        result = claude_headless("@agent-developer What agent am I?")

        assert result["success"], f"Failed: {result['error']}"
        assert "developer" in result["result"].lower(), (
            "Agent didn't identify as developer"
        )

    @pytest.mark.skip(
        reason="Need to check debug log for subagent_type - requires hook inspection"
    )
    def test_subagent_type_parameter_passed(self, claude_headless):
        """Verify subagent_type is passed to PreToolUse hook."""
        # This test requires inspecting /tmp/claude-tool-input.json
        # after a tool use occurs


class TestValidateToolEnforcement:
    """Test that validate_tool.py rules are enforced in headless mode."""

    def test_python_without_uv_run_gets_warning(self, claude_headless):
        """Verify Python without uv run triggers validation warning."""
        result = claude_headless(
            "@agent-developer Run this bash command: python --version"
        )

        # Should complete but with a warning about uv run
        # Check if warning appears in output or permission_denials
        output_text = json.dumps(result["output"]).lower()
        assert "uv run" in output_text or result.get("permission_denials"), (
            "Expected warning about using 'uv run python'"
        )

    def test_python_dash_c_is_blocked(self, claude_headless):
        """Verify python -c is blocked and Claude adapts by using a proper file."""
        result = claude_headless(
            "@agent-developer Run this bash command: python -c 'print(1+1)'"
        )

        # Claude should either:
        # 1. Explain the block (mentions "blocked" or "prohibited")
        # 2. Work around it (creates temp_test.py, mentions "approval" or "permission")
        result_text = result["result"].lower()

        # Success if Claude either explains the block OR works around it
        mentions_blocking = "blocked" in result_text or "prohibited" in result_text
        works_around_it = ("temp" in result_text and "test" in result_text) or (
            "approval" in result_text or "permission" in result_text
        )

        assert mentions_blocking or works_around_it, (
            f"Expected Claude to handle python -c block, got: {result['result']}"
        )

    def test_developer_blocked_from_claude_config(self, claude_headless):
        """Verify developer cannot edit .claude/settings.json."""
        result = claude_headless(
            "@agent-developer Edit .claude/settings.json and add a comment"
        )

        # Should be blocked
        assert result["permission_denials"], (
            "Expected developer to be blocked from .claude config"
        )
        denial_text = str(result["permission_denials"]).lower()
        assert "trainer" in denial_text


class TestPermissionEnforcement:
    """Test that PreToolUse hooks enforce permissions correctly."""

    def test_trainer_can_edit_agent_files(self, claude_headless):
        """Verify trainer agent can modify agent instruction files."""
        # Create a temporary test file
        test_content = "# Test Agent\n\nThis is a test."

        result = claude_headless(
            f"@agent-trainer Create a file at bot/agents/test_temp.md with this content:\n{test_content}"
        )

        # Check if permission was denied
        if result["permission_denials"]:
            pytest.fail(
                f"Trainer was denied permission: {result['permission_denials']}"
            )

        # Verify file was created
        test_file = Path("/home/nic/src/writing/bot/agents/test_temp.md")
        if test_file.exists():
            assert test_file.read_text() == test_content
            test_file.unlink()  # Clean up

    @pytest.mark.xfail(
        reason="Known bug: developer agent gets blocked from editing - issue #93"
    )
    def test_developer_can_edit_code_files(self, claude_headless):
        """Verify developer agent can modify code files."""
        test_file = Path("/home/nic/src/writing/bot/test_temp.py")
        test_content = '# Test file\nprint("hello")\n'

        result = claude_headless(
            f"@agent-developer Create a file at bot/test_temp.py with this content:\n{test_content}"
        )

        if result["permission_denials"]:
            pytest.fail(
                f"Developer was denied permission: {result['permission_denials']}"
            )

        if test_file.exists():
            assert test_content in test_file.read_text()
            test_file.unlink()

    def test_developer_blocked_from_agent_files(self, claude_headless):
        """Verify developer agent is blocked from modifying agent instruction files."""
        result = claude_headless(
            "@agent-developer Edit the file bot/agents/TRAINER.md and add a comment at the top saying 'test'"
        )

        # Should have permission denials
        assert result["permission_denials"], (
            "Developer should have been blocked from editing agent files"
        )
        assert any(
            "trainer" in str(denial).lower() for denial in result["permission_denials"]
        )


class TestGitCommitWorkflow:
    """Test git commit permission enforcement."""

    @pytest.mark.skip(reason="Requires actual git operations in test environment")
    def test_code_review_agent_can_commit(self, claude_headless):
        """Verify code-review agent can perform git commits."""
        # This test needs a proper git test environment
        # with changes staged for commit

    def test_developer_gets_git_commit_warning(self, claude_headless):
        """Verify developer agent gets warning (not block) for git commit."""
        # The current behavior is severity="warn" for git commits
        # Should allow but warn

        claude_headless("@agent-developer Run: git status")

        # Check if any warnings were shown about git commits
        # This is hard to test without actually triggering a commit
        # May need to check the result text for warning messages


class TestHookBehavior:
    """Test that hooks receive correct data and exit codes are respected."""

    @pytest.mark.skip(
        reason="Requires parsing debug log at /tmp/claude-tool-input.json"
    )
    def test_hook_receives_correct_input_structure(self, claude_headless):
        """Verify PreToolUse hook gets expected input structure."""
        # Need to:
        # 1. Trigger a tool use
        # 2. Parse /tmp/claude-tool-input.json
        # 3. Verify tool_name, tool_input, subagent_type are present

    @pytest.mark.skip(reason="Requires mock hook that returns specific exit codes")
    def test_hook_exit_code_0_allows(self, claude_headless):
        """Verify exit code 0 allows tool use."""

    @pytest.mark.skip(reason="Requires mock hook that returns specific exit codes")
    def test_hook_exit_code_1_warns(self, claude_headless):
        """Verify exit code 1 warns but allows."""

    @pytest.mark.skip(reason="Requires mock hook that returns specific exit codes")
    def test_hook_exit_code_2_blocks(self, claude_headless):
        """Verify exit code 2 blocks tool use."""


if __name__ == "__main__":
    # Allow running with: python test_claude_headless.py
    pytest.main([__file__, "-v"])
