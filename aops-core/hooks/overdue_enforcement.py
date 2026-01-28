"""Overdue enforcement for PreToolUse hook - blocks mutating tools when compliance overdue.

Checks custodiet state to determine if too many tool calls have occurred
without a compliance check. Blocks mutating tools (Edit, Write, Bash) but
allows read-only tools (Read, Glob, Grep) with soft reminder.

This is a hard enforcement gate - it blocks mutating operations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lib.session_state import load_custodiet_state
from lib.template_loader import load_template

# Template path
HOOK_DIR = Path(__file__).parent
BLOCK_TEMPLATE = HOOK_DIR / "templates" / "overdue-enforcement-block.md"

# Threshold: Block after this many tool calls without compliance check
THRESHOLD = 7

# Mutating tools that get hard-blocked when overdue
# Mutating tools that get hard-blocked when overdue
MUTATING_TOOLS = {
    # Claude/Legacy
    "Edit",
    "Write",
    "Bash",
    "NotebookEdit",
    # Gemini
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
    "run_command",  # Assuming generic command runner, could be destructive
    "run_shell_command",
}

# Read-only tools that get soft reminder only
READONLY_TOOLS = {
    # Claude/Legacy
    "Read",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "LSP",
    # Gemini
    "read_file",
    "read_url_content",
    "view_file",
    "view_file_outline",
    "view_code_item",
    "list_dir",
    "find_by_name",
    "grep_search",
    "search_web",
}


def get_session_id() -> str | None:
    """Get session ID from environment.

    Returns None if not found.
    """
    return os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CLAUDE_CWD")


def is_mutating_tool(tool_name: str) -> bool:
    """Check if tool is mutating (can change files/state).

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool can mutate files/state
    """
    return tool_name in MUTATING_TOOLS


def check_overdue(
    tool_name: str, tool_input: dict[str, Any], session_id: str | None = None
) -> dict[str, Any] | None:
    """Check if compliance is overdue and block mutating tools if so.

    Args:
        tool_name: Name of tool being called
        tool_input: Tool input arguments (unused, for future extension)
        session_id: Claude Code session ID (optional, falls back to env var)

    Returns:
        Block response dict if mutating tool blocked, None otherwise
    """
    sid = session_id or get_session_id()
    if not sid:
        # No session_id - fail-open, don't block
        return None

    # Load custodiet state
    state = load_custodiet_state(sid)
    if state is None:
        # No state = first session, no baseline to enforce against
        return None

    tool_calls = state.get("tool_calls_since_compliance", 0)

    # Under threshold - allow everything
    if tool_calls < THRESHOLD:
        return None

    # At or over threshold - check tool type
    if is_mutating_tool(tool_name):
        return {
            "decision": "block",
            "reason": load_template(BLOCK_TEMPLATE, {"tool_calls": str(tool_calls)}),
        }

    # Read-only tools: allow (soft reminder handled elsewhere if needed)
    return None
