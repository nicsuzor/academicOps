"""Single session file management for v1.0 core loop.

Provides atomic CRUD operations for unified session state file.
State enables cross-hook coordination per specs/flow.md.

Session file: ~/writing/sessions/status/YYYYMMDD-sessionID.json

IMPORTANT: State is keyed by session_id, NOT project cwd. Each Claude client session
is independent - multiple sessions can run from the same project directory and must
not share state. Session ID is the unique identifier provided by Claude Code.

Location: Sessions are stored in a centralized flat directory for easy access and
cleanup. Files are named by date and session hash (e.g., 20260121-abc12345.json).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict


class SessionState(TypedDict, total=False):
    """Unified session state per flow.md spec."""

    # Core identifiers
    session_id: str
    date: str  # YYYY-MM-DD
    started_at: str  # ISO timestamp
    ended_at: str | None

    # Execution state
    state: dict[str, Any]  # custodiet_blocked, current_workflow, hydration_pending,
    # reflection_output_since_prompt

    # Hydration data
    hydration: dict[
        str, Any
    ]  # original_prompt, hydrated_intent, acceptance_criteria, critic_verdict,
    # turns_since_hydration, turns_since_critic

    # Agent tracking
    main_agent: dict[str, Any]  # current_task, todos_completed, todos_total
    subagents: dict[str, Any]  # per-agent invocation records

    # Session insights (written at close)
    insights: dict[str, Any] | None


def load_session_state(session_id: str, retries: int = 3) -> SessionState | None:
    """Load unified session state.

    Searches for session file matching session_id hash. Checks today's files first,
    then yesterday's (for sessions spanning midnight). Handles both new format
    (YYYYMMDD-HH-hash.json) and legacy format (YYYYMMDD-hash.json).

    Args:
        session_id: Claude Code session ID
        retries: Number of retry attempts on JSONDecodeError

    Returns:
        SessionState dict or None if not found
    """
    from lib.session_paths import get_session_short_hash, get_session_status_dir

    # Use local time for file lookup to match local-time-based storage
    now = datetime.now()
    today = now.strftime("%Y%m%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y%m%d")

    short_hash = get_session_short_hash(session_id)
    status_dir = get_session_status_dir(session_id)

    # Search for files matching this session_id on today or yesterday
    for date_compact in [today, yesterday]:
        # New format: YYYYMMDD-HH-hash.json (try all hours)
        new_pattern = f"{date_compact}-??-{short_hash}.json"
        # Legacy format: YYYYMMDD-hash.json
        legacy_pattern = f"{date_compact}-{short_hash}.json"

        for pattern in [new_pattern, legacy_pattern]:
            matches = list(status_dir.glob(pattern))
            if matches:
                # Use the most recent file if multiple matches
                path = max(matches, key=lambda p: p.stat().st_mtime)
                for attempt in range(retries):
                    try:
                        return json.loads(path.read_text())
                    except json.JSONDecodeError as e:
                        if attempt < retries - 1:
                            time.sleep(0.01)
                            continue
                        # All retries exhausted - log the error
                        import logging

                        logging.getLogger(__name__).warning(
                            f"Session state JSON decode failed after {retries} retries: {path}: {e}"
                        )
                        return None
                    except OSError as e:
                        # I/O error - log and return None
                        import logging

                        logging.getLogger(__name__).debug(
                            f"Session state read failed (OSError): {path}: {e}"
                        )
                        return None

    return None


def save_session_state(session_id: str, state: SessionState) -> None:
    """Atomically save unified session state.

    Uses write-then-rename pattern for atomic updates.

    Args:
        session_id: Claude Code session ID
        state: SessionState to save
    """
    import tempfile

    # Ensure date is set
    if "date" not in state:
        # Standard format with TZ info in local time (e.g., 2026-01-22T16:25:17+10:00)
        state["date"] = datetime.now().astimezone().replace(microsecond=0).isoformat()
    if "session_id" not in state:
        state["session_id"] = session_id

    # Path uses the full ISO date (including hour) to ensure consistent file naming
    # across session lifetime - prevents creating new files when hour changes
    from lib.session_paths import get_session_file_path
    path = get_session_file_path(session_id, state["date"])

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path_str = tempfile.mkstemp(
        prefix=f"aops-{state['date']}-", suffix=".tmp", dir=str(path.parent)
    )
    temp_path = Path(temp_path_str)

    try:
        os.write(fd, json.dumps(state, indent=2).encode())
        os.close(fd)
        temp_path.rename(path)
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        temp_path.unlink(missing_ok=True)
        raise


def create_session_state(session_id: str) -> SessionState:
    """Create initial session state.

    Sets hydration_pending=True by default to enforce the hydration gate.
    This is cleared when:
    - UserPromptSubmit sees / or . prefix (skip hydration)
    - prompt-hydrator Task is invoked (normal flow)

    Note: UserPromptSubmit does NOT fire for the first prompt of a fresh session
    (Claude Code limitation), so we default to pending=True here in SessionStart
    to ensure the gate blocks until hydrator runs.

    Args:
        session_id: Claude Code session ID

    Returns:
        New SessionState with defaults
    """
    # Use local time with TZ info for date and started_at
    now = datetime.now().astimezone().replace(microsecond=0)
    return SessionState(
        session_id=session_id,
        date=now.isoformat(),
        started_at=now.isoformat(),
        ended_at=None,
        state={
            "custodiet_blocked": False,
            "custodiet_block_reason": None,
            "current_workflow": None,
            "hydration_pending": True,  # Default True - gate blocks until hydrator invoked
            "qa_invoked": False,
            "handover_skill_invoked": True,  # Gate starts OPEN - reset when mutating tool used
        },
        hydration={
            "original_prompt": None,
            "hydrated_intent": None,
            "acceptance_criteria": [],
            "critic_verdict": None,
            "turns_since_hydration": -1,
            "turns_since_critic": -1,
        },
        main_agent={
            "current_task": None,
            "todos_completed": 0,
            "todos_total": 0,
        },
        subagents={},
        insights=None,
    )


def get_or_create_session_state(session_id: str) -> SessionState:
    """Load existing session state or create new one.

    Args:
        session_id: Claude Code session ID

    Returns:
        SessionState (existing or new)
    """
    state = load_session_state(session_id)
    if state is None:
        state = create_session_state(session_id)
        save_session_state(session_id, state)
    return state


# ============================================================================
# Custodiet Block API
# ============================================================================


def is_custodiet_enabled() -> bool:
    """Check if custodiet blocking is enabled.

    Set CUSTODIET_DISABLED=1 to bypass blocking while keeping reporting.

    Returns:
        True if custodiet blocking is enabled (default)
    """
    disabled = os.environ.get("CUSTODIET_DISABLED", "").lower()
    return disabled not in ("1", "true", "yes")


def is_custodiet_blocked(session_id: str) -> bool:
    """Check if session is blocked by custodiet.

    Returns False if CUSTODIET_DISABLED=1, even if a block is set.
    This allows the agent to report issues without halting the session.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if custodiet_blocked flag is set AND blocking is enabled
    """
    if not is_custodiet_enabled():
        return False
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("custodiet_blocked", False)


def set_custodiet_block(session_id: str, reason: str) -> None:
    """Set custodiet block flag.

    Called when custodiet detects a violation. All hooks should check
    this flag and FAIL until cleared.

    Args:
        session_id: Claude Code session ID
        reason: Human-readable reason for block
    """
    state = get_or_create_session_state(session_id)
    state["state"]["custodiet_blocked"] = True
    state["state"]["custodiet_block_reason"] = reason
    save_session_state(session_id, state)


def clear_custodiet_block(session_id: str) -> None:
    """Clear custodiet block flag.

    Args:
        session_id: Claude Code session ID
    """
    state = load_session_state(session_id)
    if state is None:
        return
    state["state"]["custodiet_blocked"] = False
    state["state"]["custodiet_block_reason"] = None
    save_session_state(session_id, state)


# ============================================================================
# Hydration Pending API
# ============================================================================


def is_hydration_pending(session_id: str) -> bool:
    """Check if hydration is pending for this session.

    FAIL-CLOSED: Returns True if state doesn't exist (assumes pending).
    This handles the case where UserPromptSubmit doesn't fire for the
    first prompt of a session (Claude Code limitation).

    Args:
        session_id: Claude Code session ID

    Returns:
        True if hydration_pending flag is set OR state doesn't exist
    """
    state = load_session_state(session_id)
    if state is None:
        # FAIL-CLOSED: No state means first prompt, assume hydration pending
        return True
    return state.get("state", {}).get("hydration_pending", False)


def set_hydration_pending(session_id: str, original_prompt: str) -> None:
    """Set hydration pending flag with original prompt.

    Args:
        session_id: Claude Code session ID
        original_prompt: The user's original prompt
    """
    state = get_or_create_session_state(session_id)
    state["state"]["hydration_pending"] = True
    state["hydration"]["original_prompt"] = original_prompt
    save_session_state(session_id, state)


def clear_hydration_pending(session_id: str) -> None:
    """Clear hydration_pending flag.

    Called when prompt-hydrator is invoked or when a skill is invoked
    (via UserPromptSubmit detecting '/' prefix).

    Uses get_or_create to ensure state exists - otherwise clearing would
    silently fail and is_hydration_pending would return True (fail-closed).

    Args:
        session_id: Claude Code session ID
    """
    state = get_or_create_session_state(session_id)
    state["state"]["hydration_pending"] = False
    save_session_state(session_id, state)


def set_hydration_temp_path(session_id: str, temp_path: str) -> None:
    """Store the hydration temp file path.

    Called by user_prompt_submit.py after writing the hydration context file.
    The gate can then retrieve this to include in the block message.

    Args:
        session_id: Claude Code session ID
        temp_path: Absolute path to the hydration temp file
    """
    state = get_or_create_session_state(session_id)
    state["hydration"]["temp_path"] = temp_path
    save_session_state(session_id, state)


def get_hydration_temp_path(session_id: str) -> str | None:
    """Get the hydration temp file path.

    Args:
        session_id: Claude Code session ID

    Returns:
        Path to temp file, or None if not set
    """
    state = load_session_state(session_id)
    if state is None:
        return None
    return state.get("hydration", {}).get("temp_path")


# ============================================================================
# Hydration Data API
# ============================================================================


def set_hydration_result(
    session_id: str,
    hydrated_intent: str,
    acceptance_criteria: list[str],
    workflow: str,
) -> None:
    """Store hydration results.

    Args:
        session_id: Claude Code session ID
        hydrated_intent: The hydrated intent/plan
        acceptance_criteria: List of acceptance criteria
        workflow: Selected workflow name
    """
    state = get_or_create_session_state(session_id)
    state["hydration"]["hydrated_intent"] = hydrated_intent
    state["hydration"]["acceptance_criteria"] = acceptance_criteria
    state["state"]["current_workflow"] = workflow
    save_session_state(session_id, state)


def set_critic_verdict(session_id: str, verdict: str) -> None:
    """Store critic verdict.

    Args:
        session_id: Claude Code session ID
        verdict: PROCEED, REVISE, or HALT
    """
    state = get_or_create_session_state(session_id)
    state["hydration"]["critic_verdict"] = verdict
    save_session_state(session_id, state)


def get_hydration_data(session_id: str) -> dict[str, Any] | None:
    """Get hydration data for QA verifier.

    Args:
        session_id: Claude Code session ID

    Returns:
        Hydration dict or None
    """
    state = load_session_state(session_id)
    if state is None:
        return None
    return state.get("hydration")


def update_hydration_metrics(
    session_id: str,
    turns_since_hydration: int | None = None,
    turns_since_critic: int | None = None
) -> None:
    """Update hydration tracking metrics.

    Args:
        session_id: Claude Code session ID
        turns_since_hydration: Optional override for turns count
        turns_since_critic: Optional override for critic count
    """
    state = get_or_create_session_state(session_id)
    if turns_since_hydration is not None:
        state["hydration"]["turns_since_hydration"] = turns_since_hydration
    if turns_since_critic is not None:
        state["hydration"]["turns_since_critic"] = turns_since_critic
    save_session_state(session_id, state)


# ============================================================================
# Subagent Tracking API
# ============================================================================


def record_subagent_invocation(
    session_id: str, agent_name: str, result: dict[str, Any]
) -> None:
    """Record a subagent invocation.

    Args:
        session_id: Claude Code session ID
        agent_name: Name of the subagent
        result: Result data from the subagent
    """
    state = get_or_create_session_state(session_id)
    state["subagents"][agent_name] = {
        "last_invoked": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        **result,
    }
    save_session_state(session_id, state)


# ============================================================================
# Session Insights API
# ============================================================================


def set_session_insights(session_id: str, insights: dict[str, Any]) -> None:
    """Set session insights (final step before close).

    Args:
        session_id: Claude Code session ID
        insights: Session insights data
    """
    state = get_or_create_session_state(session_id)
    state["insights"] = insights
    state["ended_at"] = datetime.now().astimezone().replace(microsecond=0).isoformat()
    save_session_state(session_id, state)


# ============================================================================
# Current Task API
# ============================================================================


def set_current_task(session_id: str, task_id: str, source: str = "unknown") -> bool:
    """Bind a task to the current session.

    Called by hooks when task routing occurs. Enables observability:
    every session has a linked task after hydration.

    Args:
        session_id: Claude Code session ID
        task_id: Task ID to bind (e.g., "aops-abc123")
        source: Binding source ("hydrator" | "fallback_hook" | "manual")

    Returns:
        True if binding succeeded
    """
    import logging

    logger = logging.getLogger(__name__)

    state = get_or_create_session_state(session_id)
    state["main_agent"]["current_task"] = task_id
    state["main_agent"]["task_binding_source"] = source
    state["main_agent"]["task_binding_ts"] = (
        datetime.now().astimezone().replace(microsecond=0).isoformat()
    )
    save_session_state(session_id, state)

    logger.info(f"Task bound to session: {task_id} (source={source})")
    return True


def get_current_task(session_id: str) -> str | None:
    """Get the task bound to this session.

    Args:
        session_id: Claude Code session ID

    Returns:
        Task ID string or None if no task bound
    """
    state = load_session_state(session_id)
    if state is None:
        return None
    return state.get("main_agent", {}).get("current_task")


def clear_current_task(session_id: str) -> bool:
    """Clear the task binding from this session.

    Called when task is completed or session ends normally.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if task was cleared, False if no task was bound
    """
    import logging

    logger = logging.getLogger(__name__)

    state = load_session_state(session_id)
    if state is None:
        return False

    current_task = state.get("main_agent", {}).get("current_task")
    if not current_task:
        return False

    state["main_agent"]["current_task"] = None
    state["main_agent"]["task_cleared_ts"] = (
        datetime.now().astimezone().replace(microsecond=0).isoformat()
    )
    save_session_state(session_id, state)

    logger.info(f"Task cleared from session: {current_task}")
    return True


# ============================================================================
# Gates Bypass API
# ============================================================================


def set_gates_bypassed(session_id: str, bypassed: bool = True) -> None:
    """Set gates bypass flag for emergency/trivial operations.

    Called when user prefix '.' is detected - bypasses all enforcement gates.

    Args:
        session_id: Claude Code session ID
        bypassed: Whether gates are bypassed (default True)
    """
    state = get_or_create_session_state(session_id)
    state["state"]["gates_bypassed"] = bypassed
    save_session_state(session_id, state)


def is_gates_bypassed(session_id: str) -> bool:
    """Check if gates are bypassed for this session.

    Returns True when user has used '.' prefix for emergency/trivial operations.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if gates_bypassed flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("gates_bypassed", False)


