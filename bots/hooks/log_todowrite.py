#!/usr/bin/env python3
"""
PreToolUse hook for TodoWrite - Session Objective Logging

This hook captures session objectives when the TodoWrite tool is used.
It logs the high-level goals and tasks at the beginning of work, providing
context for what we're trying to accomplish in this session.

This complements the Stop hook logging by capturing:
- What we PLAN to do (TodoWrite hook)
- What we ACTUALLY did (Stop hook)

Exit codes:
    0: Success (allow tool use)
    1: Warning (logged but execution continues)
    2: Error (tool use may be blocked)
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Optional debug logging - gracefully handle missing hook_debug module
try:
    from hook_debug import safe_log_to_debug_file
    HAS_DEBUG = True
except ImportError:
    HAS_DEBUG = False
    def safe_log_to_debug_file(*args, **kwargs):
        """Fallback no-op function when hook_debug is not available."""
        pass


def get_project_dir() -> Path:
    """Get the project directory from environment."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        # Fallback to script location
        return Path(__file__).resolve().parent.parent.parent
    return Path(project_dir)


def extract_todo_objectives(todo_input: dict) -> str:
    """
    Extract concise objectives from TodoWrite input.

    Args:
        todo_input: TodoWrite tool input containing todos array

    Returns:
        Concise summary of objectives
    """
    todos = todo_input.get("todos", [])

    if not todos:
        return "No specific objectives"

    # Focus on in_progress and pending tasks
    objectives = []
    for todo in todos:
        status = todo.get("status", "")
        content = todo.get("content", "")

        # Prioritize in_progress tasks as current objectives
        if status == "in_progress" and content:
            objectives.insert(0, f"→ {content}")
        elif status == "pending" and content:
            objectives.append(f"• {content}")

    if not objectives:
        # If all tasks are completed, note that
        completed_count = sum(1 for t in todos if t.get("status") == "completed")
        if completed_count > 0:
            return f"Completed {completed_count} task(s)"
        return "Session planning"

    # Return first few objectives (keep it concise)
    return "; ".join(objectives[:3])


def log_session_objective(
    project_dir: Path,
    session_id: str,
    objectives: str,
) -> bool:
    """
    Log session objectives to the session log file.

    Args:
        project_dir: Project root directory
        session_id: Session ID
        objectives: Summary of session objectives

    Returns:
        True if logging succeeded, False otherwise
    """
    script_path = (
        project_dir
        / "skills"
        / "task-management"
        / "scripts"
        / "session_log.py"
    )

    if not script_path.exists():
        print(
            f"Warning: Session logging script not found at {script_path}",
            file=sys.stderr,
        )
        return False

    # Build command
    cmd = [
        "python3",
        str(script_path),
        "--session-id",
        session_id,
        "--summary",
        f"Objectives: {objectives}",
    ]

    # Run in background (don't wait for completion)
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception as e:
        print(f"Warning: Failed to log session objective: {e}", file=sys.stderr)
        return False


def main() -> int:
    """Main hook entry point."""

    try:
        # Read input from stdin
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            # Return valid empty response on bad input
            print("{}")
            print(f"Warning: Invalid JSON input: {e}", file=sys.stderr)
            return 0

        # Extract hook data
        tool_name = input_data.get("tool_name")
        tool_input = input_data.get("tool_input", {})
        session_id = input_data.get("session_id", "unknown")

        # Verify this is TodoWrite
        if tool_name != "TodoWrite":
            print("{}")
            return 0

        # Extract objectives from todos
        objectives = extract_todo_objectives(tool_input)

        # Get project directory
        project_dir = get_project_dir()

        # Log objectives in background
        log_session_objective(project_dir, session_id, objectives)

        # Log to debug file for inspection
        output = {
            "objectives": objectives,
        }
        safe_log_to_debug_file("PreToolUse_TodoWrite", input_data, output)

        # Always allow the tool use (return empty JSON with permissionDecision)
        # PreToolUse hooks must return hookSpecificOutput with permissionDecision
        response = {
            "hookSpecificOutput": {
                "permissionDecision": "allow"
            }
        }
        print(json.dumps(response))

        return 0

    except Exception as e:
        # Always return success to prevent blocking tool use
        response = {
            "hookSpecificOutput": {
                "permissionDecision": "allow"
            }
        }
        print(json.dumps(response))
        print(f"Warning: TodoWrite logging hook error: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Ultimate safeguard
        response = {
            "hookSpecificOutput": {
                "permissionDecision": "allow"
            }
        }
        print(json.dumps(response))
        sys.exit(0)
