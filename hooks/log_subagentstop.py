#!/usr/bin/env python3
"""
SubagentStop hook for Claude Code: Minimal logging.

Logs SubagentStop events to data/sessions/<date>-<hash>-hooks.jsonl

Exit codes:
    0: Success (always continues)
"""

# CRITICAL: Stop hooks must NEVER crash - wrap everything in try/except
# If imports fail (e.g., PYTHONPATH wrong), output {} and exit 0
try:
    import contextlib
    import json
    import sys
    from datetime import UTC, datetime
    from typing import Any

    from hooks.hook_logger import log_hook_event


    def main():
        """Main hook entry point - logs and continues."""
        # Read input from stdin
        input_data: dict[str, Any] = {}
        with contextlib.suppress(Exception):
            # If no stdin or parsing fails, continue with empty input
            input_data = json.load(sys.stdin)

        session_id = input_data.get("session_id", "unknown")

        # Noop output - just continue
        output_data: dict[str, Any] = {}

        # Log to hooks session file (includes both input and output)
        log_hook_event(session_id, "SubagentStop", input_data, output_data)

        # Output empty JSON (continue execution)
        print(json.dumps(output_data))

        sys.exit(0)


    if __name__ == "__main__":
        main()

except Exception as _import_error:
    # Import failed - output empty JSON and exit cleanly
    # This prevents infinite loops when Stop hook can't load
    import sys
    print("{}")
    print(f"Warning: Hook import failed: {_import_error}", file=sys.stderr)
    sys.exit(0)