# ============================================================================
# Reflection Output Tracking API
# ============================================================================


def set_reflection_output(session_id: str, value: bool = True) -> None:
    """Set reflection_output_since_prompt flag.

    Called when a Framework Reflection is detected in assistant output.

    Args:
        session_id: Claude Code session ID
        value: Whether reflection has been output (default True)
    """
    state = get_or_create_session_state(session_id)
    state["state"]["reflection_output_since_prompt"] = value
    save_session_state(session_id, state)


def clear_reflection_output(session_id: str) -> None:
    """Clear reflection_output_since_prompt flag.

    Called on UserPromptSubmit to reset tracking for new prompt.

    Args:
        session_id: Claude Code session ID
    """
    state = load_session_state(session_id)
    if state is None:
        return
    state["state"]["reflection_output_since_prompt"] = False
    save_session_state(session_id, state)


def has_reflection_output(session_id: str) -> bool:
    """Check if reflection has been output since last user prompt.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if reflection_output_since_prompt flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("reflection_output_since_prompt", False)


# ============================================================================
# Stop Hook Reflection Validation API
# ============================================================================


def set_stop_reflection_validated(session_id: str) -> None:
    """Set stop_reflection_validated flag when Stop hook validates reflection.

    This flag is NOT cleared by UserPromptSubmit, unlike reflection_output_since_prompt.
    Once the Stop hook has validated a reflection exists, the session can end
    even if additional prompts are sent.

    Args:
        session_id: Claude Code session ID
    """
    state = get_or_create_session_state(session_id)
    state["state"]["stop_reflection_validated"] = True
    save_session_state(session_id, state)


def is_stop_reflection_validated(session_id: str) -> bool:
    """Check if Stop hook has validated a reflection for this session.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if stop_reflection_validated flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("stop_reflection_validated", False)


