#!/usr/bin/env python3
"""Check for unprocessed Claude Code sessions.

Exit codes:
  0 - Sessions need processing (outputs session paths to stdout)
  1 - Nothing to do (all sessions processed or none in age window)
  2 - Configuration error (ACA_DATA missing or invalid arguments)

Criteria:
- Session JSONL must be 5 min to 7 days old (based on mtime, configurable via --min-age)
- Unprocessed means ANY of:
  a) JSONL exists but no abridged transcript
  b) Transcript exists but no mining JSON
  c) Session JSONL is newer than transcript (session was updated)

Usage:
  uv run python scripts/check_unprocessed_sessions.py
  uv run python scripts/check_unprocessed_sessions.py --allowed-projects academicOps
  uv run python scripts/check_unprocessed_sessions.py --limit 10
  # If exit 0, outputs session paths (one per line, max 20 by default) to stdout
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.session_reader import SessionInfo, find_sessions  # noqa: E402


def get_env_paths() -> Path:
    """Get required environment paths with fail-fast."""
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        print("ERROR: ACA_DATA not set", file=sys.stderr)
        sys.exit(2)

    aca_data_path = Path(aca_data)
    if not aca_data_path.exists():
        print(f"ERROR: ACA_DATA path does not exist: {aca_data_path}", file=sys.stderr)
        sys.exit(2)

    return aca_data_path


def check_session_processed(session: SessionInfo, aca_data: Path) -> bool:
    """Check if session has been fully processed.

    Returns True if processed (has both transcript AND mining JSON, and both are up-to-date).
    Returns False if:
      - Missing transcript or mining JSON
      - Session JSONL is newer than transcript (session was updated, needs re-processing)
    """
    session_id = session.session_id

    # Check for transcript
    # Pattern: $ACA_DATA/sessions/claude/YYYYMMDD-{project}-{session_id_prefix}-abridged.md
    transcript_dir = aca_data / "sessions" / "claude"
    transcript_path = None
    if transcript_dir.exists():
        # Use first 8 chars of session ID for matching (standard prefix length)
        session_prefix = session_id[:8] if len(session_id) >= 8 else session_id
        # Glob for any matching transcript
        pattern = str(transcript_dir / f"*-*-{session_prefix}*-abridged.md")
        matches = glob.glob(pattern)
        if matches:
            transcript_path = Path(matches[0])

    # Check for mining JSON
    # Pattern: $ACA_DATA/dashboard/sessions/{session_id}.json
    # Note: session-insights skill often uses 8-char prefix for filenames
    dashboard_sessions = aca_data / "dashboard" / "sessions"
    mining_json = dashboard_sessions / f"{session_id}.json"
    has_mining = mining_json.exists()

    if not has_mining and len(session_id) > 8:
        # Check for truncated ID (standard 8-char prefix)
        # Handle UUIDs and other long IDs
        short_id = session_id[:8]
        has_mining = (dashboard_sessions / f"{short_id}.json").exists()

    # Missing either = needs processing
    if not transcript_path or not has_mining:
        return False

    # Check if session was updated after transcript was generated
    # If JSONL is newer than transcript, needs re-processing
    session_mtime = session.path.stat().st_mtime
    transcript_mtime = transcript_path.stat().st_mtime
    if session_mtime > transcript_mtime:
        return False  # Session updated, needs re-processing

    # Fully processed and up-to-date
    return True


def matches_project_pattern(session: SessionInfo, patterns: list[str]) -> bool:
    """Check if session's project matches any of the allowed patterns.

    Args:
        session: Session to check
        patterns: List of patterns to match (case-insensitive partial match)

    Returns:
        True if session project matches any pattern
    """
    project_name = session.project.lower()
    return any(pattern.lower() in project_name for pattern in patterns)


def matches_exclude_pattern(session: SessionInfo, patterns: list[str]) -> bool:
    """Check if session path contains any excluded pattern.

    Args:
        session: Session to check
        patterns: List of path patterns to exclude (e.g., ["/tmp", "tmp"])

    Returns:
        True if session should be excluded
    """
    session_path = str(session.path).lower()
    project_name = session.project.lower()

    for pattern in patterns:
        pattern_lower = pattern.lower()
        # Check direct match in path
        if pattern_lower in session_path:
            return True
        # Check project name - patterns like "/tmp" should match "-tmp" project dirs
        # Convert /tmp -> tmp for matching against -tmp-* project names
        normalized_pattern = pattern_lower.lstrip("/")
        if normalized_pattern and normalized_pattern in project_name:
            return True

    return False


def main() -> None:
    """Check for unprocessed sessions and exit appropriately."""
    parser = argparse.ArgumentParser(
        description="Check for unprocessed Claude Code sessions"
    )
    parser.add_argument(
        "--allowed-projects",
        help="Comma-separated project patterns to process (partial match, case-insensitive)",
    )
    parser.add_argument(
        "--exclude-patterns",
        default="/tmp",
        help="Comma-separated path patterns to exclude (default: /tmp)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of sessions to output (default: 20)",
    )
    parser.add_argument(
        "--min-age",
        type=int,
        default=5,
        help="Minimum session age in minutes before processing (default: 5)",
    )
    args = parser.parse_args()

    # Parse patterns
    allowed_patterns = (
        [p.strip() for p in args.allowed_projects.split(",") if p.strip()]
        if args.allowed_projects
        else None
    )
    exclude_patterns = (
        [p.strip() for p in args.exclude_patterns.split(",") if p.strip()]
        if args.exclude_patterns
        else []
    )

    aca_data = get_env_paths()

    # Define age window
    # oldest_allowed = 7 days ago (don't process ancient sessions)
    # newest_allowed = min_age ago (let sessions finish before processing)
    now = datetime.now(UTC)
    newest_allowed = now - timedelta(minutes=args.min_age)
    oldest_allowed = now - timedelta(days=7)

    # Find sessions modified after oldest_allowed
    all_sessions = find_sessions(since=oldest_allowed)

    # Filter to sessions within age window (also check they're old enough)
    eligible_sessions = [
        s for s in all_sessions if oldest_allowed <= s.last_modified <= newest_allowed
    ]

    # Filter by allowed projects if specified
    if allowed_patterns:
        eligible_sessions = [
            s for s in eligible_sessions if matches_project_pattern(s, allowed_patterns)
        ]

    # Filter out excluded patterns (always applied)
    if exclude_patterns:
        eligible_sessions = [
            s
            for s in eligible_sessions
            if not matches_exclude_pattern(s, exclude_patterns)
        ]

    if not eligible_sessions:
        # No sessions in age window (or none matching filters)
        sys.exit(1)

    # Check which sessions need processing
    unprocessed = [
        s for s in eligible_sessions if not check_session_processed(s, aca_data)
    ]

    if unprocessed:
        # Output session paths (one per line) for use by caller
        # Limit to args.limit sessions (newest first, already sorted by find_sessions)
        for s in unprocessed[: args.limit]:
            print(str(s.path))
        sys.exit(0)  # Work needed
    else:
        # All eligible sessions are processed
        sys.exit(1)  # Nothing to do


if __name__ == "__main__":
    main()
