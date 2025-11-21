#!/usr/bin/env python3
"""Integration test configuration and fixtures.

Provides:
- claude_headless fixture for headless Claude Code execution
- run_claude_headless function for direct CLI invocation
- pytest configuration for integration/slow markers
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from lib.paths import get_aops_root


def _claude_cli_available() -> bool:
    """Check if claude CLI command is available in PATH."""
    import shutil
    return shutil.which("claude") is not None


def run_claude_headless(
    prompt: str,
    model: str | None = "haiku",
    timeout_seconds: int = 120,
    permission_mode: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Execute Claude Code in headless mode.

    Args:
        prompt: Prompt to send to Claude
        model: Optional model identifier (e.g., "claude-sonnet-4-5-20250929")
        timeout_seconds: Command timeout in seconds (default: 120)
        permission_mode: Optional permission mode (e.g., "disabled")
        cwd: Working directory (defaults to writing root)

    Returns:
        Dictionary with keys:
        - success (bool): Whether execution succeeded
        - output (str): Raw JSON output from claude command
        - result (dict): Parsed JSON result
        - error (str, optional): Error message if execution failed
    """
    import os

    # Check if claude CLI is available
    if not _claude_cli_available():
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": "claude CLI not found in PATH - these tests require Claude Code CLI installed",
        }

    # Build command
    cmd = ["claude", "-p", prompt, "--output-format", "json"]

    if model:
        cmd.extend(["--model", model])

    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])

    # Set working directory
    working_dir = cwd if cwd else get_aops_root()

    # Build environment - inherit current environment and ensure AOPS is set
    env = os.environ.copy()

    # Get AOPS path - prefer environment variable, fallback to lib.paths
    if "AOPS" not in env:
        from lib.paths import get_aops_root
        env["AOPS"] = str(get_aops_root())

    try:
        # Execute command
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,  # Don't raise on non-zero exit
            env=env,  # Pass environment with AOPS set
        )

        # Check for command failure
        if result.returncode != 0:
            return {
                "success": False,
                "output": result.stdout,
                "result": {},
                "error": f"Command failed with exit code {result.returncode}: {result.stderr}",
            }

        # Parse JSON output
        try:
            parsed_output = json.loads(result.stdout)
            return {
                "success": True,
                "output": result.stdout,
                "result": parsed_output,
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "output": result.stdout,
                "result": {},
                "error": f"JSON parse error: {e!s}",
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": f"Command timed out after {timeout_seconds} seconds",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": f"Command execution failed: {e!s}",
        }


@pytest.fixture
def claude_headless():
    """Pytest fixture providing headless Claude Code execution.

    Returns:
        Callable that executes claude command and returns parsed result.

    Example:
        def test_something(claude_headless):
            result = claude_headless("What is 2+2?")
            assert result["success"]

    Note:
        Tests using this fixture will be skipped if claude CLI is not in PATH.
    """
    # Skip test if claude CLI not available
    if not _claude_cli_available():
        pytest.skip("claude CLI not found in PATH - requires Claude Code CLI installed")

    return run_claude_headless


@pytest.fixture
def aops_root():
    """Pytest fixture providing aOps framework root path.

    Returns:
        Path: Absolute path to aOps framework root ($AOPS)
    """
    return get_aops_root()


def pytest_configure(config):
    """Register custom markers for integration tests."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external systems)",
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (may take minutes to complete)"
    )


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    """Auto-mark integration tests based on location."""
    for item in items:
        # Mark all tests in integration/ directory as integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
