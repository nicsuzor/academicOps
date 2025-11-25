#!/usr/bin/env python3
"""
Shared hook logging module for Claude Code hooks.

Provides centralized logging for hook events, consolidating duplicated logging
logic across multiple hooks. All hooks should use log_hook_event() instead of
implementing their own logging.

Logs to ~/.cache/aops/sessions/<date>-<shorthash>-hooks.jsonl
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lib.paths import get_data_root
from hooks.session_logger import get_log_path


def log_hook_event(
    session_id: str,
    hook_event: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any] | None = None,
) -> None:
    """
    Log a hook event to the session hooks log file.

    Combines input and output data into a single JSONL entry with timestamp.
    If session_id is missing or empty, raises ValueError immediately (fail-fast).

    Args:
        session_id: Session ID from Claude Code. Must not be empty.
        hook_event: Name of the hook event (e.g., "UserPromptSubmit", "SessionEnd")
        input_data: Input data from Claude Code (hook parameters)
        output_data: Optional output data from the hook (results/side effects)

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
        >>> output_data = {"additionalContext": "loaded from markdown"}
        >>>
        >>> log_hook_event(session_id, hook_event, input_data, output_data)
    """
    # Fail-fast: session_id is required
    if not session_id:
        raise ValueError("session_id cannot be empty or None")

    try:
        # Get data directory for session logs
        project_dir = get_data_root()

        # Get log path with -hooks suffix
        log_path = get_log_path(project_dir, session_id, suffix="-hooks")

        # Create log entry combining input and output data
        log_entry: dict[str, Any] = {
            "hook_event": hook_event,
            "logged_at": datetime.now(UTC).isoformat(),
            **input_data,  # Include ALL fields from input
        }

        # Merge output_data if provided
        if output_data:
            log_entry.update(output_data)

        # Append to JSONL file
        with log_path.open("a") as f:
            json.dump(log_entry, f, separators=(",", ":"))
            f.write("\n")

    except ValueError:
        # Re-raise validation errors (bad session_id)
        raise
    except Exception as e:
        # Log error to stderr but don't crash the hook
        print(f"[hook_logger] Error logging hook event: {e}", file=sys.stderr)
        # Never crash the hook - silently continue
        pass
