#!/usr/bin/env python3
"""Migrate insights filenames to include project name.

Renames files from old formats to: YYYYMMDD-project-sessionid-slug.json

Usage:
    uv run python aops-core/scripts/migrate_insights_filenames.py --dry-run
    uv run python aops-core/scripts/migrate_insights_filenames.py
"""

import argparse
import json
import re
import sys
from pathlib import Path


def get_summaries_dir() -> Path:
    """Get summaries directory."""
    return Path.home() / "writing" / "sessions" / "summaries"


def sanitize_segment(segment: str) -> str:
    """Sanitize a string for use in filenames."""
    sanitized = segment.lower().replace(" ", "-").replace("_", "-")
    sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized.strip("-")


def parse_existing_filename(filename: str) -> dict:
    """Parse existing filename to extract components.

    Handles various formats:
    - YYYYMMDD-sessionid-slug.json (v3.5)
    - YYYYMMDD-project-sessionid-slug.json (v3.6)
    - YYYYMMDD-slug.json (legacy)
    - YYYYMMDD-sessionid.json (minimal)
    """
    stem = filename.replace(".json", "")
    parts = stem.split("-")

    result = {
        "date": parts[0] if parts else "",
        "project": "",
        "session_id": "",
        "slug": "",
    }

    if len(parts) < 2:
        return result

    # First part is always date (YYYYMMDD)
    result["date"] = parts[0]

    # Check if second part looks like an 8-char hex session ID
    if len(parts) >= 2 and re.match(r"^[0-9a-f]{8}$", parts[1]):
        # Format: date-sessionid-slug or date-sessionid
        result["session_id"] = parts[1]
        if len(parts) >= 3:
            result["slug"] = "-".join(parts[2:])
    elif len(parts) >= 3 and re.match(r"^[0-9a-f]{8}$", parts[2]):
        # Format: date-project-sessionid-slug (already has project)
        result["project"] = parts[1]
        result["session_id"] = parts[2]
        if len(parts) >= 4:
            result["slug"] = "-".join(parts[3:])
    else:
        # Format: date-slug (legacy, no session ID in filename)
        result["slug"] = "-".join(parts[1:])

    return result


def build_new_filename(date: str, project: str, session_id: str, slug: str) -> str:
    """Build new filename with all components."""
    parts = [date]
    if project:
        parts.append(sanitize_segment(project))
    if session_id:
        parts.append(session_id)
    if slug:
        parts.append(slug)
    return "-".join(parts) + ".json"


def migrate_file(file_path: Path, dry_run: bool = True) -> tuple[bool, str]:
    """Migrate a single file to new naming convention.

    Returns (success, message) tuple.
    """
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Failed to read: {e}"

    # Extract components from JSON
    json_project = data.get("project", "")
    json_session_id = data.get("session_id", "")
    json_date = data.get("date", "")

    # Parse date to YYYYMMDD format
    if json_date:
        # Handle ISO format: 2026-01-21T20:47:26.788000+00:00
        date_match = re.match(r"(\d{4})-(\d{2})-(\d{2})", json_date)
        if date_match:
            json_date = "".join(date_match.groups())

    # Parse existing filename
    parsed = parse_existing_filename(file_path.name)

    # Determine final values (JSON takes precedence)
    final_date = json_date or parsed["date"]
    final_project = json_project or parsed["project"]
    final_session_id = json_session_id or parsed["session_id"]
    final_slug = parsed["slug"]  # Slug only comes from filename

    # Build new filename
    new_name = build_new_filename(final_date, final_project, final_session_id, final_slug)

    # Check if rename needed
    if new_name == file_path.name:
        return True, "Already correct"

    new_path = file_path.parent / new_name

    # Check for collision
    if new_path.exists() and new_path != file_path:
        return False, f"Collision: {new_name} already exists"

    if dry_run:
        return True, f"Would rename: {file_path.name} -> {new_name}"

    # Perform rename
    file_path.rename(new_path)
    return True, f"Renamed: {file_path.name} -> {new_name}"


def main():
    parser = argparse.ArgumentParser(
        description="Migrate insights filenames to include project name"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be renamed without actually renaming",
    )
    args = parser.parse_args()

    summaries_dir = get_summaries_dir()
    if not summaries_dir.exists():
        print(f"Summaries directory not found: {summaries_dir}", file=sys.stderr)
        return 1

    json_files = sorted(summaries_dir.glob("*.json"))

    if not json_files:
        print("No JSON files found")
        return 0

    print(f"{'DRY RUN - ' if args.dry_run else ''}Processing {len(json_files)} files...")
    print()

    success_count = 0
    skip_count = 0
    error_count = 0

    for file_path in json_files:
        success, message = migrate_file(file_path, dry_run=args.dry_run)

        if "Already correct" in message:
            skip_count += 1
        elif success:
            print(f"  {message}")
            success_count += 1
        else:
            print(f"  ERROR: {file_path.name}: {message}", file=sys.stderr)
            error_count += 1

    print()
    print(f"Results: {success_count} {'would be ' if args.dry_run else ''}renamed, {skip_count} already correct, {error_count} errors")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
