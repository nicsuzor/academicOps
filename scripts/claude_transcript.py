#!/usr/bin/env python3
"""
Claude Session Transcript Generator

Converts Claude Code JSONL session files to readable markdown transcripts.

Usage:
    uv run python $AOPS/scripts/claude_transcript.py session.jsonl
    uv run python $AOPS/scripts/claude_transcript.py session.jsonl -o output.md
"""

import argparse
import sys
from pathlib import Path

from lib.session_reader import SessionProcessor


def main():
    parser = argparse.ArgumentParser(
        description="Convert Claude Code JSONL sessions to markdown transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python claude_transcript.py session.jsonl                    # Generates session_XXX-full.md and session_XXX-abridged.md
  python claude_transcript.py session.jsonl -o transcript      # Generates transcript-full.md and transcript-abridged.md
  python claude_transcript.py session.jsonl --full-only        # Only full version with tool results
  python claude_transcript.py session.jsonl --abridged-only    # Only abridged version without tool results
        """
    )

    parser.add_argument('jsonl_file', help='Path to Claude Code JSONL session file')
    parser.add_argument('-o', '--output', help='Output base name (generates -full.md and -abridged.md)')
    parser.add_argument('--full-only', action='store_true', help='Generate only the full version')
    parser.add_argument('--abridged-only', action='store_true', help='Generate only the abridged version')

    args = parser.parse_args()

    # Validate input file
    jsonl_path = Path(args.jsonl_file)
    if not jsonl_path.exists():
        print(f"❌ Error: File not found: {jsonl_path}")
        return 1

    # Generate output base name
    if args.output:
        base_name = args.output
        # Strip .md suffix if provided
        if base_name.endswith('.md'):
            base_name = base_name[:-3]
        # Strip -full or -abridged suffix if provided
        if base_name.endswith('-full') or base_name.endswith('-abridged'):
            base_name = base_name.rsplit('-', 1)[0]
    else:
        session_id = jsonl_path.stem[:8]
        base_name = f"session_{session_id}"

    # Determine which versions to generate
    generate_full = not args.abridged_only
    generate_abridged = not args.full_only

    # Process the session
    processor = SessionProcessor()

    try:
        print(f"📝 Processing session: {jsonl_path}")
        session_summary, entries, agent_entries = processor.parse_jsonl(str(jsonl_path))

        print(f"📊 Found {len(entries)} entries")

        # Generate full version
        if generate_full:
            full_path = Path(f"{base_name}-full.md")
            markdown_full = processor.format_session_as_markdown(
                session_summary, entries, agent_entries, include_tool_results=True, variant="full"
            )
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(markdown_full)
            file_size = full_path.stat().st_size
            print(f"✅ Full transcript: {full_path} ({file_size:,} bytes)")

        # Generate abridged version
        if generate_abridged:
            abridged_path = Path(f"{base_name}-abridged.md")
            markdown_abridged = processor.format_session_as_markdown(
                session_summary, entries, agent_entries, include_tool_results=False, variant="abridged"
            )
            with open(abridged_path, 'w', encoding='utf-8') as f:
                f.write(markdown_abridged)
            file_size = abridged_path.stat().st_size
            print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

        return 0

    except Exception as e:
        print(f"❌ Error processing session: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
