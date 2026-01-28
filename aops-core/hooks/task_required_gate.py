#!/usr/bin/env python3
"""
PreToolUse hook: Block destructive operations without task binding.

Enforces task-gated permissions model. Destructive operations (Write, Edit,
destructive Bash) require task binding:

  (a) Task bound - session has an active task via update_task or create_task

Additional gates (b) plan mode invoked and (c) critic invoked are tracked
but not currently enforced.

This ensures all work is tracked and has an audit trail.

Bypass conditions:
- Subagent sessions (CLAUDE_AGENT_TYPE set)
- User bypass prefix '.' (gates_bypassed flag in session state)
- Task operations themselves (create_task, update_task)
- Read-only tools (Read, Glob, Grep, etc.)

Output format (JSON on stdout):
- Allow: {} (empty JSON), exit 0
- Block: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "additionalContext": "..."}}, exit 2
- Warn: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": "..."}}, exit 0

Environment variables:
- TASK_GATE_MODE: "warn" (default) or "block"
- CLAUDE_AGENT_TYPE: If set, this is a subagent session (bypass gate)

Failure mode: FAIL-CLOSED (block on error/uncertainty - safety over convenience)
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from lib.hook_utils import (
    get_session_id as _get_session_id,
    is_subagent_session,
    make_allow_output,
    make_deny_output,
    make_empty_output,
)
from lib.session_state import check_all_gates, get_current_task, load_session_state
from lib.template_loader import load_template

# Template paths
HOOK_DIR = Path(__file__).parent
BLOCK_TEMPLATE = HOOK_DIR / "templates" / "task-gate-block.md"
WARN_TEMPLATE = HOOK_DIR / "templates" / "task-gate-warn.md"

# Default gate mode - start with warn for validation
DEFAULT_GATE_MODE = "warn"

# Destructive Bash command patterns (require task)
DESTRUCTIVE_BASH_PATTERNS = [
    r"\brm\b",  # remove files
    r"\bmv\b",  # move files
    r"\bcp\b",  # copy files (creates new)
    r"\bmkdir\b",  # create directories
    r"\btouch\b",  # create files
    r"\bchmod\b",  # change permissions
    r"\bchown\b",  # change ownership
    r"\bgit\s+commit\b",  # git commit
    r"\bgit\s+push\b",  # git push
    r"\bgit\s+reset\b",  # git reset
    r"\bgit\s+checkout\b.*--",  # git checkout with file paths
    r"\bnpm\s+install\b",  # npm install
    r"\bpip\s+install\b",  # pip install
    r"\buv\s+add\b",  # uv add
    r"\bsed\s+-i\b",  # sed in-place
    r"\bawk\s+-i\b",  # awk in-place
    r">\s*[^&]",  # redirect to file (but not >& which is fd redirect)
    r">>\s*",  # append to file
]

# Safe Bash command patterns (explicitly allowed without task)
SAFE_BASH_PATTERNS = [
    r"^\s*cat\s",  # cat (read)
    r"^\s*head\s",  # head (read)
    r"^\s*tail\s",  # tail (read)
    r"^\s*less\s",  # less (read)
    r"^\s*more\s",  # more (read)
    r"^\s*ls\b",  # ls (read)
    r"^\s*find\s",  # find (read)
    r"^\s*grep\s",  # grep (read)
    r"^\s*rg\s",  # ripgrep (read)
    r"^\s*echo\s",  # echo (output only, unless redirected - caught by redirect pattern)
    r"^\s*pwd\b",  # pwd (read)
    r"^\s*which\s",  # which (read)
    r"^\s*type\s",  # type (read)
    r"^\s*git\s+status\b",  # git status (read)
    r"^\s*git\s+diff\b",  # git diff (read)
    r"^\s*git\s+log\b",  # git log (read)
    r"^\s*git\s+show\b",  # git show (read)
    r"^\s*git\s+branch\b",  # git branch (list)
    r"^\s*npm\s+list\b",  # npm list (read)
    r"^\s*pip\s+list\b",  # pip list (read)
    r"^\s*uv\s+pip\s+list\b",  # uv pip list (read)
]

# Task MCP tools that should always be allowed (they establish binding)
TASK_BINDING_TOOLS = {
    "mcp__plugin_aops-tools_task_manager__create_task",
    "mcp__plugin_aops-tools_task_manager__update_task",
    "mcp__plugin_aops-tools_task_manager__complete_task",
    "mcp__plugin_aops-tools_task_manager__decompose_task",
    "mcp__plugin_aops-tools_task_manager__claim_next_task",
    # Gemini / Short names
    "create_task",
    "update_task",
    "complete_task",
    "decompose_task",
    "claim_next_task",
}


def _gate_status(passed: bool) -> str:
    """Return gate status indicator."""
    return "\u2713" if passed else "\u2717"


def build_block_message(gates: dict[str, bool]) -> str:
    """Build a detailed block message showing which gates are missing.

    Args:
        gates: Dict from check_all_gates() with gate statuses

    Returns:
        Formatted block message
    """
    missing = []
    if not gates["task_bound"]:
        missing.append(
            '(a) Claim a task: `mcp__plugin_aops-tools_task_manager__update_task(id="...", status="active")`'
        )
    if not gates["plan_mode_invoked"]:
        missing.append(
            "(b) Enter plan mode: `EnterPlanMode()` - design your implementation approach first"
        )
    if not gates["critic_invoked"]:
        missing.append(
            '(c) Invoke critic: `Task(subagent_type="aops-core:critic", prompt="Review this plan: ...")`'
        )

    return load_template(
        BLOCK_TEMPLATE,
        {
            "task_bound_status": _gate_status(gates["task_bound"]),
            "plan_mode_invoked_status": _gate_status(gates["plan_mode_invoked"]),
            "critic_invoked_status": _gate_status(gates["critic_invoked"]),
            "todo_with_handover_status": "\u2713",  # Deprecated - always pass
            "missing_gates": "\n".join(missing),
        },
    )


def build_warn_message(gates: dict[str, bool]) -> str:
    """Build a warning message for warn-only mode.

    Args:
        gates: Dict from check_all_gates() with gate statuses

    Returns:
        Formatted warning message
    """
    return load_template(
        WARN_TEMPLATE,
        {
            "task_bound_status": _gate_status(gates["task_bound"]),
            "plan_mode_invoked_status": _gate_status(gates["plan_mode_invoked"]),
            "critic_invoked_status": _gate_status(gates["critic_invoked"]),
            "todo_with_handover_status": "\u2713",  # Deprecated - always pass
        },
    )


def get_gate_mode() -> str:
    """Get gate mode from environment, evaluated at runtime for testability."""
    return os.environ.get("TASK_GATE_MODE", DEFAULT_GATE_MODE).lower()


def get_session_id(input_data: dict[str, Any]) -> str:
    """Get session ID from hook input data or environment (wrapper for compatibility)."""
    return _get_session_id(input_data, require=False)


def is_gates_bypassed(session_id: str) -> bool:
    """Check if gates are bypassed for this session (. prefix)."""
    state = load_session_state(session_id)
    if state is None:
        return False
    inner_state = state.get("state")
    if inner_state is None:
        return False
    gates_bypassed = inner_state.get("gates_bypassed")
    if gates_bypassed is None:
        return False
    return gates_bypassed


def is_destructive_bash(command: str) -> bool:
    """Check if a Bash command is destructive (modifies state).

    Uses a two-pass approach:
    1. Check if command matches safe patterns (allow without task)
    2. Check if command matches destructive patterns (require task)

    Args:
        command: The Bash command string

    Returns:
        True if command is destructive, False if read-only
    """
    # Normalize command for matching
    cmd = command.strip()

    # First check: explicitly safe patterns
    for pattern in SAFE_BASH_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            # But check if there's a redirect that makes it destructive
            if not re.search(r">\s*[^&]|>>\s*", cmd):
                return False

    # Second check: destructive patterns
    for pattern in DESTRUCTIVE_BASH_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True

    # Default: allow (fail-open for unknown commands - they're likely read-only)
    return False


def should_require_task(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Determine if this tool call requires task binding.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        True if task binding required, False otherwise
    """
    # Task binding tools always allowed (they establish binding)
    if tool_name in TASK_BINDING_TOOLS:
        return False

    # File modification tools always require task
    if tool_name in (
        "Write",
        "Edit",
        "NotebookEdit",
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
    ):
        return True

    # Bash commands: check for destructive patterns
    if tool_name in ("Bash", "run_shell_command"):
        command = tool_input.get("command")
        if command is None:
            raise ValueError(f"{tool_name} tool_input missing required 'command' field")
        return is_destructive_bash(command)

    # Gemini run_command (checks CommandLine)
    if tool_name == "run_command":
        command = tool_input.get("CommandLine")
        if command is None:
            # Fallback for some variations?
            command = tool_input.get("command")
        if command is None:
            raise ValueError(
                "run_command tool_input missing required 'CommandLine' field"
            )
        return is_destructive_bash(command)

    # All other tools (Read, Glob, Grep, Task, MCP reads, etc.) don't require task
    return False


