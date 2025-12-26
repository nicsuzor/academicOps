#!/usr/bin/env python3
"""Find Claude Code sessions needing transcript generation.

Usage:
    uv run python skills/session-insights/scripts/find_sessions.py [--date YYYYMMDD]

Output:
    Lines of: session_path|session_id_prefix|shortproject
    Example: /path/to/session.jsonl|abc12345|writing
"""

import argparse
import glob
import os
import sys
from datetime import datetime, timezone

# Add parent to path for lib imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from lib.session_reader import find_sessions


def main():
    parser = argparse.ArgumentParser(description="Find sessions needing transcripts")
    parser.add_argument("--date", help="Target date YYYYMMDD (default: today)")
    parser.add_argument("--transcript-dir", default=None, help="Transcript output directory")
    args = parser.parse_args()

    # Parse target date
    if args.date:
        target_date = datetime.strptime(args.date, "%Y%m%d").date()
    else:
        target_date = datetime.now(timezone.utc).date()

    # Get transcript directory from environment or default
    aca_data = os.environ.get("ACA_DATA", os.path.expanduser("~/writing/data"))
    transcript_dir = args.transcript_dir or os.path.join(aca_data, "sessions/claude")
    os.makedirs(transcript_dir, exist_ok=True)

    # Find sessions matching criteria
    sessions = [
        s for s in find_sessions()
        if s.last_modified.date() == target_date
        and "claude-test" not in s.project
        and os.path.getsize(s.path) > 5000
    ]

    for s in sessions:
        session_id_prefix = s.session_id[:8]
        existing = glob.glob(f"{transcript_dir}/*{session_id_prefix}*-abridged.md")

        # Check if transcript needs (re)generation
        needs_gen = not existing or s.last_modified.timestamp() > os.path.getmtime(existing[0])

        if needs_gen:
            shortproject = s.project.split("-")[-1]
            print(f"{s.path}|{session_id_prefix}|{shortproject}")


if __name__ == "__main__":
    main()
