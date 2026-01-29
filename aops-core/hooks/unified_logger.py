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
from lib.session_paths import (
    get_session_file_path_direct,
    get_session_short_hash,
    get_session_status_dir,
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
) -> dict[str, Any] | None:
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
    elif hook_event == "PostToolUse":
        handle_post_tool_use(session_id, input_data)
    elif hook_event == "SessionStart":
        # Create session state and return path + session_id only (not full contents)
        state = get_or_create_session_state(session_id)
        short_hash = get_session_short_hash(session_id)
        state_path = get_session_file_path_direct(session_id, state.get("date"))
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"Session: {short_hash}\nState file: {state_path}",
            },
            "systemMessage": f"SessionStart:startup hook success: Success",
        }
    else:
        # For other events, just ensure session exists (creates if needed)
        # This updates the session file with the latest access
        get_or_create_session_state(session_id)
    return None


def handle_post_tool_use(session_id: str, input_data: dict[str, Any]) -> None:
    """Handle PostToolUse event.

    Checks for skill activations that trigger gates (e.g., critic).

    Args:
        session_id: Claude Code session ID
        input_data: Hook input data
    """
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input", {})

    # Detect activate_skill(name="critic")
    if tool_name == "activate_skill":
        skill_name = tool_input.get("name")
        if skill_name == "critic":
            # Critic skill invoked - satisfy the gate
            # Verdict is not available from activation (it comes from the agent's subsequent analysis)
            # We assume PROCEED or rely on user to halt if critic finds issues.
            # The gate mainly checks *that* it was invoked.
            set_critic_invoked(session_id, verdict="INVOKED")
            logger.info("Critic gate set via activate_skill")


def handle_subagent_stop(session_id: str, input_data: dict[str, Any]) -> None:
    """Handle SubagentStop event - update subagent state in session file.

    Extracts subagent information and records it in the session file's
    subagents section. For critic agents, also sets the critic_invoked gate.

    Args:
        session_id: Claude Code session ID
        input_data: SubagentStop input data containing subagent_type, result, etc.
    """
    # Extract subagent information from input
    if "subagent_type" not in input_data:
        raise ValueError("Required field 'subagent_type' missing from input_data")
    subagent_type = input_data["subagent_type"]

    if "subagent_result" not in input_data:
        raise ValueError("Required field 'subagent_result' missing from input_data")
    subagent_result = input_data["subagent_result"]

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
    if "date" not in state:
        state["date"] = datetime.now().astimezone().replace(microsecond=0).isoformat()

    metadata = {
        "session_id": extract_short_hash(session_id),
        "date": state["date"],
        "project": extract_project_name(),
    }

    # Build operational metrics with safe defaults
    state_section = state.get("state", {})
    hydration = state.get("hydration", {})
    subagents = state.get("subagents", {})

    operational_metrics = {
        "workflows_used": [state_section.get("current_workflow")] if state_section.get("current_workflow") else [],
        "subagents_invoked": list(subagents.keys()),
        "subagent_count": len(subagents),
        "custodiet_blocks": 1 if state_section.get("custodiet_blocked") else 0,
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
    result: dict[str, Any] = {}
    try:
        result = log_event_to_session(session_id, hook_event, input_data) or {}
    except Exception as e:
        # Log but don't fail - hook should continue with noop
        logger.warning(f"Failed to log event to session: {type(e).__name__}: {e}")

    # Output result (may contain debug info for SessionStart)
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
