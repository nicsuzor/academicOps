#!/usr/bin/env python3
"""
PreToolUse hook: Block when prompt-hydrator hasn't been invoked.

The hydration gate ensures agents invoke the prompt-hydrator subagent before
proceeding with work. This is a mechanical trigger enforcing the v1.0 core loop.

Gate logic:
1. SessionStart creates session state with hydration_pending=True
2. UserPromptSubmit clears pending for / or . prefixes (if it fires)
3. PreToolUse checks hydration_pending flag
4. If pending: BLOCK all tools except Task(prompt-hydrator) (exit 2)
5. When Task tool is used with subagent_type="prompt-hydrator", the gate clears

Note: UserPromptSubmit does NOT fire for the first prompt of a fresh session
(Claude Code limitation), so we rely on SessionStart setting hydration_pending=True.

Bypass conditions (gate always allows):
- Subagent sessions (CLAUDE_AGENT_TYPE environment variable set)
- Task invocations spawning prompt-hydrator
- User bypass prefixes ('.' and '/' handled by UserPromptSubmit setting hydration_pending=False)

Environment variables:
- CLAUDE_AGENT_TYPE: If set, this is a subagent session (bypass gate)
- HYDRATION_GATE_DEBUG: If "1", emit verbose debug output to stderr

Exit codes:
    0: Always (JSON output determines allow/deny via permissionDecision field)

Failure mode: FAIL-CLOSED (block on error/uncertainty - safety over convenience)
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from lib.session_state import clear_hydration_pending, is_hydration_pending
from lib.session_paths import get_session_file_path_direct, get_session_short_hash
from lib.template_loader import load_template

# Template paths
HOOK_DIR = Path(__file__).parent
BLOCK_TEMPLATE = HOOK_DIR / "templates" / "hydration-gate-block.md"


def is_debug_enabled() -> bool:
    """Check if debug output is enabled."""
    return os.environ.get("HYDRATION_GATE_DEBUG", "").strip() == "1"


def debug(msg: str) -> None:
    """Print debug message to stderr if debug is enabled."""
    if is_debug_enabled():
        print(f"[hydration_gate] {msg}", file=sys.stderr)


def get_block_message() -> str:
    """Load block message from template."""
    return load_template(BLOCK_TEMPLATE)


def get_session_id(input_data: dict[str, Any]) -> str:
    """Get session ID from hook input data or environment.

    Args:
        input_data: Hook input data dict

    Returns:
        Session ID string

    Raises:
        ValueError: If session_id is not found in input_data or environment
    """
    session_id = input_data.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
    if not session_id:
        raise ValueError(
            "session_id is required in hook input_data or CLAUDE_SESSION_ID env var. "
            "If you're seeing this error, the hook invocation is missing required context."
        )
    return session_id


def is_subagent_session() -> bool:
    """Check if this is a subagent session.

    Returns:
        True if CLAUDE_AGENT_TYPE is set (indicating subagent context)
    """
    return bool(os.environ.get("CLAUDE_AGENT_TYPE"))


def is_first_prompt_from_cli(session_id: str) -> bool:
    """DEPRECATED: Check if this is the first prompt from CLI.

    This bypass is no longer needed because:
    1. SessionStart hook now creates session state with hydration_pending=True
    2. UserPromptSubmit does NOT fire for first prompt (Claude Code limitation)
    3. Therefore the gate must NOT bypass for first prompt - it should block

    The gate now relies on SessionStart having run first to set hydration_pending.

    Args:
        session_id: Claude Code session ID

    Returns:
        Always False - bypass removed to enforce hydration on first prompt
    """
    # Always return False - first prompt should NOT bypass the gate
    # SessionStart sets hydration_pending=True, so the gate will block appropriately
    return False


def is_hydrator_task(tool_input: dict[str, Any]) -> bool:
    """Check if this is a Task invocation is spawning prompt-hydrator.

    Args:
        tool_input: The tool input parameters

    Returns:
        True if this is a Task call with subagent_type="prompt-hydrator"
    """
    subagent_type = tool_input.get("subagent_type")
    if subagent_type is None:
        return False
    return subagent_type == "prompt-hydrator"


import hashlib

def get_hydration_temp_dir() -> Path:
    """Get the temporary directory for hydration context (synchronized with user_prompt_submit).

    Raises:
        RuntimeError: If Gemini path discovery fails (no silent fallbacks)
    """
    # 1. Check for standard temp dir env var
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        debug(f"Using TMPDIR: {tmpdir}")
        return Path(tmpdir)

    # 2. Gemini-specific discovery logic
    if os.environ.get("GEMINI_CLI"):
        project_root = os.environ.get("AOPS")
        if not project_root:
            project_root = str(Path.cwd())
        abs_root = str(Path(project_root).resolve())
        project_hash = hashlib.sha256(abs_root.encode()).hexdigest()
        gemini_tmp = Path.home() / ".gemini" / "tmp" / project_hash
        if gemini_tmp.exists():
            debug(f"Using Gemini temp dir: {gemini_tmp}")
            return gemini_tmp
        # FAIL-CLOSED: Gemini temp dir doesn't exist, raise instead of falling back
        raise RuntimeError(
            f"GEMINI_CLI is set but temp dir does not exist: {gemini_tmp}. "
            "Create the directory or unset GEMINI_CLI."
        )

    # 3. Default for Claude Code (not a fallback - this is the expected path)
    debug("Using default Claude temp dir: /tmp/claude-hydrator")
    return Path("/tmp/claude-hydrator")


def is_gemini_hydration_attempt(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Check if this is a Gemini agent attempting to read hydration context.

    Gemini CLI doesn't support Task(), so it reads the hydration file directly.

    Args:
        tool_name: Name of the tool being used
        tool_input: The tool input parameters

    Returns:
        True if the tool use matches a hydration context read attempt
    """
    temp_dir = str(get_hydration_temp_dir())
    
    # Check for direct file read
    if tool_name == "read_file":
        file_path = tool_input.get("file_path")
        if file_path is None:
            return False
        path = str(file_path)
        return (
            path.startswith("/tmp/claude-hydrator/") or
            path.startswith(temp_dir)
        )

    # Check for shell commands (cat, etc) on the hydration file
    if tool_name == "run_shell_command":
        command = tool_input.get("command")
        if command is None:
            return False
        cmd = str(command)
        return (
            "/tmp/claude-hydrator/" in cmd or
            temp_dir in cmd
        )

    return False


