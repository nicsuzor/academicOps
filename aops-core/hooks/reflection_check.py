#!/usr/bin/env python3
"""
Stop hook: Require /handover skill invocation before session end.

Blocks session until the /handover skill has been invoked.
The handover_gate.py PostToolUse hook sets the flag when skill is invoked.

Exit codes:
    0: Success (JSON output with decision field handles blocking)
"""

import json
import sys
from typing import Any

from lib.hook_utils import get_session_id
from lib.session_state import is_handover_skill_invoked


def main():
    """Main hook entry point - blocks session if /handover not invoked."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # Expected failure: stdin may be empty or malformed
        print(f"DEBUG: reflection_check - JSON decode failed: {e}", file=sys.stderr)
    except Exception as e:
        # Unexpected failure: log and continue with empty input
        print(f"WARNING: reflection_check - stdin read failed: {type(e).__name__}: {e}", file=sys.stderr)

    # Get session_id from input or env (fail-open: require=False)
    session_id = get_session_id(input_data, require=False)
    if not session_id:
        # No session ID - cannot evaluate handover state. Fail open.
        print(json.dumps({}))
        sys.exit(0)

    # Check handover gate
    if not is_handover_skill_invoked(session_id):
        output_data = {
            "decision": "block",
            "reason": "Invoke Skill aops-core:handover to end session. Only the handover skill clears this gate. Use AskUserQuestion if you need user input before handover.",
        }
    else:
        output_data = {"decision": "approve"}

    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
