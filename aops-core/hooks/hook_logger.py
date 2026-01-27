#!/usr/bin/env python3
"""
Shared hook logging module for Claude Code and Gemini CLI hooks.

Provides centralized logging for hook events, consolidating duplicated logging
logic across multiple hooks. All hooks should use log_hook_event() instead of
implementing their own logging.

Logs to:
- Claude: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
- Gemini: ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-hooks.jsonl
  (same directory as Gemini transcript for easy correlation)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.session_paths import get_claude_project_folder, get_session_short_hash


def _is_gemini_session(session_id: str, input_data: dict[str, Any]) -> bool:
    """
    Detect if this is a Gemini CLI session.

    Detection methods:
    1. session_id starts with "gemini-"
    2. transcript_path contains "/.gemini/"
    """
    if session_id.startswith("gemini-"):
        return True

    transcript_path = input_data.get("transcript_path", "")
    if transcript_path and "/.gemini/" in transcript_path:
        return True

    return False


def _get_gemini_logs_dir(input_data: dict[str, Any]) -> Path | None:
    """
    Get Gemini logs directory from transcript_path.

    Gemini transcript paths look like:
    ~/.gemini/tmp/<hash>/logs/session-<uuid>.jsonl

    Returns the parent directory (the logs/ folder) or None if not found.
    """
    transcript_path = input_data.get("transcript_path", "")
    if not transcript_path:
        return None

    path = Path(transcript_path)

    # If transcript_path points to a file, use its parent directory
    if path.suffix in (".jsonl", ".json"):
        logs_dir = path.parent
    else:
        # Might be a directory already
        logs_dir = path

    # Validate it looks like a Gemini logs directory
    if "/.gemini/" in str(logs_dir):
        return logs_dir

    return None


def _json_serializer(obj: Any) -> str:
    """
    Convert non-serializable objects to strings for JSON serialization.

    This is used as the default handler for json.dump() to handle objects
    that don't have a standard JSON representation (datetime, Path, custom classes, etc).

    Args:
        obj: Any Python object

    Returns:
        String representation of the object
    """
    return str(obj)


def log_hook_event(
    session_id: str,
    hook_event: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any] | None = None,
    exit_code: int = 0,
) -> None:
    """
    Log a hook event to the per-session hooks log file.

    Writes to (auto-detected based on session type):
    - Claude: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
    - Gemini: ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-hooks.jsonl

    Per-session hook logs are stored alongside transcripts for easy correlation.
    Combines input and output data into a single JSONL entry with timestamp.
    If session_id is missing or empty, raises ValueError immediately (fail-fast).

    Gemini detection uses:
    1. session_id starting with "gemini-"
    2. transcript_path in input_data containing "/.gemini/"

    Args:
        session_id: Session ID from Claude Code or Gemini CLI. Must not be empty.
        hook_event: Name of the hook event (e.g., "UserPromptSubmit", "SessionEnd")
        input_data: Input data from hook (parameters). For Gemini, should include
            transcript_path to determine correct log directory.
        output_data: Optional output data from the hook (results/side effects)
        exit_code: Exit code of the hook (0 = success, non-zero = failure)

    Returns:
        None

    Raises:
        ValueError: If session_id is empty or None
        IOError: If log file cannot be written (re-raised from file operations)

    Example:
        >>> from hooks.hook_logger import log_hook_event
        >>>
        >>> session_id = "abc123def456"
        >>> hook_event = "UserPromptSubmit"
        >>> input_data = {"prompt": "hello", "model": "claude-opus"}
        >>> output_data = {"additionalContext": "loaded from markdown", "exitCode": 0}
        >>> exit_code = 0
        >>>
        >>> log_hook_event(session_id, hook_event, input_data, output_data, exit_code)
    """
    # Fail-fast: session_id is required
    if not session_id:
        raise ValueError("session_id cannot be empty or None")

    try:
        # Build per-session hook log path
        date = input_data.get("date")
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        short_hash = get_session_short_hash(session_id)
        date_compact = date.replace("-", "")  # YYYY-MM-DD -> YYYYMMDD

        # Determine log directory based on session type
        if _is_gemini_session(session_id, input_data):
            # Gemini: write to same directory as transcript
            # ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-hooks.jsonl
            logs_dir = _get_gemini_logs_dir(input_data)
            if logs_dir is None:
                # Fallback: use ~/.gemini/tmp/hooks/ if transcript_path not available
                logs_dir = Path.home() / ".gemini" / "tmp" / "hooks"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = logs_dir / f"{date_compact}-{short_hash}-hooks.jsonl"
        else:
            # Claude: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
            project_folder = get_claude_project_folder()
            claude_projects_dir = Path.home() / ".claude" / "projects" / project_folder
            claude_projects_dir.mkdir(parents=True, exist_ok=True)
            log_path = claude_projects_dir / f"{date_compact}-{short_hash}-hooks.jsonl"

        # Create log entry combining input and output data
        log_entry: dict[str, Any] = {
            "hook_event": hook_event,
            "logged_at": datetime.now().astimezone().replace(microsecond=0).isoformat(),
            "exit_code": exit_code,
            **input_data,  # Include ALL fields from input
        }

        # Merge output_data if provided
        if output_data:
            log_entry.update(output_data)

        # Append to JSONL file
        with log_path.open("a") as f:
            json.dump(log_entry, f, separators=(",", ":"), default=_json_serializer)
            f.write("\n")

    except ValueError:
        # Re-raise validation errors (bad session_id)
        raise
    except Exception as e:
        # Log error to stderr but don't crash the hook
        print(f"[hook_logger] Error logging hook event: {e}", file=sys.stderr)
        # Never crash the hook - silently continue
        pass
