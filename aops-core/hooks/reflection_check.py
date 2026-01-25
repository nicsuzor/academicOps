#!/usr/bin/env python3
"""
Stop hook: Require /handover skill invocation before session end.

Blocks session termination until the handover skill has been invoked.
The handover skill handles:
- Checking for uncommitted changes
- Outputting Framework Reflection
- Clearing the stop gate

Exit codes:
    0: Success (JSON output with decision field handles blocking)
"""

import json
import sys
from typing import Any

from lib.session_state import is_handover_skill_invoked


def main():
    """Main hook entry point - blocks session if handover skill not invoked."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    session_id = input_data.get("session_id", "")
    output_data: dict[str, Any] = {}

    if session_id:
        try:
            if not is_handover_skill_invoked(session_id):
                output_data = {
                    "decision": "block",
                    "reason": "Invoke /handover to end session. Only the handover skill clears this gate.",
                }
        except Exception:
            # If we can't check state, allow session to end
            pass

    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
