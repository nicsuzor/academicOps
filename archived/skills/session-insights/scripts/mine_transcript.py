#!/usr/bin/env python3
"""Mine a session transcript to extract insights.

This script is designed to be called by Claude via the session-insights skill.
It prepares the prompt but does NOT call the LLM - the skill orchestrates that.

Usage:
    python mine_transcript.py <transcript_path> [--output-dir DIR]

Output:
    Prints the prepared prompt with metadata substitutions.
    The skill then passes this to Gemini MCP for processing.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def extract_metadata_from_filename(filename: str) -> dict[str, str]:
    """Extract session metadata from transcript filename.

    Expected format: YYYYMMDD-{project}-{session_id}-{optional-suffix}-abridged.md

    Returns:
        dict with session_id, date, project
    """
    # Remove path and extension
    name = Path(filename).stem  # removes .md
    if name.endswith("-abridged"):
        name = name[:-9]  # remove -abridged

    # Extract date (first 8 chars)
    date_raw = name[:8]
    date_formatted = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"

    # Extract session_id (8 hex chars, usually near the end)
    session_match = re.search(r"-([a-f0-9]{8})(?:-|$)", name)
    session_id = session_match.group(1) if session_match else "unknown"

    # Extract project (between date and session_id)
    # Pattern: YYYYMMDD-{project}-{session_id}...
    project_match = re.match(r"^\d{8}-(.+?)-[a-f0-9]{8}", name)
    if project_match:
        project = project_match.group(1)
    else:
        # Fallback: everything between date and first hex sequence
        parts = name[9:].split("-")  # skip YYYYMMDD-
        project = parts[0] if parts else "unknown"

    return {
        "session_id": session_id,
        "date": date_formatted,
        "project": project,
    }


def prepare_prompt(template_path: Path, metadata: dict[str, str]) -> str:
    """Load template and substitute metadata placeholders."""
    template = template_path.read_text()

    for key, value in metadata.items():
        template = template.replace(f"{{{key}}}", value)

    return template


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare session mining prompt")
    parser.add_argument("transcript", help="Path to transcript file")
    parser.add_argument(
        "--template",
        default=None,
        help="Path to prompt template (default: insights.md in same dir as script)",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only output extracted metadata as JSON",
    )
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"ERROR: Transcript not found: {transcript_path}", file=sys.stderr)
        return 1

    # Extract metadata from filename
    metadata = extract_metadata_from_filename(transcript_path.name)

    if args.metadata_only:
        import json

        print(json.dumps(metadata, indent=2))
        return 0

    # Find template
    if args.template:
        template_path = Path(args.template)
    else:
        # Default: insights.md in skill directory (parent of scripts/)
        script_dir = Path(__file__).parent
        template_path = script_dir.parent / "insights.md"

    if not template_path.exists():
        print(f"ERROR: Template not found: {template_path}", file=sys.stderr)
        return 1

    # Prepare and output prompt
    prompt = prepare_prompt(template_path, metadata)
    print(prompt)

    return 0


if __name__ == "__main__":
    sys.exit(main())
