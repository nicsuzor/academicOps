"""Session path utilities - single source of truth for session file locations.

This module provides centralized path generation for session files to avoid
circular dependencies and ensure consistent path structure across all components.

Session files are stored in ~/writing/sessions/status/ as YYYYMMDD-HH-sessionID.json
where HH is the 24-hour local time when the session was created.
"""

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path


def get_claude_project_folder() -> str:
    """Get Claude Code project folder name from project directory.

    Uses CLAUDE_PROJECT_DIR env var if set (available during hook execution),
    otherwise falls back to cwd. This is critical for plugin-based hooks that
    run from the plugin cache directory rather than the project directory.

    Converts absolute path to sanitized folder name matching Claude Code's format:
    /home/user/.project -> -home-user-_project

    Claude Code replaces:
    - '/' with '-'
    - '.' with '_'

    Returns:
        Project folder name with leading dash and sanitized characters
    """
    # CLAUDE_PROJECT_DIR is set by Claude Code during hook execution
    # and contains the absolute path to the project root
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        project_path = Path(project_dir).resolve()
    else:
        # Fallback for non-hook contexts (e.g., direct script execution)
        project_path = Path.cwd().resolve()
    # Match Claude Code path sanitization: '/' -> '-', '.' -> '_'
    return "-" + str(project_path)[1:].replace("/", "-").replace(".", "_")


def get_session_short_hash(session_id: str) -> str:
    """Get 8-character identifier from session ID.

    Standardizes on the first 8 characters of the session ID (UUID prefix)
    to match Gemini CLI transcript naming. Falls back to SHA-256 hash for
    brevity if the session ID is short or non-standard.

    Args:
        session_id: Full session identifier

    Returns:
        8-character string
    """
    # 1. If it's a standard UUID or long enough, use the prefix (matches transcript)
    if len(session_id) >= 8:
        # Check if first 8 are valid hex or alphanumeric
        prefix = session_id[:8].lower()
        if all(c in "0123456789abcdefghijklmnopqrstuvwxyz" for c in prefix):
            return prefix

    # 2. Fallback to SHA-256 for short/complex IDs
    return hashlib.sha256(session_id.encode()).hexdigest()[:8]


def _is_gemini_session(session_id: str | None, input_data: dict | None) -> bool:
    """Detect if this is a Gemini CLI session.

    Detection methods:
    1. GEMINI_SESSION_ID env var is set (Gemini CLI always provides this)
    2. session_id starts with "gemini-"
    3. transcript_path contains "/.gemini/"
    4. AOPS_SESSION_STATE_DIR contains "/.gemini/" (polecat worker fallback)

    Args:
        session_id: Session ID (may have "gemini-" prefix)
        input_data: Input data dict (may contain transcript_path)

    Returns:
        True if this is a Gemini session
    """
    # Gemini CLI always sets GEMINI_SESSION_ID - most reliable detection
    if os.environ.get("GEMINI_SESSION_ID"):
        return True

    if session_id is not None and session_id.startswith("gemini-"):
        return True

    if input_data is not None:
        transcript_path = input_data.get("transcript_path")
        if transcript_path is not None and "/.gemini/" in transcript_path:
            return True

    # Polecat worker fallback: AOPS_SESSION_STATE_DIR is set by router at SessionStart
    # and persists across the session. Workers may not have transcript_path in input_data
    # but will have this env var pointing to ~/.gemini/tmp/<hash>/ for Gemini sessions.
    state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
    if state_dir and "/.gemini/" in state_dir:
        return True

    return False


def _get_gemini_status_dir(input_data: dict | None) -> Path | None:
    """Get Gemini status directory from transcript_path or AOPS_SESSION_STATE_DIR.

    Gemini transcript paths look like:
    ~/.gemini/tmp/<hash>/chats/session-<uuid>.json
    or
    ~/.gemini/tmp/<hash>/logs/session-<uuid>.jsonl

    Falls back to AOPS_SESSION_STATE_DIR when transcript_path is not available
    (e.g., polecat workers where input_data has no transcript_path).

    Returns the ~/.gemini/tmp/<hash>/ directory or None if not detectable.
    """
    if input_data is None:
        # Try AOPS_SESSION_STATE_DIR as last resort
        state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
        if state_dir and "/.gemini/" in state_dir:
            return Path(state_dir)
        return None

    transcript_path = input_data.get("transcript_path")
    if transcript_path is None:
        # Try AOPS_SESSION_STATE_DIR as fallback for workers without transcript_path
        state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
        if state_dir and "/.gemini/" in state_dir:
            return Path(state_dir)
        return None

    path = Path(transcript_path)

    # Walk up to find the hash directory (parent of chats/logs)
    for parent in path.parents:
        if parent.name in ("chats", "logs"):
            # Parent of chats/logs is the hash directory
            return parent.parent

    # Check if we are already in the hash directory
    if "/.gemini/tmp/" in str(path):
        # If path is ~/.gemini/tmp/<hash>, return it
        # Otherwise, if it's deeper, we might need more logic,
        # but usually Gemini passes transcript_path in chats/ or logs/
        parts = path.parts
        try:
            tmp_idx = parts.index("tmp")
            if len(parts) > tmp_idx + 2 and parts[tmp_idx - 1] == ".gemini":
                return Path(*parts[: tmp_idx + 2])
        except ValueError:
            pass

    return None


