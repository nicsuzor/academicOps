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
    session_id: str | None = None,
) -> tuple[dict[str, Any], str, list[dict]]:
    """Execute Claude Code in headless mode with session tracking.

    Args:
        prompt: Prompt to send to Claude
        model: Optional model identifier
        timeout_seconds: Command timeout in seconds (default: 300)
        permission_mode: Optional permission mode (e.g., "disabled")
        cwd: Working directory
        session_id: Optional session ID (generated if not provided)

    Returns:
        Tuple of (result_dict, session_id, tool_calls_list)
    """
    import os
    import uuid

    # Check if claude CLI is available
    if not _claude_cli_available():
        return (
            {
                "success": False,
                "output": "",
                "result": {},
                "error": "claude CLI not found in PATH",
            },
            "",
            [],
        )

    if session_id is None:
        session_id = str(uuid.uuid4())

    # Get built plugin directory for testing against correct artifact
    repo_root = get_repo_root()
    plugin_dir_core = str(repo_root / "dist" / "aops-claude")
    plugin_dir_tools = str(repo_root / "dist" / "aops-tools")

    # Build command
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--session-id",
        session_id,
        "--debug",
        "hooks",
        "--no-session-persistence",
        "--plugin-dir",
        plugin_dir_core,
    ]
    if Path(plugin_dir_tools).exists():
        cmd.extend(["--plugin-dir", plugin_dir_tools])

    if model:
        cmd.extend(["--model", model])

    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])
    else:
        # Default to bypassPermissions for tests
        cmd.extend(["--permission-mode", "bypassPermissions"])

    # Set working directory
    if cwd:
        working_dir = cwd
    else:
        import tempfile

        working_dir = Path(tempfile.mkdtemp(prefix="claude-test-"))

    # Build environment
    env = os.environ.copy()
    env["DEBUG_HOOKS"] = "1"
    env["CLAUDE_PLUGIN_ROOT"] = plugin_dir_core
    env["PWD"] = str(working_dir)

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
            check=False,
            env=env,
        )

        # Parse tool calls from session JSONL (even if failed)
        session_file = find_session_jsonl(session_id)
        tool_calls = parse_tool_calls(session_file) if session_file else []

        if result.returncode != 0:
            return (
                {
                    "success": False,
                    "output": result.stdout,
                    "result": {},
                    "error": f"Command failed with exit code {result.returncode}: {result.stderr}",
                },
                session_id,
                tool_calls,
            )

        try:
            parsed_output = json.loads(result.stdout)
            return (
                {
                    "success": True,
                    "output": result.stdout,
                    "result": parsed_output,
                    "stderr": result.stderr,
                },
                session_id,
                tool_calls,
            )
        except json.JSONDecodeError as e:
            return (
                {
                    "success": False,
                    "output": result.stdout,
                    "result": {},
                    "error": f"JSON parse error: {e!s}",
                },
                session_id,
                tool_calls,
            )

    except subprocess.TimeoutExpired:
        session_file = find_session_jsonl(session_id)
        tool_calls = parse_tool_calls(session_file) if session_file else []
        return (
            {
                "success": False,
                "output": "",
                "result": {},
                "error": f"Command timed out after {timeout_seconds} seconds",
            },
            session_id,
            tool_calls,
        )
    except Exception as e:
        session_file = find_session_jsonl(session_id)
        tool_calls = parse_tool_calls(session_file) if session_file else []
        return (
            {
                "success": False,
                "output": "",
                "result": {},
                "error": f"Command execution failed: {e!s}",
            },
            session_id,
            tool_calls,
        )


def _make_failing_wrapper(
    runner: Callable[..., tuple[dict[str, Any], str, list[dict]]],
) -> Callable[..., tuple[dict[str, Any], str, list[dict]]]:
    """Create a wrapper that fails tests on session failure.

    This enforces H37: tests must not pass when underlying functionality fails.
    The wrapper automatically calls pytest.fail() when the session fails,
    preventing Volkswagen tests that "pass by detecting failure correctly."

    Args:
        runner: The underlying run function

    Returns:
        Wrapped function that fails on session failure by default.
    """

    def wrapper(
        prompt: str,
        fail_on_error: bool = True,
        **kwargs,
    ) -> tuple[dict[str, Any], str, list[dict]]:
        result, session_id, tool_calls = runner(prompt, **kwargs)

        if not result["success"] and fail_on_error:
            error_msg = result.get("error", "Unknown error")
            pytest.fail(
                f"Headless session failed (set fail_on_error=False to handle manually): {error_msg}"
            )

        return result, session_id, tool_calls

    return wrapper


