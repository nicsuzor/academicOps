#!/usr/bin/env python3
"""
Session logging script for task management.

Creates daily JSON log files tracking what was done in each session,
associates entries with tasks, and updates task files with progress.
"""

import argparse
import json
import os
import sys
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
    """Get the path to today's session log file."""
    log_dir = data_dir / "sessions"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{date}.json"


def load_daily_log(log_path: Path) -> list:
    """Load existing daily log or return empty list."""
    if log_path.exists():
        try:
            with open(log_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_daily_log(log_path: Path, entries: list):
    """Save daily log to file."""
    with open(log_path, "w") as f:
        json.dump(entries, f, indent=2)


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
):
    """Update a task file with progress information."""
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

    # Load daily log
    log_path = get_daily_log_path(data_dir, today)
    entries = load_daily_log(log_path)

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

    # Add to entries
    entries.append(entry)

    # Save daily log
    save_daily_log(log_path, entries)

    # Update task progress if task_id provided
    if args.task_id and args.progress_note:
        update_task_progress(data_dir, args.task_id, args.progress_note, args.session_id)

    # Output success
    print(json.dumps({"success": True, "log_path": str(log_path)}))


if __name__ == "__main__":
    main()
