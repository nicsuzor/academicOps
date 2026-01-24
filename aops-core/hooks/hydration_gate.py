#!/usr/bin/env python3
"""
PreToolUse hook: Block or warn when prompt-hydrator hasn't been invoked.

The hydration gate ensures agents invoke the prompt-hydrator subagent before
proceeding with work. This is a mechanical trigger enforcing the v1.0 core loop.

Gate logic:
1. SessionStart creates session state with hydration_pending=True
2. UserPromptSubmit clears pending for / or . prefixes (if it fires)
3. PreToolUse checks hydration_pending flag
4. If pending:
   - WARN mode: Log warning, allow (exit 0)
   - BLOCK mode: Block all tools except Task(prompt-hydrator) (exit 2)
5. When Task tool is used with subagent_type="prompt-hydrator", the gate clears

Note: UserPromptSubmit does NOT fire for the first prompt of a fresh session
(Claude Code limitation), so we rely on SessionStart setting hydration_pending=True.

Bypass conditions (gate always allows):
- Subagent sessions (CLAUDE_AGENT_TYPE environment variable set)
- Task invocations spawning prompt-hydrator
- User bypass prefixes ('.' and '/' handled by UserPromptSubmit setting hydration_pending=False)

Environment variables:
- HYDRATION_GATE_MODE: "warn" (default) or "block"
- CLAUDE_AGENT_TYPE: If set, this is a subagent session (bypass gate)

Exit codes:
    0: Allow (hydration complete, bypassed, or warn mode)
    2: Block (hydration pending in block mode)

Failure mode: FAIL-CLOSED (block on error/uncertainty - safety over convenience)
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from lib.session_state import clear_hydration_pending, is_hydration_pending
from lib.template_loader import load_template

# Default gate mode (can be overridden by HYDRATION_GATE_MODE env var)
DEFAULT_GATE_MODE = "block"

# Template paths
HOOK_DIR = Path(__file__).parent
BLOCK_TEMPLATE = HOOK_DIR / "templates" / "hydration-gate-block.md"
WARN_TEMPLATE = HOOK_DIR / "templates" / "hydration-gate-warn.md"


def get_gate_mode() -> str:
    """Get gate mode from environment, evaluated at runtime for testability.

    Returns DEFAULT_GATE_MODE if env var is unset or empty.
    """
    mode = os.environ.get("HYDRATION_GATE_MODE")
    if mode is None:
        return DEFAULT_GATE_MODE
    mode_stripped = mode.strip().lower()
    return mode_stripped if mode_stripped else DEFAULT_GATE_MODE


def get_block_message() -> str:
    """Load block message from template."""
    return load_template(BLOCK_TEMPLATE)


def get_warn_message() -> str:
    """Load warn message from template."""
    return load_template(WARN_TEMPLATE)


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
    """Get the temporary directory for hydration context (synchronized with user_prompt_submit)."""
    # 1. Check for standard temp dir env var
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        return Path(tmpdir)

    # 2. Gemini-specific discovery logic
    if os.environ.get("GEMINI_CLI"):
        try:
            project_root = os.environ.get("AOPS")
            if not project_root:
                project_root = str(Path.cwd())
            abs_root = str(Path(project_root).resolve())
            project_hash = hashlib.sha256(abs_root.encode()).hexdigest()
            gemini_tmp = Path.home() / ".gemini" / "tmp" / project_hash
            if gemini_tmp.exists():
                return gemini_tmp
        except Exception:
            pass

    # 3. Default fallback for Claude Code
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
        path = str(tool_input.get("file_path", ""))
        return (
            path.startswith("/tmp/claude-hydrator/") or 
            path.startswith(temp_dir)
        )

    # Check for shell commands (cat, etc) on the hydration file
    if tool_name == "run_shell_command":
        cmd = str(tool_input.get("command", ""))
        return (
            "/tmp/claude-hydrator/" in cmd or 
            temp_dir in cmd
        )

    return False


def main():
    """Main hook entry point - checks hydration status and blocks/warns if needed."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # FAIL-CLOSED: block on parse error (safety over convenience)
        print("⛔ HYDRATION GATE: Failed to parse hook input", file=sys.stderr)
        sys.exit(2)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    try:
        session_id = get_session_id(input_data)
    except ValueError as e:
        # FAIL-CLOSED: block on missing session_id (safety over convenience)
        print(f"⛔ HYDRATION GATE: {e}", file=sys.stderr)
        sys.exit(2)

    # BYPASS: Subagent sessions (invoked by main agent)
    if is_subagent_session():
        print(json.dumps({}))
        sys.exit(0)

    # BYPASS: First prompt from CLI (no state exists yet)
    if is_first_prompt_from_cli(session_id):
        print(json.dumps({}))
        sys.exit(0)

    # Check if hydration is pending
    if not is_hydration_pending(session_id):
        # Hydration complete or not required - allow all tools
        print(json.dumps({}))
        sys.exit(0)

    # Hydration pending - check if this is the hydrator being invoked
    # 1. Claude: Task(subagent_type="prompt-hydrator")
    # 2. Gemini: Reading hydration file directly
    if (tool_name == "Task" and is_hydrator_task(tool_input)) or \
       is_gemini_hydration_attempt(tool_name, tool_input):
        # This is the hydrator being spawned/consumed - clear the gate and allow
        clear_hydration_pending(session_id)
        print(json.dumps({}))
        sys.exit(0)

    # Hydration pending - enforce based on mode
    gate_mode = get_gate_mode()
    if gate_mode == "block":
        # Block mode: exit 2 to block the tool
        print(get_block_message(), file=sys.stderr)
        sys.exit(2)
    else:
        # Warn mode (default): log warning but allow (exit 0)
        print(get_warn_message(), file=sys.stderr)
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