# ============================================================================
# Critic Invocation Tracking API
# ============================================================================


def set_critic_invoked(session_id: str, verdict: str | None = None) -> None:
    """Set critic_invoked flag when critic agent completes.

    Part of the three-gate requirement for destructive operations:
    (a) task claimed, (b) critic invoked, (c) todo with handover.

    Args:
        session_id: Claude Code session ID
        verdict: Optional critic verdict (PROCEED/REVISE/HALT)
    """
    state = get_or_create_session_state(session_id)
    state["state"]["critic_invoked"] = True
    if verdict:
        state["hydration"]["critic_verdict"] = verdict
    save_session_state(session_id, state)


def is_critic_invoked(session_id: str) -> bool:
    """Check if critic agent has been invoked for this session.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if critic_invoked flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("critic_invoked", False)


# ============================================================================
# QA Invocation Tracking API
# ============================================================================


def set_qa_invoked(session_id: str) -> None:
    """Set qa_invoked flag when QA skill is executed.

    Args:
        session_id: Claude Code session ID
    """
    state = get_or_create_session_state(session_id)
    state["state"]["qa_invoked"] = True
    save_session_state(session_id, state)


def is_qa_invoked(session_id: str) -> bool:
    """Check if QA skill has been invoked for this session.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if qa_invoked flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("qa_invoked", False)


