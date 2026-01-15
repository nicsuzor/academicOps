"""Single session file management for v1.0 core loop.

Provides atomic CRUD operations for unified session state file.
State enables cross-hook coordination per specs/flow.md.

Session file: ~/.claude/projects/<project>/{YYYYMMDD}-{hash}/session-state.json

IMPORTANT: State is keyed by session_id, NOT project cwd. Each Claude client session
is independent - multiple sessions can run from the same project directory and must
not share state. Session ID is the unique identifier provided by Claude Code.

Location: Sessions are organized in subdirectories by date and session hash for easy
chronological navigation and cleanup.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict, cast


class CustodietState(TypedDict, total=False):
    """Backward compatibility for CustodietState."""

    last_compliance_ts: float
    tool_calls_since_compliance: int
    last_drift_warning: str | None
    error_flag: dict[str, Any] | None


class HydratorState(TypedDict, total=False):
    """Backward compatibility for HydratorState."""

    last_hydration_ts: float
    declared_workflow: dict[str, str]
    active_skill: str
    intent_envelope: str
    guardrails: list[str]
    hydration_pending: bool


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

    Returns: ~/.claude/projects/<project>/{YYYYMMDD}-{hash}/session-state.json

    Args:
        session_id: Claude Code session ID
        date: Optional date string (YYYY-MM-DD). Defaults to today UTC.

    Returns:
        Path to session state file in organized subdirectory structure
    """
    from .session_paths import get_session_directory

    session_dir = get_session_directory(session_id, date)
    return session_dir / "session-state.json"


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
        state["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if "session_id" not in state:
        state["session_id"] = session_id

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
# Backward Compatibility API
# ============================================================================


def load_custodiet_state(session_id: str) -> CustodietState | None:
    """Backward compatibility for load_custodiet_state.

    Args:
        session_id: Claude Code session ID (historically CWD)

    Returns:
        CustodietState or None
    """
    state = load_session_state(session_id)
    if state is None:
        return None

    # Map from SessionState["state"] to CustodietState
    s = state.get("state", {})
    return cast(
        CustodietState,
        {
            "last_compliance_ts": s.get("last_compliance_ts", 0.0),
            "tool_calls_since_compliance": s.get("tool_calls_since_compliance", 0),
            "last_drift_warning": s.get("last_drift_warning"),
        },
    )


def save_custodiet_state(session_id: str, custodiet_state: CustodietState) -> None:
    """Backward compatibility for save_custodiet_state.

    Args:
        session_id: Claude Code session ID (historically CWD)
        custodiet_state: Legacy CustodietState dict
    """
    state = get_or_create_session_state(session_id)
    # Map from CustodietState back to SessionState["state"]
    for k, v in custodiet_state.items():
        state["state"][k] = v
    save_session_state(session_id, state)


def get_state_dir() -> Path:
    """Backward compatibility for get_state_dir.

    Returns:
        Path to state directory
    """
    return Path(os.environ.get("CLAUDE_SESSION_STATE_DIR", "/tmp/claude-session"))


def get_hydrator_state_path(session_id: str) -> Path:
    """Backward compatibility for get_hydrator_state_path."""
    state_dir = get_state_dir()
    safe_id = session_id.replace("/", "_").lstrip("_")
    return state_dir / f"hydrator-{safe_id}.json"


def get_custodiet_state_path(session_id: str) -> Path:
    """Backward compatibility for get_custodiet_state_path."""
    state_dir = get_state_dir()
    safe_id = session_id.replace("/", "_").lstrip("_")
    return state_dir / f"custodiet-{safe_id}.json"


def load_hydrator_state(session_id: str) -> HydratorState | None:
    """Backward compatibility for load_hydrator_state."""
    state = load_session_state(session_id)
    if state is None:
        return None

    h = state.get("hydration", {})
    s = state.get("state", {})
    return cast(
        HydratorState,
        {
            "last_hydration_ts": s.get("last_hydration_ts", 0.0),
            "declared_workflow": {
                "gate": s.get("current_workflow", "none"),
                "approach": "direct",
            },
            "active_skill": s.get("active_skill", ""),
            "intent_envelope": h.get("original_prompt", ""),
            "guardrails": h.get("acceptance_criteria", []),
            "hydration_pending": s.get("hydration_pending", False),
        },
    )


def save_hydrator_state(session_id: str, hydrator_state: HydratorState) -> None:
    """Backward compatibility for save_hydrator_state."""
    state = get_or_create_session_state(session_id)
    # Map back as best as possible
    state["state"]["hydration_pending"] = hydrator_state.get("hydration_pending", False)
    state["state"]["last_hydration_ts"] = hydrator_state.get("last_hydration_ts", 0.0)
    state["hydration"]["original_prompt"] = hydrator_state.get("intent_envelope", "")
    state["hydration"]["acceptance_criteria"] = hydrator_state.get("guardrails", [])
    save_session_state(session_id, state)


def get_error_flag(session_id: str) -> dict[str, Any] | None:
    """Backward compatibility for get_error_flag."""
    state = load_session_state(session_id)
    if state is None:
        return None
    return state.get("state", {}).get("error_flag")


def set_error_flag(session_id: str, error_type: str, message: str) -> None:
    """Backward compatibility for set_error_flag."""
    state = get_or_create_session_state(session_id)
    state["state"]["error_flag"] = {
        "error_type": error_type,
        "message": message,
        "timestamp": time.time(),
    }
    save_session_state(session_id, state)


def clear_error_flag(session_id: str) -> None:
    """Backward compatibility for clear_error_flag."""
    state = load_session_state(session_id)
    if state is None:
        return
    if "error_flag" in state["state"]:
        del state["state"]["error_flag"]
    save_session_state(session_id, state)


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
