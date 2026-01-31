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
    # SessionStart (Startup Info)
    {"name": "session_start", "check": "session_start", "events": ["SessionStart"]},
    # PreToolUse gates (Enforcement Pipeline)
    # 1. Hydration: Blocks non-hydrator tools until context is loaded
    {"name": "hydration", "check": "hydration", "events": ["PreToolUse"]},
    # 2. (Merged) Axiom Enforcer: Now part of Custodiet
    # {"name": "axiom_enforcer", "check": "axiom_enforcer", "events": ["PreToolUse"]},
    # 3. Task Required: Blocks destructive operations without task binding
    {"name": "task_required", "check": "task_required", "events": ["PreToolUse"]},
    # 4. Custodiet: Blocks mutating tools when compliance check is overdue
    {"name": "custodiet", "check": "custodiet", "events": ["PreToolUse"]},
    # 5. QA Enforcement: Blocks task completion if QA missing
    {"name": "qa_enforcement", "check": "qa_enforcement", "events": ["PreToolUse"]},
    # PostToolUse gates (Accounting Pipeline)
    # 1. Accountant: Updates state (hydration cleared, tool counts, handover flags)
    {"name": "accountant", "check": "accountant", "events": ["PostToolUse"]},
    # 2. Post-hydration trigger: Injects next step after hydration
    {"name": "post_hydration", "check": "post_hydration", "events": ["PostToolUse"]},
    # 3. Post-critic trigger: Updates state after critic invocation
    # 3. Post-critic trigger: Updates state after critic invocation
    {"name": "post_critic", "check": "post_critic", "events": ["PostToolUse"]},
    # 4. Skill Activation Listener: Clears hydration if skill activated
    {
        "name": "skill_activation",
        "check": "skill_activation",
        "events": ["PostToolUse"],
    },
    # AfterAgent gates (Response Review Pipeline)
    # 1. Agent Response Listener: Updates state based on response text (Hydration, Handover)
    {
        "name": "agent_response_listener",
        "check": "agent_response_listener",
        "events": ["AfterAgent"],
    },
    # Stop / AfterAgent gates (Final Review Pipeline)
    # 1. Stop Gate: Enforces Critic invocation and handover warnings
    {"name": "stop_gate", "check": "stop_gate", "events": ["Stop"]},
    # 2. Hydration Recency: Blocks exit if turns since hydration == 0
    {"name": "hydration_recency", "check": "hydration_recency", "events": ["Stop"]},
]


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # JSON parse error - log and fail open (gates shouldn't block on malformed input)
        print(f"WARNING: gates.py JSON parse failed: {e}", file=sys.stderr)
        print(json.dumps(make_empty_output()))
        sys.exit(0)
    except Exception as e:
        # Unexpected error - log and fail open
        print(f"ERROR: gates.py stdin read failed: {type(e).__name__}: {e}", file=sys.stderr)
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    event_name = input_data.get("hook_event_name")
    if not event_name:
        # No event name - can't evaluate gates. Fail open with debug log.
        print("DEBUG: gates.py - no hook_event_name, skipping", file=sys.stderr)
        print(json.dumps(make_empty_output()))
        sys.exit(0)

    session_id = get_session_id(input_data, require=False)
    if not session_id:
        # No session ID - can't evaluate session-scoped gates. Fail open with debug log.
        print("DEBUG: gates.py - no session_id, skipping", file=sys.stderr)
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
                    print(json.dumps(result.to_json()))
                    sys.exit(0)

    # No gates triggered
    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