@pytest.fixture
def claude_headless():
    """Pytest fixture providing headless Claude Code execution.

    Returns:
        Callable that executes claude command and returns (result, session_id, tool_calls).
        Automatically fails the test if the session fails (H37 enforcement).
    """
    # Skip test if claude CLI not available
    if not _claude_cli_available():
        pytest.fail("claude CLI not found in PATH - requires Claude Code CLI installed")

    return _make_failing_wrapper(run_claude_headless)


def run_gemini_headless(
    prompt: str,
    model: str | None = None,
    timeout_seconds: int = 600,
    permission_mode: str | None = None,
    cwd: Path | None = None,
    gemini_home: Path | None = None,
) -> tuple[dict[str, Any], str, list[dict]]:
    """Execute Gemini CLI in headless mode with session tracking.

    Args:
        prompt: Prompt to send to Gemini
        model: Optional model identifier
        timeout_seconds: Command timeout in seconds (default: 600)
        permission_mode: Optional permission mode
        cwd: Working directory
        gemini_home: Optional path to GEMINI_CLI_HOME

    Returns:
        Tuple of (result_dict, session_id, tool_calls_list)
    """
    # Check if gemini CLI is available
    if not _gemini_cli_available():
        return (
            {
                "success": False,
                "output": "",
                "result": {},
                "error": "gemini CLI not found in PATH",
            },
            "",
            [],
        )

    # Build command
    cmd = ["gemini", "-p", prompt, "-o", "json"]

    if model:
        cmd.extend(["-m", model])

    if permission_mode in ("bypassPermissions", "yolo"):
        cmd.append("--yolo")
    elif permission_mode == "auto_edit":
        cmd.extend(["--approval-mode", "auto_edit"])

    # Set working directory
    if cwd:
        working_dir = cwd
    else:
        import tempfile

        working_dir = Path(tempfile.mkdtemp(prefix="gemini-test-"))

    # Build environment
    env = os.environ.copy()
    from lib.agent_env import apply_env_mappings

    apply_env_mappings(env)

    if gemini_home:
        env["GEMINI_CLI_HOME"] = str(gemini_home)

    if "CLAUDE_PLUGIN_ROOT" not in env and "AOPS" in env:
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

        if result.returncode != 0:
            return (
                {
                    "success": False,
                    "output": result.stdout,
                    "result": {},
                    "error": f"Command failed with exit code {result.returncode}: {result.stderr}",
                },
                "",
                [],
            )

        # Parse JSON output robustly
        parsed_output = {}
        try:
            parsed_output = json.loads(result.stdout)
        except json.JSONDecodeError:
            candidates = []
            output = result.stdout
            for i, char in enumerate(output):
                if char == "{":
                    try:
                        obj, end_idx = json.JSONDecoder().raw_decode(output[i:])
                        candidates.append((i + end_idx, obj))
                    except json.JSONDecodeError:
                        continue
            if candidates:
                _, parsed_output = max(candidates, key=lambda x: x[0])

        # Extract session info if possible
        session_id = ""
        tool_calls = []
        if isinstance(parsed_output, dict):
            # Gemini CLI sometimes includes session info in JSON output
            session_id = parsed_output.get("sessionId", "")
            # Try to extract tool calls from history if present
            history = parsed_output.get("history", [])
            for turn in history:
                for msg in turn.get("messages", []):
                    if msg.get("role") == "assistant":
                        for part in msg.get("parts", []):
                            if "toolCall" in part:
                                tc = part["toolCall"]
                                tool_calls.append(
                                    {"name": tc.get("name"), "input": tc.get("args", {})}
                                )

        return (
            {
                "success": True,
                "output": result.stdout,
                "result": parsed_output,
                "stderr": result.stderr,
            },
            session_id,
            tool_calls,
        )

    except subprocess.TimeoutExpired as e:
        return (
            {
                "success": False,
                "output": e.stdout if isinstance(e.stdout, str) else "",
                "result": {},
                "error": f"Command timed out after {timeout_seconds} seconds",
            },
            "",
            [],
        )
    except Exception as e:
        return (
            {
                "success": False,
                "output": "",
                "result": {},
                "error": f"Command execution failed: {e!s}",
            },
            "",
            [],
        )


