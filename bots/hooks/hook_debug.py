#!/usr/bin/env python3
"""
Shared debug logging utilities for Claude Code hooks.

Provides safe, non-invasive logging of hook inputs and outputs to help
understand available data and design future hooks.
"""

import datetime
import json
from pathlib import Path
from typing import Any


def safe_log_to_debug_file(
    hook_event: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
) -> None:
    """
    Safely log hook invocation to a timestamped debug file.

    This function is wrapped in try-catch to prevent logging failures
    from crashing the hook. All logs are written to /tmp for easy
    inspection without affecting the repository.

    Args:
        hook_event: Name of the hook event (SessionStart, PreToolUse, etc.)
        input_data: Input data received from Claude Code
        output_data: Output data being sent back to Claude Code

    Output:
        Creates a JSON file at /tmp/claude_{hook_event}_{timestamp}.json
        containing the full hook context for inspection.
    """
    try:
        # Use /tmp for logs to avoid permission issues
        log_dir = Path("/tmp")

        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S_%f")
        log_file = log_dir / f"claude_{hook_event.lower()}_{timestamp}.json"

        debug_data = {
            "hook_event": hook_event,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "input": input_data,
            "output": output_data,
        }

        with log_file.open("w") as f:
            json.dump(debug_data, f, indent=2)
            f.write("\n")
    except Exception:
        # Silently ignore logging failures - never crash a hook
        pass
