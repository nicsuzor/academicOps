#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code: Minimal logging.

Logs UserPromptSubmit events to data/sessions/<date>-<hash>-hooks.jsonl
Also loads additional context from prompts/user-prompt-submit.md

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lib.paths import get_data_root, get_hooks_dir
from hooks.session_logger import get_log_path

# Paths
HOOK_DIR = get_hooks_dir()
PROMPT_FILE = HOOK_DIR / "prompts" / "user-prompt-submit.md"


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


def load_prompt_from_markdown() -> str:
    """Load prompt content from markdown file."""
    if not PROMPT_FILE.exists():
        return ""

    content = PROMPT_FILE.read_text().strip()
    if not content:
        return ""

    # Remove markdown header if present
    lines = content.split("\n")
    if lines and lines[0].startswith("#"):
        content_lines = []
        skip_header = True
        for line in lines[1:]:
            if skip_header and line.strip() == "":
                continue
            skip_header = False
            content_lines.append(line)
        content = "\n".join(content_lines).strip()

    return content


def main():
    """Main hook entry point - logs and continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        # If no stdin or parsing fails, continue with empty input
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")

    # Clear end-of-session documentation request flag for new turn
    state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")
    if state_file.exists():
        state_file.unlink()

    # Log to hooks session file
    log_to_session_file(session_id, "UserPromptSubmit", input_data)

    # Load additional context
    additional_context = load_prompt_from_markdown()
    output_data: dict[str, Any] = {}
    if additional_context:
        output_data["additionalContext"] = additional_context

    # Output JSON (continue execution)
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
