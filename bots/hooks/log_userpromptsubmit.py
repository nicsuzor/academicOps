#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code: Debug logging only (noop).

This hook logs all UserPromptSubmit events to help understand what data is
available for future hook development. It does not modify behavior.

Exit codes:
    0: Success (always continues)
"""

import json
import sys
from typing import Any

from hook_debug import safe_log_to_debug_file


def main():
    """Main hook entry point - logs and continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    # Noop output - just continue
    output_data: dict[str, Any] = {}

    # Debug log hook execution
    safe_log_to_debug_file("UserPromptSubmit", input_data, output_data)

    # Output empty JSON (continue execution)
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