# ============================================================================
# Todo Handover Validation API
# ============================================================================


def set_todo_with_handover(session_id: str, handover_content: str | None = None) -> None:
    """Set todo_with_handover flag when todo list includes handover step.

    Part of the three-gate requirement for destructive operations:
    (a) task claimed, (b) critic invoked, (c) todo with handover.

    Args:
        session_id: Claude Code session ID
        handover_content: Optional content of the handover todo item
    """
    state = get_or_create_session_state(session_id)
    state["state"]["todo_with_handover"] = True
    if handover_content:
        state["state"]["handover_step_content"] = handover_content
    save_session_state(session_id, state)


def has_todo_with_handover(session_id: str) -> bool:
    """Check if todo list includes a handover/session-end step.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if todo_with_handover flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("todo_with_handover", False)


def clear_todo_handover(session_id: str) -> None:
    """Clear todo_with_handover flag (e.g., when todos are reset).

    Args:
        session_id: Claude Code session ID
    """
    state = load_session_state(session_id)
    if state is None:
        return
    state["state"]["todo_with_handover"] = False
    state["state"]["handover_step_content"] = None
    save_session_state(session_id, state)


# ============================================================================
# Plan Mode Invocation Tracking API
# ============================================================================


def set_plan_mode_invoked(session_id: str) -> None:
    """Set plan_mode_invoked flag when EnterPlanMode tool is called.

    Part of the four-gate requirement for destructive operations:
    (a) task claimed, (b) plan mode invoked, (c) critic invoked, (d) todo with handover.

    Args:
        session_id: Claude Code session ID
    """
    state = get_or_create_session_state(session_id)
    state["state"]["plan_mode_invoked"] = True
    save_session_state(session_id, state)


def is_plan_mode_invoked(session_id: str) -> bool:
    """Check if EnterPlanMode has been invoked for this session.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if plan_mode_invoked flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("plan_mode_invoked", False)


