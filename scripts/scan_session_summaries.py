#!/usr/bin/env python3
"""Scan session summaries for daily note and overwhelm dashboard.

Scans the last N days of session summary JSONs from ~/writing/sessions/summaries/
and presents an ordered list suitable for:
- Daily note synthesis (LLM summarization)
- Overwhelm dashboard display

Usage:
    scan_session_summaries.py [--days N] [--format FORMAT] [--project PROJECT]

Output formats:
    json    - Full structured JSON (default)
    compact - Condensed JSON for LLM context
    text    - Human-readable text summary
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def get_summaries_dir() -> Path:
    """Get the session summaries directory.

    Returns:
        Path to ~/writing/sessions/summaries/
    """
    return Path.home() / "writing" / "sessions" / "summaries"


def parse_summary_filename(filename: str) -> dict[str, str] | None:
    """Parse summary filename to extract metadata.

    Filename formats:
        YYYYMMDD-HH-project-sessionid-suffix.json (v3.7.0+)
        YYYYMMDD-project-sessionid-suffix.json (older)

    Args:
        filename: The summary filename (stem, no extension)

    Returns:
        Dict with date, hour (optional), project, session_id, or None if invalid
    """
    parts = filename.split("-")
    if len(parts) < 3:
        return None

    # Check for valid date prefix
    if len(parts[0]) != 8 or not parts[0].isdigit():
        return None

    date_str = parts[0]

    # Check for hour component (v3.7.0+)
    if len(parts) >= 4 and len(parts[1]) == 2 and parts[1].isdigit():
        return {
            "date": date_str,
            "hour": parts[1],
            "project": parts[2],
            "session_id": parts[3] if len(parts) > 3 else "",
        }
    else:
        return {
            "date": date_str,
            "hour": None,
            "project": parts[1],
            "session_id": parts[2] if len(parts) > 2 else "",
        }


def load_summary(path: Path) -> dict[str, Any] | None:
    """Load a session summary JSON file.

    Args:
        path: Path to the summary JSON file

    Returns:
        Parsed JSON dict or None if invalid/missing
    """
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def scan_summaries(
    days: int = 1,
    project_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Scan session summaries for the last N days.

    Args:
        days: Number of days to look back (default: 1)
        project_filter: Optional project name to filter by

    Returns:
        List of summary dicts, sorted by date descending
    """
    summaries_dir = get_summaries_dir()
    if not summaries_dir.exists():
        return []

    # Calculate date range
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)  # Include today
    cutoff_str = cutoff.strftime("%Y%m%d")

    results = []

    for json_file in summaries_dir.glob("*.json"):
        # Skip non-summary files
        if json_file.name.startswith("."):
            continue

        # Parse filename for metadata
        file_meta = parse_summary_filename(json_file.stem)
        if not file_meta:
            continue

        # Date filter
        if file_meta["date"] < cutoff_str:
            continue

        # Project filter
        if project_filter and file_meta["project"] != project_filter:
            continue

        # Load the summary
        summary = load_summary(json_file)
        if not summary:
            continue

        # Enrich with file metadata
        summary["_file"] = json_file.name
        summary["_file_date"] = file_meta["date"]
        summary["_file_hour"] = file_meta["hour"]
        summary["_file_project"] = file_meta["project"]

        results.append(summary)

    # Sort by date descending (most recent first), then by hour if available
    results.sort(
        key=lambda x: (x.get("_file_date", ""), x.get("_file_hour") or "00"),
        reverse=True,
    )

    return results


def format_json(summaries: list[dict[str, Any]]) -> str:
    """Format summaries as full JSON."""
    return json.dumps(summaries, indent=2, default=str)


def format_compact(summaries: list[dict[str, Any]]) -> str:
    """Format summaries as compact JSON for LLM context.

    Extracts only the fields needed for synthesis:
    - session_id, date, project
    - summary, outcome
    - accomplishments
    - friction_points
    """
    compact = []
    for s in summaries:
        entry = {
            "session_id": s.get("session_id", s.get("_file", "unknown")),
            "date": s.get("date", s.get("_file_date", "")),
            "project": s.get("project", s.get("_file_project", "")),
            "summary": s.get("summary", ""),
            "outcome": s.get("outcome", "unknown"),
            "accomplishments": s.get("accomplishments", []),
            "friction_points": s.get("friction_points", []),
        }
        compact.append(entry)

    return json.dumps(compact, indent=2, default=str)


def format_text(summaries: list[dict[str, Any]]) -> str:
    """Format summaries as human-readable text."""
    if not summaries:
        return "No session summaries found."

    lines = []
    current_date = None

    for s in summaries:
        date = s.get("_file_date", "")
        if date != current_date:
            if current_date is not None:
                lines.append("")
            formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) == 8 else date
            lines.append(f"=== {formatted_date} ===")
            current_date = date

        session_id = s.get("session_id", "unknown")[:8]
        project = s.get("project", s.get("_file_project", "unknown"))
        outcome = s.get("outcome", "unknown")
        summary = s.get("summary", "No summary")

        lines.append(f"\n[{session_id}] {project} ({outcome})")
        lines.append(f"  {summary}")

        accomplishments = s.get("accomplishments", [])
        if accomplishments:
            lines.append("  Accomplishments:")
            for acc in accomplishments[:5]:  # Limit to first 5
                lines.append(f"    - {acc}")
            if len(accomplishments) > 5:
                lines.append(f"    ... and {len(accomplishments) - 5} more")

        friction = s.get("friction_points", [])
        if friction:
            lines.append("  Friction:")
            for f in friction[:3]:  # Limit to first 3
                lines.append(f"    ! {f}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Scan session summaries for daily note and overwhelm dashboard"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to scan (default: 1 = today only)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "compact", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Filter by project name",
    )
    args = parser.parse_args()

    summaries = scan_summaries(days=args.days, project_filter=args.project)

    if args.format == "json":
        print(format_json(summaries))
    elif args.format == "compact":
        print(format_compact(summaries))
    elif args.format == "text":
        print(format_text(summaries))


if __name__ == "__main__":
    main()
