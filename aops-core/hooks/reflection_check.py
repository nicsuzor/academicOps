#!/usr/bin/env python3
"""
Stop hook: Require /handover skill invocation before session end.

Blocks session until the /handover skill has been invoked.
The handover_gate.py PostToolUse hook sets the flag when skill is invoked.

Exit codes:
    0: Success (JSON output with decision field handles blocking)
"""

import json
import os
import sys
from typing import Any

from lib.session_state import is_handover_skill_invoked


def main():
    """Main hook entry point - blocks session if /handover not invoked."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    session_id = input_data.get("session_id", "") or os.environ.get(
        "CLAUDE_SESSION_ID", ""
    )
    output_data: dict[str, Any] = {}

    if session_id:
        if not is_handover_skill_invoked(session_id):
            output_data = {
                "decision": "block",
                "reason": "Invoke Skill aops-core:handover to end session. Only the handover skill clears this gate. Use AskUserQuestion if you need user input before handover.",
            }
        else:
            output_data["decision"] = "approve"
    # Output

    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
