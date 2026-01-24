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
from lib.session_state import has_reflection_output, set_reflection_output
from lib.transcript_parser import SessionProcessor, parse_framework_reflection

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


def check_for_reflection(session_id: str, transcript_path: str | None) -> tuple[bool, dict[str, Any] | None]:
    """Check if session has valid parseable Framework Reflection output.

    Searches recent assistant messages for a Framework Reflection section
    and validates it can be parsed into structured fields using the same
    parser as transcript.py.

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to session transcript file

    Returns:
        Tuple of (found, parsed_reflection) where parsed_reflection is the
        structured dict from parse_framework_reflection or None
    """
    # Check if already marked as having reflection
    if has_reflection_output(session_id):
        logger.info("Reflection already detected in session state")
        return True, None

    if not transcript_path:
        logger.debug("No transcript path provided")
        return False, None

    path = Path(transcript_path)
    messages = extract_recent_assistant_messages(path)

    if not messages:
        logger.debug("No assistant messages found in transcript")
        return False, None

    # Check each message for parseable reflection using parse_framework_reflection
    # This ensures the reflection is in the correct format for transcript.py
    for message in messages:
        parsed = parse_framework_reflection(message)
        if parsed:
            # Validate minimum required fields
            required_fields = ["outcome"]  # At minimum, outcome must be present
            if any(parsed.get(field) for field in required_fields):
                logger.info(f"Valid Framework Reflection detected: outcome={parsed.get('outcome')}")
                set_reflection_output(session_id, True)
                return True, parsed
            else:
                logger.warning("Framework Reflection found but missing required fields")

    logger.debug(f"No parseable Framework Reflection found in {len(messages)} recent messages")
    return False, None


def main():
    """Main hook entry point - blocks session if Framework Reflection missing."""
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
            found, parsed = check_for_reflection(session_id, transcript_path)

            if not found:
                # Block session - Framework Reflection is mandatory
                # The reflection must be parseable by parse_framework_reflection
                # Note: Due to timing, reflection must be output BEFORE the stopping turn
                output_data = {
                    "decision": "block",
                    "reason": (
                        "Run the session handover workflow before ending:\n"
                        "1. Update active task with progress checkpoint\n"
                        "2. File follow-up tasks for incomplete work\n"
                        "3. Persist key learnings to memory (if any)\n"
                        "4. Output ## Framework Reflection with:\n"
                        "   **Outcome**: success/partial/failure\n"
                        "   **Accomplishments**: what was done\n"
                        "   **Next step**: what to do next\n\n"
                        "See: workflows/handover.md for full workflow"
                    ),
                }
                logger.info("Session blocked: Parseable Framework Reflection not found")
        except Exception as e:
            logger.warning(f"Reflection check failed: {type(e).__name__}: {e}")

    # Exit 0 so JSON is processed; decision:block handles the blocking
    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
