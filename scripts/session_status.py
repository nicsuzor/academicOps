#!/usr/bin/env python3
"""Authoritative tool for checking session processing status.

Identifies:
- Sessions needing transcript generation
- Sessions needing mining (JSON summaries)
- Fully processed sessions

Supports both cron mode (path output) and report mode (human-readable).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add framework root to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.session_reader import (  # noqa: E402
    SessionInfo,
    find_sessions,
    get_session_state,
    SessionState,
)


def get_aca_data() -> Path:
    """Get ACA_DATA path with fail-fast."""
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        print("ERROR: ACA_DATA not set", file=sys.stderr)
        sys.exit(2)
    return Path(aca_data)


def format_report(results: dict[SessionState, list[SessionInfo]]) -> str:
    """Format a human-readable report of session states."""
    lines = ["Session Status Report", "=" * 60, ""]

    # Processed first (can be many, so keep brief)
    processed = results.get(SessionState.PROCESSED, [])
    lines.append(f"## Fully Processed ({len(processed)} sessions)")
    if processed:
        for s in processed[:10]:
            lines.append(f"  ✓ {s.session_id[:8]} | {s.project_display} ({s.source})")
        if len(processed) > 10:
            lines.append(f"  ... and {len(processed) - 10} more")
    lines.append("")

    # Pending Mining
    pending_mining = results.get(SessionState.PENDING_MINING, [])
    lines.append(f"## Pending Mining ({len(pending_mining)} sessions)")
    lines.append("Transcripts exist but JSON summaries are missing.")
    for s in pending_mining:
        lines.append(f"  ● {s.session_id[:8]} | {s.project_display} ({s.source})")
    lines.append("")

    # Pending Transcript
    pending_transcript = results.get(SessionState.PENDING_TRANSCRIPT, [])
    lines.append(f"## Pending Transcript ({len(pending_transcript)} sessions)")
    lines.append("Raw session files need transcript generation.")
    for s in pending_transcript:
        lines.append(f"  ○ {s.session_id[:8]} | {s.project_display} ({s.source})")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check session processing status")
    parser.add_argument(
        "--mode",
        choices=["report", "cron-transcript", "cron-mining"],
        default="report",
        help="Output mode: report (human), cron-transcript (paths needing transcript), cron-mining (paths needing mining)",
    )
    parser.add_argument(
        "--allowed-projects", help="Comma-separated project patterns to include"
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Max sessions to output in cron mode"
    )
    parser.add_argument(
        "--days", type=int, default=7, help="How many days back to look"
    )
    parser.add_argument(
        "--min-age", type=int, default=5, help="Min session age in minutes"
    )
    parser.add_argument(
        "--include-noise",
        action="store_true",
        help="Include hook logs, tmp sessions, and test dirs (excluded by default)",
    )

    args = parser.parse_args()
    aca_data = get_aca_data()

    # Define age window
    now = datetime.now(UTC)
    newest_allowed = now - timedelta(minutes=args.min_age)
    oldest_allowed = now - timedelta(days=args.days)

    allowed_patterns = (
        [p.strip().lower() for p in args.allowed_projects.split(",")]
        if args.allowed_projects
        else None
    )

    # Find all sessions in window
    all_sessions = find_sessions(since=oldest_allowed)

    # Noise patterns to exclude by default
    noise_patterns = [
        "-hooks.jsonl",  # Hook log files (not main sessions)
        "-tmp-claude-headless",  # Old cron headless sessions
        "-tmp-claude-test",  # Integration test sessions
        "-tmp-tmp",  # Pytest temp dirs
        "-tmp-task-viz-test",  # Task viz test dirs
    ]

    # Filter by age, project, and noise
    eligible = []
    for s in all_sessions:
        if not (oldest_allowed <= s.last_modified <= newest_allowed):
            continue

        if allowed_patterns:
            project_lower = s.project.lower()
            if not any(p in project_lower for p in allowed_patterns):
                continue

        # Exclude noise unless explicitly included
        if not args.include_noise:
            path_str = str(s.path)
            project_str = s.project
            if any(
                pattern in path_str or pattern in project_str
                for pattern in noise_patterns
            ):
                continue

        eligible.append(s)

    # Group by state
    results: dict[SessionState, list[SessionInfo]] = {
        SessionState.PENDING_TRANSCRIPT: [],
        SessionState.PENDING_MINING: [],
        SessionState.PROCESSED: [],
    }

    for s in eligible:
        state = get_session_state(s, aca_data)
        results[state].append(s)

    # Output based on mode
    if args.mode == "report":
        print(format_report(results))
        return 0

    elif args.mode == "cron-transcript":
        targets = results[SessionState.PENDING_TRANSCRIPT][: args.limit]
        if not targets:
            return 1  # Nothing to do
        for s in targets:
            print(str(s.path))
        return 0

    elif args.mode == "cron-mining":
        targets = results[SessionState.PENDING_MINING][: args.limit]
        if not targets:
            return 1  # Nothing to do
        for s in targets:
            print(str(s.path))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
