#!/usr/bin/env python3
"""
PostToolUse hook: Bind/unbind task to session when task MCP operations occur.

Enables session observability by automatically linking every session to a task
when task routing happens. The session state records current_task, allowing
queries like "what task was this session working on?"

Triggers (bind):
- After update_task MCP tool with status="in_progress" (task claimed for work)
Note: "active" status means ready/available, not being worked on - no binding.

Triggers (unbind):
- After complete_task MCP tool (task completed)
- After complete_tasks MCP tool (batch completion)

Exit codes:
    0: Success (always - this hook doesn't block)
"""

import json
import os
import sys
from typing import Any

# Re-export from hook_utils for backwards compatibility
from lib.hook_utils import get_task_id_from_result


def main() -> None:
    """Main hook entry point."""
    # Read input from stdin
    input_data: dict[str, Any] = json.load(sys.stdin)

    # Extract tool info (support both naming conventions)
    tool_name = input_data.get("tool_name") or input_data.get("toolName", "")
    tool_input = input_data.get("tool_input") or input_data.get("toolInput", {})

    # Handle Gemini tool_response vs Claude tool_result
    tool_result = (
        input_data.get("tool_result")
        or input_data.get("toolResult")
        or input_data.get("tool_response", {})
    )

    # Get session ID from input_data (Gemini) or environment (Claude)
    session_id = input_data.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
    if not session_id:
        raise ValueError("Missing session_id in input and CLAUDE_SESSION_ID env var")

    # Track state changes
    from lib.event_detector import detect_tool_state_changes, StateChange

    changes = detect_tool_state_changes(tool_name, tool_input, tool_result)

    # 1. PLAN MODE
    if StateChange.PLAN_MODE in changes:
        from lib.session_state import is_plan_mode_invoked, set_plan_mode_invoked

        if not is_plan_mode_invoked(session_id):
            set_plan_mode_invoked(session_id)
            output = {
                "verdict": "allow",
                "system_message": "Plan mode gate passed ✓",
            }
            print(json.dumps(output))
            sys.exit(0)
        
        print(json.dumps({}))
        sys.exit(0)

    # 2. TASK UNBINDING
    if StateChange.UNBIND_TASK in changes:
        from lib.session_state import clear_current_task, get_current_task

        current = get_current_task(session_id)
        if current:
            clear_current_task(session_id)
            output = {
                "verdict": "allow",
                "system_message": f"Task completed and unbound from session: {current}",
            }
            print(json.dumps(output))
            sys.exit(0)
        
        print(json.dumps({}))
        sys.exit(0)

    # 3. TASK BINDING
    if StateChange.BIND_TASK in changes:
        # Extract task_id from result (still need specific logic for this as it depends on extracting ID)
        task_id = get_task_id_from_result(tool_result)
        if not task_id:
            print(json.dumps({}))
            sys.exit(0)

        # Determine binding source
        source = "claim"

        from lib.session_state import get_current_task, set_current_task

        # Check if already bound to a different task
        current = get_current_task(session_id)
        if current and current != task_id:
            # Already bound to another task - log but don't override
            output = {
                "verdict": "allow",
                "system_message": f"Note: Session already bound to task {current}, ignoring {task_id}",
            }
            print(json.dumps(output))
            sys.exit(0)

        # Bind the task
        set_current_task(session_id, task_id, source=source)

        # Output confirmation
        output = {
            "verdict": "allow",
            "system_message": f"Task bound to session: {task_id}",
        }
        print(json.dumps(output))
        sys.exit(0)

    # No changes detected
    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
