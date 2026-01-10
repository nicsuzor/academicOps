#!/usr/bin/env python3
"""
Stop hook: Inject instruction to invoke session-insights skill.

H31 compliant - no LLM calls in hooks. Just injects instruction for agent.

Exit codes:
    0: Success (no instruction needed - very short session)
    1: Warning with skill invocation instruction
"""

import json
import sys
from pathlib import Path
from typing import Any


def get_project_from_cwd(cwd: str) -> str:
    """Extract project name from cwd path."""
    if not cwd:
        return "unknown"
    parts = Path(cwd).parts
    return parts[-1] if parts else "unknown"


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    # Get session info
    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path", "")

    # Skip for very short sessions (no transcript)
    if not transcript_path:
        print(json.dumps({}))
        sys.exit(0)

    # Build instruction for agent
    short_id = session_id[:8] if session_id else "unknown"
    message = (
        f"Session ending. To record accomplishments, invoke:\n\n"
        f'  Skill(skill="session-insights")\n\n'
        f"This extracts insights from the transcript and saves to dashboard.\n"
        f"Session ID: {short_id}"
    )

    output: dict[str, Any] = {
        "reason": message,
        "continue": True,
    }

    print(json.dumps(output))
    sys.exit(1)  # 1 = warn but allow (shows message to agent)


if __name__ == "__main__":
    main()
