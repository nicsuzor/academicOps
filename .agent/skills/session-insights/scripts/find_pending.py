#!/usr/bin/env python3
"""Find sessions pending insights generation.

Scans transcript directory and returns sessions that don't have a corresponding insights file.

Usage:
    find_pending.py [--limit N]

Output:
    pipe-separated lines: TRANSCRIPT_PATH|SESSION_ID|DATE
"""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Find pending sessions")
    parser.add_argument("--limit", type=int, default=5, help="Max number of sessions to return")
    args = parser.parse_args()

    sessions_dir = Path(os.environ.get("AOPS_SESSIONS", str(Path.home() / ".aops" / "sessions")))

    transcripts_dir = sessions_dir / "transcripts"
    insights_dir = sessions_dir / "summaries"

    if not transcripts_dir.exists():
        print(
            f"Warning: Transcript directory not found: {transcripts_dir}",
            file=sys.stderr,
        )
        return

    count = 0

    # Iterate over all .md files in transcripts directory
    # Sort by mtime descending (most recent first) to prioritize recent sessions?
    # Or scanning all? The bash loop had a limit.

    transcripts = sorted(
        transcripts_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    for transcript in transcripts:
        if count >= args.limit:
            break

        # Format: YYYYMMDD-{project}-{session_id}-{suffix}.md
        parts = transcript.stem.split("-")

        # We need at least date and session_id
        if len(parts) >= 3:
            # Check date format roughly
            if len(parts[0]) == 8 and parts[0].isdigit():
                date_str = parts[0]
                date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

                # Session ID is usually the 3rd or later part, but let's be more robust
                # The inline script assumed parts[2].
                # Standard format: YYYYMMDD-project-session_id
                session_id = parts[2]

                # Check if insights exist (v3.4.0: YYYYMMDD format)
                insights_file = insights_dir / f"{date_str}-{session_id}.json"

                if not insights_file.exists():
                    print(f"{transcript}|{session_id}|{date_formatted}")
                    count += 1

    if count == 0:
        # No output means no pending sessions found
        pass


if __name__ == "__main__":
    main()
