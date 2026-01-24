#!/usr/bin/env python3
"""
PostToolUse hook: Validate TodoWrite includes handover step.

Part of the three-gate requirement for destructive operations:
(a) task claimed, (b) critic invoked, (c) todo with handover.

This hook fires after TodoWrite and checks if the todo list contains
a session end/handover step. If found, sets the todo_with_handover flag.

Handover patterns detected (case-insensitive):
- "session end" / "session close" / "session handover"
- "handover" / "hand over" / "hand-over"
- "commit and push" / "final commit"
- "wrap up" / "wrap-up" / "wrapup"
- "conclude session" / "close session"

Exit codes:
    0: Success (always - this hook doesn't block, only tracks state)
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

# Patterns that indicate a handover/session-end step
HANDOVER_PATTERNS = [
    r"\bsession\s*(end|close|handover|completion)\b",
    r"\b(hand\s*over|hand-over|handover)\b",
    r"\b(commit\s+and\s+push|final\s+commit)\b",
    r"\b(wrap\s*up|wrap-up|wrapup)\b",
    r"\b(conclude|close|end)\s+session\b",
    r"\bframework\s+reflection\b",
    r"\bpush\s+changes\b",
    r"\bsession\s+summary\b",
]


def contains_handover_step(todos: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """Check if todo list contains a handover/session-end step.

    Args:
        todos: List of todo items from TodoWrite input

    Returns:
        Tuple of (found, content) where content is the matching todo text
    """
    for todo in todos:
        content = todo.get("content", "")
        active_form = todo.get("activeForm", "")

        # Check both content and activeForm
        for text in [content, active_form]:
            if not text:
                continue
            text_lower = text.lower()
            for pattern in HANDOVER_PATTERNS:
                if re.search(pattern, text_lower):
                    return True, content

    return False, None


def main() -> None:
    """Main hook entry point."""
    # Read input from stdin
    try:
        input_data: dict[str, Any] = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        sys.exit(0)

    # Extract tool info (support both naming conventions)
    tool_name = input_data.get("tool_name") or input_data.get("toolName", "")
    tool_input = input_data.get("tool_input") or input_data.get("toolInput", {})

    # Only handle TodoWrite
    if tool_name != "TodoWrite":
        print(json.dumps({}))
        sys.exit(0)

    # Get session ID from environment
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if not session_id:
        print(json.dumps({}))
        sys.exit(0)

    # Check for handover step in todos
    todos = tool_input.get("todos", [])
    has_handover, handover_content = contains_handover_step(todos)

    if has_handover:
        try:
            from lib.session_state import set_todo_with_handover

            set_todo_with_handover(session_id, handover_content)
            output = {
                "systemMessage": f"[Gate] Todo handover step detected: '{handover_content[:50]}...'"
                if handover_content and len(handover_content) > 50
                else f"[Gate] Todo handover step detected: '{handover_content}'"
            }
            print(json.dumps(output))
        except Exception as e:
            print(f"todowrite_handover_gate hook error: {e}", file=sys.stderr)
            print(json.dumps({}))
    else:
        # No handover step - clear the flag (in case todos were rewritten without one)
        try:
            from lib.session_state import clear_todo_handover

            clear_todo_handover(session_id)
        except Exception:
            pass
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
