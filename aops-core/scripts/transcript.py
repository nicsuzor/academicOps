#!/usr/bin/env python3
"""
Session Transcript Generator

Converts Claude Code JSONL and Gemini JSON session files to readable markdown transcripts.

Usage:
    uv run python aops-core/scripts/transcript.py session.jsonl
    uv run python aops-core/scripts/transcript.py session.jsonl -o output.md
    uv run python aops-core/scripts/transcript.py --all  # Process all sessions
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.session_reader import find_sessions  # noqa: E402
from lib.transcript_parser import SessionProcessor  # noqa: E402
from lib.paths import get_sessions_dir  # noqa: E402


def format_markdown(file_path: Path) -> bool:
    """Format markdown file with dprint.

    Checks multiple locations for dprint, preferring local installs for speed.
    Skips formatting if no local dprint found (npx is too slow).
    Returns True if formatting succeeded or skipped, False on error.
    """
    # Check locations in order of preference (fastest first)
    dprint_locations = [
        Path.home() / ".dprint" / "bin" / "dprint",  # Official installer
        Path(__file__).parent.parent / "node_modules" / ".bin" / "dprint",  # Local npm
    ]

    dprint_path = None
    for path in dprint_locations:
        if path.exists():
            dprint_path = path
            break

    if dprint_path is None:
        # No local dprint found, skip formatting (npx is too slow)
        return True

    try:
        result = subprocess.run(
            [str(dprint_path), "fmt", str(file_path)],
            capture_output=True,
            timeout=30,
            check=False,
        )
        # Exit code 0 = success, 14 = no matching files (OK for external paths)
        return result.returncode in (0, 14)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _is_test_session(p: Path) -> bool:
    """Heuristically detect obvious test/demo sessions to exclude from batch runs.

    Excludes paths under /tmp and filenames or parent folders containing
    keywords like test, demo, scratch, sample, example, tmp, local, dev.
    """
    s = str(p).lower()
    name = p.name.lower()
    parts = [part.lower() for part in p.parts]

    # Exclude /tmp paths
    if s.startswith("/tmp") or "/tmp/" in s:
        return True

    keywords = (
        "test",
        "tests",
        "demo",
        "scratch",
        "sample",
        "example",
        "tmp",
        "local",
        "dev",
    )
    if any(k in name for k in keywords):
        return True
    if any(k in parts for k in keywords):
        return True

    return False


def _output_exists(out_dir: Path, slug: str) -> bool:
    """Check if output files already exist for this session."""
    pattern = f"*{slug}*-full.md"
    return any(out_dir.glob(pattern))


def main():
    parser = argparse.ArgumentParser(
        description="Convert Claude Code JSONL or Gemini JSON sessions to markdown transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transcript.py session.jsonl                    # Auto-names in sessions/claude/
  python transcript.py session.json                     # Generates Gemini transcript
  python transcript.py session.jsonl -o transcript      # Uses sessions/claude/transcript-{full,abridged}.md
  python transcript.py session.jsonl -o /abs/path/name  # Uses absolute path
  python transcript.py --all                            # Process all sessions in ~/.claude/projects/
        """,
    )

    parser.add_argument(
        "session_file",
        nargs="?",
        help="Path to Session file (Claude .jsonl or Gemini .json)",
    )
    parser.add_argument(
        "-o", "--output", help="Output base name (generates -full.md and -abridged.md)"
    )
    parser.add_argument(
        "--slug",
        help="Brief slug describing session work (auto-generated if not provided)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all sessions found in ~/.claude/projects/ and write to sessions/claude/",
    )

    args = parser.parse_args()

    # Default output directory
    sessions_claude = get_sessions_dir() / "claude"
    sessions_claude.mkdir(parents=True, exist_ok=True)

    processor = SessionProcessor()

    # Batch mode: process all sessions
    if args.all:
        sessions = find_sessions()
        if not sessions:
            print("No sessions found.", file=sys.stderr)
            return 0

        # Exclude obvious test/demo sessions, then process newest-first
        sessions = [
            s
            for s in sessions
            if not _is_test_session(s.path if hasattr(s, "path") else Path(str(s)))
        ]
        # Process newest sessions first (reverse chronological)
        sessions = sorted(
            sessions,
            key=lambda s: s.path.stat().st_mtime
            if hasattr(s, "path") and s.path.exists()
            else 0,
            reverse=True,
        )

        processed = 0
        skipped = 0
        errors = 0

        for s in sessions:
            try:
                session_path = s.path if hasattr(s, "path") else Path(str(s))

                # Process the session
                print(f"📝 Processing session: {session_path}")
                session_summary, entries, agent_entries = processor.parse_session_file(
                    str(session_path)
                )

                # Check for meaningful content
                MIN_MEANINGFUL_ENTRIES = 2
                meaningful_count = sum(
                    1
                    for e in entries
                    if e.type in ("user", "assistant")
                    and not (
                        hasattr(e, "message")
                        and e.message
                        and e.message.get("subtype") in ("system", "informational")
                    )
                )
                if meaningful_count < MIN_MEANINGFUL_ENTRIES:
                    print(
                        f"⏭️  Skipping: only {meaningful_count} meaningful entries (need {MIN_MEANINGFUL_ENTRIES}+)"
                    )
                    skipped += 1
                    continue

                # Generate output name
                date_str = None
                for entry in entries:
                    if entry.timestamp:
                        date_str = entry.timestamp.strftime("%Y%m%d")
                        break
                if not date_str:
                    date_str = datetime.fromtimestamp(
                        session_path.stat().st_mtime
                    ).strftime("%Y%m%d")

                # Get short project name
                project = session_path.parent.name
                if session_path.suffix == ".json":
                    if project == "chats":
                        hash_dir = session_path.parent.parent.name
                        short_project = f"gemini-{hash_dir[:6]}"
                    else:
                        short_project = "gemini"
                else:
                    project_parts = project.strip("-").split("-")
                    short_project = project_parts[-1] if project_parts else "unknown"

                # Get session ID
                session_id = session_path.stem
                if len(session_id) > 8:
                    if session_id.startswith("session-"):
                        parts = session_id.split("-")
                        session_id = parts[-1]
                    else:
                        session_id = session_id[:8]

                # Get slug
                slug = processor.generate_session_slug(entries)
                filename = f"{date_str}-{short_project}-{session_id}-{slug}"

                # Check if already exists
                if _output_exists(sessions_claude, slug):
                    skipped += 1
                    continue

                base_name = str(sessions_claude / filename)

                # Generate full version
                full_path = Path(f"{base_name}-full.md")
                markdown_full = processor.format_session_as_markdown(
                    session_summary,
                    entries,
                    agent_entries,
                    include_tool_results=True,
                    variant="full",
                    source_file=str(session_path.resolve()),
                )
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(markdown_full)
                format_markdown(full_path)
                file_size = full_path.stat().st_size
                print(f"✅ Full transcript: {full_path} ({file_size:,} bytes)")

                # Generate abridged version
                abridged_path = Path(f"{base_name}-abridged.md")
                markdown_abridged = processor.format_session_as_markdown(
                    session_summary,
                    entries,
                    agent_entries,
                    include_tool_results=False,
                    variant="abridged",
                    source_file=str(session_path.resolve()),
                )
                with open(abridged_path, "w", encoding="utf-8") as f:
                    f.write(markdown_abridged)
                format_markdown(abridged_path)
                file_size = abridged_path.stat().st_size
                print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

                processed += 1

            except Exception as e:
                errors += 1
                print(f"❌ Error processing {session_path}: {e}", file=sys.stderr)

        print(f"Processed: {processed}", file=sys.stderr)
        print(f"Skipped: {skipped}", file=sys.stderr)
        print(f"Errors: {errors}", file=sys.stderr)
        return 0

    # Single session mode
    if not args.session_file:
        print("Error: must provide a session file or use --all", file=sys.stderr)
        return 1

    # Validate input file
    session_path = Path(args.session_file)
    if not session_path.exists():
        print(f"❌ Error: File not found: {session_path}")
        return 1

    # Check if this is a hooks file and find the actual session file
    if session_path.name.endswith("-hooks.jsonl"):
        import json

        with open(session_path, "r") as f:
            first_line = f.readline().strip()
            if first_line:
                try:
                    data = json.loads(first_line)
                    transcript_path = data.get("transcript_path")
                    if transcript_path:
                        actual_session = Path(transcript_path)
                        if actual_session.exists():
                            print(
                                f"⚠️  Hooks file provided. Using actual session: {actual_session}"
                            )
                            session_path = actual_session
                        else:
                            print(
                                f"❌ Error: Hooks file references missing session: {transcript_path}"
                            )
                            return 1
                except json.JSONDecodeError:
                    print("❌ Error: Could not parse hooks file")
                    return 1

    # Process the session
    try:
        print(f"📝 Processing session: {session_path}")
        session_summary, entries, agent_entries = processor.parse_session_file(
            str(session_path)
        )

        # Generate output base name
        if args.output:
            output_path = Path(args.output)

            # Check if -o is a directory path
            if output_path.is_dir():
                # Use the directory but auto-generate filename
                output_dir = output_path
            else:
                output_base = args.output
                # Strip .md suffix if provided
                if output_base.endswith(".md"):
                    output_base = output_base[:-3]
                # Strip -full or -abridged suffix if provided
                if output_base.endswith("-full") or output_base.endswith("-abridged"):
                    output_base = output_base.rsplit("-", 1)[0]

                # If output is just a basename (no directory), place in sessions/claude/
                output_path = Path(output_base)
                if not output_path.is_absolute() and output_path.parent == Path("."):
                    base_name = str(sessions_claude / output_base)
                else:
                    base_name = output_base

                # Skip the auto-generation logic below
                print(f"📊 Found {len(entries)} entries")

                # Check for meaningful content
                MIN_MEANINGFUL_ENTRIES = 2
                meaningful_count = sum(
                    1
                    for e in entries
                    if e.type in ("user", "assistant")
                    and not (
                        hasattr(e, "message")
                        and e.message
                        and e.message.get("subtype") in ("system", "informational")
                    )
                )
                if meaningful_count < MIN_MEANINGFUL_ENTRIES:
                    print(
                        f"⏭️  Skipping: only {meaningful_count} meaningful entries (need {MIN_MEANINGFUL_ENTRIES}+)"
                    )
                    return 2

                # Generate transcripts and return
                full_path = Path(f"{base_name}-full.md")
                markdown_full = processor.format_session_as_markdown(
                    session_summary,
                    entries,
                    agent_entries,
                    include_tool_results=True,
                    variant="full",
                    source_file=str(session_path.resolve()),
                )
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(markdown_full)
                format_markdown(full_path)
                file_size = full_path.stat().st_size
                print(f"✅ Full transcript: {full_path} ({file_size:,} bytes)")

                abridged_path = Path(f"{base_name}-abridged.md")
                markdown_abridged = processor.format_session_as_markdown(
                    session_summary,
                    entries,
                    agent_entries,
                    include_tool_results=False,
                    variant="abridged",
                    source_file=str(session_path.resolve()),
                )
                with open(abridged_path, "w", encoding="utf-8") as f:
                    f.write(markdown_abridged)
                format_markdown(abridged_path)
                file_size = abridged_path.stat().st_size
                print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

                return 0
        else:
            output_dir = sessions_claude

        # Auto-generate filename: YYYYMMDD-shortproject-sessionid-slug
        # (Used when -o is a directory or not specified)
        date_str = None
        if session_path.suffix == ".json":
            # Try to get timestamp from filename for Gemini: session-YYYY-MM-DDTHH-MM...
            try:
                parts = session_path.stem.split("-")
                if len(parts) >= 4:
                    # 2026-01-08T08
                    date_part = "".join(parts[1:4])
                    if date_part.isdigit():
                        date_str = date_part
            except Exception:
                pass

        if not date_str:
            for entry in entries:
                if entry.timestamp:
                    date_str = entry.timestamp.strftime("%Y%m%d")
                    break

                if hasattr(entry, "message") and entry.message:
                    ts = entry.message.get("timestamp")
                    if ts:
                        try:
                            date_str = datetime.fromisoformat(
                                ts.replace("Z", "+00:00")
                            ).strftime("%Y%m%d")
                            break
                        except (ValueError, TypeError):
                            continue
        if not date_str:
            date_str = datetime.fromtimestamp(
                session_path.stat().st_mtime
            ).strftime("%Y%m%d")

        # Get short project name
        project = session_path.parent.name
        if session_path.suffix == ".json":
            # Gemini structure: hash/chats/session.json
            # Parent is 'chats', grand-parent is hash.
            if project == "chats":
                hash_dir = session_path.parent.parent.name
                short_project = f"gemini-{hash_dir[:6]}"
            else:
                short_project = "gemini"
        else:
            # e.g., -opt-nic-buttermilk -> buttermilk
            project_parts = project.strip("-").split("-")
            short_project = project_parts[-1] if project_parts else "unknown"

        # Get session ID from filename (first 8 chars of UUID)
        # Gemini filenames might have uuid at end
        session_id = session_path.stem
        if len(session_id) > 8:
            if session_id.startswith("session-"):
                # session-2026-01-08T08-18-a5234d3e -> a5234d3e
                parts = session_id.split("-")
                session_id = parts[-1]
            else:
                session_id = session_id[:8]

        # Get or generate slug
        slug = args.slug if args.slug else processor.generate_session_slug(entries)

        filename = f"{date_str}-{short_project}-{session_id}-{slug}"

        base_name = str(output_dir / filename)
        print(f"📛 Generated filename: {filename}")

        print(f"📊 Found {len(entries)} entries")

        # Check for meaningful content (user prompts or assistant responses)
        # Require at least 2 meaningful entries to be worth transcribing
        MIN_MEANINGFUL_ENTRIES = 2
        meaningful_count = sum(
            1
            for e in entries
            if e.type in ("user", "assistant")
            and not (
                hasattr(e, "message")
                and e.message
                and e.message.get("subtype") in ("system", "informational")
            )
        )
        if meaningful_count < MIN_MEANINGFUL_ENTRIES:
            print(
                f"⏭️  Skipping: only {meaningful_count} meaningful entries (need {MIN_MEANINGFUL_ENTRIES}+)"
            )
            return 2  # Exit 2 = skipped (no content), distinct from 0 (success) and 1 (error)

        # Generate full version
        full_path = Path(f"{base_name}-full.md")
        markdown_full = processor.format_session_as_markdown(
            session_summary,
            entries,
            agent_entries,
            include_tool_results=True,
            variant="full",
            source_file=str(session_path.resolve()),
        )
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(markdown_full)
        format_markdown(full_path)
        file_size = full_path.stat().st_size
        print(f"✅ Full transcript: {full_path} ({file_size:,} bytes)")

        # Generate abridged version
        abridged_path = Path(f"{base_name}-abridged.md")
        markdown_abridged = processor.format_session_as_markdown(
            session_summary,
            entries,
            agent_entries,
            include_tool_results=False,
            variant="abridged",
            source_file=str(session_path.resolve()),
        )
        with open(abridged_path, "w", encoding="utf-8") as f:
            f.write(markdown_abridged)
        format_markdown(abridged_path)
        file_size = abridged_path.stat().st_size
        print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

        return 0

    except Exception as e:
        print(f"❌ Error processing session: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
