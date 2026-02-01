#!/usr/bin/env python3
"""
Unified hook logger for Claude Code and Gemini CLI.

Logs ALL hook events to:
1. Session state file: /tmp/aops-{YYYY-MM-DD}-{session_id}.json (for gate state)
2. Per-session JSONL hook log: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
   or ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-hooks.jsonl (for event audit trail)

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
from pathlib import Path
from typing import Any

from lib.insights_generator import (
    extract_project_name,
    extract_short_hash,
    generate_fallback_insights,
)
from lib.session_paths import (
    get_claude_project_folder,
    get_session_file_path_direct,
    get_session_short_hash,
    get_session_status_dir,
)
from lib.session_state import (
    clear_hydration_pending,
    get_or_create_session_state,
    record_subagent_invocation,
    set_critic_invoked,
    set_qa_invoked,
    set_session_insights,
)
from lib.gate_model import GateResult, GateVerdict

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Hook Event Logging (per-session JSONL files) ---


def _is_gemini_session(session_id: str, input_data: dict[str, Any]) -> bool:
    """
    Detect if this is a Gemini CLI session.

    Detection methods:
    1. session_id starts with "gemini-"
    2. transcript_path contains "/.gemini/"
    """
    if session_id.startswith("gemini-"):
        return True

    transcript_path = input_data.get("transcript_path", "")
    if transcript_path and "/.gemini/" in transcript_path:
        return True

    return False


def _get_gemini_logs_dir(input_data: dict[str, Any]) -> Path | None:
    """
    Get Gemini logs directory from transcript_path.

    Gemini transcript paths look like:
    ~/.gemini/tmp/<hash>/logs/session-<uuid>.jsonl

    Returns the parent directory (the logs/ folder) or None if not found.
    """
    transcript_path = input_data.get("transcript_path", "")
    if not transcript_path:
        return None

    path = Path(transcript_path)

    # If transcript_path points to a file, use its parent directory
    if path.suffix in (".jsonl", ".json"):
        logs_dir = path.parent
    else:
        # Might be a directory already
        logs_dir = path

    # Validate it looks like a Gemini logs directory
    if "/.gemini/" in str(logs_dir):
        return logs_dir

    return None


def _json_serializer(obj: Any) -> str:
    """
    Convert non-serializable objects to strings for JSON serialization.

    This is used as the default handler for json.dump() to handle objects
    that don't have a standard JSON representation (datetime, Path, custom classes, etc).

    Args:
        obj: Any Python object

    Returns:
        String representation of the object
    """
    return str(obj)


def get_hook_log_path(
    session_id: str, input_data: dict[str, Any], date: str | None = None
) -> Path:
    """
    Get the path for the per-session hook log file.

    Logs to:
    - Claude: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
    - Gemini: ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-hooks.jsonl

    Args:
        session_id: Session ID from Claude Code or Gemini CLI
        input_data: Input data from hook (may contain transcript_path for Gemini)
        date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns:
        Path to the hook log file
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    short_hash = get_session_short_hash(session_id)
    date_compact = date.replace("-", "")  # YYYY-MM-DD -> YYYYMMDD

    # Determine log directory based on session type
    if _is_gemini_session(session_id, input_data):
        # Gemini: write to same directory as transcript
        logs_dir = _get_gemini_logs_dir(input_data)
        if logs_dir is None:
            # Fallback: use ~/.gemini/tmp/hooks/ if transcript_path not available
            logs_dir = Path.home() / ".gemini" / "tmp" / "hooks"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir / f"{date_compact}-{short_hash}-hooks.jsonl"
    else:
        # Claude: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
        project_folder = get_claude_project_folder()
        claude_projects_dir = Path.home() / ".claude" / "projects" / project_folder
        claude_projects_dir.mkdir(parents=True, exist_ok=True)
        return claude_projects_dir / f"{date_compact}-{short_hash}-hooks.jsonl"


