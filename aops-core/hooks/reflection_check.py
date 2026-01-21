#!/usr/bin/env python3
"""
Reflection check hook for Claude Code Stop event.

Checks the last few assistant messages for a Framework Reflection section
and updates the session state flag. This enables automated verification
that agents are outputting required reflections before session end.

Exit codes:
    0: Success (continues with noop or warning)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

from lib.reflection_detector import has_reflection
from lib.session_state import set_reflection_output, has_reflection_output
from lib.transcript_parser import SessionProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Number of recent assistant messages to check for reflection
MAX_MESSAGES_TO_CHECK = 10


def extract_recent_assistant_messages(
    transcript_path: Path, max_messages: int = MAX_MESSAGES_TO_CHECK
) -> list[str]:
    """Extract recent assistant message texts from transcript.

    Args:
        transcript_path: Path to JSONL transcript file
        max_messages: Maximum number of messages to extract

    Returns:
        List of assistant message texts (newest first)
    """
    if not transcript_path.exists():
        return []

    try:
        processor = SessionProcessor()
        _, entries, agent_entries = processor.parse_session_file(
            transcript_path, load_agents=True, load_hooks=False
        )

        messages = []

        # Collect from main entries (reverse order - newest first)
        for entry in reversed(entries):
            if entry.type != "assistant":
                continue

            text = _extract_text_from_entry(entry)
            if text:
                messages.append(text)
                if len(messages) >= max_messages:
                    break

        # Also check agent entries if we haven't found enough
        if len(messages) < max_messages and agent_entries:
            for agent_id, agent_entry_list in agent_entries.items():
                for entry in reversed(agent_entry_list):
                    if entry.type != "assistant":
                        continue
                    text = _extract_text_from_entry(entry)
                    if text:
                        messages.append(text)
                        if len(messages) >= max_messages:
                            break
                if len(messages) >= max_messages:
                    break

        return messages

    except Exception as e:
        logger.warning(f"Failed to extract messages from transcript: {e}")
        return []


def _extract_text_from_entry(entry: Any) -> str:
    """Extract text content from an Entry object."""
    text = ""
    if entry.message:
        content = entry.message.get("content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")
    elif entry.content:
        text = str(entry.content.get("content", ""))
    return text


def check_for_reflection(session_id: str, transcript_path: str | None) -> bool:
    """Check if session has Framework Reflection output.

    Searches recent assistant messages for a Framework Reflection section.
    Updates session state flag if found.

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to session transcript file

    Returns:
        True if reflection found, False otherwise
    """
    # Check if already marked as having reflection
    if has_reflection_output(session_id):
        logger.info("Reflection already detected in session state")
        return True

    if not transcript_path:
        logger.debug("No transcript path provided")
        return False

    path = Path(transcript_path)
    messages = extract_recent_assistant_messages(path)

    if not messages:
        logger.debug("No assistant messages found in transcript")
        return False

    # Check each message for reflection
    for message in messages:
        if has_reflection(message):
            logger.info("Framework Reflection detected in session")
            set_reflection_output(session_id, True)
            return True

    logger.debug(f"No Framework Reflection found in {len(messages)} recent messages")
    return False


def main():
    """Main hook entry point - checks for reflection and returns noop."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        logger.debug(f"JSON decode failed (expected if no stdin): {e}")
    except Exception as e:
        logger.warning(f"Unexpected error reading stdin: {type(e).__name__}: {e}")

    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path")

    output_data: dict[str, Any] = {}

    if session_id:
        try:
            found = check_for_reflection(session_id, transcript_path)
            if not found:
                # Optionally warn that no reflection was found
                # This is informational - don't block the session
                output_data = {
                    "hookSpecificOutput": {
                        "hookEventName": "Stop",
                        "additionalContext": (
                            "Note: No Framework Reflection detected in this session. "
                            "Framework Reflections help capture session insights for learning."
                        ),
                    }
                }
        except Exception as e:
            logger.warning(f"Reflection check failed: {type(e).__name__}: {e}")

    # Noop response - continue without blocking
    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
