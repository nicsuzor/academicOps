#!/usr/bin/env python3
"""
Session logging module for Claude Code.

Writes session logs to ~/.cache/aops/sessions/<date>-<shorthash>.jsonl
Each log entry contains session metadata, transcript summary, and activity details.

Session logs are cached locally and not tracked in git.
"""

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def get_session_short_hash(session_id: str) -> str:
    """
    Generate a short hash from the session ID.

    Args:
        session_id: Full session ID

    Returns:
        8-character hash
    """
    hash_obj = hashlib.sha256(session_id.encode())
    return hash_obj.hexdigest()[:8]


def validate_date(date: str) -> bool:
    """
    Validate date string to prevent path traversal attacks.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        True if valid, False otherwise
    """
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", date))


def get_log_path(
    project_dir: Path, session_id: str, date: str | None = None, suffix: str = ""
) -> Path:
    """
    Get the log file path for a session.

    Args:
        project_dir: Project root directory (unused, kept for compatibility)
        session_id: Session ID
        date: Optional date string (YYYY-MM-DD). Defaults to today.
        suffix: Optional suffix to append before .jsonl (e.g., "-hooks")

    Returns:
        Path to the log file

    Raises:
        ValueError: If date format is invalid
    """
    if date is None:
        date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

    # Security: Validate date format to prevent path traversal
    if not validate_date(date):
        msg = f"Invalid date format: {date}. Must be YYYY-MM-DD"
        raise ValueError(msg)

    short_hash = get_session_short_hash(session_id)
    filename = f"{date}-{short_hash}{suffix}.jsonl"

    # Use ~/.cache/aops for session logs (not tracked in git)
    log_dir = Path.home() / ".cache" / "aops" / "sessions"
    log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir / filename


def extract_transcript_summary(transcript_path: str) -> dict[str, Any]:  # noqa: C901, PLR0912
    """
    Extract summary information from a transcript file.

    Args:
        transcript_path: Path to the transcript JSONL file

    Returns:
        Dictionary with summary statistics
    """
    summary = {
        "user_messages": 0,
        "assistant_messages": 0,
        "tools_used": set(),
        "files_modified": [],
        "errors": [],
    }

    if not transcript_path or not Path(transcript_path).exists():
        return {**summary, "tools_used": []}

    try:
        with Path(transcript_path).open() as f:
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
                        if isinstance(content, str) and "error" in content.lower():
                            error_preview = content[:200]
                            if error_preview not in summary["errors"]:
                                summary["errors"].append(error_preview)

                except json.JSONDecodeError:
                    continue

    except OSError:
        pass

    # Convert set to list for JSON serialization
    summary["tools_used"] = list(summary["tools_used"])

    return summary


def create_session_note(transcript_summary: dict[str, Any], _session_id: str) -> str:
    """
    Create a concise note about the session.

    Args:
        transcript_summary: Summary extracted from transcript
        session_id: Session ID

    Returns:
        Concise session description
    """
    tools = transcript_summary.get("tools_used", [])
    files = transcript_summary.get("files_modified", [])
    user_msgs = transcript_summary.get("user_messages", 0)

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


def write_session_log(
    project_dir: Path,
    session_id: str,
    transcript_path: str | None = None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """
    Write a session log entry.

    Args:
        project_dir: Project root directory
        session_id: Session ID
        transcript_path: Optional path to transcript file
        summary: Optional custom summary
        metadata: Optional additional metadata

    Returns:
        Path to the written log file
    """
    # Extract transcript summary if available
    transcript_summary = {}
    if transcript_path:
        transcript_summary = extract_transcript_summary(transcript_path)

    # Generate summary if not provided
    if summary is None:
        summary = create_session_note(transcript_summary, session_id)

    # Create log entry
    log_entry = {
        "session_id": session_id,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "summary": summary,
        "transcript_summary": transcript_summary,
    }

    # Add optional metadata
    if metadata:
        log_entry["metadata"] = metadata

    # Get log path and write
    log_path = get_log_path(project_dir, session_id)

    # Append to JSONL file
    with log_path.open("a") as f:
        json.dump(log_entry, f, separators=(",", ":"))
        f.write("\n")

    return log_path