def get_gemini_logs_dir(input_data: dict | None) -> Path | None:
    """Get Gemini logs directory from transcript_path.

    Returns the logs/ folder within the Gemini state directory.
    """
    state_dir = _get_gemini_status_dir(input_data)
    if state_dir:
        logs_dir = state_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir
    return None


def get_hook_log_path(
    session_id: str, input_data: dict | None = None, date: str | None = None
) -> Path:
    """Get the path for the per-session hook log file.

    Logs to:
    - Claude: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
    - Gemini: ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-hooks.jsonl

    Args:
        session_id: Session ID from Claude Code or Gemini CLI
        input_data: Optional input data dict (may contain transcript_path for Gemini)
        date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns:
        Path to the hook log file
    """

    # if we successfully saved the session state path in env vars, we should use that to ensure consistency across all hooks
    if env_hook_log_path := os.environ.get("AOPS_HOOK_LOG_PATH"):
        return Path(env_hook_log_path)

    if date is None:
        from datetime import datetime

        date = datetime.now(UTC).strftime("%Y-%m-%d")

    short_hash = get_session_short_hash(session_id)
    date_compact = date.replace("-", "")  # YYYY-MM-DD -> YYYYMMDD

    # Determine log directory based on session type
    if _is_gemini_session(session_id, input_data):
        # Gemini: write to logs/ directory in state dir
        logs_dir = get_gemini_logs_dir(input_data)
        if logs_dir is None:
            raise ValueError("Gemini session detected but no logs directory configured")
        return logs_dir / f"{date_compact}-{short_hash}-hooks.jsonl"
    else:
        # Claude: ~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl
        project_folder = get_claude_project_folder()
        claude_projects_dir = Path.home() / ".claude" / "projects" / project_folder
        claude_projects_dir.mkdir(parents=True, exist_ok=True)
        return claude_projects_dir / f"{date_compact}-{short_hash}-hooks.jsonl"


def get_session_status_dir(session_id: str | None = None, input_data: dict | None = None) -> Path:
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

        # Fallback: use hash-based path from GEMINI_PROJECT_DIR (provided by Gemini CLI)
        project_root = (
            os.environ.get("GEMINI_PROJECT_DIR")
            or os.environ.get("CLAUDE_PROJECT_DIR")  # Gemini also provides this alias
            or str(Path.cwd().resolve())
        )
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


def get_session_file_path(
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

    return (
        get_session_status_dir(session_id, input_data) / f"{date_compact}-{hour}-{short_hash}.json"
    )


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


GATE_NAMES = ("hydration", "custodiet", "critic")


def get_gate_file_path(
    gate: str,
    session_id: str,
    input_data: dict | None = None,
    date: str | None = None,
) -> Path:
    """Get the path for a gate context file.

    Writes to the same directory as hook log files:
    - Claude: ~/.claude/projects/<project>/<date>-<shorthash>-<gate>.md
    - Gemini: ~/.gemini/tmp/<hash>/logs/<date>-<shorthash>-<gate>.md

    Checks AOPS_GATE_FILE_<GATE> env var first for session-stable path.

    Args:
        gate: Gate name (hydration, custodiet, critic, qa)
        session_id: Session ID from Claude Code or Gemini CLI
        input_data: Optional input data dict for Gemini detection
        date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns:
        Path to the gate context file
    """
    env_var = f"AOPS_GATE_FILE_{gate.upper()}"
    if env_path := os.environ.get(env_var):
        return Path(env_path)

    if date is None:
        date = datetime.now(UTC).strftime("%Y-%m-%d")

    short_hash = get_session_short_hash(session_id)
    date_compact = date.replace("-", "")

    if _is_gemini_session(session_id, input_data):
        logs_dir = get_gemini_logs_dir(input_data)
        if logs_dir is None:
            raise ValueError("Gemini session detected but no logs directory configured")
        return logs_dir / f"{date_compact}-{short_hash}-{gate}.md"
    else:
        project_folder = get_claude_project_folder()
        claude_projects_dir = Path.home() / ".claude" / "projects" / project_folder
        claude_projects_dir.mkdir(parents=True, exist_ok=True)
        return claude_projects_dir / f"{date_compact}-{short_hash}-{gate}.md"


def get_all_gate_file_paths(
    session_id: str,
    input_data: dict | None = None,
    date: str | None = None,
) -> dict[str, Path]:
    """Get paths for all gate context files.

    Returns:
        Dict mapping gate name to file path
    """
    return {gate: get_gate_file_path(gate, session_id, input_data, date) for gate in GATE_NAMES}


def get_pid_session_map_path() -> Path:
    """Get path for PID -> SessionID mapping file.

    Used by router to bootstrap session ID from process ID when not provided.
    Stores simple JSON: {"session_id": "..."}
    """
    aops_sessions = Path(os.getenv("AOPS_SESSIONS", "/tmp"))
    if not aops_sessions.exists():
        try:
            aops_sessions.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Fallback to /tmp

    return aops_sessions / f"session-{os.getppid()}.json"
