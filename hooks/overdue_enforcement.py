"""Overdue enforcement for PreToolUse hook - blocks mutating tools when compliance overdue.

Checks custodiet state to determine if too many tool calls have occurred
without a compliance check. Blocks mutating tools (Edit, Write, Bash) but
allows read-only tools (Read, Glob, Grep) with soft reminder.

This is a hard enforcement gate - it blocks mutating operations.
"""

from __future__ import annotations

import os
from typing import Any

from lib.session_state import load_custodiet_state

# Threshold: Block after this many tool calls without compliance check
THRESHOLD = 7

# Mutating tools that get hard-blocked when overdue
MUTATING_TOOLS = {"Edit", "Write", "Bash", "NotebookEdit"}

# Read-only tools that get soft reminder only
READONLY_TOOLS = {"Read", "Glob", "Grep", "WebFetch", "WebSearch", "LSP"}


def get_session_id() -> str:
    """Get session ID from environment.

    Returns empty string if not found (caller should handle gracefully).
    """
    return os.environ.get("CLAUDE_SESSION_ID", "")


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
            "reason": (
                f"Compliance check overdue ({tool_calls} tool calls since last check). "
                "Spawn custodiet agent before continuing with mutating operations."
            ),
        }

    # Read-only tools: allow (soft reminder handled elsewhere if needed)
    return None
