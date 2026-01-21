#!/usr/bin/env python3
"""
Shared hook logging module for Claude Code hooks.

Provides centralized logging for hook events, consolidating duplicated logging
logic across multiple hooks. All hooks should use log_hook_event() instead of
implementing their own logging.

Logs to ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
(per-session file alongside Claude transcripts)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.session_paths import get_claude_project_folder, get_session_short_hash


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

    Writes to: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl

    Per-session hook logs are stored alongside Claude transcripts for easy correlation.
    Combines input and output data into a single JSONL entry with timestamp.
    If session_id is missing or empty, raises ValueError immediately (fail-fast).

    Args:
        session_id: Session ID from Claude Code. Must not be empty.
        hook_event: Name of the hook event (e.g., "UserPromptSubmit", "SessionEnd")
        input_data: Input data from Claude Code (hook parameters)
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
        # Build per-session hook log path:
        # ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
        date = input_data.get("date")
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        project_folder = get_claude_project_folder()
        short_hash = get_session_short_hash(session_id)
        date_compact = date.replace("-", "")  # YYYY-MM-DD -> YYYYMMDD

        # Claude projects directory
        claude_projects_dir = Path.home() / ".claude" / "projects" / project_folder
        claude_projects_dir.mkdir(parents=True, exist_ok=True)

        # Per-session hooks file
        log_path = claude_projects_dir / f"{date_compact}-{short_hash}-hooks.jsonl"

        # Create log entry combining input and output data
        log_entry: dict[str, Any] = {
            "hook_event": hook_event,
            "logged_at": datetime.now().astimezone().isoformat(),
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
