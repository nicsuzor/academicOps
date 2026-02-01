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


def _is_gemini_session(session_id: str | None, input_data: dict | None) -> bool:
    """Detect if this is a Gemini CLI session.

    Detection methods:
    1. session_id starts with "gemini-"
    2. transcript_path contains "/.gemini/"

    Args:
        session_id: Session ID (may have "gemini-" prefix)
        input_data: Input data dict (may contain transcript_path)

    Returns:
        True if this is a Gemini session
    """
    if session_id is not None and session_id.startswith("gemini-"):
        return True

    if input_data is not None:
        transcript_path = input_data.get("transcript_path")
        if transcript_path is not None and "/.gemini/" in transcript_path:
            return True

    return False


def _get_gemini_status_dir(input_data: dict | None) -> Path | None:
    """Get Gemini status directory from transcript_path.

    Gemini transcript paths look like:
    ~/.gemini/tmp/<hash>/chats/session-<uuid>.json

    Returns the ~/.gemini/tmp/<hash>/ directory or None if not detectable.
    """
    if input_data is None:
        return None

    transcript_path = input_data.get("transcript_path")
    if transcript_path is None:
        return None
    if "/.gemini/" not in transcript_path:
        return None

    # Extract the base directory (before /chats/ or /logs/)
    path = Path(transcript_path)

    # Walk up to find the hash directory (parent of chats/logs)
    for parent in path.parents:
        if parent.name in ("chats", "logs"):
            # Parent of chats/logs is the hash directory
            return parent.parent

    return None


def get_session_status_dir(
    session_id: str | None = None, input_data: dict | None = None
) -> Path:
    """Get session status directory from AOPS_SESSION_STATE_DIR or auto-detect.

    This env var is set by the router at SessionStart:
    - Gemini: ~/.gemini/tmp/<hash>/ (from transcript_path)
    - Claude: ~/.claude/projects/<encoded-cwd>/

    Falls back to auto-detection based on:
    1. session_id starting with "gemini-" -> Gemini path
    2. transcript_path containing "/.gemini/" -> Gemini path (extracts from path)
    3. Otherwise (UUID format) -> Claude path derived from cwd

    Args:
        session_id: Optional session ID for client detection.
        input_data: Optional input data dict containing transcript_path for Gemini detection.

    Returns:
        Path to session status directory (created if doesn't exist)
    """
    # 1. Prefer explicit env var from router (must be non-empty)
    state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
    if state_dir:
        status_dir = Path(state_dir)
        status_dir.mkdir(parents=True, exist_ok=True)
        return status_dir

    # 2. Auto-detect Gemini from session_id or transcript_path
    if _is_gemini_session(session_id, input_data):
        # Try to extract from transcript_path first
        gemini_dir = _get_gemini_status_dir(input_data)
        if gemini_dir is not None:
            gemini_dir.mkdir(parents=True, exist_ok=True)
            return gemini_dir

        # Fallback: use hash-based path from cwd
        project_root = str(Path.cwd().resolve())
        project_hash = hashlib.sha256(project_root.encode()).hexdigest()
        gemini_tmp = Path.home() / ".gemini" / "tmp" / project_hash
        gemini_tmp.mkdir(parents=True, exist_ok=True)
        return gemini_tmp

    # 3. Claude Code session (or unknown) - derive path from cwd
    # Same logic as session_env_setup.sh: ~/.claude/projects/-<cwd-with-dashes>/
    project_folder = get_claude_project_folder()
    status_dir = Path.home() / ".claude" / "projects" / project_folder
    status_dir.mkdir(parents=True, exist_ok=True)
    return status_dir


def get_session_file_path_direct(
    session_id: str, date: str | None = None, input_data: dict | None = None
) -> Path:
    """Get session state file path (flat structure).

    Returns: ~/writing/sessions/status/YYYYMMDD-HH-sessionID.json

    Args:
        session_id: Session identifier from CLAUDE_SESSION_ID
        date: Date in YYYY-MM-DD format or ISO 8601 with timezone (defaults to now local time).
              The hour component is extracted from ISO 8601 dates (e.g., 2026-01-24T17:30:00+10:00).
              For simple YYYY-MM-DD dates, the current hour (local time) is used.
        input_data: Optional input data dict containing transcript_path for Gemini detection.

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

    return get_session_status_dir(session_id, input_data) / f"{date_compact}-{hour}-{short_hash}.json"


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
    return get_session_status_dir(session_id)
