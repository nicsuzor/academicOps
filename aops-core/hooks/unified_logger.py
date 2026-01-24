#!/usr/bin/env python3
"""
Unified hook logger for Claude Code.

Logs ALL hook events to the single session file per flow.md spec.
Session file: /tmp/aops-{YYYY-MM-DD}-{session_id}.json

Event-specific behavior:
- SubagentStop: Updates subagent states in session file
- Stop: Records operational metrics to session state
- All others: Basic event logging (updates session file timestamps)

Note: Permanent session insights are extracted from Framework Reflection
by transcript.py, not by this hook. This hook only records operational
metrics to the temporary session state file.

Exit codes:
    0: Success (always continues with noop response)
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from lib.insights_generator import (
    extract_project_name,
    extract_short_hash,
    generate_fallback_insights,
)
from lib.session_state import (
    get_or_create_session_state,
    record_subagent_invocation,
    set_critic_invoked,
    set_session_insights,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def log_event_to_session(
    session_id: str, hook_event: str, input_data: dict[str, Any]
) -> None:
    """Log a hook event to the single session file.

    Updates the session file with event timestamp. For SubagentStop and Stop events,
    performs additional state updates.

    Args:
        session_id: Claude Code session ID
        hook_event: Name of the hook event
        input_data: Full input data from the hook
    """
    if not session_id or session_id == "unknown":
        return

    if hook_event == "SubagentStop":
        handle_subagent_stop(session_id, input_data)
    elif hook_event == "Stop":
        handle_stop(session_id, input_data)
    else:
        # For other events, just ensure session exists (creates if needed)
        # This updates the session file with the latest access
        get_or_create_session_state(session_id)


def handle_subagent_stop(session_id: str, input_data: dict[str, Any]) -> None:
    """Handle SubagentStop event - update subagent state in session file.

    Extracts subagent information and records it in the session file's
    subagents section. For critic agents, also sets the critic_invoked gate.

    Args:
        session_id: Claude Code session ID
        input_data: SubagentStop input data containing subagent_type, result, etc.
    """
    # Extract subagent information from input
    subagent_type = input_data.get("subagent_type", "unknown")
    subagent_result = input_data.get("subagent_result", {})

    # Handle both string and dict results
    if isinstance(subagent_result, str):
        result_data = {"output": subagent_result}
    elif isinstance(subagent_result, dict):
        result_data = subagent_result
    else:
        result_data = {"raw": str(subagent_result)}

    # Add metadata
    result_data["stopped_at"] = (
        datetime.now().astimezone().replace(microsecond=0).isoformat()
    )

    # Record to session file
    record_subagent_invocation(session_id, subagent_type, result_data)

    # Set critic_invoked gate when critic agent completes
    # This is part of the three-gate requirement for destructive operations
    if subagent_type == "critic":
        # Extract verdict from result if available
        verdict = None
        if isinstance(subagent_result, dict):
            verdict = subagent_result.get("verdict")
        elif isinstance(subagent_result, str):
            # Try to extract verdict from output text
            for v in ["PROCEED", "REVISE", "HALT"]:
                if v in subagent_result.upper():
                    verdict = v
                    break
        set_critic_invoked(session_id, verdict)
        logger.info(f"Critic gate set: verdict={verdict}")


def handle_stop(session_id: str, input_data: dict[str, Any]) -> None:
    """Handle Stop event - record operational metrics to session state.

    Records basic operational metrics to session state for QA verifier access.
    Does NOT write to permanent storage - that's handled by transcript.py which
    extracts the Framework Reflection from the session transcript.

    Args:
        session_id: Claude Code session ID
        input_data: Stop input data
    """
    # Get current session state to build insights
    state = get_or_create_session_state(session_id)

    # Extract metadata
    metadata = {
        "session_id": extract_short_hash(session_id),
        "date": state.get(
            "date", datetime.now().astimezone().replace(microsecond=0).isoformat()
        ),
        "project": extract_project_name(),
    }

    # Build operational metrics
    subagents = state.get("subagents", {})
    current_workflow = state.get("state", {}).get("current_workflow")
    custodiet_blocked = state.get("state", {}).get("custodiet_blocked", False)
    hydration = state.get("hydration", {})

    operational_metrics = {
        "workflows_used": [current_workflow] if current_workflow else [],
        "subagents_invoked": list(subagents.keys()),
        "subagent_count": len(subagents),
        "custodiet_blocks": 1 if custodiet_blocked else 0,
        "stop_reason": input_data.get("stop_reason", "unknown"),
        "critic_verdict": hydration.get("critic_verdict"),
        "acceptance_criteria_count": len(hydration.get("acceptance_criteria", [])),
    }

    # Generate minimal insights for session state only
    # Full insights are extracted from Framework Reflection by transcript.py
    insights = generate_fallback_insights(metadata, operational_metrics)

    logger.info(
        f"Session stopped: {metadata['session_id']} "
        f"(subagents={len(subagents)}, custodiet_blocks={operational_metrics['custodiet_blocks']})"
    )

    # Write to session state only (for QA verifier access during session)
    # Permanent storage is handled by transcript.py extracting Framework Reflection
    try:
        set_session_insights(session_id, insights)
        logger.info("Updated session state with operational metrics")
    except Exception as e:
        logger.error(f"Failed to update session state: {e}")


def main():
    """Main hook entry point - logs event to session file and returns noop."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # Expected failure: stdin may be empty or malformed
        logger.debug(f"JSON decode failed (expected if no stdin): {e}")
    except Exception as e:
        # Unexpected failure: I/O errors, permissions, etc.
        logger.warning(f"Unexpected error reading stdin: {type(e).__name__}: {e}")

    session_id = input_data.get("session_id", "unknown")
    hook_event = input_data.get("hook_event_name", "Unknown")

    # Log event to single session file
    try:
        log_event_to_session(session_id, hook_event, input_data)
    except Exception as e:
        # Log but don't fail - hook should continue with noop
        logger.warning(f"Failed to log event to session: {type(e).__name__}: {e}")

    # Noop response - continue without modification
    print("{}")
    sys.exit(0)


if __name__ == "__main__":
    main()