@pytest.fixture
def gemini_headless(gemini_home):
    """Pytest fixture providing headless Gemini CLI execution.

    Returns:
        Callable that executes gemini command and returns tuple of
        (result_dict, session_id, tool_calls_list).
        Automatically fails the test if the session fails (H37 enforcement).

    Example:
        def test_something(gemini_headless):
            result, session_id, tool_calls = gemini_headless("What is 2+2?")
            # No need to check result["success"] - fixture fails automatically

    Args passed to callable:
        prompt: The prompt to send
        fail_on_error: If True (default), pytest.fail() on session failure.
                       Set to False to handle errors manually.
        **kwargs: Passed to run_gemini_headless (model, timeout_seconds, etc.)
    """
    # Skip test if gemini CLI not available
    if not _gemini_cli_available():
        pytest.fail("gemini CLI not found in PATH - requires Gemini CLI installed")

    def _run(prompt, **kwargs):
        return run_gemini_headless(prompt, gemini_home=gemini_home, **kwargs)

    return _make_failing_wrapper(_run)


# --- Parameterized CLI fixture for cross-platform tests ---


def _run_claude_docker_simple(
    prompt: str, tmp_path: Path, **kwargs
) -> tuple[dict[str, Any], str, list[dict]]:
    """Run Claude in Docker with session tracking."""
    import uuid

    # Import _build_docker_cmd from polecat
    repo_root = get_repo_root()
    polecat_dir = str(repo_root / "polecat")
    aops_core_dir = str(repo_root / "aops-core")
    if polecat_dir not in sys.path:
        sys.path.insert(0, polecat_dir)
    if aops_core_dir not in sys.path:
        sys.path.insert(0, aops_core_dir)

    from cli import _build_docker_cmd

    session_id = str(uuid.uuid4())
    workspace = tmp_path / f"docker-test-{session_id[:8]}"
    workspace.mkdir(exist_ok=True, parents=True)

    session_dir = tmp_path / f"sessions-{session_id[:8]}"
    session_dir.mkdir(exist_ok=True, parents=True)

    model = kwargs.get("model", "haiku")
    timeout_seconds = kwargs.get("timeout_seconds", 300)

    agent_cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--verbose",
        "--debug",
        "hooks",
        "--session-id",
        session_id,
        "--model",
        model,
        "--max-turns",
        "3",
    ]

    env = {}
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
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

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds, check=False
        )
    except subprocess.TimeoutExpired:
        session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
        tool_calls = parse_tool_calls(session_file) if session_file else []
        return (
            {
                "success": False,
                "output": "",
                "result": {},
                "error": f"Docker session timed out after {timeout_seconds}s",
            },
            session_id,
            tool_calls,
        )

    if result.returncode != 0:
        session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
        tool_calls = parse_tool_calls(session_file) if session_file else []
        return (
            {
                "success": False,
                "output": result.stdout,
                "result": {},
                "error": f"Docker session failed (exit {result.returncode}): {result.stderr[:500]}",
            },
            session_id,
            tool_calls,
        )

    # Parse tool calls
    session_file = find_session_jsonl(session_id, search_dirs=[session_dir])
    tool_calls = parse_tool_calls(session_file) if session_file else []

    try:
        parsed = json.loads(result.stdout)
        if isinstance(parsed, list):
            result_msg = next(
                (m for m in parsed if isinstance(m, dict) and m.get("type") == "result"),
                parsed[-1] if parsed else {},
            )
        else:
            result_msg = parsed
        return (
            {"success": True, "output": result.stdout, "result": result_msg},
            session_id,
            tool_calls,
        )
    except json.JSONDecodeError as e:
        return (
            {
                "success": False,
                "output": result.stdout,
                "result": {},
                "error": f"JSON parse error: {e}",
            },
            session_id,
            tool_calls,
        )