def main():
    """Main hook entry point - checks hydration status and blocks if needed.

    FAIL-CLOSED: All error paths output permissionDecision:deny. No silent fallbacks.
    """
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # FAIL-CLOSED: block on parse error (safety over convenience)
        # Use JSON permissionDecision:deny with exit 0 so Claude Code processes it
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "additionalContext": f"⛔ HYDRATION GATE: Failed to parse hook input: {e}"
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    tool_name = input_data.get("tool_name")
    if tool_name is None:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "additionalContext": "⛔ HYDRATION GATE: hook input missing required 'tool_name' field"
            }
        }
        print(json.dumps(output))
        sys.exit(0)
    tool_input = input_data.get("tool_input")
    if tool_input is None:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "additionalContext": "⛔ HYDRATION GATE: hook input missing required 'tool_input' field"
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    debug(f"Tool: {tool_name}")

    try:
        session_id = get_session_id(input_data)
    except ValueError as e:
        # FAIL-CLOSED: block on missing session_id (safety over convenience)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "additionalContext": f"⛔ HYDRATION GATE: {e}"
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    short_hash = get_session_short_hash(session_id)
    debug(f"Session: {short_hash} (full: {session_id[:8]}...)")

    # BYPASS: Subagent sessions (invoked by main agent)
    if is_subagent_session():
        debug("ALLOW: Subagent session (CLAUDE_AGENT_TYPE set)")
        print(json.dumps({}))
        sys.exit(0)

    # BYPASS: First prompt from CLI (no state exists yet) - DEPRECATED, always False
    if is_first_prompt_from_cli(session_id):
        debug("ALLOW: First prompt from CLI (deprecated bypass)")
        print(json.dumps({}))
        sys.exit(0)

    # Check if hydration is pending
    hydration_pending = is_hydration_pending(session_id)
    state_file = get_session_file_path_direct(session_id)
    debug(f"State file: {state_file}")
    debug(f"Hydration pending: {hydration_pending}")

    if not hydration_pending:
        # Hydration complete or not required - allow all tools
        debug("ALLOW: Hydration not pending (already complete or bypassed)")
        print(json.dumps({}))
        sys.exit(0)

    # Hydration pending - check if this is the hydrator being invoked
    # 1. Claude: Task(subagent_type="prompt-hydrator")
    # 2. Gemini: Reading hydration file directly
    is_hydrator = (tool_name == "Task" and is_hydrator_task(tool_input))
    is_gemini = is_gemini_hydration_attempt(tool_name, tool_input)
    debug(f"Is hydrator task: {is_hydrator}, Is Gemini hydration: {is_gemini}")

    if is_hydrator or is_gemini:
        # This is the hydrator being spawned/consumed - clear the gate and allow
        debug("ALLOW: Hydrator being invoked - clearing gate")
        clear_hydration_pending(session_id)
        print(json.dumps({}))
        sys.exit(0)

    # FAIL-CLOSED: Hydration pending and not invoking hydrator - BLOCK
    # Use JSON permissionDecision:deny with exit 0 so Claude Code processes it
    debug(f"BLOCK: Hydration pending, tool={tool_name} is not hydrator")
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "additionalContext": get_block_message()
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
