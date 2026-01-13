#!/usr/bin/env python3
"""
Unified hook logger for Claude Code.

Logs ALL hook events to the single session file per flow.md spec.
Session file: /tmp/aops-{YYYY-MM-DD}-{session_id}.json

Event-specific behavior:
- SubagentStop: Updates subagent states in session file
- Stop: Writes session insights and closes session
- All others: Basic event logging (updates session file timestamps)

Exit codes:
    0: Success (always continues with noop response)
"""

import contextlib
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from lib.insights_generator import (
    extract_project_name,
    extract_short_hash,
    generate_fallback_insights,
    get_insights_file_path,
    write_insights_file,
)
from lib.session_state import (
    get_or_create_session_state,
    record_subagent_invocation,
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
    subagents section.

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
    result_data["stopped_at"] = datetime.now(timezone.utc).isoformat()

    # Record to session file
    record_subagent_invocation(session_id, subagent_type, result_data)


def handle_stop(session_id: str, input_data: dict[str, Any]) -> None:
    """Handle Stop event - write session insights and close session.

    Generates structured session insights and writes to both:
    1. Permanent storage: $ACA_DATA/sessions/insights/{date}-{session_id}.json
    2. Session state: For backward compatibility and QA verifier access

    Args:
        session_id: Claude Code session ID
        input_data: Stop input data
    """
    # Get current session state to build insights
    state = get_or_create_session_state(session_id)

    # Extract metadata
    metadata = {
        "session_id": extract_short_hash(session_id),
        "date": state.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
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

    # Generate insights (currently using fallback approach)
    # TODO: Implement LLM-based generation when API integration is available
    # For now, we generate operational metrics with minimal required fields
    insights = generate_fallback_insights(metadata, operational_metrics)

    logger.info(
        f"Generated session insights for {metadata['session_id']}: "
        f"outcome={insights['outcome']}, accomplishments={len(insights['accomplishments'])}"
    )

    # Write to permanent storage ($ACA_DATA/sessions/insights/)
    try:
        insights_path = get_insights_file_path(insights["date"], insights["session_id"])
        write_insights_file(insights_path, insights)
        logger.info(f"Wrote insights to permanent storage: {insights_path}")
    except Exception as e:
        logger.error(f"Failed to write insights to permanent storage: {e}")
        # Continue - at least save to session state

    # Write to session state (backward compatibility + QA verifier access)
    try:
        set_session_insights(session_id, insights)
        logger.info("Updated session state with insights")
    except Exception as e:
        logger.error(f"Failed to update session state insights: {e}")


def main():
    """Main hook entry point - logs event to session file and returns noop."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")
    hook_event = input_data.get("hook_event_name", "Unknown")

    # Log event to single session file
    with contextlib.suppress(Exception):
        log_event_to_session(session_id, hook_event, input_data)

    # Noop response - continue without modification
    print("{}")
    sys.exit(0)


if __name__ == "__main__":
    main()
