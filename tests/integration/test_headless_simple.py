#!/usr/bin/env python3
"""
Simple integration test to verify headless mode works.
"""

import json
import os
import subprocess
from pathlib import Path
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


def test_claude_headless_fixture(claude_headless, repo_root: Path):
    """Test that Claude Code works in headless mode with permission-mode flag."""

    result = claude_headless("What is your current working directory?", model="haiku")

    assert result["success"], f"Failed: {result['error']}"

    assert repo_root == Path(result["result"].strip()), (
        f"Expected CWD to be {repo_root}, got: {result['result']}"
    )