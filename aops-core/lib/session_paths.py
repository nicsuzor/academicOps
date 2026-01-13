"""Session path utilities - single source of truth for session file locations.

This module provides centralized path generation for session files to avoid
circular dependencies and ensure consistent path structure across all components.
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


def get_session_directory(
    session_id: str, date: str | None = None, base_dir: Path | None = None
) -> Path:
    """Get session directory path (single source of truth).

    Returns: ~/.claude/projects/<project>/{YYYYMMDD}-{hash}/

    Directory structure organizes sessions by date and hash for easy
    chronological navigation while ensuring uniqueness per session.

    Args:
        session_id: Session identifier from CLAUDE_SESSION_ID
        date: Date in YYYY-MM-DD format (defaults to today UTC)
        base_dir: Override base directory (primarily for test isolation)

    Returns:
        Path to session directory (created if doesn't exist)

    Examples:
        >>> get_session_directory("abc123")
        PosixPath('/home/user/.claude/projects/-home-user-myproject/20260113-26912019')

        >>> get_session_directory("abc123", "2026-01-13", Path("/tmp/test"))
        PosixPath('/tmp/test/-home-user-myproject/20260113-26912019')
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Default to ~/.claude/projects/ unless override set
    if base_dir is None:
        base_dir = Path(
            os.environ.get(
                "CLAUDE_SESSION_STATE_DIR", str(Path.home() / ".claude" / "projects")
            )
        )

    # Build: <base>/<project>/{YYYYMMDD}-{hash}/
    project_folder = get_claude_project_folder()
    short_hash = get_session_short_hash(session_id)
    date_compact = date.replace("-", "")  # YYYY-MM-DD -> YYYYMMDD

    session_dir = base_dir / project_folder / f"{date_compact}-{short_hash}"
    session_dir.mkdir(parents=True, exist_ok=True)

    return session_dir
