"""Single session file management for v1.0 core loop.

Provides atomic CRUD operations for unified session state file.
State enables cross-hook coordination per specs/flow.md.

Session file: /tmp/aops-{YYYY-MM-DD}-{session_id}.json

IMPORTANT: State is keyed by session_id, NOT project cwd. Each Claude client session
is independent - multiple sessions can run from the same project directory and must
not share state. Session ID is the unique identifier provided by Claude Code.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
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
    state: dict[str, Any]  # custodiet_blocked, current_workflow, hydration_pending

    # Hydration data
    hydration: dict[
        str, Any
    ]  # original_prompt, hydrated_intent, acceptance_criteria, critic_verdict

    # Agent tracking
    main_agent: dict[str, Any]  # current_task, todos_completed, todos_total
    subagents: dict[str, Any]  # per-agent invocation records

    # Session insights (written at close)
    insights: dict[str, Any] | None


def get_session_file_path(session_id: str, date: str | None = None) -> Path:
    """Get unified session file path.

    Args:
        session_id: Claude Code session ID
        date: Optional date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Path to /tmp/aops-{date}-{session_id}.json
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Path("/tmp") / f"aops-{date}-{session_id}.json"


def load_session_state(session_id: str, retries: int = 3) -> SessionState | None:
    """Load unified session state.

    Searches for session file with today's date first, then tries yesterday
    (for sessions spanning midnight).

    Args:
        session_id: Claude Code session ID
        retries: Number of retry attempts on JSONDecodeError

    Returns:
        SessionState dict or None if not found
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    for date in [today, yesterday]:
        path = get_session_file_path(session_id, date)
        if not path.exists():
            continue

        for attempt in range(retries):
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                if attempt < retries - 1:
                    time.sleep(0.01)
                    continue
                return None
            except OSError:
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
        state["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if "session_id" not in state:
        state["session_id"] = session_id

    path = get_session_file_path(session_id, state["date"])

    fd, temp_path_str = tempfile.mkstemp(
        prefix=f"aops-{state['date']}-", suffix=".tmp", dir="/tmp"
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

    Args:
        session_id: Claude Code session ID

    Returns:
        New SessionState with defaults
    """
    now = datetime.now(timezone.utc)
    return SessionState(
        session_id=session_id,
        date=now.strftime("%Y-%m-%d"),
        started_at=now.isoformat(),
        ended_at=None,
        state={
            "custodiet_blocked": False,
            "custodiet_block_reason": None,
            "current_workflow": None,
            "hydration_pending": False,
        },
        hydration={
            "original_prompt": None,
            "hydrated_intent": None,
            "acceptance_criteria": [],
            "critic_verdict": None,
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


def is_custodiet_blocked(session_id: str) -> bool:
    """Check if session is blocked by custodiet.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if custodiet_blocked flag is set
    """
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

    Args:
        session_id: Claude Code session ID

    Returns:
        True if hydration_pending flag is set
    """
    state = load_session_state(session_id)
    if state is None:
        return False
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

    Called when prompt-hydrator is invoked.

    Args:
        session_id: Claude Code session ID
    """
    state = load_session_state(session_id)
    if state is None:
        return
    state["state"]["hydration_pending"] = False
    save_session_state(session_id, state)


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
        "last_invoked": datetime.now(timezone.utc).isoformat(),
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
    state["ended_at"] = datetime.now(timezone.utc).isoformat()
    save_session_state(session_id, state)
