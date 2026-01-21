"""Session path utilities - single source of truth for session file locations.

This module provides centralized path generation for session files to avoid
circular dependencies and ensure consistent path structure across all components.

Session files are stored in ~/writing/session/status/ as YYYYMMDD-sessionID.json
"""

import hashlib
import os
from datetime import datetime, timezone
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
    """Get centralized session status directory.

    Returns ~/writing/session/status/ by default, or CLAUDE_SESSION_STATE_DIR if set.

    Returns:
        Path to session status directory (created if doesn't exist)
    """
    status_dir = Path(
        os.environ.get(
            "CLAUDE_SESSION_STATE_DIR", str(Path.home() / "writing" / "session" / "status")
        )
    )
    status_dir.mkdir(parents=True, exist_ok=True)
    return status_dir


def get_session_file_path_direct(session_id: str, date: str | None = None) -> Path:
    """Get session state file path (flat structure).

    Returns: ~/writing/session/status/YYYYMMDD-sessionID.json

    Args:
        session_id: Session identifier from CLAUDE_SESSION_ID
        date: Date in YYYY-MM-DD format (defaults to today UTC)

    Returns:
        Path to session state file
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    short_hash = get_session_short_hash(session_id)
    date_compact = date.replace("-", "")  # YYYY-MM-DD -> YYYYMMDD

    return get_session_status_dir() / f"{date_compact}-{short_hash}.json"


def get_session_directory(
    session_id: str, date: str | None = None, base_dir: Path | None = None
) -> Path:
    """Get session directory path (single source of truth).

    Returns: ~/writing/session/status/ (centralized flat directory)

    NOTE: This function now returns the centralized status directory.
    Session files are named YYYYMMDD-sessionID.json directly in this directory.
    The base_dir parameter is preserved for test isolation only.

    Args:
        session_id: Session identifier from CLAUDE_SESSION_ID
        date: Date in YYYY-MM-DD format (defaults to today UTC)
        base_dir: Override base directory (primarily for test isolation)

    Returns:
        Path to session directory (created if doesn't exist)

    Examples:
        >>> get_session_directory("abc123")
        PosixPath('/home/user/writing/session/status')
    """
    if base_dir is not None:
        # Test isolation mode - use old structure for compatibility
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        project_folder = get_claude_project_folder()
        short_hash = get_session_short_hash(session_id)
        date_compact = date.replace("-", "")
        session_dir = base_dir / project_folder / f"{date_compact}-{short_hash}"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    # Production mode - use centralized status directory
    return get_session_status_dir()
