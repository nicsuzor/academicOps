#!/usr/bin/env python3
"""
Shared fixtures for integration tests.

This provides common utilities for testing Claude Code in headless mode.
"""

import json
import subprocess
from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "claude_headless" in item.fixturenames:
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.timeout(120))


@pytest.fixture
def personal_repo_root() -> Path:
    """Get the personal repository root from environment variable."""
    import os

    personal_root = os.getenv("ACADEMICOPS_PERSONAL")
    if not personal_root:
        raise RuntimeError(
            "ACADEMICOPS_PERSONAL environment variable not set. "
            "This must point to your personal repository root."
        )

    path = Path(personal_root)
    if not path.exists():
        raise RuntimeError(
            f"ACADEMICOPS_PERSONAL path does not exist: {personal_root}"
        )

    return path


@pytest.fixture
def has_user_context(personal_repo_root: Path) -> bool:
    """Check if user context files are available."""
    return (personal_repo_root / "docs" / "agents" / "INSTRUCTIONS.md").exists()


@pytest.fixture
def validate_tool_script() -> Path:
    """Path to validate_tool.py script."""
    import os

    bot_root = os.getenv("ACADEMICOPS_BOT")
    if not bot_root:
        raise RuntimeError(
            "ACADEMICOPS_BOT environment variable not set. "
            "This must point to the academicOps bot repository root."
        )

    path = Path(bot_root) / "scripts" / "validate_tool.py"
    if not path.exists():
        raise RuntimeError(
            f"validate_tool.py not found at expected path: {path}"
        )

    return path


@pytest.fixture
def validate_env_script() -> Path:
    """Path to load_instructions.py script (renamed from validate_env.py)."""
    import os

    bot_root = os.getenv("ACADEMICOPS_BOT")
    if not bot_root:
        raise RuntimeError(
            "ACADEMICOPS_BOT environment variable not set. "
            "This must point to the academicOps bot repository root."
        )

    path = Path(bot_root) / "scripts" / "load_instructions.py"
    if not path.exists():
        raise RuntimeError(
            f"load_instructions.py not found at expected path: {path}"
        )

    return path


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
def claude_headless(personal_repo_root: Path):
    """
    Fixture that provides the run_claude_headless function with proper cwd.

    Usage:
        def test_something(claude_headless):
            result = claude_headless("test prompt")
            assert result["success"]
    """

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
            cwd=str(personal_repo_root),
        )

    return _run_claude
