#!/usr/bin/env python3
"""Find sessions pending insights generation.

Scans transcript directory and returns sessions that don't have a corresponding insights file.

Usage:
    find_pending.py [--limit N]

Output:
    pipe-separated lines: TRANSCRIPT_PATH|SESSION_ID|DATE

Note:
    Uses lib.paths.get_data_root() for canonical path resolution.
"""

import argparse
import sys
from pathlib import Path

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.paths import get_summaries_dir, get_transcripts_dir


def main():
    parser = argparse.ArgumentParser(description="Find pending sessions")
    parser.add_argument("--limit", type=int, default=5, help="Max number of sessions to return")
    args = parser.parse_args()

    try:
        transcripts_dir = get_transcripts_dir()
        insights_dir = get_summaries_dir()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not transcripts_dir.exists():
        print(
            f"Warning: Transcript directory not found: {transcripts_dir}",
            file=sys.stderr,
        )
        return

    # Iterate over all .md files in transcripts directory
    # Sort by mtime descending (most recent first) to prioritize recent sessions.
    transcripts = sorted(
        transcripts_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    # Deduplicate by session_id: prefer full transcripts over abridged ones.
    # A session with both *-full.md and *-abridged.md should only appear once.
    seen_session_ids: dict[str, Path] = {}

    for transcript in transcripts:
        # Format: YYYYMMDD-{project}-{session_id}-{suffix}.md
        # or v3.7.0+: YYYYMMDD-HH-{project}-{session_id}-{suffix}.md
        parts = transcript.stem.split("-")

        # We need at least date and session_id
        if len(parts) < 3:
            continue
        if len(parts[0]) != 8 or not parts[0].isdigit():
            continue

        date_str = parts[0]
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # Check for hour component (v3.7.0+)
        shift = 1 if (len(parts[1]) == 2 and parts[1].isdigit()) else 0

        if len(parts) < 3 + shift:
            continue

        # Standard format: YYYYMMDD-[HH]-project-session_id
        session_id = parts[2 + shift]

        # Check if insights exist (v3.4.0: YYYYMMDD format)
        insights_file = insights_dir / f"{date_str}-{session_id}.json"
        if insights_file.exists():
            continue

        # Deduplicate: prefer full transcript over abridged
        if session_id in seen_session_ids:
            existing = seen_session_ids[session_id]
            # Replace with full transcript if current is full and existing is not
            if "full" in transcript.stem and "full" not in existing.stem:
                seen_session_ids[session_id] = transcript
        else:
            seen_session_ids[session_id] = transcript

    count = 0
    for session_id, transcript in list(seen_session_ids.items()):
        if count >= args.limit:
            break
        parts = transcript.stem.split("-")
        date_str = parts[0]
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        print(f"{transcript}|{session_id}|{date_formatted}")
        count += 1


if __name__ == "__main__":
    main()
