#!/usr/bin/env python3
"""
Shared debug logging utilities for Claude Code hooks.

Provides safe, non-invasive logging of hook inputs and outputs to help
understand available data and design future hooks.
"""

import datetime
import fcntl
import json
from pathlib import Path
from typing import Any


def safe_log_to_debug_file(
    hook_event: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
) -> None:
    """
    Safely log hook invocation to a session-based JSONL debug file.

    This function is wrapped in try-catch to prevent logging failures
    from crashing the hook. All logs are written to /tmp for easy
    inspection without affecting the repository.

    Logs are consolidated by session ID when available, creating one
    JSONL file per session for easier tracking and analysis.

    Args:
        hook_event: Name of the hook event (SessionStart, PreToolUse, etc.)
        input_data: Input data received from Claude Code
        output_data: Output data being sent back to Claude Code

    Output:
        Appends to /tmp/claude_session_{session_id}.jsonl

    Raises:
        ValueError: If session_id is not present in input_data
    """
    try:
        # Use /tmp for logs to avoid permission issues
        log_dir = Path("/tmp")

        # Extract session ID - REQUIRED (fail-fast, no fallbacks)
        session_id = input_data.get("session_id")
        if not session_id:
            msg = (
                f"session_id missing from {hook_event} hook input_data. "
                "Claude Code should provide session_id in all hook invocations."
            )
            raise ValueError(msg)

        log_file = log_dir / f"claude_session_{session_id}.jsonl"

        debug_data = {
            "hook_event": hook_event,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "input": input_data,
            "output": output_data,
        }

        # Append to JSONL file with file locking to prevent race conditions
        with log_file.open("a") as f:
            # Acquire exclusive lock
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                # Write single-line JSON
                json.dump(debug_data, f, separators=(",", ":"))
                f.write("\n")
            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        # Silently ignore logging failures - never crash a hook
        pass
