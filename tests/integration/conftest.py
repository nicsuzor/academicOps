#!/usr/bin/env python3
"""
Shared fixtures for integration tests.

This provides common utilities for testing Claude Code in headless mode.
"""

import json
import subprocess
from pathlib import Path

import pytest

# Import from parent conftest for path utilities
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import get_aca_root


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest for integration tests - override parallelism."""
    # Override -n flag for integration tests (use 4 workers instead of 20)
    # Integration tests spawn subprocesses, so we want less parallelism
    config.option.numprocesses = 4


# ============================================================================
# Test Fixtures
# ============================================================================


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "claude_headless" in item.fixturenames:
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.timeout(120))


def run_claude_headless(
    prompt: str,
    timeout: int = 120,
    permission_mode: str = "acceptEdits",
    model: str | None = None,
    cwd: str | None = None,
) -> dict:
    """
    Run claude CLI in headless mode and return parsed JSON output.

    Args:
        prompt: The prompt to send to Claude
        timeout: Timeout in seconds (default 120)
        permission_mode: Permission mode (default "acceptEdits")
            - "acceptEdits": Auto-accept edit operations
            - "ask": Prompt for permission (will hang in headless)
            - "deny": Auto-deny all operations
        model: Model to use (e.g. "haiku", "sonnet", "opus" or full model name)
            - If not specified, uses default model from settings
        cwd: Working directory for the command (default: current directory)

    Returns:
        dict with keys: success, output, error, permission_denials, result, duration_ms
    """
    cmd = ["claude", "-p", prompt, "--output-format", "json"]

    # Add permission mode if specified
    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])

    # Add model if specified
    if model:
        cmd.extend(["--model", model])

    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd or Path.cwd(),
    )

    try:
        output = json.loads(result.stdout)
        return {
            "success": not output.get("is_error", True),
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


@pytest.fixture
def claude_headless():
    """
    Fixture that provides the run_claude_headless function with proper cwd.

    Usage:
        def test_something(claude_headless):
            result = claude_headless("test prompt", model="haiku")
            assert result["success"]
    """
    # Get ACA root (personal workspace) for test execution
    aca_root = get_aca_root()

    def _run_claude(
        prompt: str,
        timeout: int = 120,
        permission_mode: str = "acceptEdits",
        model: str | None = None,
    ) -> dict:
        return run_claude_headless(
            prompt=prompt,
            timeout=timeout,
            permission_mode=permission_mode,
            model=model,
            cwd=str(aca_root),
        )

    return _run_claude
