"""Pytest fixtures for aOps framework tests.

Provides fixtures for common paths and test setup.
All paths resolve using AOPS and ACA_DATA environment variables.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC
from pathlib import Path
from typing import Any

import pytest

from .paths import (
    get_bots_dir,
    get_data_dir,
    get_hooks_dir,
    get_repo_root,
    get_writing_root,
)

log = logging.getLogger(__name__)

# Max turns for Claude in test fixtures — higher than the default of 3 to allow
# for hook overhead (hydration gate, custodiet) before reaching the actual task.
TEST_CLAUDE_MAX_TURNS = "10"

# Base CLI args for each backend — single source of truth for headless execution.
CLAUDE_BASE_ARGS = [
    "claude",
    "--dangerously-skip-permissions",
    "--model",
    "haiku",
    "--max-turns",
    TEST_CLAUDE_MAX_TURNS,
]

GEMINI_BASE_ARGS = [
    "gemini",
    "--approval-mode",
    "yolo",
    "--raw-output",
    "--accept-raw-output-risk",
]


def build_claude_agent_cmd(
    prompt: str,
    output_format: str = "json",
    extra_args: list[str] | None = None,
    include_binary: bool = True,
    model: str | None = None,
) -> list[str]:
    """Build Claude CLI args from base args + prompt + extras.

    Set include_binary=False when passing args after '--' to polecat crew
    (the CLI already launches claude).

    Args:
        model: Override the default model from CLAUDE_BASE_ARGS.
    """
    cmd = list(CLAUDE_BASE_ARGS) if include_binary else list(CLAUDE_BASE_ARGS[1:])
    if model is not None:
        # Replace the --model value already set in CLAUDE_BASE_ARGS
        try:
            idx = cmd.index("--model")
            cmd[idx + 1] = model
        except ValueError:
            cmd.extend(["--model", model])
    cmd.extend(["-p", prompt, "--output-format", output_format])
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def build_gemini_agent_cmd(
    prompt: str,
    extra_args: list[str] | None = None,
    include_binary: bool = True,
) -> list[str]:
    """Build Gemini CLI args from base args + prompt + extras.

    Set include_binary=False when passing args after '--' to polecat crew
    (the CLI already launches gemini).
    """
    cmd = list(GEMINI_BASE_ARGS) if include_binary else list(GEMINI_BASE_ARGS[1:])
    cmd.extend(["-p", prompt])
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def _redact_cmd(cmd: list[str]) -> list[str]:
    """Redact secrets and sensitive host paths from command for logging.

    Redacts:
    1. Environment variable values (GH_TOKEN=xxx, etc.)
    2. Host paths in Docker mounts when the container side is sensitive
       (e.g., /Users/nic/.claude.json -> [REDACTED_PATH]:/home/worker/.claude.json)
    """
    redacted = []
    # Match strings like KEY=VALUE
    secret_keys = {
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "AOPS_BOT_GH_TOKEN",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
    }

    for arg in cmd:
        arg_str = str(arg)

        # 1. Redact env var values: KEY=VALUE
        # Exclude paths (containing "/") to avoid misidentifying mount args
        if "=" in arg_str and "/" not in arg_str:
            key, val = arg_str.split("=", 1)
            if key in secret_keys:
                redacted.append(f"{key}=[REDACTED]")
                continue

        # 2. Redact host paths in Docker mounts: src:dst[:mode]
        # Only redact the host side if the container side is a known sensitive path
        if ":" in arg_str:
            parts = arg_str.split(":")
            if len(parts) >= 2:
                # Sensitive destination patterns in the container
                sensitive_dst = [".claude.json", ".claude/", ".gemini/"]
                if any(x in parts[1] for x in sensitive_dst):
                    # Redact the host (source) path
                    parts[0] = "[REDACTED_PATH]"
                    redacted.append(":".join(parts))
                    continue

        redacted.append(arg_str)

    return redacted


def _is_xdist_worker() -> bool:
    """Check if running in an xdist worker process."""
    return os.environ.get("PYTEST_XDIST_WORKER") is not None


@pytest.fixture(scope="session")
def gemini_home(tmp_path_factory) -> Path:
    """Session-scoped fixture to build and link Gemini extension.

    Ensures that extension hooks are active in the test environment
    by building the current code and linking it into a temporary
    GEMINI_CLI_HOME.

    Returns:
        Path: Path to the temporary GEMINI_CLI_HOME directory
    """
    tmp_home = tmp_path_factory.mktemp("gemini_home")
    repo_root = get_repo_root()

    # 1. Build extensions to ensure dist/aops-gemini exists
    build_result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "build.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if build_result.returncode != 0:
        pytest.skip(
            f"Gemini extension build failed (exit {build_result.returncode}): "
            f"{build_result.stderr[:200]}"
        )

    # 2. Setup GEMINI_CLI_HOME structure
    # Gemini CLI expects extensions in ~/.gemini/extensions
    # We map this to <tmp_home>/.gemini/extensions
    dot_gemini = tmp_home / ".gemini"
    dot_gemini.mkdir(parents=True, exist_ok=True)
    ext_dir = dot_gemini / "extensions"
    ext_dir.mkdir(parents=True, exist_ok=True)

    # 2a. Copy original settings and auth to preserve login
    # This ensures that the headless session can authenticate
    orig_gemini = Path.home() / ".gemini"
    for filename in [
        "settings.json",
        "google_accounts.json",
        "oauth_creds.json",
        "installation_id",
        "trustedFolders.json",
        "projects.json",
        "state.json",
    ]:
        src = orig_gemini / filename
        if src.exists():
            if filename == "settings.json":
                # Strip MCP servers to speed up initialization for tests
                try:
                    settings = json.loads(src.read_text())
                    if "mcpServers" in settings:
                        settings["mcpServers"] = {}
                    (dot_gemini / filename).write_text(json.dumps(settings, indent=2))
                except (json.JSONDecodeError, OSError) as e:
                    pytest.fail(f"Failed to parse or write settings.json ({src}): {e}")
            else:
                shutil.copy2(src, dot_gemini / filename)

    # 3. Link extension using 'gemini extensions link'
    # This is safer than manual symlinking as it might update internal registries
    dist_gemini = repo_root / "dist" / "aops-gemini"
    if not dist_gemini.exists():
        pytest.fail(
            f"Build artifact not found: {dist_gemini}. "
            "Expected build.py to produce dist/aops-gemini."
        )

    if not shutil.which("gemini"):
        pytest.fail("gemini CLI not found in PATH - requires Gemini CLI installed")

    # Set GEMINI_CLI_HOME env for the link command
    env = os.environ.copy()
    env["GEMINI_CLI_HOME"] = str(tmp_home)

    # --consent prevents interactive prompts during linking
    result = subprocess.run(
        ["gemini", "extensions", "link", str(dist_gemini), "--consent"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Failed to link Gemini extension (exit {result.returncode}). Stderr: {result.stderr}"
        )

    # 4. Set permissive extension enablement so hooks fire for any workspace path.
    # `gemini extensions link` restricts overrides to /home/<user>/* which won't
    # match test tmp dirs, crew worktrees, or CI workspaces.
    enablement_path = ext_dir / "extension-enablement.json"
    if enablement_path.exists():
        try:
            enablement = json.loads(enablement_path.read_text())
            for ext_name in enablement:
                enablement[ext_name]["overrides"] = ["*"]
            enablement_path.write_text(json.dumps(enablement, indent=2))
        except (json.JSONDecodeError, OSError):
            pass  # Best effort — test will fail downstream if this matters

    return tmp_home


_ORIGINAL_AOPS_SESSIONS = os.environ.get("AOPS_SESSIONS")
_ORIGINAL_ACA_DATA = os.environ.get("ACA_DATA")


@pytest.fixture(scope="session")
def original_env():
    """Returns a dictionary containing original environment variables before they were patched."""
    return {
        "AOPS_SESSIONS": _ORIGINAL_AOPS_SESSIONS,
        "ACA_DATA": _ORIGINAL_ACA_DATA,
    }


@pytest.fixture(autouse=True)
def ensure_test_environment(monkeypatch, tmp_path):
    """Ensure ACA_DATA is set and directories exist for all tests.

    This provides a fallback test environment if ACA_DATA is not set externally.
    """
    # ALWAYS use tmp_path for ACA_DATA to prevent tests from mutating host environment
    data_dir = tmp_path / "aca_data"
    monkeypatch.setenv("ACA_DATA", str(data_dir))

    # Ensure required structure exists
    (data_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (data_dir / "projects").mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    (data_dir / "goals").mkdir(parents=True, exist_ok=True)
    (data_dir / "context").mkdir(parents=True, exist_ok=True)
    # Always use tmp_path for AOPS_SESSIONS to ensure full test isolation
    # (avoids writing alongside external ACA_DATA paths when ACA_DATA is set externally)
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))

    # Redirect UV cache to prevent PermissionError in /opt/suzor/cache/uv
    # This is required for hooks to run successfully under macOS Seatbelt
    uv_cache = tmp_path / "uv_cache"
    uv_cache.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("UV_CACHE_DIR", str(uv_cache))


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

from pathlib import Path

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
        timeout_seconds: Command timeout in seconds (default: 300)
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

    # Get built plugin directory for testing against correct artifact
    repo_root = get_repo_root()
    plugin_dir_core = str(repo_root / "dist" / "aops-claude")

    # Build command with --debug flag and --no-session-persistence for test isolation
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--debug",
        "hooks",
        "--no-session-persistence",
        "--plugin-dir",
        plugin_dir_core,
    ]

    if model:
        cmd.extend(["--model", model])

    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])

    # Set working directory - use unique directory for each session to prevent state clobbering
    if cwd:
        working_dir = cwd
    else:
        import tempfile

        working_dir = Path(tempfile.mkdtemp(prefix="claude-test-"))

    # Build environment - inherit current environment
    env = os.environ.copy()
    env["DEBUG_HOOKS"] = "1"
    env["CLAUDE_PLUGIN_ROOT"] = plugin_dir_core
    env["PWD"] = str(working_dir)

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

    # Apply agent-env-map.conf credential isolation mappings
    from lib.agent_env import apply_env_mappings

    apply_env_mappings(env)

    try:
        # Execute command
        log.debug("Full Launch Command: %s", " ".join(_redact_cmd(cmd)))
        log.debug("Working Directory: %s", working_dir)

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
                "stderr": result.stderr,
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
    model: str | None = "gemini-2.5-flash",
    timeout_seconds: int = 600,
    permission_mode: str | None = None,
    cwd: Path | None = None,
    gemini_home: Path | None = None,
) -> dict[str, Any]:
    """Execute Gemini CLI in headless mode.

    Args:
        prompt: Prompt to send to Gemini
        model: Optional model identifier (e.g., "gemini-2.5-flash")
        timeout_seconds: Command timeout in seconds (default: 600)
        permission_mode: Optional permission mode ("yolo" maps to --yolo)
        cwd: Working directory (defaults to /tmp/gemini-test)
        gemini_home: Optional path to GEMINI_CLI_HOME (overrides system path)

    Returns:
        Dictionary with keys:
        - success (bool): Whether execution succeeded
        - output (str): Raw JSON output from gemini command
        - result (dict): Parsed JSON result
        - error (str, optional): Error message if execution failed
    """
    # Check if gemini CLI is available
    if not _gemini_cli_available():
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": "gemini CLI not found in PATH - these tests require Gemini CLI installed",
        }

    # Build command - use -p for non-interactive prompt with JSON output
    cmd = ["gemini", "-p", prompt, "-o", "json"]

    if model:
        cmd.extend(["-m", model])

    # Map permission_mode to Gemini flags
    if permission_mode in ("bypassPermissions", "yolo"):
        cmd.append("--yolo")
    elif permission_mode == "auto_edit":
        cmd.extend(["--approval-mode", "auto_edit"])

    # Set working directory - use unique directory for each session to prevent state clobbering
    if cwd:
        working_dir = cwd
    else:
        import tempfile

        working_dir = Path(tempfile.mkdtemp(prefix="gemini-test-"))

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

    # Apply agent-env-map.conf credential isolation mappings
    from lib.agent_env import apply_env_mappings

    apply_env_mappings(env)

    # Set GEMINI_CLI_HOME if provided (used by fixture-based tests)
    if gemini_home:
        env["GEMINI_CLI_HOME"] = str(gemini_home)

    # Ensure CLAUDE_PLUGIN_ROOT is set for hooks.json variable expansion
    if "CLAUDE_PLUGIN_ROOT" not in env:
        # aops-core is the plugin root
        env["CLAUDE_PLUGIN_ROOT"] = str(Path(env["AOPS"]) / "aops-core")

    try:
        # Execute command
        log.debug("Full Launch Command: %s", " ".join(_redact_cmd(cmd)))
        log.debug("Working Directory: %s", working_dir)

        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )

        # Gemini may write JSON to stdout or stderr (stderr when extension
        # validation warnings cause non-zero exit, e.g. exit 41).
        raw_output = result.stdout or result.stderr or ""

        # Check for command failure — but Gemini may exit non-zero (e.g. 41 for
        # extension validation warnings) while still producing valid JSON output.
        if result.returncode != 0 and not raw_output.strip():
            return {
                "success": False,
                "output": "",
                "result": {},
                "error": f"Command failed with exit code {result.returncode}: {result.stderr}",
            }

        # Parse JSON output - robustly handle hook logging noise
        try:
            # Try direct parse first
            parsed_output = json.loads(raw_output)
        except json.JSONDecodeError:
            # Fallback: look for JSON object boundaries
            # We want the LAST valid JSON object, as that's likely the CLI response
            # (Hooks log earlier)
            candidates = []
            for i, char in enumerate(raw_output):
                if char == "{":
                    try:
                        obj, end_idx = json.JSONDecoder().raw_decode(raw_output[i:])
                        candidates.append((i + end_idx, obj))
                    except json.JSONDecodeError:
                        continue

            if candidates:
                # Use the last successfully parsed object
                _, parsed_output = max(candidates, key=lambda x: x[0])
            else:
                return {
                    "success": False,
                    "output": raw_output,
                    "result": {},
                    "error": "Could not find valid JSON in output",
                }

        return {
            "success": True,
            "output": raw_output,
            "result": parsed_output,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired as e:
        return {
            "success": False,
            "output": e.stdout if isinstance(e.stdout, str) else "",
            "result": {},
            "error": f"Command timed out after {timeout_seconds} seconds. Stderr: {e.stderr if isinstance(e.stderr, str) else ''}",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "result": {},
            "error": f"Command execution failed: {e!s}",
        }


@pytest.fixture
def gemini_headless(gemini_home):
    """Pytest fixture providing headless Gemini CLI execution.

    Returns:
        Callable that executes gemini command and returns parsed result.
        Automatically fails the test if the session fails (H37 enforcement).

    Example:
        def test_something(gemini_headless):
            result = gemini_headless("What is 2+2?")
            # No need to check result["success"] - fixture fails automatically

    Args passed to callable:
        prompt: The prompt to send
        fail_on_error: If True (default), pytest.fail() on session failure.
                       Set to False to handle errors manually.
        **kwargs: Passed to run_gemini_headless (model, timeout_seconds, etc.)

    Note:
        Tests using this fixture will be skipped if gemini CLI is not in PATH.
    """
    # Skip test if gemini CLI not available
    if not _gemini_cli_available():
        pytest.skip("gemini CLI not found in PATH - requires Gemini CLI installed")

    def _run(prompt, **kwargs):
        return run_gemini_headless(prompt, gemini_home=gemini_home, **kwargs)

    return _make_failing_wrapper(_run)


# --- Session tracking fixtures for E2E tool verification ---


def find_session_jsonl(session_id: str, search_dirs: list[Path] | None = None) -> Path | None:
    """Find session JSONL file by session ID.

    Args:
        session_id: UUID of the session
        search_dirs: Extra directories to search first (e.g. mounted session dirs).
            Searched via rglob before falling back to ~/.claude/projects/.

    Returns:
        Path to JSONL file if found, None otherwise
    """
    # Search provided dirs first (these are the Docker-mounted session dirs)
    if search_dirs:
        for d in search_dirs:
            if not d.exists():
                continue
            for match in d.rglob(f"{session_id}.jsonl"):
                return match

    # Fall back to host's Claude projects directory
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return None

    for project_dir in claude_dir.iterdir():
        if not project_dir.is_dir():
            continue
        session_file = project_dir / f"{session_id}.jsonl"
        if session_file.exists():
            return session_file

    return None


def parse_tool_calls(session_file: Path) -> list[dict]:
    """Parse tool calls from a session file (Claude JSONL or Gemini JSON).

    Args:
        session_file: Path to session file (.jsonl for Claude, .json for Gemini)

    Returns:
        List of tool call dictionaries with 'name' and 'input' keys
    """
    if session_file.suffix == ".json":
        return _parse_gemini_tool_calls(session_file)
    return _parse_claude_tool_calls(session_file)


def _parse_claude_tool_calls(session_file: Path) -> list[dict]:
    """Parse tool calls from Claude JSONL session file."""
    tool_calls = []
    with session_file.open() as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
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


# Gemini tool names to search for in message content strings
_GEMINI_TOOL_NAMES = [
    "run_shell_command",
    "read_file",
    "write_file",
    "replace",
    "grep_search",
    "glob",
    "list_directory",
    "create_task",
    "get_task",
    "update_task",
    "complete_task",
    "list_tasks",
    "task_search",
    "activate_skill",
]


def _parse_gemini_tool_calls(session_file: Path) -> list[dict]:
    """Parse tool calls from Gemini JSON session file.

    Gemini stores tool calls as structured ``toolCalls`` arrays inside
    each model message.  Falls back to grepping for known tool names
    in the ``content`` string when structured data is absent.
    """
    import re

    data = json.loads(session_file.read_text())
    tool_calls = []
    for msg in data.get("messages", []):
        if msg.get("type") != "gemini":
            continue

        # Prefer structured toolCalls (Gemini CLI >= 0.5)
        for tc in msg.get("toolCalls", []):
            tool_calls.append({"name": tc.get("name", ""), "input": tc.get("args", {})})

        # Fallback: grep known tool names in content string
        if not msg.get("toolCalls"):
            content = msg.get("content", "")
            if isinstance(content, str):
                for tool_name in _GEMINI_TOOL_NAMES:
                    if re.search(rf"\b{tool_name}\b", content):
                        tool_calls.append({"name": tool_name, "input": {}})
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
def claude_headless_tracked(tmp_path):
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
        """Run claude with session tracking."""
        import json

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
            "--no-session-persistence",
        ]

        env = os.environ.copy()

        try:
            # Use a safe temporary directory to avoid Seatbelt permission errors
            if cwd:
                test_dir = cwd
            else:
                test_dir = tmp_path / "claude-test"
                test_dir.mkdir(parents=True, exist_ok=True)

            log.debug("Full Launch Command: %s", " ".join(_redact_cmd(cmd)))
            log.debug("Working Directory: %s", test_dir)

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


def pytest_collection_modifyitems(config, items):
    """Auto-mark integration tests and configure slow test execution."""
    # First: auto-mark tests in integration/ directory so all_slow check sees them
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

    # If ALL collected tests are slow/integration, disable xdist parallelism.
    # These tests spawn Docker containers and LLM sessions that compete for
    # resources and hit the global pytest-timeout when run in parallel.
    all_slow = all(
        any(m.name in ("slow", "integration") for m in item.iter_markers()) for item in items
    )
    if all_slow and items:
        try:
            workercount = config.getoption("numprocesses", default=None)
            if workercount and workercount != 0:
                config.option.numprocesses = 0
                log.info("All tests are slow/integration — disabled xdist parallelism")
        except (ValueError, AttributeError):
            pass

    for item in items:
        # Give slow tests a generous timeout (10 min) instead of the global default
        if any(m.name == "slow" for m in item.iter_markers()):
            # Don't override an explicit timeout marker already on the test
            if not any(m.name == "timeout" for m in item.iter_markers()):
                item.add_marker(pytest.mark.timeout(600))


def check_blocked(result: dict) -> bool:
    """Check if the agent was blocked.

    Args:
        result: Dictionary from claude_headless or gemini_headless

    Returns:
        True if the agent was blocked, False otherwise.
    """
    import json

    parts = []
    for key in ("output", "result"):
        val = result.get(key, "")
        if isinstance(val, dict | list):
            val = json.dumps(val)
        parts.append(str(val))

    combined = " ".join(parts).lower()

    block_indicators = ["hydration", "blocked", "gate", "pending", "access denied", "denied"]
    return any(indicator in combined for indicator in block_indicators)


# ---------------------------------------------------------------------------
# Docker-containerised Claude fixtures
# ---------------------------------------------------------------------------


def _docker_available() -> bool:
    """Check if Docker is available and the aops-crew image exists."""
    try:
        result = subprocess.run(
            ["docker", "images", "aops-crew", "--format", "{{.Repository}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "aops-crew" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture
def claude_docker(tmp_path):
    """Run Claude inside Docker container, matching polecat crew behavior.

    Returns callable with same API as claude_headless_tracked::

        result, session_id, tool_calls = claude_docker(
            "What is 2+2?",
            timeout_seconds=60,
        )

    Skips if: Docker unavailable, no Claude auth, or aops-crew image not built.
    Claude authenticates via OAuth (stored in ~/.claude/.credentials.json) which is
    bind-mounted into the container. Falls back to ANTHROPIC_API_KEY if set.
    """
    import uuid

    if not _docker_available():
        pytest.skip("Docker not available or aops-crew image not built")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    has_oauth = (Path.home() / ".claude" / ".credentials.json").exists()
    if not api_key and not oauth_token and not has_oauth:
        pytest.skip(
            "No Claude auth: neither ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, nor OAuth credentials found"
        )

    # Import _build_docker_cmd from polecat
    repo_root = get_repo_root()
    polecat_dir = str(repo_root / "polecat")
    aops_core_dir = str(repo_root / "aops-core")
    if polecat_dir not in sys.path:
        sys.path.insert(0, polecat_dir)
    if aops_core_dir not in sys.path:
        sys.path.insert(0, aops_core_dir)

    from cli import _build_docker_cmd

    def _run_in_docker(
        prompt: str,
        model: str = "haiku",
        timeout_seconds: int = 120,
        fail_on_error: bool = True,
    ) -> tuple[dict, str, list[dict]]:
        """Run Claude in Docker with session tracking."""
        session_id = str(uuid.uuid4())

        # Create workspace directory
        workspace = tmp_path / f"docker-test-{session_id[:8]}"
        workspace.mkdir()

        # Create session directory so Claude transcripts persist on the host
        session_dir = tmp_path / f"sessions-{session_id[:8]}"
        session_dir.mkdir()

        # Build agent command — use --verbose so stdout includes the init
        # message (with apiKeySource, mcp_servers status, etc.) as a JSON array
        agent_cmd = build_claude_agent_cmd(
            prompt,
            output_format="json",
            model=model,
            extra_args=[
                "--verbose",
                "--debug",
                "hooks",
                "--session-id",
                session_id,
            ],
        )

        # Build Docker command via polecat's builder
        env = {}
        if api_key:
            env["ANTHROPIC_API_KEY"] = api_key
        if oauth_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
        # Forward ACA_DATA if set
        aca_data = os.environ.get("ACA_DATA")
        if aca_data:
            env["ACA_DATA"] = aca_data

        cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=workspace,
            env=env,
            agent_cmd=agent_cmd,
            is_interactive=False,
            session_dir=session_dir,
        )

        log.debug("Docker command: %s", " ".join(_redact_cmd(cmd)))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            # Try to extract partial progress from session file
            session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
            tool_calls = parse_tool_calls(session_file) if session_file else []
            error_msg = f"Docker session timed out after {timeout_seconds}s"
            if fail_on_error:
                pytest.fail(f"{error_msg}. Session made {len(tool_calls)} tool calls.")
            return (
                {"success": False, "output": "", "result": {}, "error": error_msg},
                session_id,
                tool_calls,
            )

        if result.returncode != 0:
            session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
            tool_calls = parse_tool_calls(session_file) if session_file else []
            error_msg = (
                f"Docker session failed (exit {result.returncode}): "
                f"{result.stderr[:500] if result.stderr else 'no stderr'}"
            )
            if fail_on_error:
                pytest.fail(f"{error_msg}. Session made {len(tool_calls)} tool calls.")
            return (
                {"success": False, "output": result.stdout, "result": {}, "error": error_msg},
                session_id,
                tool_calls,
            )

        # Parse JSON output — Claude --output-format json writes a JSON array:
        # [{"type":"system","subtype":"init",...}, {"type":"result",...}]
        # or a single JSON object for the result.
        try:
            parsed = json.loads(result.stdout)
            # Normalise: extract the result message from an array if needed
            if isinstance(parsed, list):
                result_msg = next(
                    (m for m in parsed if isinstance(m, dict) and m.get("type") == "result"),
                    parsed[-1] if parsed else {},
                )
                init_msg = next(
                    (m for m in parsed if isinstance(m, dict) and m.get("type") == "system"),
                    {},
                )
            else:
                result_msg = parsed
                init_msg = {}
            response = {
                "success": True,
                "output": result.stdout,
                "stderr": result.stderr,
                "result": result_msg,
                "init": init_msg,
            }
        except json.JSONDecodeError as e:
            error_msg = f"JSON parse error: {e}. stdout: {result.stdout[:200]}"
            if fail_on_error:
                pytest.fail(error_msg)
            response = {
                "success": False,
                "output": result.stdout,
                "stderr": result.stderr,
                "result": {},
                "error": error_msg,
            }

        # Include session_dir in response so tests can find transcripts
        response["session_dir"] = session_dir

        # Extract tool calls from session JSONL (written to bind-mounted ~/.claude/)
        session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
        tool_calls = parse_tool_calls(session_file) if session_file else []

        return response, session_id, tool_calls

    return _run_in_docker


@pytest.fixture
def gemini_docker(tmp_path):
    """Run Gemini inside Docker container with a mounted session_dir.

    Returns callable with same API as claude_docker:
        result, session_id, tool_calls = gemini_docker(
            "Reply with hello", timeout_seconds=90
        )
    """
    import json
    import os
    import subprocess
    import sys
    import uuid
    from pathlib import Path

    if not _docker_available():
        pytest.skip("Docker not available or aops-crew image not built")
    if not _gemini_cli_available():
        pytest.skip("Gemini CLI not available")

    # Import polecat helpers
    repo_root = get_repo_root()
    polecat_dir = str(repo_root / "polecat")
    aops_core_dir = str(repo_root / "aops-core")
    if polecat_dir not in sys.path:
        sys.path.insert(0, polecat_dir)
    if aops_core_dir not in sys.path:
        sys.path.insert(0, aops_core_dir)

    from cli import _replicate_gemini_auth

    def _run_in_docker(
        prompt: str,
        timeout_seconds: int = 120,
        fail_on_error: bool = True,
    ) -> tuple[dict, str, list[dict]]:
        session_id = str(uuid.uuid4())

        workspace = tmp_path / f"docker-test-{session_id[:8]}"
        workspace.mkdir(parents=True, exist_ok=True)

        # The clean host directory where we expect logs to persist
        session_dir = tmp_path / f"sessions-{session_id[:8]}"
        session_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()

        # Set up auth replication exactly as polecat/cli.py does
        tmp_gemini_home = _replicate_gemini_auth(env, work_dir=workspace)
        if not tmp_gemini_home:
            pytest.skip("Gemini auth replication failed")

        env.setdefault("GEMINI_SANDBOX_IMAGE", "aops-crew")

        gemini_slug = "docker-test"
        # Match how polecat/cli.py mounts the volume using the native Gemini log path inside the sandbox
        if tmp_gemini_home:
            container_sessions_dir = str(tmp_gemini_home / ".gemini" / "tmp" / gemini_slug)
        else:
            container_sessions_dir = str(Path.home() / ".gemini" / "tmp" / gemini_slug)

        env["AOPS_SESSION_STATE_DIR"] = container_sessions_dir

        # In polecat/cli.py this goes in SANDBOX_MOUNTS
        mounts = env.get("SANDBOX_MOUNTS", "")
        new_mount = f"{session_dir.resolve()}:{container_sessions_dir}:rw"
        env["SANDBOX_MOUNTS"] = f"{mounts},{new_mount}" if mounts else new_mount
        env["GEMINI_SESSION_ID"] = f"gemini-{session_id}"

        from lib.agent_env import apply_env_mappings

        apply_env_mappings(env)

        # Prepare prompt to write output to a file for robust extraction
        # This bypasses all CLI noise (warnings, ANSI, etc.)
        result_file_name = "test_result.json"
        staged_prompt = (
            f"{prompt}\n\nIMPORTANT: When you have the final answer, YOU MUST "
            f"write it as a JSON object to the file '{result_file_name}' in the "
            "current directory. The JSON object must have a 'response' field."
        )

        cmd = [
            "gemini",
            "--approval-mode",
            "yolo",
            "--raw-output",
            "--accept-raw-output-risk",
            "-p",
            staged_prompt,
            "-o",
            "json",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=env,
                cwd=workspace,
            )
        except subprocess.TimeoutExpired:
            res = {
                "success": False,
                "output": "",
                "result": {},
                "error": "Timeout",
                "session_dir": session_dir,
            }
            if fail_on_error:
                pytest.fail("Timeout")
            return res, session_id, []

        # First attempt: Read result from file (most robust)
        result_file = workspace / result_file_name
        if result_file.exists():
            try:
                parsed = json.loads(result_file.read_text())
                return (
                    {
                        "success": True,
                        "output": result.stdout,
                        "stderr": result.stderr,
                        "result": parsed,
                        "session_dir": session_dir,
                    },
                    session_id,
                    [],
                )
            except json.JSONDecodeError:
                pass

        try:
            parsed = json.loads(result.stdout)
            res = {
                "success": True,
                "output": result.stdout,
                "result": parsed,
                "session_dir": session_dir,
            }
        except json.JSONDecodeError as e:
            res = {
                "success": False,
                "output": result.stdout,
                "result": {},
                "error": str(e),
                "session_dir": session_dir,
            }
            if fail_on_error:
                pytest.fail(f"JSON decode error: {e}")

        return res, session_id, []

    return _run_in_docker
