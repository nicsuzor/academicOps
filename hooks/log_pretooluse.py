#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code: Minimal logging.

Logs PreToolUse events to data/sessions/<date>-<hash>-hooks.jsonl

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from datetime import UTC, datetime
from typing import Any

from lib.paths import get_data_root
from hooks.session_logger import get_log_path


def log_to_session_file(
    session_id: str, hook_event: str, input_data: dict[str, Any]
) -> None:
    """
    Append hook event to hooks log file.

    Args:
        session_id: Session ID
        hook_event: Name of the hook event
        input_data: Input data from Claude Code (complete data passed through)
    """
    try:
        # Get data directory for session logs
        project_dir = get_data_root()

        # Get log path with -hooks suffix
        log_path = get_log_path(project_dir, session_id, suffix="-hooks")

        # Create log entry with ALL input data plus our own timestamp if missing
        log_entry = {
            "hook_event": hook_event,
            "logged_at": datetime.now(UTC).isoformat(),
            **input_data,  # Include ALL fields from input
        }

        # Append to JSONL file
        with log_path.open("a") as f:
            json.dump(log_entry, f, separators=(",", ":"))
            f.write("\n")
    except Exception:
        # Never crash the hook
        pass


def validate_minimal_documentation(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """
    Enforce MINIMAL principle for documentation files.

    Blocks creation of:
    - *-GUIDE.md files (e.g., INSTALLATION-GUIDE.md)
    - .md files exceeding 200 lines

    Returns:
        None if validation passes (continue)
        Dict with {"continue": False, "systemMessage": "..."} if blocked
    """
    if tool_name != "Write":
        return None

    file_path = args.get("file_path", "")
    content = args.get("content", "")

    # Block *-GUIDE.md files (e.g., INSTALLATION-GUIDE.md, USER-GUIDE.md)
    if file_path.endswith("-GUIDE.md") or "GUIDE.md" in file_path.upper():
        return {
            "continue": False,
            "systemMessage": (
                "❌ BLOCKED: *-GUIDE.md files violate MINIMAL principle.\n\n"
                "User explicitly: 'I hate installation guides. I hate long documents.'\n"
                "CLAUDE.md: 'the watchword is MINIMAL. We are ACTIVELY FIGHTING bloat.'\n\n"
                "Instead:\n"
                "- Add 2 sentences to README.md\n"
                "- Installation docs belong in package's auto-generated INSTALL.md\n"
                "- Never create separate guide files\n\n"
                "See: Issue #202"
            )
        }

    # Block .md files exceeding 200 lines
    if file_path.endswith(".md"):
        line_count = len(content.split("\n"))
        if line_count > 200:
            return {
                "continue": False,
                "systemMessage": (
                    f"❌ BLOCKED: {line_count} lines violates MINIMAL principle.\n\n"
                    "Documentation limits:\n"
                    "- Skills: 500 lines max\n"
                    "- Docs/chunks: 300 lines max\n"
                    "- General docs: 200 lines max\n\n"
                    "Consider:\n"
                    "- Is this documentation necessary?\n"
                    "- Can it be 2 sentences in README instead?\n"
                    "- Should it be split into focused chunks in docs/chunks/?\n\n"
                    "User values: 'efficiency over lengthy explanation'\n\n"
                    "See: Issue #202"
                )
            }

    return None


def main():
    """Main hook entry point - logs and validates."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        # If no stdin or parsing fails, continue with empty input
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")
    tool_name = input_data.get("tool", "")
    args = input_data.get("args", {})

    # Log to hooks session file
    log_to_session_file(session_id, "PreToolUse", input_data)

    # Validate MINIMAL documentation principle
    validation_result = validate_minimal_documentation(tool_name, args)
    if validation_result is not None:
        # Blocked - return error
        print(json.dumps(validation_result))
        sys.exit(0)

    # Validation passed - continue
    output_data: dict[str, Any] = {}
    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
