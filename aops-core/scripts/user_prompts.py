#!/usr/bin/env python3
"""Assemble a threaded user-prompt timeline across sessions."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add aops-core to path
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.session_naming import generate_base_name, infer_provider_from_path
from lib.session_reader import find_sessions
from lib.transcript_parser import SessionProcessor, extract_timeline_events


def parse_period(period_str: str) -> datetime:
    period_str = period_str.strip().lower()
    now = datetime.now().astimezone()

    if period_str == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period_str == "yesterday":
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Check for Xd, Xh
    if period_str.endswith("d") and period_str[:-1].isdigit():
        return now - timedelta(days=int(period_str[:-1]))
    if period_str.endswith("h") and period_str[:-1].isdigit():
        return now - timedelta(hours=int(period_str[:-1]))

    # Check for YYYY-MM-DD
    try:
        dt = datetime.strptime(period_str, "%Y-%m-%d")
        return dt.astimezone()
    except ValueError:
        pass

    print(f"Warning: Unknown period format '{period_str}'. Defaulting to today.", file=sys.stderr)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def main():
    parser = argparse.ArgumentParser(description="Assemble threaded user-prompt timeline")
    parser.add_argument(
        "--period", "-p", default="today", help="Period (e.g. today, 1d, 7d, 2026-05-29)"
    )
    args = parser.parse_args()

    cutoff = parse_period(args.period)
    sessions = find_sessions(since=cutoff)

    if not sessions:
        print(f"No sessions found since {cutoff.isoformat()}")
        return

    processor = SessionProcessor()
    session_threads = []

    for session in sessions:
        try:
            summary, entries, agent_entries = processor.parse_session_file(session.path)
            if not entries:
                continue

            turns = processor.group_entries_into_turns(entries, agent_entries)
            timeline_events = extract_timeline_events(turns, session.session_id)

            prompts = [e for e in timeline_events if e.get("type") == "user_prompt"]
            if not prompts:
                continue

            # Find the true start time of the session from its first prompt or first entry
            session_start = session.last_modified
            for entry in entries:
                if entry.timestamp:
                    session_start = entry.timestamp
                    break

            provider = summary.provider or infer_provider_from_path(session.path)
            repo = summary.repo or session.project
            sid = session.session_id
            slug = summary.slug or processor.generate_session_slug(entries)

            filename_base = generate_base_name(
                session_id=sid,
                timestamp=session_start,
                slug=slug,
                repo=repo,
                provider=provider,
                task_id=summary.task_id,
            )

            rotation_dir = session_start.astimezone().strftime("%Y-%m")
            transcript_url = f"$AOPS_SESSIONS/transcripts/{rotation_dir}/{filename_base}-full.md"

            session_threads.append(
                {
                    "start_time": session_start,
                    "session_id": sid,
                    "repo": repo,
                    "model": summary.provider or "unknown",
                    "slug": slug,
                    "url": transcript_url,
                    "prompts": prompts,
                }
            )
        except Exception as e:
            print(f"Error processing {session.path}: {e}", file=sys.stderr)

    # Sort threads by their start time
    session_threads.sort(key=lambda x: x["start_time"])

    print(f"# User Prompt Timeline: Since {args.period}\n")
    for thread in session_threads:
        ts_str = thread["start_time"].strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"## {ts_str} | {thread['repo']} | {thread['model']} | [{thread['session_id']}]({thread['url']})"
        )
        print(f"**Context**: {thread['slug']}")
        print()

        for i, p in enumerate(thread["prompts"], 1):
            p_ts = ""
            if p.get("timestamp"):
                dt = datetime.fromisoformat(p["timestamp"]).astimezone()
                p_ts = dt.strftime("%H:%M:%S")
            print(f"### Prompt {i} ({p_ts})")
            for line in p["description"].strip().splitlines():
                print(f"> {line}")
            print()
        print("---\n")


if __name__ == "__main__":
    main()
