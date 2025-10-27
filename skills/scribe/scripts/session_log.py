#!/usr/bin/env python3
"""
Session logging script for task management.

Creates daily JSON log files tracking what was done in each session,
associates entries with tasks, and updates task files with progress.
"""

import argparse
import fcntl
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_data_dir() -> Path:
    """Get the data directory from environment."""
    personal_dir = os.environ.get("ACADEMICOPS_PERSONAL")
    if not personal_dir:
        print("Error: ACADEMICOPS_PERSONAL not set", file=sys.stderr)
        sys.exit(1)
    return Path(personal_dir) / "data"


def get_daily_log_path(data_dir: Path, date: str) -> Path:
    """
    Get the path to today's session log file.

    Args:
        data_dir: Base data directory
        date: Date string in YYYY-MM-DD format

    Returns:
        Path to the daily log file

    Raises:
        ValueError: If date format is invalid (prevents path traversal)
    """
    # Validate date format to prevent path traversal attacks
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise ValueError(f"Invalid date format: {date}. Expected YYYY-MM-DD")

    log_dir = data_dir / "sessions"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{date}.json"


def append_to_daily_log(log_path: Path, new_entry: dict) -> bool:
    """
    Atomically append a new entry to the daily log file.

    Uses file locking and atomic write pattern (write-to-temp-then-rename)
    to prevent race conditions and data corruption when multiple sessions
    end simultaneously.

    Args:
        log_path: Path to the daily log file
        new_entry: New log entry to append

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure parent directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Use a lock file to coordinate access
        lock_path = log_path.parent / f"{log_path.name}.lock"

        with open(lock_path, "w") as lock_file:
            # Acquire exclusive lock for entire read-modify-write operation
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            try:
                # Read existing entries
                entries = []
                if log_path.exists():
                    try:
                        with open(log_path, "r") as f:
                            entries = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        # If file is corrupted, start fresh
                        entries = []

                # Append new entry
                entries.append(new_entry)

                # Write to temporary file in same directory (atomic rename requires same filesystem)
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=log_path.parent,
                    prefix=f".{log_path.name}.tmp.",
                    text=True
                )

                try:
                    with os.fdopen(temp_fd, 'w') as temp_file:
                        json.dump(entries, temp_file, indent=2)
                        # Ensure data is written to disk before rename
                        temp_file.flush()
                        os.fsync(temp_file.fileno())

                    # Atomic rename (replaces old file)
                    os.rename(temp_path, log_path)

                except Exception as e:
                    # Clean up temp file on error
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                    raise e

            finally:
                # Release lock (also happens automatically when file closes)
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

        # Clean up lock file (best effort, not critical)
        try:
            lock_path.unlink()
        except OSError:
            pass

        return True

    except Exception as e:
        print(f"Error appending to daily log: {e}", file=sys.stderr)
        return False


def extract_session_summary(transcript_path: Optional[str]) -> dict:
    """
    Extract a concise summary from the session transcript.

    This is a simple implementation that counts tool uses and extracts
    basic information. Can be enhanced with AI summarization later.
    """
    summary = {
        "tools_used": [],
        "files_modified": [],
        "commands_run": [],
    }

    if not transcript_path or not os.path.exists(transcript_path):
        return summary

    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Track tool uses
                    if "tool_name" in entry:
                        tool = entry["tool_name"]
                        if tool not in summary["tools_used"]:
                            summary["tools_used"].append(tool)

                        # Track file modifications
                        if tool in ["Write", "Edit"]:
                            file_path = entry.get("tool_input", {}).get("file_path")
                            if file_path and file_path not in summary["files_modified"]:
                                summary["files_modified"].append(file_path)

                        # Track bash commands
                        if tool == "Bash":
                            cmd = entry.get("tool_input", {}).get("command", "")
                            if cmd:
                                # Store first 100 chars of command
                                cmd_summary = cmd[:100] + "..." if len(cmd) > 100 else cmd
                                if cmd_summary not in summary["commands_run"]:
                                    summary["commands_run"].append(cmd_summary)

                except json.JSONDecodeError:
                    continue
    except IOError:
        pass

    return summary


def update_task_progress(
    data_dir: Path, task_id: str, progress_note: str, session_id: str
) -> bool:
    """
    Update a task file with progress information.

    Args:
        data_dir: Base data directory
        task_id: Task identifier
        progress_note: Note describing progress made
        session_id: Session identifier

    Returns:
        True if task was found and updated, False otherwise
    """
    # Search for task in inbox, queue, and archived
    for subdir in ["inbox", "queue", "archived"]:
        task_path = data_dir / "tasks" / subdir / f"{task_id}.json"
        if task_path.exists():
            try:
                with open(task_path) as f:
                    task = json.load(f)

                # Add progress entry
                if "progress" not in task:
                    task["progress"] = []

                task["progress"].append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "note": progress_note,
                })

                # Update modified timestamp
                task["modified"] = datetime.now(timezone.utc).isoformat()

                # Save back
                with open(task_path, "w") as f:
                    json.dump(task, f, indent=2)

                return True
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not update task {task_id}: {e}", file=sys.stderr)
                return False

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Log session activity to daily JSON files"
    )
    parser.add_argument("--session-id", required=True, help="Session ID")
    parser.add_argument("--transcript", help="Path to session transcript")
    parser.add_argument("--summary", help="Concise summary of what was done")
    parser.add_argument("--finished", action="store_true", help="Mark as finished")
    parser.add_argument("--next-step", help="What to do next")
    parser.add_argument("--task-id", help="Associated task ID (optional)")
    parser.add_argument(
        "--progress-note", help="Progress note to add to task (if task-id provided)"
    )

    args = parser.parse_args()

    # Get data directory
    data_dir = get_data_dir()

    # Get today's date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Get log path
    log_path = get_daily_log_path(data_dir, today)

    # Extract session summary from transcript
    session_summary = extract_session_summary(args.transcript)

    # Create new entry
    entry = {
        "session_id": args.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": args.summary or "Session activity",
        "finished": args.finished,
        "next_step": args.next_step,
        "task_id": args.task_id,
        "tools_used": session_summary["tools_used"],
        "files_modified": session_summary["files_modified"],
        "commands_run": session_summary["commands_run"],
    }

    # Atomically append to daily log (handles locking and race conditions)
    if not append_to_daily_log(log_path, entry):
        print(json.dumps({"success": False, "error": "Failed to append to log"}))
        sys.exit(1)

    # Update task progress if task_id provided
    if args.task_id and args.progress_note:
        update_task_progress(data_dir, args.task_id, args.progress_note, args.session_id)

    # Output success
    print(json.dumps({"success": True, "log_path": str(log_path)}))


if __name__ == "__main__":
    main()
