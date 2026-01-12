"""Session state management for gate agent coordination.

Provides atomic CRUD operations for hydrator and custodiet state files.
State files enable cross-gate communication per specs/gate-agent-architecture.md.

State files:
- hydrator-{session_id}.json: Written by UserPromptSubmit, read by PreToolUse/PostToolUse
- custodiet-{session_id}.json: Written by PostToolUse, read by PreToolUse for overdue check

IMPORTANT: State is keyed by session_id, NOT project cwd. Each Claude client session
is independent - multiple sessions can run from the same project directory and must
not share state. Session ID is the unique identifier provided by Claude Code.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import TypedDict


class HydratorState(TypedDict):
    """State written by UserPromptSubmit hook."""

    last_hydration_ts: float
    declared_workflow: dict[str, str]  # {gate, pre_work, approach}
    active_skill: str
    intent_envelope: str
    guardrails: list[str]
    hydration_pending: bool  # True until prompt-hydrator is invoked


class ErrorFlag(TypedDict):
    """Error flag for cross-hook coordination.

    Set by custodiet when compliance check fails or intervention needed.
    Other hooks can read via get_error_flag() to enforce blocking.
    """

    error_type: str  # compliance_failure, intervention_required, cannot_assess
    message: str
    timestamp: float


class CustodietState(TypedDict):
    """State written by PostToolUse hook."""

    last_compliance_ts: float
    tool_calls_since_compliance: int
    last_drift_warning: str | None
    error_flag: ErrorFlag | None


def get_state_dir() -> Path:
    """Get session state directory.

    Uses CLAUDE_SESSION_STATE_DIR env var if set, otherwise /tmp/claude-session.

    Returns:
        Path to state directory
    """
    override = os.environ.get("CLAUDE_SESSION_STATE_DIR")
    if override:
        return Path(override)
    return Path("/tmp/claude-session")


def get_hydrator_state_path(session_id: str) -> Path:
    """Get hydrator state file path for session.

    Args:
        session_id: Claude Code session ID (unique per client session)

    Returns:
        Path to hydrator-{session_id}.json
    """
    return get_state_dir() / f"hydrator-{session_id}.json"


def get_custodiet_state_path(session_id: str) -> Path:
    """Get custodiet state file path for session.

    Args:
        session_id: Claude Code session ID (unique per client session)

    Returns:
        Path to custodiet-{session_id}.json
    """
    return get_state_dir() / f"custodiet-{session_id}.json"


def load_hydrator_state(session_id: str, retries: int = 3) -> HydratorState | None:
    """Load hydrator state for session.

    Uses retry logic to handle race conditions during concurrent writes.

    Args:
        session_id: Claude Code session ID
        retries: Number of retry attempts on JSONDecodeError

    Returns:
        HydratorState dict or None if not found
    """
    path = get_hydrator_state_path(session_id)
    if not path.exists():
        return None

    for attempt in range(retries):
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            if attempt < retries - 1:
                time.sleep(0.01)  # 10ms backoff
                continue
            return None  # Give up after retries
        except OSError:
            return None

    return None


def save_hydrator_state(session_id: str, state: HydratorState) -> None:
    """Atomically save hydrator state.

    Uses write-then-rename pattern for atomic updates.
    Unique temp file per write to avoid race conditions.

    Args:
        session_id: Claude Code session ID
        state: HydratorState to save
    """
    import tempfile

    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)

    state_path = get_hydrator_state_path(session_id)

    # Write to unique temp file to avoid race conditions
    fd, temp_path_str = tempfile.mkstemp(
        prefix=state_path.stem + "_", suffix=".tmp", dir=state_dir
    )
    temp_path = Path(temp_path_str)

    try:
        os.write(fd, json.dumps(state, indent=2).encode())
        os.close(fd)
        # Atomic rename
        temp_path.rename(state_path)
    except Exception:
        # Clean up temp file on failure
        os.close(fd) if fd else None
        temp_path.unlink(missing_ok=True)
        raise


def load_custodiet_state(session_id: str, retries: int = 3) -> CustodietState | None:
    """Load custodiet state for session.

    Uses retry logic to handle race conditions during concurrent writes.

    Args:
        session_id: Claude Code session ID
        retries: Number of retry attempts on JSONDecodeError

    Returns:
        CustodietState dict or None if not found
    """
    path = get_custodiet_state_path(session_id)
    if not path.exists():
        return None

    for attempt in range(retries):
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            if attempt < retries - 1:
                time.sleep(0.01)  # 10ms backoff
                continue
            return None  # Give up after retries
        except OSError:
            return None

    return None


def save_custodiet_state(session_id: str, state: CustodietState) -> None:
    """Atomically save custodiet state.

    Uses write-then-rename pattern for atomic updates.
    Unique temp file per write to avoid race conditions.

    Args:
        session_id: Claude Code session ID
        state: CustodietState to save
    """
    import tempfile

    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)

    state_path = get_custodiet_state_path(session_id)

    # Write to unique temp file to avoid race conditions
    fd, temp_path_str = tempfile.mkstemp(
        prefix=state_path.stem + "_", suffix=".tmp", dir=state_dir
    )
    temp_path = Path(temp_path_str)

    try:
        os.write(fd, json.dumps(state, indent=2).encode())
        os.close(fd)
        # Atomic rename
        temp_path.rename(state_path)
    except Exception:
        # Clean up temp file on failure
        os.close(fd) if fd else None
        temp_path.unlink(missing_ok=True)
        raise


# ============================================================================
# Error Flag API (for cross-hook coordination)
# ============================================================================


def set_error_flag(session_id: str, error_type: str, message: str) -> None:
    """Set error flag in custodiet state.

    Called when custodiet detects compliance failure or needs intervention.
    Other hooks can read this via get_error_flag() to enforce blocking.

    Args:
        session_id: Claude Code session ID
        error_type: Type of error (compliance_failure, intervention_required, cannot_assess)
        message: Human-readable error description
    """
    state = load_custodiet_state(session_id)
    if state is None:
        state = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 0,
            "last_drift_warning": None,
            "error_flag": None,
        }

    state["error_flag"] = {
        "error_type": error_type,
        "message": message,
        "timestamp": time.time(),
    }
    save_custodiet_state(session_id, state)


def get_error_flag(session_id: str) -> ErrorFlag | None:
    """Get error flag from custodiet state.

    Called by other hooks to check if custodiet has flagged an issue.

    Args:
        session_id: Claude Code session ID

    Returns:
        ErrorFlag dict or None if no flag set
    """
    state = load_custodiet_state(session_id)
    if state is None:
        return None
    return state.get("error_flag")


def clear_error_flag(session_id: str) -> None:
    """Clear error flag from custodiet state.

    Called after intervention is resolved or compliance check passes.

    Args:
        session_id: Claude Code session ID
    """
    state = load_custodiet_state(session_id)
    if state is None:
        return

    state["error_flag"] = None
    save_custodiet_state(session_id, state)


# ============================================================================
# Hydration Gate API (for PreToolUse blocking until hydrator invoked)
# ============================================================================


def is_hydration_pending(session_id: str) -> bool:
    """Check if hydration is pending for this session.

    Called by PreToolUse gate to block tools until prompt-hydrator is invoked.

    Args:
        session_id: Claude Code session ID

    Returns:
        True if hydration_pending flag is set, False otherwise
    """
    state = load_hydrator_state(session_id)
    if state is None:
        return False
    return state.get("hydration_pending", False)


def clear_hydration_pending(session_id: str) -> None:
    """Clear hydration_pending flag.

    Called by PreToolUse gate when it sees Task(prompt-hydrator) invocation.
    This is the mechanical trigger - only the hook can clear it.

    Args:
        session_id: Claude Code session ID
    """
    state = load_hydrator_state(session_id)
    if state is None:
        return

    state["hydration_pending"] = False
    save_hydrator_state(session_id, state)