# ============================================================================
# Gate Status Check API
# ============================================================================


def check_all_gates(session_id: str) -> dict[str, bool]:
    """Check status of all four gates for destructive operations.

    Returns status of: task_bound, plan_mode_invoked, critic_invoked, todo_with_handover.

    Args:
        session_id: Claude Code session ID

    Returns:
        Dict with gate statuses and overall 'all_passed' flag
    """
    task_bound = get_current_task(session_id) is not None
    plan_mode = is_plan_mode_invoked(session_id)
    critic_invoked = is_critic_invoked(session_id)
    todo_handover = has_todo_with_handover(session_id)

    return {
        "task_bound": task_bound,
        "plan_mode_invoked": plan_mode,
        "critic_invoked": critic_invoked,
        "todo_with_handover": todo_handover,
        "all_passed": task_bound and plan_mode and critic_invoked and todo_handover,
    }


# ============================================================================
# Handover Skill Tracking API
# ============================================================================


def set_handover_skill_invoked(session_id: str) -> None:
    """Set handover_skill_invoked flag when /handover skill is executed.

    Called by the PostToolUse handover_gate.py hook when it detects
    the Skill tool being invoked with skill="handover".

    Args:
        session_id: Claude Code session ID
    """
    state = get_or_create_session_state(session_id)
    state["state"]["handover_skill_invoked"] = True
    save_session_state(session_id, state)


