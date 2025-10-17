#!/usr/bin/env python3
"""
Minimal integration tests for Claude Code in headless mode.

These tests verify that Claude Code correctly integrates with our hook system.
Business logic is tested in test_validation_hooks.py (unit tests).

Run with: uv run pytest tests/integration/test_claude_headless.py -v --slow
"""

import pytest

# Mark all tests in this file as slow (integration tests)
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
        """Verify @agent-developer syntax is recognized."""
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
        """Verify that hook 'deny' decisions block tool execution."""
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
        """Verify that hook 'allow' decisions permit tool execution."""
        result = claude_headless(
            "Use the Read tool to read bot/README.md and tell me if it exists",
            model="haiku",
        )

        assert result["success"], f"Read should be allowed. Error: {result['error']}"
        assert not result["permission_denials"], (
            "Read should not trigger permission denials"
        )


class TestBasicFunctionality:
    """Smoke tests for basic Claude Code functionality."""

    def test_headless_mode_works(self, claude_headless):
        """Basic smoke test - verify Claude Code responds in headless mode."""
        result = claude_headless(
            "What is 2+2? Answer with just the number.", model="haiku"
        )

        assert result["success"], f"Basic query failed: {result['error']}"
        assert "4" in result["result"], f"Expected '4', got: {result['result']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--slow"])
