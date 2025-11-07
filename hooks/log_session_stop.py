#!/usr/bin/env python3
"""
Session Stop hook for logging session activity.

This hook captures session information and logs it to daily JSON files,
creating a detailed history of work done across sessions.

The hook:
1. Extracts session ID and transcript path from hook input
2. Analyzes the transcript to create a concise summary
3. Logs to daily JSON files in $ACADEMICOPS_PERSONAL/data/sessions/
4. Associates with tasks if applicable
5. Runs silently in the background

Exit codes:
    0: Success (allow stop)
    1: Warning (logged but execution continues)
    2: Error (execution may be affected)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Optional debug logging - gracefully handle missing hook_debug module
try:
    from hook_debug import safe_log_to_debug_file

    HAS_DEBUG = True
except ImportError:
    HAS_DEBUG = False

    def safe_log_to_debug_file(*args, **kwargs):
        """Fallback no-op function when hook_debug is not available."""


def get_project_dir() -> Path:
    """Get the project directory from environment."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        # Fallback to script location
        return Path(__file__).resolve().parent.parent.parent
    return Path(project_dir)


def extract_transcript_summary(transcript_path: str) -> dict:
    """
    Extract a concise summary from the transcript.

    Returns:
        dict with summary information
    """
    summary = {
        "user_messages": 0,
        "assistant_messages": 0,
        "tools_used": set(),
        "files_modified": [],
        "errors": [],
        "accomplishments": [],
    }

    if not os.path.exists(transcript_path):
        return {**summary, "tools_used": []}

    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Count messages
                    if entry.get("type") == "message":
                        role = entry.get("role")
                        if role == "user":
                            summary["user_messages"] += 1
                        elif role == "assistant":
                            summary["assistant_messages"] += 1

                    # Track tool uses
                    if "tool_name" in entry:
                        tool = entry["tool_name"]
                        summary["tools_used"].add(tool)

                        # Track file modifications (deduplicate)
                        if tool in ["Write", "Edit"]:
                            file_path = entry.get("tool_input", {}).get("file_path")
                            if file_path and file_path not in summary["files_modified"]:
                                summary["files_modified"].append(file_path)

                    # Look for errors in tool results
                    if entry.get("type") == "tool_result":
                        content = entry.get("content", "")
                        # Only check string content to avoid false positives
                        if isinstance(content, str) and "error" in content.lower():
                            summary["errors"].append(content[:200])

                except json.JSONDecodeError:
                    continue
    except OSError as e:
        print(f"Warning: Could not read transcript: {e}", file=sys.stderr)

    # Convert set to list for JSON serialization
    summary["tools_used"] = list(summary["tools_used"])

    return summary


def create_session_note(transcript_summary: dict, session_id: str) -> str:
    """
    Create a concise note about the session based on the transcript summary.

    Args:
        transcript_summary: Summary extracted from transcript
        session_id: Session ID

    Returns:
        A concise note describing the session
    """
    tools = transcript_summary.get("tools_used", [])
    files = transcript_summary.get("files_modified", [])
    user_msgs = transcript_summary.get("user_messages", 0)

    # Create a simple summary
    parts = []

    if user_msgs == 0:
        parts.append("No user interaction")
    elif user_msgs == 1:
        parts.append("Brief session")
    elif user_msgs < 5:
        parts.append("Short session")
    else:
        parts.append("Extended session")

    if tools:
        parts.append(f"used {', '.join(tools[:3])}")
        if len(tools) > 3:
            parts.append(f"and {len(tools) - 3} more tools")

    if files:
        parts.append(f"modified {len(files)} file(s)")

    return "; ".join(parts) if parts else "Session activity"


def invoke_session_logger(
    project_dir: Path,
    session_id: str,
    transcript_path: str,
    summary: str,
    task_id: str | None = None,
) -> bool:
    """
    Invoke the session logging script in the background.

    Args:
        project_dir: Project root directory
        session_id: Session ID
        transcript_path: Path to session transcript
        summary: Summary of session activity
        task_id: Optional task ID to associate with

    Returns:
        True if invocation succeeded, False otherwise
    """
    script_path = (
        project_dir / "skills" / "task-management" / "scripts" / "session_log.py"
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
        "--transcript",
        transcript_path,
        "--summary",
        summary,
    ]

    if task_id:
        cmd.extend(["--task-id", task_id])

    # Run in background (don't wait for completion to not block stop)
    try:
        # Use subprocess.Popen to run without blocking
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception as e:
        print(f"Warning: Failed to invoke session logger: {e}", file=sys.stderr)
        return False


def main() -> int:
    """Main hook entry point."""

    try:
        # Read input from stdin
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print("{}")
            print(f"Warning: Invalid JSON input: {e}", file=sys.stderr)
            return 0

        # Extract session info
        session_id = input_data.get("session_id", "unknown")
        transcript_path = input_data.get("transcript_path")
        input_data.get("cwd", ".")

        # Get project directory
        project_dir = get_project_dir()

        # Extract transcript summary
        transcript_summary = {}
        if transcript_path:
            transcript_summary = extract_transcript_summary(transcript_path)

        # Create session note
        session_note = create_session_note(transcript_summary, session_id)

        # Invoke session logger in background
        # Note: We don't wait for it to complete to avoid blocking stop
        invoke_session_logger(
            project_dir,
            session_id,
            transcript_path or "",
            session_note,
            task_id=None,  # Could be extracted from transcript or context
        )

        # Log to debug file for inspection
        output = {
            "session_note": session_note,
            "transcript_summary": transcript_summary,
        }
        safe_log_to_debug_file("SessionStop", input_data, output)

        # Always allow stop (return empty JSON)
        print("{}")

        # Print to stderr for user visibility (if desired)
        # Comment out if you want complete silence
        # print(f"✓ Session logged: {session_note}", file=sys.stderr)

        return 0

    except Exception as e:
        # Always return success to prevent blocking stop
        print("{}")
        print(f"Warning: Session logging hook error: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Ultimate safeguard
        print("{}")
        sys.exit(0)
