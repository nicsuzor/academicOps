#!/usr/bin/env python3
"""
Unified hook logger for Claude Code and Gemini CLI.

Logs ALL hook events to:
1. Session state file: /tmp/aops-{YYYY-MM-DD}-{session_id}.json (for gate state)
2. Per-session JSONL hook log: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
   or ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-hooks.jsonl (for event audit trail)

Note: Permanent session insights are extracted from Framework Reflection
by transcript.py, not by this hook. This hook only records operational
metrics to the temporary session state file.
"""

import json
import logging
import os
import psutil
import sys
import time
from datetime import datetime, timezone
from typing import Any

from lib.insights_generator import (
    extract_project_name,
    extract_short_hash,
    generate_fallback_insights,
)
from lib.session_paths import (
    get_hook_log_path,
)
from lib.session_state import (
    clear_hydration_pending,
    clear_hydrator_active,
    get_or_create_session_state,
    record_subagent_invocation,
    set_critic_invoked,
    set_qa_invoked,
    set_session_insights,
)
from lib.gate_model import GateResult
from hooks.internal_models import HookLogEntry
from hooks.schemas import HookContext, CanonicalHookOutput

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _json_serializer(obj: Any) -> str:
    """Convert non-serializable objects to strings for JSON serialization."""
    return str(obj)


def log_hook_event(
    ctx: HookContext,
    output: CanonicalHookOutput | None = None,
    exit_code: int = 0,
) -> None:
    """
    Log a hook event to the per-session hooks log file.
    """
    session_id = ctx.session_id
    # Fail-safe: empty session_id = skip (don't crash hook)
    if not session_id or session_id == "unknown":
        return

    try:
        # Build per-session hook log path
        input_data = ctx.raw_input
        date = input_data.get("date")
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        log_path = get_hook_log_path(session_id, input_data, date)

        # Gather process metrics for debugging (aops-runaway-fix)
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()

        # Create log entry using typed model
        log_entry = HookLogEntry(
            hook_event=ctx.hook_event,
            logged_at=datetime.now().astimezone().replace(microsecond=0).isoformat(),
            exit_code=exit_code,
            agent_id=ctx.agent_id,
            slug=ctx.slug,
            is_sidechain=ctx.is_sidechain,
            input=input_data,
            output=output.model_dump() if output else None,
        )

        # Add debug metrics to metadata
        log_dict = log_entry.model_dump()
        log_dict["debug"] = {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "mem_rss_mb": mem_info.rss / (1024 * 1024),
            "mem_vms_mb": mem_info.vms / (1024 * 1024),
            "process_uptime": time.time() - process.create_time(),
            "subagent_type": os.environ.get("CLAUDE_SUBAGENT_TYPE"),
        }

        # Append to JSONL file
        with log_path.open("a") as f:
            json.dump(
                log_dict,
                f,
                separators=(",", ":"),
                default=_json_serializer,
            )
            f.write("\n")

    except Exception as e:
        # Log error to stderr but don't crash the hook
        print(f"[unified_logger] Error logging hook event: {e}", file=sys.stderr)


def log_event_to_session(
    session_id: str, hook_event: str, input_data: dict[str, Any]
) -> GateResult | None:
    """Update session state for a hook event.

    NOTE: Logging to JSONL is handled by log_hook_event, called by the router.

    Args:
        session_id: Session ID
        hook_event: Name of the hook event
        input_data: Full input data from the hook

    Returns:
        None
    """
    if not session_id or session_id == "unknown":
        return None

    if hook_event == "SubagentStop":
        handle_subagent_stop(session_id, input_data)
    elif hook_event == "Stop":
        handle_stop(session_id, input_data)
    elif hook_event == "PostToolUse":
        handle_post_tool_use(session_id, input_data)
    elif hook_event == "SessionStart":
        get_or_create_session_state(session_id)
    else:
        # For other events, just ensure session exists
        get_or_create_session_state(session_id)
    return None


def handle_post_tool_use(session_id: str, input_data: dict[str, Any]) -> None:
    """Handle PostToolUse event."""
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input", {})

    # Detect activate_skill(name="critic")
    if tool_name == "activate_skill":
        skill_name = tool_input.get("name")
        if skill_name == "critic":
            set_critic_invoked(session_id, verdict="INVOKED")
            logger.info("Critic gate set via activate_skill")
        elif skill_name == "qa":
            set_qa_invoked(session_id)
            logger.info("QA gate set via activate_skill")


