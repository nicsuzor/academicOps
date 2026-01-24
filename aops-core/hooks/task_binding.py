#!/usr/bin/env python3
"""
PostToolUse hook: Bind/unbind task to session when task MCP operations occur.

Enables session observability by automatically linking every session to a task
when task routing happens. The session state records current_task, allowing
queries like "what task was this session working on?"

Triggers (bind):
- After create_task MCP tool (new task created)
- After update_task MCP tool with status="active" (task claimed)

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


def get_task_id_from_result(tool_result: dict[str, Any]) -> str | None:
    """Extract task_id from MCP tool result.

    Args:
        tool_result: The tool_result dict from hook input

    Returns:
        Task ID string or None if not found
    """
    # MCP task tools return {"success": true, "task": {"id": "...", ...}}
    task = tool_result.get("task", {})
    return task.get("id")


def should_bind_task(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Determine if this tool call should trigger task binding.

    Binding occurs for:
    - create_task: New task created (agent taking ownership)
    - update_task with status="active": Task being claimed

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Parameters passed to the tool

    Returns:
        True if task binding should occur
    """
    # Create task - always bind (agent is creating work to track)
    if tool_name == "mcp__plugin_aops-tools_task_manager__create_task":
        return True

    # Update task - only bind if claiming (status -> active)
    if tool_name == "mcp__plugin_aops-tools_task_manager__update_task":
        new_status = tool_input.get("status", "")
        return new_status == "active"

    return False


def should_unbind_task(tool_name: str, tool_result: dict[str, Any]) -> bool:
    """Determine if this tool call should trigger task unbinding.

    Unbinding occurs for:
    - complete_task: Task completed (session work done)
    - complete_tasks: Batch completion

    Args:
        tool_name: Name of the tool being invoked
        tool_result: Result from the tool

    Returns:
        True if task unbinding should occur
    """
    # Complete task - unbind if successful
    if tool_name == "mcp__plugin_aops-tools_task_manager__complete_task":
        return tool_result.get("success", False)

    # Complete tasks (batch) - unbind if any succeeded
    if tool_name == "mcp__plugin_aops-tools_task_manager__complete_tasks":
        return tool_result.get("success_count", 0) > 0

    return False


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
    tool_result = input_data.get("tool_result") or input_data.get("toolResult", {})

    # Get session ID from environment
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if not session_id:
        print(json.dumps({}))
        sys.exit(0)

    # Check if this tool call should trigger unbinding (task completion)
    if should_unbind_task(tool_name, tool_result):
        try:
            from lib.session_state import clear_current_task, get_current_task

            current = get_current_task(session_id)
            if current:
                clear_current_task(session_id)
                output = {"systemMessage": f"Task completed and unbound from session: {current}"}
                print(json.dumps(output))
                sys.exit(0)
        except Exception as e:
            print(f"task_binding unbind error: {e}", file=sys.stderr)
        print(json.dumps({}))
        sys.exit(0)

    # Check if this tool call should trigger binding
    if not should_bind_task(tool_name, tool_input):
        print(json.dumps({}))
        sys.exit(0)

    # Extract task_id from result
    task_id = get_task_id_from_result(tool_result)
    if not task_id:
        print(json.dumps({}))
        sys.exit(0)

    # Determine binding source
    source = "create" if "create_task" in tool_name else "claim"

    # Bind task to session
    try:
        from lib.session_state import get_current_task, set_current_task

        # Check if already bound to a different task
        current = get_current_task(session_id)
        if current and current != task_id:
            # Already bound to another task - log but don't override
            # (session stays with originally claimed task)
            output = {
                "systemMessage": f"Note: Session already bound to task {current}, ignoring {task_id}"
            }
            print(json.dumps(output))
            sys.exit(0)

        # Bind the task
        set_current_task(session_id, task_id, source=source)

        # Output confirmation
        output = {"systemMessage": f"Task bound to session: {task_id}"}
        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        # Log error but don't block execution
        print(f"task_binding hook error: {e}", file=sys.stderr)
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
