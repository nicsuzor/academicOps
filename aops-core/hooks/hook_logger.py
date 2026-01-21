#!/usr/bin/env python3
"""
Shared hook logging module for Claude Code hooks.

Provides centralized logging for hook events, consolidating duplicated logging
logic across multiple hooks. All hooks should use log_hook_event() instead of
implementing their own logging.

Logs to ~/writing/sessions/status/hooks.jsonl
"""

import json
import sys
from datetime import datetime
from typing import Any


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
    Log a hook event to the session hooks log file.

    Writes to: ~/writing/sessions/status/hooks.jsonl

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
        # Get session directory for log files
        from lib.session_paths import get_session_directory

        # Extract date from input or use today
        date = input_data.get("date")
        session_dir = get_session_directory(session_id, date)

        # Hook logs stored in session subdirectory
        log_path = session_dir / "hooks.jsonl"

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
