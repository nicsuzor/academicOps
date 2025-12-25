"""Tests for prompt router hook.

Tests the v7 prompt router that:
1. Skips slash commands (Claude Code handles them)
2. Injects instruction to invoke intent-router subagent

The intent-router subagent (Haiku) has full context and returns
filtered guidance - main agent stays clean.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# AOPS root for PYTHONPATH
AOPS_ROOT = Path(__file__).parent.parent

from hooks.prompt_router import (
    FRAMING_VERSION,
    analyze_prompt,
)


class TestAnalyzePrompt:
    """Tests for analyze_prompt function."""

    def test_slash_command_returns_empty(self) -> None:
        """Test that slash commands return empty (Claude Code handles)."""
        result, matched = analyze_prompt("/meta show status")

        assert result == ""
        assert matched == []

    def test_any_slash_command_returns_empty(self) -> None:
        """Test that any slash command returns empty."""
        result, matched = analyze_prompt("/unknowncommand")

        assert result == ""
        assert matched == []

    def test_non_slash_returns_route_required(self) -> None:
        """Test that non-slash prompts return ROUTE_REQUIRED."""
        result, matched = analyze_prompt("help with framework")

        assert result == "ROUTE_REQUIRED"
        assert matched == []

    def test_empty_input(self) -> None:
        """Test that empty string returns empty tuple."""
        result, matched = analyze_prompt("")

        assert result == ""
        assert matched == []

    def test_framing_version_is_v7(self) -> None:
        """Test that framing version is v7-subagent-router for tracking."""
        assert FRAMING_VERSION == "v7-subagent-router"


def test_hook_script_slash_command_returns_empty_context(hooks_dir) -> None:
    """Test that slash commands get empty additionalContext."""
    hook_script = hooks_dir / "prompt_router.py"
    input_data = json.dumps({"prompt": "/meta show status"})

    env = {**os.environ, "PYTHONPATH": str(AOPS_ROOT)}
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_data,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    output = json.loads(result.stdout)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert hook_output["additionalContext"] == ""
    assert hook_output["framingVersion"] == "v7-subagent-router"


def test_hook_script_non_slash_invokes_router(hooks_dir) -> None:
    """Test that non-slash prompts get instruction to invoke router."""
    hook_script = hooks_dir / "prompt_router.py"
    input_data = json.dumps({"prompt": "help with python"})

    env = {**os.environ, "PYTHONPATH": str(AOPS_ROOT)}
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_data,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    output = json.loads(result.stdout)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    context = hook_output["additionalContext"]

    # Should instruct to invoke intent-router
    assert "ROUTE FIRST" in context
    assert "intent-router" in context
    assert "Task(" in context
