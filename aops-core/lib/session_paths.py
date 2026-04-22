"""Session path utilities - single source of truth for session file locations.

This module provides centralized path generation for session files to avoid
circular dependencies and ensure consistent path structure across all components.

Session files are stored in ~/writing/sessions/status/ as YYYYMMDD-HH-sessionID.json
where HH is the 24-hour local time when the session was created.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from lib import session_naming


def _parse_date_arg(date: str | None) -> datetime | None:
    """Parse a date/ISO-8601 string into a datetime, or None to let callers default to now."""
    if date is None:
        return None
    dt = datetime.fromisoformat(date)
    # Only attach local timezone for naive datetimes; preserve explicit tz as-is
    return dt if dt.tzinfo is not None else dt.astimezone()


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
    return session_naming.get_session_short_hash(session_id)


def _is_gemini_session(session_id: str | None, transcript_path: str | None = None) -> bool:
    """Detect if this is a Gemini CLI session.

    Detection methods:
    1. GEMINI_SESSION_ID env var is set (Gemini CLI always provides this)
    2. session_id starts with "gemini-"
    3. transcript_path contains "/.gemini/"
    4. AOPS_SESSION_STATE_DIR contains "/.gemini/" (polecat worker fallback)

    Args:
        session_id: Session ID (may have "gemini-" prefix)
        transcript_path: Optional transcript path for Gemini detection

    Returns:
        True if this is a Gemini session
    """
    # Gemini CLI always sets GEMINI_SESSION_ID - most reliable detection
    if os.environ.get("GEMINI_SESSION_ID"):
        return True

    if session_id is not None and session_id.startswith("gemini-"):
        return True

    if transcript_path is not None and "/.gemini/" in transcript_path:
        return True

    # Polecat worker fallback: AOPS_SESSION_STATE_DIR is set by router at SessionStart
    # and persists across the session. Workers may not have transcript_path in transcript_path
    # but will have this env var pointing to ~/.gemini/tmp/<hash>/ for Gemini sessions.
    state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
    if state_dir and "/.gemini/" in state_dir:
        return True

    return False


def _get_gemini_status_dir(transcript_path: str | None = None) -> Path | None:
    """Get Gemini status directory from transcript_path or AOPS_SESSION_STATE_DIR.

    Gemini transcript paths look like:
    ~/.gemini/tmp/<hash>/chats/session-<uuid>.json
    or
    ~/.gemini/tmp/<hash>/logs/session-<uuid>.jsonl

    Returns the ~/.gemini/tmp/<hash>/ directory or None if not detectable.
    No fallback chains — returns None if neither signal is available.
    """
    # 1. Extract from transcript_path (parent of chats/ or logs/)
    if transcript_path:
        for parent in Path(transcript_path).parents:
            if parent.name in ("chats", "logs"):
                return parent.parent

    # 2. AOPS_SESSION_STATE_DIR (set at SessionStart, persisted for session)
    state_dir = os.environ.get("AOPS_SESSION_STATE_DIR")
    if state_dir and "/.gemini/" in state_dir:
        return Path(state_dir)

    return None


def get_gemini_logs_dir(transcript_path: str | None = None) -> Path | None:
    """Get Gemini logs directory from transcript_path.

    Returns the logs/ folder within the Gemini state directory.
    """
    state_dir = _get_gemini_status_dir(transcript_path)
    if state_dir:
        logs_dir = state_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir
    return None


def get_hook_log_path(
    session_id: str, transcript_path: str | None = None, date: str | None = None
) -> Path:
    """Get the path for the per-session hook log file.

    Logs to:
    - Claude: ~/.claude/projects/<project>/YYYYMMDD-HH-<shorthash>-hooks.jsonl
    - Gemini: ~/.gemini/tmp/<hash>/logs/YYYYMMDD-HH-<shorthash>-hooks.jsonl

    Args:
        session_id: Session ID from Claude Code or Gemini CLI
        transcript_path: Optional transcript path for Gemini detection
        date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns:
        Path to the hook log file
    """

    # if we successfully saved the session state path in env vars, we should use that to ensure consistency across all hooks
    if env_hook_log_path := os.environ.get("AOPS_HOOK_LOG_PATH"):
        return Path(env_hook_log_path)

    filename = session_naming.generate_session_filename(
        session_id,
        timestamp=_parse_date_arg(date),
        artifact_type="hooks",
        crew_name=session_naming.resolve_crew_name(),
    )

    # Unify hook logging: Always prefer centralized AOPS_SESSIONS if reachable
    aops_sessions = os.environ.get("AOPS_SESSIONS")
    if aops_sessions:
        logs_dir = Path(aops_sessions).resolve() / "hooks"
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            return logs_dir / filename
        except (PermissionError, OSError):
            # AOPS_SESSIONS points to an unreachable host path (common in crew
            # containers without a volume mount). Fall through to local path.
            pass

    # Determine log directory based on session type
    if _is_gemini_session(session_id, transcript_path):
        # Gemini: write to logs/ directory in state dir
        logs_dir = get_gemini_logs_dir(transcript_path)
        if logs_dir is None:
            raise ValueError("Gemini session detected but no logs directory configured")
        return logs_dir / filename
    else:
        # Claude: ~/.claude/projects/<project>/YYYYMMDD-HH-<shorthash>-hooks.jsonl
        project_folder = get_claude_project_folder()
        claude_projects_dir = Path.home() / ".claude" / "projects" / project_folder
        try:
            claude_projects_dir.mkdir(parents=True, exist_ok=True)
            return claude_projects_dir / filename
        except (PermissionError, OSError) as e:
            print(
                f"WARNING: hook log dir {claude_projects_dir} inaccessible ({e}); falling back to /tmp/aops-hooks",
                file=sys.stderr,
            )
            fallback_dir = Path("/tmp") / f"aops-hooks-{os.getuid()}" / project_folder
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir / filename


def get_session_status_dir(
    session_id: str | None = None, transcript_path: str | None = None
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
        transcript_path: Optional transcript path for Gemini detection.

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
    if _is_gemini_session(session_id, transcript_path):
        gemini_dir = _get_gemini_status_dir(transcript_path)
        if gemini_dir is not None:
            gemini_dir.mkdir(parents=True, exist_ok=True)
            return gemini_dir

        raise ValueError(
            "Gemini session detected but cannot determine status directory. "
            "Set AOPS_SESSION_STATE_DIR or ensure transcript_path is provided."
        )

    # 3. Claude Code session (or unknown) - derive path from cwd
    # Same logic as session_env_setup.sh: ~/.claude/projects/-<cwd-with-dashes>/
    project_folder = get_claude_project_folder()
    status_dir = Path.home() / ".claude" / "projects" / project_folder
    try:
        status_dir.mkdir(parents=True, exist_ok=True)
        return status_dir
    except (PermissionError, OSError) as e:
        print(
            f"WARNING: session status dir {status_dir} inaccessible ({e}); falling back to /tmp/aops-state",
            file=sys.stderr,
        )
        fallback_dir = Path("/tmp") / f"aops-state-{os.getuid()}" / project_folder
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


def get_session_file_path(
    session_id: str, date: str | None = None, transcript_path: str | None = None
) -> Path:
    """Get session state file path (flat structure).

    Returns: ~/writing/sessions/status/YYYYMMDD-HH-sessionID.json

    Args:
        session_id: Session identifier from CLAUDE_SESSION_ID
        date: Date in YYYY-MM-DD format or ISO 8601 with timezone (defaults to now local time).
              The hour component is extracted from ISO 8601 dates (e.g., 2026-01-24T17:30:00+10:00).
              For simple YYYY-MM-DD dates, the current hour (local time) is used.
        transcript_path: Optional transcript path for Gemini detection.

    Returns:
        Path to session state file
    """
    filename = session_naming.generate_session_filename(
        session_id,
        timestamp=_parse_date_arg(date),
        artifact_type="insights",
        crew_name=session_naming.resolve_crew_name(),
    )
    return get_session_status_dir(session_id, transcript_path) / filename


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
        # We use get_session_filename without suffix to get the folder name
        folder_name = session_naming.get_session_filename(session_id, date=date, suffix="")
        project_folder = get_claude_project_folder()
        session_dir = base_dir / project_folder / folder_name
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    # Production mode - use centralized status directory
    return get_session_status_dir(session_id)


def find_recent_hooks_logs(n: int) -> list[Path]:
    """Find the N most recent hooks log files across all Claude projects.

    Skips test fixtures (paths containing 'pytest' or '/tmp-tmp').
    Returns paths sorted by modification time, most recent first.

    Args:
        n: Maximum number of log paths to return

    Returns:
        List of up to n Path objects to hooks JSONL files
    """
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.exists():
        return []

    hooks_logs: list[tuple[float, Path]] = []
    for log_path in claude_projects.rglob("*-hooks.jsonl"):
        if "pytest" in str(log_path) or "/tmp-tmp" in str(log_path):
            continue
        try:
            mtime = log_path.stat().st_mtime
            hooks_logs.append((mtime, log_path))
        except OSError:
            continue

    hooks_logs.sort(key=lambda x: x[0], reverse=True)
    return [path for _, path in hooks_logs[:n]]


GATE_NAMES = ("enforcer",)


def get_gate_file_path(
    gate: str,
    session_id: str,
    transcript_path: str | None = None,
    date: str | None = None,
) -> Path:
    """Get the path for a gate context file.

    Writes to the same directory as hook log files:
    - Claude: ~/.claude/projects/<project>/YYYYMMDD-HH-<shorthash>-<gate>.md
    - Gemini: ~/.gemini/tmp/<hash>/logs/YYYYMMDD-HH-<shorthash>-<gate>.md

    Checks AOPS_GATE_FILE_<GATE> env var first for session-stable path.

    Args:
        gate: Gate name (enforcer, qa, handover)
        session_id: Session ID from Claude Code or Gemini CLI
        transcript_path: Optional transcript path for Gemini detection
        date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns:
        Path to the gate context file
    """
    env_var = f"AOPS_GATE_FILE_{gate.upper()}"
    if env_path := os.environ.get(env_var):
        return Path(env_path)

    # Gates reuse the shared base name then append {-gate}.md
    base = session_naming.generate_base_name(
        session_id,
        timestamp=_parse_date_arg(date),
        crew_name=session_naming.resolve_crew_name(),
    )
    filename = f"{base}-{gate}.md"

    # Unify gate logging: Always prefer centralized AOPS_SESSIONS if reachable
    aops_sessions = os.environ.get("AOPS_SESSIONS")
    if aops_sessions:
        logs_dir = Path(aops_sessions).resolve() / "hooks"
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            return logs_dir / filename
        except (PermissionError, OSError):
            # AOPS_SESSIONS points to an unreachable host path (common in crew
            # containers without a volume mount). Fall through to local path.
            pass

    if _is_gemini_session(session_id, transcript_path):
        logs_dir = get_gemini_logs_dir(transcript_path)
        if logs_dir is None:
            raise ValueError("Gemini session detected but no logs directory configured")
        return logs_dir / filename
    else:
        project_folder = get_claude_project_folder()
        claude_projects_dir = Path.home() / ".claude" / "projects" / project_folder
        try:
            claude_projects_dir.mkdir(parents=True, exist_ok=True)
            return claude_projects_dir / filename
        except (PermissionError, OSError) as e:
            print(
                f"WARNING: gate file dir {claude_projects_dir} inaccessible ({e}); falling back to /tmp/aops-gates",
                file=sys.stderr,
            )
            fallback_dir = Path("/tmp") / f"aops-gates-{os.getuid()}" / project_folder
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir / filename


def get_all_gate_file_paths(
    session_id: str,
    transcript_path: str | None = None,
    date: str | None = None,
) -> dict[str, Path]:
    """Get paths for all gate context files.

    Returns:
        Dict mapping gate name to file path
    """
    return {
        gate: get_gate_file_path(gate, session_id, transcript_path, date) for gate in GATE_NAMES
    }


def get_pid_session_map_path() -> Path:
    """Get path for PID -> SessionID mapping file.

    Used by router to bootstrap session ID from process ID when not provided.
    Stores simple JSON: {"session_id": "..."}
    """
    # PID session maps are ephemeral runtime files, always use /tmp
    return Path("/tmp") / f"session-{os.getppid()}.json"
