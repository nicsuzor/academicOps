#!/usr/bin/env python3
"""
Session Transcript Generator

Converts Claude Code JSONL and Gemini JSON session files to readable markdown transcripts.

Usage:
    uv run python $AOPS/scripts/session_transcript.py session.jsonl
    uv run python $AOPS/scripts/session_transcript.py session.jsonl -o output.md
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Add framework root to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.session_reader import SessionProcessor  # noqa: E402
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


def generate_slug(entries: list, max_words: int = 3) -> str:
    """Generate a brief slug from the first substantive user message.

    Args:
        entries: List of Entry dataclass objects from SessionProcessor
        max_words: Maximum words in slug (default 3)

    Returns:
        Kebab-case slug like 'session-storage-fix' or 'transcript-update'
    """
    # Find first user message that isn't a command or tool result
    for entry in entries:
        entry_type = entry.type if hasattr(entry, "type") else entry.get("type", "")
        if entry_type == "user":
            # Get content from message dict or content dict
            if hasattr(entry, "message") and entry.message:
                content = entry.message.get("content", "")
                # Handle content that might be a list (tool results)
                if isinstance(content, list):
                    continue
            elif hasattr(entry, "content"):
                content = str(entry.content)
            else:
                content = entry.get("content", "") if isinstance(entry, dict) else ""
            # Skip command invocations, tool results, system messages, and empty tags
            if (
                content.startswith("<command")
                or content.startswith("[{")
                or content.startswith("Caveat:")
                or content.startswith("<local-command")
                or content.startswith("<system")
            ):
                continue
            # Skip very short messages
            if len(content) < 10:
                continue

            # Extract meaningful words (skip common words)
            stop_words = {
                "the",
                "a",
                "an",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "to",
                "of",
                "and",
                "in",
                "that",
                "have",
                "i",
                "it",
                "for",
                "not",
                "on",
                "with",
                "he",
                "as",
                "you",
                "do",
                "at",
                "this",
                "but",
                "his",
                "by",
                "from",
                "they",
                "we",
                "say",
                "her",
                "she",
                "or",
                "will",
                "my",
                "one",
                "all",
                "would",
                "there",
                "their",
                "what",
                "so",
                "up",
                "out",
                "if",
                "about",
                "who",
                "get",
                "which",
                "go",
                "me",
                "when",
                "make",
                "can",
                "like",
                "time",
                "no",
                "just",
                "him",
                "know",
                "take",
                "people",
                "into",
                "year",
                "your",
                "good",
                "some",
                "could",
                "them",
                "see",
                "other",
                "than",
                "then",
                "now",
                "look",
                "only",
                "come",
                "its",
                "over",
                "think",
                "also",
                "back",
                "after",
                "use",
                "two",
                "how",
                "our",
                "work",
                "first",
                "well",
                "way",
                "even",
                "new",
                "want",
                "because",
                "any",
                "these",
                "give",
                "day",
                "most",
                "us",
                "please",
                "help",
                "let",
                "need",
                "should",
            }

            # Clean and tokenize
            words = re.findall(r"[a-zA-Z]+", content.lower())
            meaningful = [w for w in words if w not in stop_words and len(w) > 2]

            if meaningful:
                slug_words = meaningful[:max_words]
                return "-".join(slug_words)

    return "session"


def main():
    parser = argparse.ArgumentParser(
        description="Convert Claude Code JSONL or Gemini JSON sessions to markdown transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python session_transcript.py session.jsonl                    # Auto-names in $ACA_DATA/sessions/claude/
  python session_transcript.py session.json                     # Generates Gemini transcript
  python session_transcript.py session.jsonl -o transcript      # Uses $ACA_DATA/sessions/claude/transcript-{full,abridged}.md
  python session_transcript.py session.jsonl -o /abs/path/name  # Uses absolute path
        """,
    )

    parser.add_argument(
        "session_file", help="Path to Session file (Claude .jsonl or Gemini .json)"
    )
    parser.add_argument(
        "-o", "--output", help="Output base name (generates -full.md and -abridged.md)"
    )
    parser.add_argument(
        "--slug",
        help="Brief slug describing session work (auto-generated if not provided)",
    )

    args = parser.parse_args()

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
    processor = SessionProcessor()

    try:
        print(f"📝 Processing session: {session_path}")
        session_summary, entries, agent_entries = processor.parse_session_file(
            str(session_path)
        )

        # Generate output base name
        if args.output:
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
                sessions_claude = get_sessions_dir() / "claude"
                sessions_claude.mkdir(parents=True, exist_ok=True)
                base_name = str(sessions_claude / output_base)
            else:
                base_name = output_base
        else:
            # Auto-generate name: YYYYMMDD-shortproject-sessionid-slug
            from datetime import datetime

            # Get date from first entry timestamp or file mtime
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
            slug = args.slug if args.slug else generate_slug(entries)

            filename = f"{date_str}-{short_project}-{session_id}-{slug}"

            # Place in sessions/claude/ directory
            sessions_claude = get_sessions_dir() / "claude"
            sessions_claude.mkdir(parents=True, exist_ok=True)
            base_name = str(sessions_claude / filename)
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