def handle_subagent_stop(session_id: str, input_data: dict[str, Any]) -> None:
    """Handle SubagentStop event - update subagent state in session file."""
    if "subagent_type" not in input_data:
        raise ValueError("Required field 'subagent_type' missing from input_data")
    subagent_type = input_data["subagent_type"]

    if "subagent_result" not in input_data:
        raise ValueError("Required field 'subagent_result' missing from input_data")
    subagent_result = input_data["subagent_result"]

    # Handle both string and dict results
    # TRUNCATE: Never store more than 1KB of subagent output in the session state file.
    # The full output is already logged to the per-session hooks.jsonl audit trail.
    # Storing large strings in the shared state file causes memory-bloat in hooks.
    max_len = 1000
    if isinstance(subagent_result, str):
        if len(subagent_result) > max_len:
            result_data = {"output": subagent_result[:max_len] + "... [TRUNCATED]"}
        else:
            result_data = {"output": subagent_result}
    elif isinstance(subagent_result, dict):
        # Strip large fields but preserve keys for gate logic (verdict, etc.)
        result_data = {
            k: (v[:max_len] + "... [TRUNCATED]")
            if isinstance(v, str) and len(v) > max_len
            else v
            for k, v in subagent_result.items()
        }
    else:
        raw = str(subagent_result)
        result_data = {
            "raw": raw[:max_len] + "... [TRUNCATED]" if len(raw) > max_len else raw
        }

    result_data["stopped_at"] = (
        datetime.now().astimezone().replace(microsecond=0).isoformat()
    )

    record_subagent_invocation(session_id, subagent_type, result_data)

    if subagent_type == "critic":
        verdict = None
        if isinstance(subagent_result, dict):
            verdict = subagent_result.get("verdict")
        elif isinstance(subagent_result, str):
            for v in ["PROCEED", "REVISE", "HALT"]:
                if v in subagent_result.upper():
                    verdict = v
                    break
        set_critic_invoked(session_id, verdict)
        logger.info(f"Critic gate set: verdict={verdict}")

    if "hydrator" in subagent_type.lower():
        clear_hydrator_active(session_id)

        result_text = ""
        if isinstance(subagent_result, dict):
            result_text = subagent_result.get("output", "")
        elif isinstance(subagent_result, str):
            result_text = subagent_result

        if "## HYDRATION RESULT" in result_text or "HYDRATION RESULT" in result_text:
            clear_hydration_pending(session_id)
            logger.info("Hydration gate cleared: valid hydrator output received")
        else:
            logger.warning(
                "Hydrator completed without valid plan. "
                "Missing '## HYDRATION RESULT' marker. Gate remains blocked."
            )


def handle_stop(session_id: str, input_data: dict[str, Any]) -> None:
    """Handle Stop event - record operational metrics to session state."""
    state = get_or_create_session_state(session_id)

    if "hydration" not in state:
        raise ValueError("Required field 'hydration' missing from session state")
    if "stop_reason" not in input_data:
        raise ValueError("Required field 'stop_reason' missing from input_data")

    if "date" not in state:
        state["date"] = datetime.now().astimezone().replace(microsecond=0).isoformat()

    metadata = {
        "session_id": extract_short_hash(session_id),
        "date": state["date"],
        "project": extract_project_name(),
    }

    state_section = state["state"]
    hydration = state["hydration"]
    subagents = state["subagents"]

    operational_metrics = {
        "workflows_used": [state_section["current_workflow"]]
        if "current_workflow" in state_section
        else [],
        "subagents_invoked": list(subagents.keys()),
        "subagent_count": len(subagents),
        "custodiet_blocks": 1 if state_section.get("custodiet_blocked") else 0,
        "stop_reason": input_data["stop_reason"],
        "critic_verdict": hydration["critic_verdict"]
        if "critic_verdict" in hydration
        else None,
        "acceptance_criteria_count": len(hydration["acceptance_criteria"])
        if "acceptance_criteria" in hydration
        else 0,
    }

    insights = generate_fallback_insights(metadata, operational_metrics)

    logger.info(
        f"Session stopped: {metadata['session_id']} "
        f"(subagents={len(subagents)}, custodiet_blocks={operational_metrics['custodiet_blocks']})"
    )

    try:
        set_session_insights(session_id, insights)
        logger.info("Updated session state with operational metrics")
    except Exception as e:
        logger.error(f"Failed to update session state: {e}")