def log_hook_event(
    session_id: str,
    hook_event: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any] | None = None,
    exit_code: int = 0,
) -> None:
    """
    Log a hook event to the per-session hooks log file.

    Writes to (auto-detected based on session type):
    - Claude: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
    - Gemini: ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-hooks.jsonl

    Per-session hook logs are stored alongside transcripts for easy correlation.
    Combines input and output data into a single JSONL entry with timestamp.
    If session_id is missing or empty, silently returns (fail-safe for logging).

    Args:
        session_id: Session ID from Claude Code or Gemini CLI. Empty = skip.
        hook_event: Name of the hook event (e.g., "UserPromptSubmit", "SessionEnd")
        input_data: Input data from hook (parameters). For Gemini, should include
            transcript_path to determine correct log directory.
        output_data: Optional output data from the hook (results/side effects)
        exit_code: Exit code of the hook (0 = success, non-zero = failure)

    Returns:
        None (never raises - logging should not crash hooks)

    Example:
        >>> log_hook_event(
        ...     session_id="abc123def456",
        ...     hook_event="UserPromptSubmit",
        ...     input_data={"prompt": "hello", "model": "claude-opus"},
        ...     output_data={"additionalContext": "loaded from markdown"},
        ...     exit_code=0
        ... )
    """
    # Fail-safe: empty session_id = skip (don't crash hook)
    if not session_id or session_id == "unknown":
        return

    try:
        # Build per-session hook log path
        date = input_data.get("date")
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        log_path = get_hook_log_path(session_id, input_data, date)

        # Create log entry with separated input and output
        log_entry: dict[str, Any] = {
            "hook_event": hook_event,
            "logged_at": datetime.now().astimezone().replace(microsecond=0).isoformat(),
            "exit_code": exit_code,
            "input": input_data,
            "output": output_data,
        }

        # Append to JSONL file
        with log_path.open("a") as f:
            json.dump(log_entry, f, separators=(",", ":"), default=_json_serializer)
            f.write("\n")

    except Exception as e:
        # Log error to stderr but don't crash the hook
        print(f"[unified_logger] Error logging hook event: {e}", file=sys.stderr)
        # Never crash the hook - silently continue
        pass


def log_event_to_session(
    session_id: str, hook_event: str, input_data: dict[str, Any]
) -> GateResult | None:
    """Update session state for a hook event.

    NOTE: This function no longer logs to the JSONL file directly.
    Logging is now done by the router AFTER all gates complete,
    so that output data can be included in the log entry.

    1. Updates the session state file with event timestamp
    2. For SubagentStop and Stop events, performs additional state updates

    Args:
        session_id: Claude Code session ID
        hook_event: Name of the hook event
        input_data: Full input data from the hook

    Returns:
        GateResult for SessionStart events, None otherwise
    """
    if not session_id or session_id == "unknown":
        return None

    # NOTE: JSONL logging moved to router.py execute_hooks() to include output

    if hook_event == "SubagentStop":
        handle_subagent_stop(session_id, input_data)
    elif hook_event == "Stop":
        handle_stop(session_id, input_data)
    elif hook_event == "PostToolUse":
        handle_post_tool_use(session_id, input_data)
    elif hook_event == "SessionStart":
        # Create session state - the actual output is handled by check_session_start_gate
        # to avoid duplication. This just ensures state file exists.
        get_or_create_session_state(session_id)
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
        elif skill_name == "qa":
            # QA skill invoked
            set_qa_invoked(session_id)
            logger.info("QA gate set via activate_skill")


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

    # Clear hydration_pending when hydrator completes with valid output
    # This is the ONLY place hydration_pending should be cleared for hydrator
    if "hydrator" in subagent_type.lower():
        result_text = ""
        if isinstance(subagent_result, dict):
            result_text = subagent_result.get("output", "")
        elif isinstance(subagent_result, str):
            result_text = subagent_result

        # Validate hydrator returned a proper plan (has HYDRATION RESULT marker)
        if "## HYDRATION RESULT" in result_text or "HYDRATION RESULT" in result_text:
            clear_hydration_pending(session_id)
            logger.info("Hydration gate cleared: valid hydrator output received")
        else:
            # Invalid hydrator output - keep gate blocked
            logger.warning(
                "Hydrator completed without valid plan. "
                "Missing '## HYDRATION RESULT' marker. Gate remains blocked."
            )


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

    # Session ID and hook event are required - fail if missing
    if "session_id" not in input_data:
        print(json.dumps({}))
        sys.exit(0)
    session_id = input_data["session_id"]

    if "hook_event_name" not in input_data:
        print(json.dumps({}))
        sys.exit(0)
    hook_event = input_data["hook_event_name"]

    # Log event to single session file
    result: GateResult | None = None
    try:
        result = log_event_to_session(session_id, hook_event, input_data)
    except Exception as e:
        # Log but don't fail - hook should continue with noop
        logger.warning(f"Failed to log event to session: {type(e).__name__}: {e}")

    # Output result as JSON (may contain debug info for SessionStart)
    if result:
        # Use pydantic model for proper serialization
        print(json.dumps({
            "verdict": result.verdict.value,
            "system_message": result.system_message,
            "context_injection": result.context_injection,
            "metadata": result.metadata,
        }))
    else:
        print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
