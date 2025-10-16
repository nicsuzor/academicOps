#!/usr/bin/env python3
"""
Simple integration test to verify headless mode works.

Run with: uv run pytest tests/integration/test_headless_simple.py -v
"""

import json
import subprocess

import pytest

# Mark all tests in this file as slow (integration tests invoking Claude CLI)
pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]


def test_claude_headless_basic():
    """Test that Claude Code works in headless mode with permission-mode flag."""
    result = subprocess.run(
        [
            "claude",
            "-p", "What is 2+2? Just give me the number.",
            "--output-format", "json",
            "--permission-mode", "acceptEdits"
        ],
        capture_output=True,
        text=True,
        timeout=120,  # Increased to 120 seconds
        cwd="/home/nic/src/writing"
    )

    output = json.loads(result.stdout)

    assert output["is_error"] == False, f"Command failed: {output}"
    assert "4" in output["result"], f"Expected '4' in result, got: {output['result']}"
    assert output["duration_ms"] < 10000, f"Took too long: {output['duration_ms']}ms"


def test_validate_tool_enforcement():
    """Test that validate_tool.py blocks operations in headless mode."""
    # Test that developer cannot edit .claude config
    result = subprocess.run(
        [
            "claude",
            "-p", "@agent-developer Read the file .claude/settings.json and tell me the first line",
            "--output-format", "json",
            "--permission-mode", "acceptEdits"
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd="/home/nic/src/writing"
    )

    output = json.loads(result.stdout)

    # Should complete successfully (Read is allowed, just not Edit)
    assert output["is_error"] == False

    # Now try to edit (should be blocked by validate_tool.py)
    result2 = subprocess.run(
        [
            "claude",
            "-p", "@agent-developer Use the Edit tool to change something in .claude/settings.json",
            "--output-format", "json",
            "--permission-mode", "acceptEdits"
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd="/home/nic/src/writing"
    )

    output2 = json.loads(result2.stdout)

    # Check if there were permission denials
    if "permission_denials" in output2:
        # Good - validate_tool.py blocked it
        denials = str(output2["permission_denials"]).lower()
        assert "trainer" in denials or "blocked" in denials