def is_handover_skill_invoked(session_id: str) -> bool:
    """Check if the handover gate is open (allowing stop without handover).

    The gate starts OPEN (True) and closes when mutating tools are detected.
    Returns True if no state exists or no mutations have occurred.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if gate is open (no handover required), False if closed (handover required)
    """
    state = load_session_state(session_id)
    if state is None:
        # No state = no mutations = gate open
        return True
    # Default to True for backwards compatibility with old state files
    # that don't have this field
    return state.get("state", {}).get("handover_skill_invoked", True)


def clear_handover_skill_invoked(session_id: str) -> None:
    """Clear handover_skill_invoked flag.

    Called on new user prompt to reset for multi-turn sessions.

    Args:
        session_id: Claude Code session ID
    """
    state = load_session_state(session_id)
    if state is None:
        return
    state["state"]["handover_skill_invoked"] = False
    save_session_state(session_id, state)


def set_hydrator_active(session_id: str) -> None:
    """Set hydrator_active flag when prompt-hydrator subagent starts.

    Called by PreToolUse when Task tool is invoked with hydrator subagent_type.
    This flag allows the hydration gate to bypass checks for the hydrator's
    own tool calls (which would otherwise be blocked in a recursive loop).

    Args:
        session_id: Claude Code session ID
    """
    state = get_or_create_session_state(session_id)
    state["state"]["hydrator_active"] = True
    save_session_state(session_id, state)


def is_hydrator_active(session_id: str) -> bool:
    """Check if the prompt-hydrator subagent is currently active.

    Used by hydration gate to bypass blocking for the hydrator's tool calls.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if hydrator_active flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("hydrator_active", False)


def clear_hydrator_active(session_id: str) -> None:
    """Clear hydrator_active flag when prompt-hydrator subagent completes.

    Called by PostToolUse when Task tool completes.

    Args:
        session_id: Claude Code session ID
    """
    state = load_session_state(session_id)
    if state is None:
        return
    state["state"]["hydrator_active"] = False
    save_session_state(session_id, state)


# ============================================================================
# Stop Hook Mode API (Interactive/Relaxed Sessions)
# ============================================================================


def set_stop_hook_relaxed(session_id: str) -> None:
    """Set stop_hook_relaxed flag to disable hard-blocking.

    When set, the stop hook will warn instead of block. Useful for
    interactive sessions where user is actively engaged.

    Args:
        session_id: Claude Code session ID
    """
    state = get_or_create_session_state(session_id)
    state["state"]["stop_hook_relaxed"] = True
    save_session_state(session_id, state)


def is_stop_hook_relaxed(session_id: str) -> bool:
    """Check if stop hook is in relaxed (warn-only) mode.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if stop_hook_relaxed flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("stop_hook_relaxed", False)


def clear_stop_hook_relaxed(session_id: str) -> None:
    """Clear stop_hook_relaxed flag to restore hard-blocking.

    Args:
        session_id: Claude Code session ID
    """
    state = load_session_state(session_id)
    if state is None:
        return
    state["state"]["stop_hook_relaxed"] = False
    save_session_state(session_id, state)
