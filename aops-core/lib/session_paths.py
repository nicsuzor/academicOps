"""Session path utilities - single source of truth for session file locations.

This module provides centralized path generation for session files to avoid
circular dependencies and ensure consistent path structure across all components.

Session files are stored in ~/writing/sessions/status/ as YYYYMMDD-HH-sessionID.json
where HH is the 24-hour local time when the session was created.
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path


def get_claude_project_folder() -> str:
    """Get Claude Code project folder name from cwd.

    Converts absolute path to sanitized folder name:
    /home/user/project -> -home-user-project

    Returns:
        Project folder name with leading dash and all slashes replaced
    """
    cwd = Path.cwd().resolve()
    # Replace leading / with -, then all / with -
    return "-" + str(cwd).replace("/", "-")[1:]


def get_session_short_hash(session_id: str) -> str:
    """Get 8-character hash from session ID.

    Uses SHA-256 and takes first 8 hex characters for brevity.
    Provides 2^32 (~4 billion) unique combinations.

    Args:
        session_id: Full session identifier

    Returns:
        8-character hex string
    """
    return hashlib.sha256(session_id.encode()).hexdigest()[:8]


def get_session_status_dir() -> Path:
    """Get session status directory from AOPS_SESSION_STATE_DIR.

    This env var is set by the router at SessionStart:
    - Gemini: ~/.gemini/tmp/<hash>/ (from transcript_path)
    - Claude: ~/.claude/projects/<encoded-cwd>/

    Falls back to /tmp for unit tests that don't go through the router.

    Returns:
        Path to session status directory (created if doesn't exist)
    """
    state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
    if not state_dir:
        # Fallback for unit tests that don't go through router
        state_dir = "/tmp/aops-test-sessions"
    status_dir = Path(state_dir)
    status_dir.mkdir(parents=True, exist_ok=True)
    return status_dir


def get_session_file_path_direct(session_id: str, date: str | None = None) -> Path:
    """Get session state file path (flat structure).

    Returns: ~/writing/sessions/status/YYYYMMDD-HH-sessionID.json

    Args:
        session_id: Session identifier from CLAUDE_SESSION_ID
        date: Date in YYYY-MM-DD format or ISO 8601 with timezone (defaults to now local time).
              The hour component is extracted from ISO 8601 dates (e.g., 2026-01-24T17:30:00+10:00).
              For simple YYYY-MM-DD dates, the current hour (local time) is used.

    Returns:
        Path to session state file
    """
    if date is None:
        now = datetime.now().astimezone()
        date_compact = now.strftime("%Y%m%d")
        hour = now.strftime("%H")
    elif "T" in date:
        # ISO 8601 format with time: 2026-01-24T17:30:00+10:00
        date_compact = date[:10].replace("-", "")  # Extract YYYY-MM-DD -> YYYYMMDD
        hour = date[11:13]  # Extract HH from time portion
    else:
        # Simple YYYY-MM-DD format - use current hour
        date_compact = date.replace("-", "")
        hour = datetime.now().astimezone().strftime("%H")

    short_hash = get_session_short_hash(session_id)

    return get_session_status_dir() / f"{date_compact}-{hour}-{short_hash}.json"


def get_session_directory(
    session_id: str, date: str | None = None, base_dir: Path | None = None
) -> Path:
    """Get session directory path (single source of truth).

    Returns: ~/writing/sessions/status/ (centralized flat directory)

    NOTE: This function now returns the centralized status directory.
    Session files are named YYYYMMDD-HH-sessionID.json directly in this directory.
    The base_dir parameter is preserved for test isolation only.

    Args:
        session_id: Session identifier from CLAUDE_SESSION_ID
        date: Date in YYYY-MM-DD or ISO 8601 format (defaults to now local time)
        base_dir: Override base directory (primarily for test isolation)

    Returns:
        Path to session directory (created if doesn't exist)

    Examples:
        >>> get_session_directory("abc123")
        PosixPath('/home/user/writing/sessions/status')
    """
    if base_dir is not None:
        # Test isolation mode - use old structure for compatibility
        if date is None:
            now = datetime.now().astimezone()
            date_compact = now.strftime("%Y%m%d")
            hour = now.strftime("%H")
        elif "T" in date:
            date_compact = date[:10].replace("-", "")
            hour = date[11:13]
        else:
            date_compact = date.replace("-", "")
            hour = datetime.now().astimezone().strftime("%H")
        project_folder = get_claude_project_folder()
        short_hash = get_session_short_hash(session_id)
        session_dir = base_dir / project_folder / f"{date_compact}-{hour}-{short_hash}"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    # Production mode - use centralized status directory
    return get_session_status_dir()
