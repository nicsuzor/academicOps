#!/usr/bin/env python3
"""Compare processed sessions (JSON summaries) vs available transcripts.

Identifies:
- Sessions with JSON summary but no transcript (contemporaneous capture)
- Sessions with transcript but no JSON summary (need mining)
- Sessions with both (fully processed)

Usage:
    uv run python skills/session-insights/scripts/compare_sessions.py [--date YYYYMMDD]
    uv run python skills/session-insights/scripts/compare_sessions.py --all
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def get_aca_data() -> Path:
    """Get ACA_DATA path from environment."""
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        raise RuntimeError("ACA_DATA environment variable not set")
    return Path(aca_data)


def find_transcripts(aca_data: Path, date_filter: str | None = None) -> dict[str, dict]:
    """Find all transcript files (Claude and Gemini).

    Returns dict mapping session_id -> {path, date, project, source}
    """
    transcripts = {}

    # Claude transcripts: $ACA_DATA/sessions/claude/YYYYMMDD-project-sessionid-*-abridged.md
    claude_dir = aca_data / "sessions" / "claude"
    if claude_dir.exists():
        for f in claude_dir.glob("*-abridged.md"):
            # Parse: 20260108-academicOps-138295b6-crontab-fix-abridged.md
            match = re.match(r"(\d{8})-([^-]+)-([a-f0-9]{8})", f.name)
            if match:
                date, project, session_id = match.groups()
                if date_filter and date != date_filter:
                    continue
                transcripts[session_id] = {
                    "path": str(f),
                    "date": date,
                    "project": project,
                    "source": "claude",
                }

    # Gemini transcripts: $ACA_DATA/sessions/gemini/*-abridged.md
    gemini_dir = aca_data / "sessions" / "gemini"
    if gemini_dir.exists():
        for f in gemini_dir.glob("*-abridged.md"):
            # Parse: 20260108-gemini-hash-sessionid-session-abridged.md
            match = re.match(r"(\d{8})-[^-]+-[a-f0-9]+-([a-f0-9]{8})", f.name)
            if match:
                date, session_id = match.groups()
                if date_filter and date != date_filter:
                    continue
                transcripts[session_id] = {
                    "path": str(f),
                    "date": date,
                    "project": "gemini",
                    "source": "gemini",
                }

    return transcripts


def find_summaries(
    aca_data: Path, date_filter: str | None = None
) -> dict[str, dict[str, Any]]:
    """Find all session JSON summaries.

    Returns dict mapping session_id -> {path, date, project, has_accomplishments}
    """
    summaries: dict[str, dict[str, Any]] = {}
    summary_dir = aca_data / "dashboard" / "sessions"

    if not summary_dir.exists():
        return summaries

    for f in summary_dir.glob("*.json"):
        session_id = f.stem
        try:
            with open(f) as fp:
                data = json.load(fp)
            date = data.get("date", "").replace("-", "")
            if date_filter and date != date_filter:
                continue
            summaries[session_id] = {
                "path": str(f),
                "date": date,
                "project": data.get("project", "unknown"),
                "summary": data.get("summary", ""),
                "accomplishments": data.get("accomplishments", []),
                "has_accomplishments": bool(data.get("accomplishments")),
                "skill_compliance": data.get("skill_compliance", {}),
            }
        except (json.JSONDecodeError, KeyError):
            continue

    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare sessions vs summaries")
    parser.add_argument("--date", help="Filter to specific date (YYYYMMDD)")
    parser.add_argument("--all", action="store_true", help="Show all dates")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    aca_data = get_aca_data()
    date_filter = None if args.all else (args.date or datetime.now().strftime("%Y%m%d"))

    transcripts = find_transcripts(aca_data, date_filter)
    summaries = find_summaries(aca_data, date_filter)

    all_ids = set(transcripts.keys()) | set(summaries.keys())

    results: dict[str, Any] = {
        "date_filter": date_filter or "all",
        "summary_only": [],  # Have JSON but no transcript
        "transcript_only": [],  # Have transcript but no JSON (need mining)
        "both": [],  # Fully processed
    }

    for sid in sorted(all_ids):
        has_transcript = sid in transcripts
        has_summary = sid in summaries

        entry = {
            "session_id": sid,
            "date": transcripts.get(sid, summaries.get(sid, {})).get("date", "unknown"),
            "project": transcripts.get(sid, summaries.get(sid, {})).get(
                "project", "unknown"
            ),
        }

        if has_summary:
            entry["summary"] = summaries[sid].get("summary", "")[:80]
            entry["accomplishment_count"] = len(
                summaries[sid].get("accomplishments", [])
            )

        if has_transcript and has_summary:
            results["both"].append(entry)
        elif has_summary:
            results["summary_only"].append(entry)
        elif has_transcript:
            results["transcript_only"].append(entry)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"Session Comparison (date: {results['date_filter']})")
        print("=" * 60)

        print(f"\n## Fully Processed ({len(results['both'])} sessions)")
        print("Have both transcript and JSON summary")
        for e in results["both"]:
            print(
                f"  {e['session_id']} | {e['project']} | {e.get('accomplishment_count', 0)} accomplishments"
            )

        print(f"\n## Summary Only ({len(results['summary_only'])} sessions)")
        print("JSON summary exists but no transcript (contemporaneous capture)")
        for e in results["summary_only"]:
            print(
                f"  {e['session_id']} | {e['project']} | {e.get('accomplishment_count', 0)} accomplishments"
            )
            if e.get("summary"):
                print(f"    → {e['summary']}")

        print(f"\n## Transcript Only ({len(results['transcript_only'])} sessions)")
        print("Transcript exists but needs mining")
        for e in results["transcript_only"]:
            print(f"  {e['session_id']} | {e['project']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
