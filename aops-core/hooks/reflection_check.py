#!/usr/bin/env python3
"""
Stop hook: Require Framework Reflection before session end.

Checks recent assistant messages for a valid Framework Reflection.
If not found, blocks session and provides format instructions.

Exit codes:
    0: Success (JSON output with decision field handles blocking)
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


# Framework Reflection pattern - matches the required format
REFLECTION_PATTERN = re.compile(
    r"##\s*Framework\s+Reflection.*?"
    r"\*\*Outcome\*\*:\s*(success|partial|failure)",
    re.IGNORECASE | re.DOTALL,
)


def get_reflection_instructions() -> str:
    """Return Framework Reflection format instructions."""
    return """Output Framework Reflection:
```
## Framework Reflection
**Outcome**: success|partial|failure
**Accomplishments**: [What was completed]
**Friction points**: [Issues encountered, or "none"]
```"""


def check_transcript_for_reflection(transcript_path: str) -> bool:
    """Check if transcript contains a valid Framework Reflection.

    Reads the last portion of the transcript file and searches for
    the reflection pattern in recent assistant messages.

    Args:
        transcript_path: Path to JSONL transcript file

    Returns:
        True if valid reflection found
    """
    if not transcript_path:
        return False

    path = Path(transcript_path)
    if not path.exists():
        return False

    try:
        # Read last 50KB of transcript (should contain recent messages)
        file_size = path.stat().st_size
        read_size = min(file_size, 50000)

        with open(path, "r") as f:
            if file_size > read_size:
                f.seek(file_size - read_size)
                # Skip partial line
                f.readline()
            content = f.read()

        # Parse JSONL and extract assistant message content
        for line in reversed(content.strip().split("\n")):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                # Check if this is an assistant message
                if entry.get("type") != "assistant":
                    continue

                # Extract text content
                message = entry.get("message", {})
                msg_content = message.get("content", "")

                # Handle both string and list content formats
                if isinstance(msg_content, list):
                    text_parts = []
                    for block in msg_content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    text = "\n".join(text_parts)
                else:
                    text = str(msg_content)

                # Check for reflection pattern
                if REFLECTION_PATTERN.search(text):
                    return True

            except json.JSONDecodeError:
                continue

    except Exception:
        pass

    return False


def main():
    """Main hook entry point - blocks session if reflection not found."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    transcript_path = input_data.get("transcript_path", "")
    output_data: dict[str, Any] = {}

    if transcript_path:
        if not check_transcript_for_reflection(transcript_path):
            instructions = get_reflection_instructions()
            output_data = {
                "decision": "block",
                "reason": f"Missing Framework Reflection. {instructions}",
            }

    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
