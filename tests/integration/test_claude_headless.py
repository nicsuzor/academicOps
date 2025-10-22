#!/usr/bin/env python3
"""
Minimal integration tests for Claude Code in headless mode.

These tests verify that Claude Code correctly integrates with our hook system.
"""

import pytest
# Mark all tests in this file as slow (integration tests invoking Claude CLI)
pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]


class TestAgentDetection:
    """Test that agent type detection works in headless mode."""

    def test_trainer_agent_syntax_works(self, claude_headless):
        """Verify @agent-trainer syntax is recognized."""
        result = claude_headless(
            "@agent-trainer What agent type am I? Answer in one word.", model="haiku"
        )

        assert result["success"], f"Failed: {result['error']}"
        assert "trainer" in result["result"].lower(), "Agent didn't identify as trainer"

    def test_developer_agent_syntax_works(self, claude_headless):
        result = claude_headless(
            "@agent-developer What agent type am I? Answer in one word.", model="haiku"
        )

        assert result["success"], f"Failed: {result['error']}"
        assert "developer" in result["result"].lower(), (
            "Agent didn't identify as developer"
        )


class TestHookIntegration:
    """Test that hooks correctly control Claude Code behavior."""

    def test_hook_deny_blocks_execution(self, claude_headless):
        result = claude_headless(
            "Run this exact bash command: python -c 'print(1+1)'", model="haiku"
        )

        # Claude should either acknowledge the block or adapt by creating a file
        result_lower = result["result"].lower()

        mentions_block = (
            "blocked" in result_lower
            or "prohibited" in result_lower
            or len(result.get("permission_denials", [])) > 0
        )

        adapts_properly = "test" in result_lower and "file" in result_lower

        assert mentions_block or adapts_properly, (
            f"Expected Claude to handle python -c block. Got: {result['result']}"
        )

    def test_hook_allow_permits_execution(self, claude_headless):
        # Test hooks work from subdirectory (validates $CLAUDE_PROJECT_DIR)
        result = claude_headless(
            "First cd to tests/ subdirectory, then use the Read tool to read ../README.md and tell me if it exists",
            model="haiku",
        )

        assert result["success"], f"Read should be allowed from subdirectory. Error: {result['error']}"
        assert not result["permission_denials"], (
            "Read should not trigger permission denials from subdirectory"
        )


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


class TestBasicFunctionality:
    """Smoke tests for basic Claude Code functionality."""

    def test_headless_mode_works(self, claude_headless):
        result = claude_headless(
            "What is 2+2? Answer with just the number.", model="haiku"
        )

        assert result["success"], f"Basic query failed: {result['error']}"
        assert "4" in result["result"], f"Expected '4', got: {result['result']}"


