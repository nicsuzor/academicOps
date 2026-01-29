#!/usr/bin/env python3
"""
Universal Gate Runner.

This script is invoked by the router for generic gate enforcement.
It loads active gates from configuration and executes them.
"""

import json
import sys
from pathlib import Path

# Ensure aops-core is in path
HOOK_DIR = Path(__file__).parent
AOPS_CORE_DIR = HOOK_DIR.parent
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.gate_registry import GATE_CHECKS, GateContext
from lib.hook_utils import make_empty_output, get_session_id

# Configuration could be loaded from a file, but for now we define it here
# matching the logic of the old system.
# In the future this can be loaded from hooks.json or gates.json
ACTIVE_GATES = [
    {"name": "hydration", "check": "hydration", "events": ["PreToolUse"]},
    {"name": "custodiet", "check": "custodiet", "events": ["PostToolUse"]},
    {"name": "hydration_recency", "check": "hydration_recency", "events": ["Stop"]},
    {"name": "post_hydration", "check": "post_hydration", "events": ["PostToolUse"]},
    {"name": "post_critic", "check": "post_critic", "events": ["PostToolUse"]},
]


def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        # If we can't parse input, we can't do anything meaningful.
        # Fail open or closed? Safe default is empty output (no action).
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    event_name = input_data.get("hook_event_name")
    if not event_name:
        # Fallback for direct invocation if needed, or error
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    session_id = get_session_id(input_data, require=False)
    if not session_id:
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    ctx = GateContext(session_id, event_name, input_data)

    # Run applicable gates
    for gate_config in ACTIVE_GATES:
        if event_name in gate_config["events"]:
            check_func = GATE_CHECKS.get(gate_config["check"])
            if check_func:
                result = check_func(ctx)
                if result:
                    # Gate triggered! Return the result immediately.
                    # This supports fail-fast / single-failure blocking.
                    # We could also collect multiple failures, but sticking to "first block wins" is safer.
                    print(json.dumps(result))
                    sys.exit(0)

    # No gates triggered
    print(json.dumps(make_empty_output()))
    sys.exit(0)


if __name__ == "__main__":
    main()