def _run_gemini_docker(
    prompt: str, gemini_home: Path | None = None, **kwargs
) -> tuple[dict[str, Any], str, list[dict]]:
    """Run Gemini with --sandbox (tool calls inside Docker container)."""
    # Ensure polecat is importable
    repo_root = get_repo_root()
    polecat_dir = str(repo_root / "polecat")
    aops_core_dir = str(repo_root / "aops-core")
    if polecat_dir not in sys.path:
        sys.path.insert(0, polecat_dir)
    if aops_core_dir not in sys.path:
        sys.path.insert(0, aops_core_dir)

    timeout_seconds = kwargs.get("timeout_seconds", 300)
    model = kwargs.get("model")

    cmd = ["gemini", "--sandbox", "--yolo", "-p", prompt, "-o", "json"]
    if model:
        cmd.extend(["-m", model])

    env = os.environ.copy()
    env["GEMINI_SANDBOX_IMAGE"] = os.environ.get("GEMINI_SANDBOX_IMAGE", "aops-crew")

    tmp_gemini_home = None
    if gemini_home:
        env["GEMINI_CLI_HOME"] = str(gemini_home)
    else:
        from cli import _replicate_gemini_auth

        tmp_gemini_home = _replicate_gemini_auth(env)

    # Apply credential isolation
    from lib.agent_env import apply_env_mappings

    apply_env_mappings(env)

    try:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_seconds, check=False, env=env
            )
        except subprocess.TimeoutExpired:
            return (
                {
                    "success": False,
                    "output": "",
                    "result": {},
                    "error": f"Gemini sandbox session timed out after {timeout_seconds}s",
                },
                "",
                [],
            )

        if result.returncode != 0:
            return (
                {
                    "success": False,
                    "output": result.stdout,
                    "result": {},
                    "error": f"Gemini sandbox failed (exit {result.returncode}): {result.stderr[:500]}",
                },
                "",
                [],
            )

        # Parse JSON
        parsed = {}
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            candidates = []
            output = result.stdout
            for i, char in enumerate(output):
                if char == "{":
                    try:
                        obj, end_idx = json.JSONDecoder().raw_decode(output[i:])
                        candidates.append((i + end_idx, obj))
                    except json.JSONDecodeError:
                        continue
            if candidates:
                _, parsed = max(candidates, key=lambda x: x[0])

        session_id = ""
        tool_calls = []
        if isinstance(parsed, dict):
            session_id = parsed.get("sessionId", "")
            history = parsed.get("history", [])
            for turn in history:
                for msg in turn.get("messages", []):
                    if msg.get("role") == "assistant":
                        for part in msg.get("parts", []):
                            if "toolCall" in part:
                                tc = part["toolCall"]
                                tool_calls.append(
                                    {"name": tc.get("name"), "input": tc.get("args", {})}
                                )

        return (
            {
                "success": True,
                "output": result.stdout,
                "stderr": result.stderr,
                "result": parsed,
            },
            session_id,
            tool_calls,
        )
    finally:
        if tmp_gemini_home and tmp_gemini_home.exists():
            shutil.rmtree(tmp_gemini_home)


@pytest.fixture(params=["claude-host", "gemini-host", "claude-docker", "gemini-docker"])
def cli_headless(request, tmp_path, gemini_home):
    """Parameterized fixture that yields headless runners across all backends.

    Covers host and Docker execution for both Claude and Gemini.

    Example:
        def test_simple_math(cli_headless):
            runner, platform = cli_headless
            result, session_id, tool_calls = runner("What is 2+2?")
            assert result["success"]

    Returns:
        Tuple of (runner_function, platform_name)

    Backends:
        - claude-host: Claude CLI on host
        - gemini-host: Gemini CLI on host
        - claude-docker: Claude inside aops-crew Docker container
        - gemini-docker: Gemini with --sandbox (tool calls in Docker)
    """
    platform = request.param

    if platform == "claude-host":
        if not _claude_cli_available():
            pytest.skip("claude CLI not found in PATH")
        return _make_failing_wrapper(run_claude_headless), "claude-host"

    elif platform == "gemini-host":
        if not _gemini_cli_available():
            pytest.skip("gemini CLI not found in PATH")

        def _run_gemini(prompt, **kwargs):
            return run_gemini_headless(prompt, gemini_home=gemini_home, **kwargs)

        return _make_failing_wrapper(_run_gemini), "gemini-host"

    elif platform == "claude-docker":
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")
        has_oauth = (Path.home() / ".claude" / ".credentials.json").exists()
        if not os.environ.get("ANTHROPIC_API_KEY") and not has_oauth:
            pytest.skip("No Claude auth for Docker")

        def _run_claude_in_docker(prompt, **kwargs):
            return _run_claude_docker_simple(prompt, tmp_path=tmp_path, **kwargs)

        return _make_failing_wrapper(_run_claude_in_docker), "claude-docker"

    elif platform == "gemini-docker":
        if not _gemini_cli_available():
            pytest.skip("gemini CLI not found in PATH")
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

        def _run_gemini_in_docker(prompt, **kwargs):
            return _run_gemini_docker(prompt, gemini_home=gemini_home, **kwargs)

        return _make_failing_wrapper(_run_gemini_in_docker), "gemini-docker"


@pytest.fixture
def aops_root():
    """Pytest fixture providing aOps framework root path.

    Returns:
        Path: Absolute path to aOps framework root ($AOPS)
    """
    return get_bots_dir()


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
