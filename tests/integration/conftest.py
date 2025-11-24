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
        cwd: Working directory (defaults to /tmp/claude-test-XXXXXX)

    Returns:
        Dictionary with keys:
        - success (bool): Whether execution succeeded
        - output (str): Raw JSON output from claude command
        - result (dict): Parsed JSON result
        - error (str, optional): Error message if execution failed
    """
    import os
    import tempfile

    # Check if claude CLI is available
    if not _claude_cli_available():
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": "claude CLI not found in PATH - these tests require Claude Code CLI installed",
        }

    # Build command with --debug flag
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--debug"]

    if model:
        cmd.extend(["--model", model])

    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])

    # Set working directory - always use /tmp for tests
    if cwd:
        working_dir = cwd
    else:
        # Create temporary directory in /tmp for this test run
        working_dir = Path(tempfile.mkdtemp(prefix="claude-test-", dir="/tmp"))

    # Build environment - inherit current environment
    env = os.environ.copy()

    # FAIL FAST: Required environment variables must be set
    if "AOPS" not in env:
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": "AOPS environment variable not set - required for tests",
        }

    if "ACA_DATA" not in env:
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": "ACA_DATA environment variable not set - required for bmem tests",
        }

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


# --- Session tracking fixtures for E2E tool verification ---


def find_session_jsonl(session_id: str) -> Path | None:
    """Find session JSONL file by session ID.

    Args:
        session_id: UUID of the session

    Returns:
        Path to JSONL file if found, None otherwise
    """
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return None

    # Search all project directories for matching session file
    for project_dir in claude_dir.iterdir():
        if not project_dir.is_dir():
            continue
        session_file = project_dir / f"{session_id}.jsonl"
        if session_file.exists():
            return session_file

    return None


def parse_tool_calls(session_file: Path) -> list[dict]:
    """Parse tool calls from session JSONL.

    Args:
        session_file: Path to session JSONL file

    Returns:
        List of tool call dictionaries with 'name' and 'input' keys
    """
    tool_calls = []
    with session_file.open() as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                # Look for tool_use content blocks in assistant messages
                if entry.get("type") == "assistant":
                    message = entry.get("message", {})
                    for content in message.get("content", []):
                        if content.get("type") == "tool_use":
                            tool_calls.append({
                                "name": content.get("name"),
                                "input": content.get("input", {}),
                            })
            except json.JSONDecodeError:
                continue
    return tool_calls


def _skill_was_invoked(tool_calls: list[dict], skill_name: str) -> bool:
    """Check if a specific skill was invoked.

    Args:
        tool_calls: List of parsed tool calls
        skill_name: Name of skill to check for (e.g., "bmem", "framework")

    Returns:
        True if Skill tool was called with the specified skill
    """
    for call in tool_calls:
        if call["name"] == "Skill":
            skill_param = call["input"].get("skill", "")
            if skill_name in skill_param.lower():
                return True
    return False


@pytest.fixture
def skill_was_invoked():
    """Pytest fixture providing skill invocation checker.

    Returns:
        Callable that checks if a skill was invoked in tool_calls.

    Example:
        def test_something(claude_headless_tracked, skill_was_invoked):
            result, _, tool_calls = claude_headless_tracked("prompt")
            assert skill_was_invoked(tool_calls, "framework")
    """
    return _skill_was_invoked


@pytest.fixture
def claude_headless_tracked():
    """Pytest fixture providing headless Claude Code with session tracking.

    Returns:
        Callable that executes claude command with session ID tracking.
        Returns tuple of (result dict, session_id, tool_calls list).

    Example:
        def test_something(claude_headless_tracked):
            result, session_id, tool_calls = claude_headless_tracked("What is 2+2?")
            assert result["success"]
            assert any(c["name"] == "Bash" for c in tool_calls)
    """
    import os
    import subprocess
    import uuid

    # Skip test if claude CLI not available
    if not _claude_cli_available():
        pytest.skip("claude CLI not found in PATH - requires Claude Code CLI installed")

    def _run_tracked(
        prompt: str,
        model: str = "haiku",
        timeout_seconds: int = 120,
        permission_mode: str = "bypassPermissions",
    ) -> tuple[dict, str, list[dict]]:
        """Run claude with session tracking.

        Args:
            prompt: Prompt to send
            model: Model to use (default: haiku)
            timeout_seconds: Command timeout
            permission_mode: Permission mode (default: bypassPermissions)

        Returns:
            Tuple of (result dict, session_id, tool_calls list)
        """
        session_id = str(uuid.uuid4())

        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--session-id", session_id,
            "--model", model,
            "--permission-mode", permission_mode,
        ]

        env = os.environ.copy()

        try:
            result = subprocess.run(
                cmd,
                cwd=Path("/tmp"),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=env,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "output": result.stdout,
                    "result": {},
                    "error": f"Command failed: {result.stderr}",
                }, session_id, []

            try:
                parsed = json.loads(result.stdout)
                response = {
                    "success": True,
                    "output": result.stdout,
                    "result": parsed,
                }
            except json.JSONDecodeError as e:
                response = {
                    "success": False,
                    "output": result.stdout,
                    "result": {},
                    "error": f"JSON parse error: {e}",
                }

            # Parse tool calls from session JSONL
            session_file = find_session_jsonl(session_id)
            tool_calls = parse_tool_calls(session_file) if session_file else []

            return response, session_id, tool_calls

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "result": {},
                "error": f"Timeout after {timeout_seconds}s",
            }, session_id, []

    return _run_tracked


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
