"""Session state management for gate agent coordination.

Provides atomic CRUD operations for hydrator and custodiet state files.
State files enable cross-gate communication per specs/gate-agent-architecture.md.

State files:
- hydrator-{project_hash}.json: Written by UserPromptSubmit, read by PreToolUse/PostToolUse
- custodiet-{project_hash}.json: Written by PostToolUse, read by PreToolUse for overdue check
"""

from __future__ import annotations

import hashlib
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


def get_project_hash(cwd: str) -> str:
    """Hash project cwd to stable 12-char identifier.

    Same cwd always produces same hash, enabling state persistence
    across subagents (which get new session_ids but share cwd).

    Args:
        cwd: Current working directory path

    Returns:
        12-character hex string
    """
    return hashlib.sha256(cwd.encode()).hexdigest()[:12]


def get_hydrator_state_path(cwd: str) -> Path:
    """Get hydrator state file path for project.

    Args:
        cwd: Current working directory

    Returns:
        Path to hydrator-{project_hash}.json
    """
    project_hash = get_project_hash(cwd)
    return get_state_dir() / f"hydrator-{project_hash}.json"


def get_custodiet_state_path(cwd: str) -> Path:
    """Get custodiet state file path for project.

    Args:
        cwd: Current working directory

    Returns:
        Path to custodiet-{project_hash}.json
    """
    project_hash = get_project_hash(cwd)
    return get_state_dir() / f"custodiet-{project_hash}.json"


def load_hydrator_state(cwd: str, retries: int = 3) -> HydratorState | None:
    """Load hydrator state for project.

    Uses retry logic to handle race conditions during concurrent writes.

    Args:
        cwd: Current working directory
        retries: Number of retry attempts on JSONDecodeError

    Returns:
        HydratorState dict or None if not found
    """
    path = get_hydrator_state_path(cwd)
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


def save_hydrator_state(cwd: str, state: HydratorState) -> None:
    """Atomically save hydrator state.

    Uses write-then-rename pattern for atomic updates.
    Unique temp file per write to avoid race conditions.

    Args:
        cwd: Current working directory
        state: HydratorState to save
    """
    import tempfile

    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)

    state_path = get_hydrator_state_path(cwd)

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


def load_custodiet_state(cwd: str, retries: int = 3) -> CustodietState | None:
    """Load custodiet state for project.

    Uses retry logic to handle race conditions during concurrent writes.

    Args:
        cwd: Current working directory
        retries: Number of retry attempts on JSONDecodeError

    Returns:
        CustodietState dict or None if not found
    """
    path = get_custodiet_state_path(cwd)
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


def save_custodiet_state(cwd: str, state: CustodietState) -> None:
    """Atomically save custodiet state.

    Uses write-then-rename pattern for atomic updates.
    Unique temp file per write to avoid race conditions.

    Args:
        cwd: Current working directory
        state: CustodietState to save
    """
    import tempfile

    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)

    state_path = get_custodiet_state_path(cwd)

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


def set_error_flag(cwd: str, error_type: str, message: str) -> None:
    """Set error flag in custodiet state.

    Called when custodiet detects compliance failure or needs intervention.
    Other hooks can read this via get_error_flag() to enforce blocking.

    Args:
        cwd: Current working directory for project hash
        error_type: Type of error (compliance_failure, intervention_required, cannot_assess)
        message: Human-readable error description
    """
    state = load_custodiet_state(cwd)
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
    save_custodiet_state(cwd, state)


def get_error_flag(cwd: str) -> ErrorFlag | None:
    """Get error flag from custodiet state.

    Called by other hooks to check if custodiet has flagged an issue.

    Args:
        cwd: Current working directory for project hash

    Returns:
        ErrorFlag dict or None if no flag set
    """
    state = load_custodiet_state(cwd)
    if state is None:
        return None
    return state.get("error_flag")


def clear_error_flag(cwd: str) -> None:
    """Clear error flag from custodiet state.

    Called after intervention is resolved or compliance check passes.

    Args:
        cwd: Current working directory for project hash
    """
    state = load_custodiet_state(cwd)
    if state is None:
        return

    state["error_flag"] = None
    save_custodiet_state(cwd, state)
