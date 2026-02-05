#!/usr/bin/env python3
"""Prepare session insights prompt for Gemini.

Extracts metadata from transcript filename and substitutes into shared prompt template.

Usage:
    prepare_prompt.py <transcript_path>

Example:
    prepare_prompt.py $ACA_DATA/sessions/claude/20260113-academicOps-a1b2c3d4-main.md
    # Outputs prepared prompt with {session_id}, {date}, {project} substituted
"""

import argparse
import re
import sys
from pathlib import Path

# Add aops-core to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.insights_generator import (
    load_prompt_template,
    substitute_prompt_variables,
)


def extract_metadata_from_filename(filename: str) -> dict[str, str]:
    """Extract session_id, date, project from transcript filename.

    Expected formats:
    - YYYYMMDD-{project}-{session_id}-{suffix}.md
    - YYYYMMDD-{project}-{session_id}.md
    - {session_id}.json (fallback for raw session files)

    Args:
        filename: Transcript filename (basename, not full path)

    Returns:
        Dict with 'session_id', 'date', 'project' keys

    Raises:
        ValueError: If filename format is not recognized
    """
    # Remove extension
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename

    # Pattern 1a: YYYYMMDD-HH-{project}-{session_id}-{suffix} (v3.7.0+)
    # Example: 20260130-17-academicOps-a1b2c3d4-main-abridged
    match = re.match(r"^(\d{8})-\d{2}-([^-]+)-([a-f0-9]{8})", stem)
    if match:
        date_str, project, session_id = match.groups()
        # Convert YYYYMMDD to YYYY-MM-DD
        date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return {"session_id": session_id, "date": date, "project": project}

    # Pattern 1b: YYYYMMDD-{project}-{session_id}-{suffix} (Legacy)
    # Example: 20260113-academicOps-a1b2c3d4-main-abridged
    match = re.match(r"^(\d{8})-([^-]+)-([a-f0-9]{8})", stem)
    if match:
        date_str, project, session_id = match.groups()
        # Convert YYYYMMDD to YYYY-MM-DD
        date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return {"session_id": session_id, "date": date, "project": project}

    # Pattern 2: {session_id}.json (raw session file)
    # Example: a1b2c3d4.json
    match = re.match(r"^([a-f0-9]{8})$", stem)
    if match:
        session_id = match.group(1)
        # Use today's date as fallback
        from datetime import datetime, timezone

        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {"session_id": session_id, "date": date, "project": "unknown"}

    # Pattern 3: Try to extract any 8-char hex as session_id
    hex_match = re.search(r"([a-f0-9]{8})", stem)
    if hex_match:
        session_id = hex_match.group(1)
        # Try to extract date
        date_match = re.match(r"^(\d{8})", stem)
        if date_match:
            date_str = date_match.group(1)
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            from datetime import datetime, timezone

            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Try to extract project (usually between date and session_id)
        # Handle optional hour component: YYYYMMDD-[HH]-project
        project_match = re.match(r"^\d{8}-(?:\d{2}-)?([^-]+)-", stem)
        project = project_match.group(1) if project_match else "unknown"

        return {"session_id": session_id, "date": date, "project": project}

    raise ValueError(
        f"Could not extract metadata from filename: {filename}\n"
        f"Expected format: YYYYMMDD-{{project}}-{{session_id}}-{{suffix}}.md"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Prepare session insights prompt with metadata substitution"
    )
    parser.add_argument("transcript", help="Path to transcript file")
    parser.add_argument(
        "--debug", action="store_true", help="Print metadata extraction details"
    )
    args = parser.parse_args()

    transcript_path = Path(args.transcript)

    # Validate transcript exists
    if not transcript_path.exists():
        print(f"ERROR: Transcript file not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    # Extract metadata from filename
    try:
        metadata = extract_metadata_from_filename(transcript_path.name)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.debug:
        print("Extracted metadata:", file=sys.stderr)
        print(f"  session_id: {metadata['session_id']}", file=sys.stderr)
        print(f"  date: {metadata['date']}", file=sys.stderr)
        print(f"  project: {metadata['project']}", file=sys.stderr)
        print("", file=sys.stderr)

    # Load shared template
    try:
        template = load_prompt_template()
    except FileNotFoundError as e:
        print(f"ERROR: Could not load prompt template: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Ensure aops-core/specs/session-insights-prompt.md exists", file=sys.stderr
        )
        sys.exit(1)

    # Substitute variables
    prepared_prompt = substitute_prompt_variables(template, metadata)

    # Output prepared prompt
    print(prepared_prompt)


if __name__ == "__main__":
    main()