def _make_deny_output(message: str) -> dict:
    """Build JSON output for deny/block decision."""
    return make_deny_output(message, "PreToolUse")


def _make_warn_output(message: str) -> dict:
    """Build JSON output for warn (allow with warning) decision."""
    return make_allow_output(message, "PreToolUse")


def main() -> None:
    """Main hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # FAIL-CLOSED: block on parse error
        output = _make_deny_output("⛔ TASK GATE: Failed to parse hook input")
        print(json.dumps(output))
        sys.exit(0)

    tool_name = input_data.get("tool_name")
    if tool_name is None:
        output = _make_deny_output(
            "⛔ TASK GATE: hook input missing required 'tool_name' field"
        )
        print(json.dumps(output))
        sys.exit(0)
    tool_input = input_data.get("tool_input")
    if tool_input is None:
        output = _make_deny_output(
            "⛔ TASK GATE: hook input missing required 'tool_input' field"
        )
        print(json.dumps(output))
        sys.exit(0)
    session_id = get_session_id(input_data)

    # FAIL-CLOSED: if no session_id, block for destructive ops
    if not session_id:
        if should_require_task(tool_name, tool_input):
            output = _make_deny_output("⛔ TASK GATE: No session ID available")
            print(json.dumps(output))
            sys.exit(0)
        # Non-destructive ops can proceed
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    # BYPASS: Subagent sessions
    if is_subagent_session():
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    # BYPASS: User prefix '.'
    if is_gates_bypassed(session_id):
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    # Check if this operation requires task binding
    if not should_require_task(tool_name, tool_input):
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    # Gate check: currently only task_bound is enabled (others disabled for testing)
    # Full four-gate check: task bound, plan mode, critic invoked, todo with handover
    gates = check_all_gates(session_id)

    # TEMP: Only enforce task_bound gate (other 3 disabled for validation)
    if gates["task_bound"]:
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    # Gates not passed - enforce based on mode
    gate_mode = get_gate_mode()
    if gate_mode == "block":
        output = _make_deny_output(build_block_message(gates))
        print(json.dumps(output))
        sys.exit(2)  # Exit 2 = BLOCK per router.py
    else:
        # Warn mode: allow but inject warning as context
        output = _make_warn_output(build_warn_message(gates))
        print(json.dumps(output))
        sys.exit(0)


if __name__ == "__main__":
    main()
