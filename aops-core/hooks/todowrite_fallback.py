#!/usr/bin/env python3
"""
PostToolUse hook: Create ad-hoc task when TodoWrite is called without bound task.

Safety net for sessions that skip task routing (e.g., simple prompts, agents
that skip hydration). Ensures every session with a work plan has a task record.

Triggers:
- After TodoWrite tool call
- Only when current_task is None

Exit codes:
    0: Success (always - this hook doesn't block)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))


def extract_task_title_from_todos(tool_input: dict[str, Any]) -> str:
    """Extract task title from first todo item.

    Args:
        tool_input: TodoWrite tool input containing "todos" array

    Returns:
        Task title (max 60 chars) or default
    """
    todos = tool_input.get("todos", [])
    if not todos:
        return "Ad-hoc work session"

    first_todo = todos[0]
    content = first_todo.get("content", "Ad-hoc work session")

    # Truncate to 60 chars for reasonable task titles
    if len(content) > 60:
        content = content[:57] + "..."

    return f"[Ad-hoc] {content}"


def create_adhoc_task(title: str, session_id: str) -> str | None:
    """Create an ad-hoc task directly using TaskStorage.

    Args:
        title: Task title
        session_id: Session ID for logging

    Returns:
        Task ID if created, None on failure
    """
    try:
        from lib.task_storage import TaskStorage
        from lib.task_index import TaskIndex
        from lib.paths import get_data_root

        storage = TaskStorage(get_data_root())

        # Create task with ad-hoc metadata using storage.create_task() which handles ID generation
        task = storage.create_task(
            title=title,
            project=None,  # Goes to inbox
            body=f"Auto-created by TodoWrite fallback hook.\n\nSession: {session_id}\nCreated: {datetime.now(timezone.utc).isoformat()}",
            tags=["ad-hoc", "auto-created"],
        )

        # Save task
        storage.save_task(task)

        # Rebuild index to include the new task
        index = TaskIndex(get_data_root())
        index.rebuild()

        return task.id

    except Exception as e:
        print(f"todowrite_fallback: Failed to create task: {e}", file=sys.stderr)
        return None


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

    # Check if current_task is already set
    try:
        from lib.session_state import get_current_task, set_current_task

        current_task = get_current_task(session_id)
        if current_task:
            # Task already bound - nothing to do
            print(json.dumps({}))
            sys.exit(0)

        # No task bound - create ad-hoc task
        title = extract_task_title_from_todos(tool_input)
        task_id = create_adhoc_task(title, session_id)

        if task_id:
            # Bind the new task to the session
            set_current_task(session_id, task_id, source="fallback_hook")

            output = {
                "systemMessage": f"[Ad-hoc task created] Session had no bound task. Created and bound: {task_id}"
            }
            print(json.dumps(output))
            sys.exit(0)
        else:
            # Failed to create task - log but don't block
            output = {
                "systemMessage": "[Warning] TodoWrite without bound task, failed to create ad-hoc task"
            }
            print(json.dumps(output))
            sys.exit(0)

    except Exception as e:
        # Log error but don't block execution
        print(f"todowrite_fallback hook error: {e}", file=sys.stderr)
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
