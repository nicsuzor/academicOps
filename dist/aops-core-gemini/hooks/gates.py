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

# Gate configuration: Maps events to ordered list of gate checks
# Order matters - gates run in sequence, first deny wins
ACTIVE_GATES = [
    # --- SessionStart ---
    {"name": "unified_logger", "check": "unified_logger", "events": ["SessionStart"]},
    {"name": "session_start", "check": "session_start", "events": ["SessionStart"]},

    # --- UserPromptSubmit ---
    {"name": "user_prompt_submit", "check": "user_prompt_submit", "events": ["UserPromptSubmit"]},
    {"name": "unified_logger_ups", "check": "unified_logger", "events": ["UserPromptSubmit"]},

    # --- PreToolUse (Enforcement Pipeline) ---
    {"name": "unified_logger_pre", "check": "unified_logger", "events": ["PreToolUse"]},
    {"name": "subagent_restrictions", "check": "subagent_restrictions", "events": ["PreToolUse"]},
    {"name": "hydration", "check": "hydration", "events": ["PreToolUse"]},
    {"name": "task_required", "check": "task_required", "events": ["PreToolUse"]},
    {"name": "custodiet", "check": "custodiet", "events": ["PreToolUse"]},
    {"name": "qa_enforcement", "check": "qa_enforcement", "events": ["PreToolUse"]},

    # --- PostToolUse (Accounting Pipeline) ---
    {"name": "unified_logger_post", "check": "unified_logger", "events": ["PostToolUse"]},
    {"name": "task_binding", "check": "task_binding", "events": ["PostToolUse"]},
    {"name": "accountant", "check": "accountant", "events": ["PostToolUse"]},
    {"name": "post_hydration", "check": "post_hydration", "events": ["PostToolUse"]},
    {"name": "post_critic", "check": "post_critic", "events": ["PostToolUse"]},
    {"name": "post_qa", "check": "post_qa", "events": ["PostToolUse"]},
    {"name": "skill_activation", "check": "skill_activation", "events": ["PostToolUse"]},

    # --- AfterAgent ---
    {"name": "unified_logger_agent", "check": "unified_logger", "events": ["AfterAgent"]},
    {"name": "agent_response", "check": "agent_response", "events": ["AfterAgent"]},

    # --- SubagentStop ---
    {"name": "unified_logger_subagent", "check": "unified_logger", "events": ["SubagentStop"]},

    # --- Stop (Final Review Pipeline) ---
    {"name": "unified_logger_stop", "check": "unified_logger", "events": ["Stop"]},
    {"name": "stop_gate", "check": "stop_gate", "events": ["Stop"]},
    {"name": "hydration_recency", "check": "hydration_recency", "events": ["Stop"]},
    {"name": "generate_transcript", "check": "generate_transcript", "events": ["Stop"]},
    {"name": "session_end_commit", "check": "session_end_commit", "events": ["Stop"]},

    # --- SessionEnd (Post-Stop cleanup) ---
    {"name": "unified_logger_end", "check": "unified_logger", "events": ["SessionEnd"]},
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
                    #<!-- NS: ensure we use our typed classes internally all the way up to here and only convert to in the required client-specific format json at the last step.  -->
                    print(json.dumps(result.to_json()))
                    sys.exit(0)

    # No gates triggered
    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
