"""Pytest fixtures for aOps framework tests.

Provides fixtures for common paths and test setup.
All paths resolve using AOPS and ACA_DATA environment variables.
"""

import os
from datetime import UTC
from pathlib import Path

import pytest

from .paths import (
    get_bots_dir,
    get_data_dir,
    get_hooks_dir,
    get_repo_root,
    get_writing_root,
)


def _is_xdist_worker() -> bool:
    """Check if running in an xdist worker process."""
    return os.environ.get("PYTEST_XDIST_WORKER") is not None


@pytest.fixture(autouse=True)
def ensure_test_environment(monkeypatch, tmp_path):
    """Ensure ACA_DATA is set and directories exist for all tests.

    This provides a fallback test environment if ACA_DATA is not set externally.
    """
    if not os.environ.get("ACA_DATA"):
        # Use a stable temp dir for the session if possible, or tmp_path
        # But tmp_path is unique per test.
        # Ideally we want a shared one for the session, but per-test is safer for isolation.
        data_dir = tmp_path / "aca_data"
        monkeypatch.setenv("ACA_DATA", str(data_dir))
    else:
        data_dir = Path(os.environ["ACA_DATA"])

    # Ensure required structure exists
    (data_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (data_dir / "projects").mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    (data_dir / "goals").mkdir(parents=True, exist_ok=True)
    (data_dir / "context").mkdir(parents=True, exist_ok=True)
    # Sessions is sibling of data_root
    (data_dir.parent / "sessions").mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def skip_demo_in_xdist(request):
    """Skip demo tests when running in xdist workers.

    Demo tests need visible print output for human validation (H37a).
    xdist captures worker output, hiding print statements.

    Run demo tests with: pytest -m demo -n 0
    """
    if "demo" in request.keywords and _is_xdist_worker():
        pytest.skip("Demo tests require -n 0 for visible output. Run: pytest -m demo -n 0")


@pytest.fixture
def bots_dir() -> Path:
    """Return Path to framework root (AOPS).

    Legacy alias - framework root is the old "bots" directory.

    Returns:
        Path: Absolute path to framework root ($AOPS)
    """
    return get_bots_dir()


@pytest.fixture
def data_dir() -> Path:
    """Return Path to data directory (ACA_DATA).

    Returns:
        Path: Absolute path to data directory ($ACA_DATA)
    """
    return get_data_dir()


@pytest.fixture
def hooks_dir() -> Path:
    """Return Path to hooks directory.

    Returns:
        Path: Absolute path to hooks/ directory ($AOPS/hooks)
    """
    return get_hooks_dir()


@pytest.fixture
def writing_root() -> Path:
    """Return Path to writing root (framework root).

    Returns:
        Path: Absolute path to framework root ($AOPS)
    """
    return get_writing_root()


@pytest.fixture
def repo_root() -> Path:
    """Return Path to repository root (parent of aops-core plugin).

    GitHub workflows and other repo-level files live here, not in the plugin.

    Returns:
        Path: Absolute path to repository root
    """
    return get_repo_root()


@pytest.fixture
def test_data_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create temporary data directory structure for task tests.

    Creates the standard task directory structure in a temp location
    and sets the ACA_DATA environment variable to point to it.
    Also creates sample task files for tests that need them.

    Args:
        tmp_path: pytest's temporary directory fixture
        monkeypatch: pytest monkeypatch fixture for environment variables

    Returns:
        Path: Path to the temporary tasks directory (where inbox, archived, queue live)
    """
    data_dir = tmp_path / "data"
    tasks_dir = data_dir / "tasks"
    inbox_dir = tasks_dir / "inbox"
    (inbox_dir).mkdir(parents=True)
    (tasks_dir / "queue").mkdir(parents=True)
    (tasks_dir / "archived").mkdir(parents=True)

    # Create sample task files for tests
    _create_sample_task(inbox_dir, "sample-task-1", "High Priority Task", 1, "project-a")
    _create_sample_task(inbox_dir, "sample-task-2", "Medium Priority Task", 2, "project-b")
    _create_sample_task(inbox_dir, "sample-task-3", "Low Priority Task", 3, "project-a")

    # Set ACA_DATA - server reads this directly via task_ops.get_data_dir()
    monkeypatch.setenv("ACA_DATA", str(data_dir))

    return tasks_dir


def _create_sample_task(
    directory: Path, task_id: str, title: str, priority: int, project: str
) -> None:
    """Create a sample task file in markdown format.

    Args:
        directory: Directory to create task file in
        task_id: Task ID for the file
        title: Task title
        priority: Priority level (0-3)
        project: Project name
    """
    from datetime import datetime

    filename = f"{task_id}.md"
    filepath = directory / filename

    # Generate properly formatted content
    now = datetime.now(UTC).isoformat()
    created = datetime(2025, 1, 1, tzinfo=UTC).isoformat()

    content = f"""---
title: {title}
permalink: tasks/{task_id}
type: task
task_id: {task_id}
aliases: []
status: inbox
priority: {priority}
project: {project}
tags: [test, sample]
created: {created}
updated: {now}
---

# {title}

Test task for integration testing with priority {priority}.

This is a sample task created by the test fixture.
- Supports project: {project}

"""
    filepath.write_text(content, encoding="utf-8")


#!/usr/bin/env python3
"""Integration test configuration and fixtures.

Provides:
- claude_headless fixture for headless Claude Code execution
- run_claude_headless function for direct CLI invocation
- pytest configuration for integration/slow markers
"""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from lib.paths import get_plugin_root as get_aops_root


def extract_response_text(result: dict[str, Any]) -> str:
    """Extract text response from claude_headless result.

    Claude CLI returns JSON in two formats:
    1. Dict with "result" key containing text (current format, --output-format json)
    2. List of message objects (legacy debug format)

    This function handles both formats.

    Args:
        result: Dictionary from claude_headless with "result" key

    Returns:
        The text response content

    Raises:
        ValueError: If result structure is unexpected or no response found
        TypeError: If result structure is malformed
    """
    result_data = result.get("result")

    # Handle current CLI format: dict with "result" string field
    if isinstance(result_data, dict):
        # New format: {"type": "result", "result": "response text", ...}
        if "result" in result_data:
            text = result_data.get("result")
            if isinstance(text, str):
                return text
            raise TypeError(
                f"Expected result['result']['result'] to be string, got {type(text).__name__}"
            )
        raise ValueError(f"Dict result missing 'result' field. Keys: {list(result_data.keys())}")

    # Handle string result directly (simplest case)
    if isinstance(result_data, str):
        return result_data

    # Handle legacy format: list of message objects
    if isinstance(result_data, list):
        if not result_data:
            raise ValueError("result['result'] is an empty list - no response found")

        # Extract text from the last message in the chain
        for message in reversed(result_data):
            if not isinstance(message, dict):
                continue

            message_type = message.get("type")

            # Check for result message (final response)
            if message_type == "result":
                result_field = message.get("result")
                if isinstance(result_field, str):
                    return result_field

            # Check for assistant message with content
            if message_type == "assistant":
                message_obj = message.get("message")
                if not isinstance(message_obj, dict):
                    continue

                content = message_obj.get("content")
                if not isinstance(content, list):
                    continue

                # Find text content in the message
                for content_block in content:
                    if not isinstance(content_block, dict):
                        continue

                    if content_block.get("type") == "text":
                        text_value = content_block.get("text")
                        if isinstance(text_value, str):
                            return text_value

        raise ValueError(
            f"Could not extract text from message chain. "
            f"Message types: {[m.get('type') for m in result_data if isinstance(m, dict)]}"
        )

    raise TypeError(
        f"Expected result['result'] to be dict, str, or list, got {type(result_data).__name__}"
    )


def _claude_cli_available() -> bool:
    """Check if claude CLI command is available in PATH."""
    import shutil

    return shutil.which("claude") is not None


def _gemini_cli_available() -> bool:
    """Check if gemini CLI command is available in PATH."""
    import shutil

    return shutil.which("gemini") is not None


def run_claude_headless(
    prompt: str,
    model: str | None = "haiku",
    timeout_seconds: int = 300,
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

    # Check if claude CLI is available
    if not _claude_cli_available():
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": "claude CLI not found in PATH - these tests require Claude Code CLI installed",
        }

    # Get aops-core plugin directory for testing against current code
    aops_root = get_aops_root()
    plugin_dir_core = aops_root
    plugin_dir_tools = aops_root / ".." / "aops-tools"

    # Build command with --debug flag and --no-session-persistence for test isolation
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--debug",
        "--no-session-persistence",
        "--plugin-dir",
        plugin_dir_core,
        "--plugin-dir",
        plugin_dir_tools,
    ]

    if model:
        cmd.extend(["--model", model])

    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])

    # Set working directory - use predictable path for tests
    if cwd:
        working_dir = cwd
    else:
        # Use predictable directory for tests (consistent across runs)
        working_dir = Path("/tmp/claude-test")
        working_dir.mkdir(parents=True, exist_ok=True)

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
            "error": "ACA_DATA environment variable not set - required for memory server tests",
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


def _make_failing_wrapper(
    runner: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    """Create a wrapper that fails tests on session failure.

    This enforces H37: tests must not pass when underlying functionality fails.
    The wrapper automatically calls pytest.fail() when the session fails,
    preventing Volkswagen tests that "pass by detecting failure correctly."

    Args:
        runner: The underlying run function (run_claude_headless, etc.)

    Returns:
        Wrapped function that fails on session failure by default.
    """

    def wrapper(
        prompt: str,
        fail_on_error: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        result = runner(prompt, **kwargs)

        if not result["success"] and fail_on_error:
            error_msg = result.get("error", "Unknown error")
            pytest.fail(
                f"Headless session failed (set fail_on_error=False to handle manually): {error_msg}"
            )

        return result

    return wrapper


@pytest.fixture
def claude_headless():
    """Pytest fixture providing headless Claude Code execution.

    Returns:
        Callable that executes claude command and returns parsed result.
        Automatically fails the test if the session fails (H37 enforcement).

    Example:
        def test_something(claude_headless):
            result = claude_headless("What is 2+2?")
            # No need to check result["success"] - fixture fails automatically

    Args passed to callable:
        prompt: The prompt to send
        fail_on_error: If True (default), pytest.fail() on session failure.
                       Set to False to handle errors manually.
        **kwargs: Passed to run_claude_headless (model, timeout_seconds, etc.)

    Note:
        Tests using this fixture will be skipped if claude CLI is not in PATH.
    """
    # Skip test if claude CLI not available
    if not _claude_cli_available():
        pytest.skip("claude CLI not found in PATH - requires Claude Code CLI installed")

    return _make_failing_wrapper(run_claude_headless)


def run_gemini_headless(
    prompt: str,
    model: str | None = None,
    timeout_seconds: int = 120,
    permission_mode: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Execute Gemini CLI in headless mode.

    Args:
        prompt: Prompt to send to Gemini
        model: Optional model identifier (e.g., "gemini-2.0-flash")
        timeout_seconds: Command timeout in seconds (default: 120)
        permission_mode: Optional permission mode ("yolo" maps to --yolo)
        cwd: Working directory (defaults to /tmp/gemini-test)

    Returns:
        Dictionary with keys:
        - success (bool): Whether execution succeeded
        - output (str): Raw JSON output from gemini command
        - result (dict): Parsed JSON result
        - error (str, optional): Error message if execution failed
    """
    import os

    # Check if gemini CLI is available
    if not _gemini_cli_available():
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": "gemini CLI not found in PATH - these tests require Gemini CLI installed",
        }

    # Build command - use positional prompt with JSON output
    cmd = ["gemini", prompt, "-o", "json"]

    if model:
        cmd.extend(["-m", model])

    # Map permission_mode to Gemini flags
    if permission_mode in ("bypassPermissions", "yolo"):
        cmd.append("--yolo")
    elif permission_mode == "auto_edit":
        cmd.extend(["--approval-mode", "auto_edit"])

    # Set working directory
    if cwd:
        working_dir = cwd
    else:
        working_dir = Path("/tmp/gemini-test")
        working_dir.mkdir(parents=True, exist_ok=True)

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

    # Ensure CLAUDE_PLUGIN_ROOT is set for hooks.json variable expansion
    if "CLAUDE_PLUGIN_ROOT" not in env:
        # aops-core is the plugin root
        env["CLAUDE_PLUGIN_ROOT"] = str(Path(env["AOPS"]) / "aops-core")

    try:
        # Execute command
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )

        # Check for command failure
        if result.returncode != 0:
            return {
                "success": False,
                "output": result.stdout,
                "result": {},
                "error": f"Command failed with exit code {result.returncode}: {result.stderr}",
            }

        # Parse JSON output - robustly handle hook logging noise
        try:
            # Try direct parse first
            parsed_output = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Fallback: look for JSON object boundaries
            # We want the LAST valid JSON object, as that's likely the CLI response
            # (Hooks log earlier)

            # Simple heuristic: Look for { ... } that parse successfully
            candidates = []
            # This regex matches balanced braces is hard, so we'll try a simpler approach:
            # Find all start braces '{'
            output = result.stdout
            for i, char in enumerate(output):
                if char == "{":
                    # Try to parse from here to end, then backtrack if needed
                    # Actually, better to just try parsing substring starting at i
                    try:
                        obj, end_idx = json.JSONDecoder().raw_decode(output[i:])
                        candidates.append((i + end_idx, obj))
                    except json.JSONDecodeError:
                        continue

            if candidates:
                # Use the last successfully parsed object
                _, parsed_output = max(candidates, key=lambda x: x[0])
            else:
                return {
                    "success": False,
                    "output": result.stdout,
                    "result": {},
                    "error": "Could not find valid JSON in output",
                }

        return {
            "success": True,
            "output": result.stdout,
            "result": parsed_output,
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
def gemini_headless():
    """Pytest fixture providing headless Gemini CLI execution.

    Returns:
        Callable that executes gemini command and returns parsed result.

    Example:
        def test_something(gemini_headless):
            result = gemini_headless("What is 2+2?")
            assert result["success"]

    Note:
        Tests using this fixture will be skipped if gemini CLI is not in PATH.
    """
    # Skip test if gemini CLI not available
    if not _gemini_cli_available():
        pytest.skip("gemini CLI not found in PATH - requires Gemini CLI installed")

    return run_gemini_headless


# --- Parameterized CLI fixture for cross-platform tests ---


@pytest.fixture(params=["claude", "gemini"])
def cli_headless(request):
    """Parameterized fixture that yields both Claude and Gemini headless runners.

    Use this for tests that should run on both platforms.

    Example:
        def test_simple_math(cli_headless):
            runner, platform = cli_headless
            result = runner("What is 2+2?")
            assert result["success"]

    Returns:
        Tuple of (runner_function, platform_name)
    """
    platform = request.param

    if platform == "claude":
        if not _claude_cli_available():
            pytest.skip("claude CLI not found in PATH")
        return run_claude_headless, "claude"
    else:
        if not _gemini_cli_available():
            pytest.skip("gemini CLI not found in PATH")
        return run_gemini_headless, "gemini"


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
                            tool_calls.append(
                                {
                                    "name": content.get("name"),
                                    "input": content.get("input", {}),
                                }
                            )
            except json.JSONDecodeError:
                continue
    return tool_calls


def _skill_was_invoked(tool_calls: list[dict], skill_name: str) -> bool:
    """Check if a specific skill was invoked.

    Args:
        tool_calls: List of parsed tool calls
        skill_name: Name of skill to check for (e.g., "memory", "framework")

    Returns:
        True if Skill tool was called with the specified skill
    """
    for call in tool_calls:
        if call["name"] == "Skill":
            skill_param = call["input"].get("skill", "")
            if skill_name in skill_param.lower():
                return True
    return False


def extract_subagent_tool_calls(tool_calls: list[dict]) -> list[dict]:
    """Extract subagent tool calls from a list of main agent tool calls.

    Extracts both Task tool and Skill tool invocations. The Task tool spawns
    actual subagents (separate processes), while Skill tool invokes skills
    within the current agent context.

    Args:
        tool_calls: List of parsed tool calls from main agent session
                   (output of parse_tool_calls())

    Returns:
        List of subagent tool call information dicts with keys:
        - type: "task" or "skill" indicating invocation type
        - name: Subagent type (for Task) or skill name (for Skill)
        - prompt: Task prompt (Task only)
        - args: Arguments (Skill only, may include nested skill names)
        - model: Model used (Task only, if specified)
        - run_in_background: Whether Task runs in background (Task only)
        - input: Raw input dict from the tool call
        - index: Position in the main agent's tool call sequence

    Example:
        # In a test:
        result, session_id, tool_calls = claude_headless_tracked(
            "Use the Explore agent to find Python files"
        )
        subagent_calls = extract_subagent_tool_calls(tool_calls)

        # Check for Task subagent spawns
        task_calls = [c for c in subagent_calls if c["type"] == "task"]
        assert any(c["name"] == "Explore" for c in task_calls)

        # Check for Skill invocations
        skill_calls = [c for c in subagent_calls if c["type"] == "skill"]
        assert any(c["name"] == "framework" for c in skill_calls)
    """
    subagent_calls = []

    for index, call in enumerate(tool_calls):
        call_name = call.get("name", "")
        input_data = call.get("input", {})

        if call_name == "Task":
            # Task tool spawns actual subagents
            subagent_type = input_data.get("subagent_type", "")
            if not subagent_type:
                continue

            subagent_calls.append(
                {
                    "type": "task",
                    "name": subagent_type,
                    "prompt": input_data.get("prompt", ""),
                    "model": input_data.get("model"),
                    "run_in_background": input_data.get("run_in_background", False),
                    "input": input_data,
                    "index": index,
                }
            )

        elif call_name == "Skill":
            # Skill tool invokes skills within current context
            skill_name = input_data.get("skill", "")
            if not skill_name:
                continue

            subagent_calls.append(
                {
                    "type": "skill",
                    "name": skill_name,
                    "args": input_data.get("args", ""),
                    "input": input_data,
                    "index": index,
                }
            )

    return subagent_calls


def extract_task_calls(tool_calls: list[dict]) -> list[dict]:
    """Extract Task tool invocations (subagent spawns) from tool calls.

    This is a convenience helper for tests that only care about Task tool
    invocations, not Skill invocations.

    Args:
        tool_calls: List of parsed tool calls from main agent session

    Returns:
        List of Task invocation dicts with keys:
        - subagent_type: Type of subagent spawned
        - prompt: Task prompt
        - model: Model used (if specified)
        - run_in_background: Whether running in background
        - input: Raw input dict
        - index: Position in tool call sequence

    Example:
        task_calls = extract_task_calls(tool_calls)
        assert any(c["subagent_type"] == "Explore" for c in task_calls)
    """
    task_calls = []

    for index, call in enumerate(tool_calls):
        if call.get("name") != "Task":
            continue

        input_data = call.get("input", {})
        subagent_type = input_data.get("subagent_type", "")

        if not subagent_type:
            continue

        task_calls.append(
            {
                "subagent_type": subagent_type,
                "prompt": input_data.get("prompt", ""),
                "model": input_data.get("model"),
                "run_in_background": input_data.get("run_in_background", False),
                "input": input_data,
                "index": index,
            }
        )

    return task_calls


def task_tool_with_type(tool_calls: list[dict], subagent_type: str) -> bool:
    """Check if Task tool was used with a specific subagent type.

    Args:
        tool_calls: List of parsed tool calls from session
        subagent_type: Expected subagent_type value (e.g., "Explore", "critic")

    Returns:
        True if Task tool was called with matching subagent_type

    Example:
        assert task_tool_with_type(tool_calls, "Explore")
        assert task_tool_with_type(tool_calls, "general-purpose")
    """
    task_calls = extract_task_calls(tool_calls)
    return any(c["subagent_type"] == subagent_type for c in task_calls)


def count_task_calls(tool_calls: list[dict]) -> int:
    """Count number of Task tool invocations.

    Args:
        tool_calls: List of parsed tool calls from session

    Returns:
        Number of Task tool calls

    Example:
        # Verify parallel agent spawn
        assert count_task_calls(tool_calls) >= 2
    """
    return len(extract_task_calls(tool_calls))


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
def extract_subagent_calls():
    """Pytest fixture providing subagent tool call extractor.

    Returns:
        Callable that extracts subagent tool calls (both Task and Skill) from
        main agent tool calls.

    Example:
        def test_subagent_invocation(claude_headless_tracked, extract_subagent_calls):
            result, _, tool_calls = claude_headless_tracked("prompt")
            subagent_calls = extract_subagent_calls(tool_calls)

            # Check for Task subagent spawns
            task_calls = [c for c in subagent_calls if c["type"] == "task"]
            assert any(c["name"] == "Explore" for c in task_calls)

            # Check for Skill invocations
            skill_calls = [c for c in subagent_calls if c["type"] == "skill"]
            assert any(c["name"] == "framework" for c in skill_calls)
    """
    return extract_subagent_tool_calls


@pytest.fixture
def get_task_calls():
    """Pytest fixture providing Task tool call extractor.

    Returns:
        Callable that extracts Task tool invocations from tool calls.

    Example:
        def test_explore_agent(claude_headless_tracked, get_task_calls):
            result, _, tool_calls = claude_headless_tracked("prompt")
            task_calls = get_task_calls(tool_calls)
            assert any(c["subagent_type"] == "Explore" for c in task_calls)
    """
    return extract_task_calls


@pytest.fixture
def check_task_type():
    """Pytest fixture for checking if Task tool was used with specific subagent type.

    Returns:
        Callable that checks if Task tool was called with matching subagent_type.

    Example:
        def test_explore_agent(claude_headless_tracked, check_task_type):
            result, _, tool_calls = claude_headless_tracked("Use Explore agent")
            assert check_task_type(tool_calls, "Explore")
    """
    return task_tool_with_type


@pytest.fixture
def get_task_count():
    """Pytest fixture for counting Task tool invocations.

    Returns:
        Callable that returns number of Task tool calls.

    Example:
        def test_parallel_spawn(claude_headless_tracked, get_task_count):
            result, _, tool_calls = claude_headless_tracked("Spawn 2 agents")
            assert get_task_count(tool_calls) >= 2
    """
    return count_task_calls


@pytest.fixture
def claude_headless_tracked():
    """Pytest fixture providing headless Claude Code with session tracking.

    Returns:
        Callable that executes claude command with session ID tracking.
        Returns tuple of (result dict, session_id, tool_calls list).
        Automatically fails the test if the session fails (H37 enforcement).

    Example:
        def test_something(claude_headless_tracked):
            result, session_id, tool_calls = claude_headless_tracked("What is 2+2?")
            # No need to check result["success"] - fixture fails automatically
            assert any(c["name"] == "Bash" for c in tool_calls)

    Args passed to callable:
        prompt: The prompt to send
        fail_on_error: If True (default), pytest.fail() on session failure.
                       Set to False to handle errors manually.
        **kwargs: model, timeout_seconds, permission_mode, cwd
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
        cwd: Path | None = None,
        fail_on_error: bool = True,
    ) -> tuple[dict, str, list[dict]]:
        """Run claude with session tracking.

        Args:
            prompt: Prompt to send
            model: Model to use (default: haiku)
            timeout_seconds: Command timeout
            permission_mode: Permission mode (default: bypassPermissions)
            cwd: Working directory (defaults to /tmp/claude-test for exclusion from transcription)
            fail_on_error: If True (default), pytest.fail() on session failure

        Returns:
            Tuple of (result dict, session_id, tool_calls list)
        """
        session_id = str(uuid.uuid4())

        # Get aops-core plugin directory for agent availability
        aops_root = get_aops_root()
        plugin_dir_core = aops_root / ".." / "aops-core"
        plugin_dir_tools = aops_root / ".." / "aops-tools"

        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--session-id",
            session_id,
            "--model",
            model,
            "--permission-mode",
            permission_mode,
            "--plugin-dir",
            plugin_dir_core,
            "--plugin-dir",
            plugin_dir_tools,
        ]

        env = os.environ.copy()

        try:
            # Use /tmp/claude-test by default to exclude test sessions from
            # automated transcription (filtered by -tmp-claude-test pattern)
            if cwd:
                test_dir = cwd
            else:
                test_dir = Path("/tmp/claude-test")
                test_dir.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                cmd,
                cwd=test_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=env,
            )

            if result.returncode != 0:
                # Parse tool calls from session file - session may have made progress
                session_file = find_session_jsonl(session_id)
                tool_calls = parse_tool_calls(session_file) if session_file else []
                error_msg = f"Command failed with exit code {result.returncode}: {result.stderr}"
                if fail_on_error:
                    pytest.fail(
                        f"Headless session failed (set fail_on_error=False to handle manually): "
                        f"{error_msg}. Session made {len(tool_calls)} tool calls."
                    )
                return (
                    {
                        "success": False,
                        "output": result.stdout,
                        "result": {},
                        "error": error_msg,
                    },
                    session_id,
                    tool_calls,
                )

            try:
                parsed = json.loads(result.stdout)
                response = {
                    "success": True,
                    "output": result.stdout,
                    "result": parsed,
                }
            except json.JSONDecodeError as e:
                error_msg = f"JSON parse error: {e}"
                if fail_on_error:
                    pytest.fail(
                        f"Headless session failed (set fail_on_error=False to handle manually): "
                        f"{error_msg}"
                    )
                response = {
                    "success": False,
                    "output": result.stdout,
                    "result": {},
                    "error": error_msg,
                }

            # Parse tool calls from session JSONL
            session_file = find_session_jsonl(session_id)
            tool_calls = parse_tool_calls(session_file) if session_file else []

            return response, session_id, tool_calls

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout after {timeout_seconds}s"
            # Still parse tool calls from session file - session may have made progress
            session_file = find_session_jsonl(session_id)
            tool_calls = parse_tool_calls(session_file) if session_file else []
            if fail_on_error:
                pytest.fail(
                    f"Headless session failed (set fail_on_error=False to handle manually): "
                    f"{error_msg}. Session made {len(tool_calls)} tool calls before timeout."
                )
            return (
                {
                    "success": False,
                    "output": "",
                    "result": {},
                    "error": error_msg,
                },
                session_id,
                tool_calls,  # Return actual tool calls, not empty list
            )

    return _run_tracked


def pytest_configure(config):
    """Register custom markers for integration tests."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external systems)",
    )
    config.addinivalue_line("markers", "slow: mark test as slow (may take minutes to complete)")


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    """Auto-mark integration tests based on location."""
    for item in items:
        # Mark all tests in integration/ directory as integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
