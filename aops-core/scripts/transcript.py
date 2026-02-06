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
from datetime import datetime, timedelta

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.session_reader import find_sessions  # noqa: E402
from lib.transcript_parser import (  # noqa: E402
    SessionProcessor,
    UsageStats,
    decode_claude_project_path,
    extract_reflection_from_entries,
    extract_working_dir_from_content,
    extract_working_dir_from_entries,
    format_reflection_header,
    infer_project_from_working_dir,
    reflection_to_insights,
)
from lib.paths import get_sessions_dir  # noqa: E402
from lib.insights_generator import (  # noqa: E402
    find_existing_insights,
    get_insights_file_path,
    write_insights_file,
    validate_insights_schema,
    InsightsValidationError,
)


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


def _save_minimal_token_summary(
    session_id: str,
    date_str: str,
    project: str,
    slug: str,
    timestamp: datetime | None,
    usage_stats: "UsageStats",
    session_duration_minutes: float | None,
) -> None:
    """Save minimal summary with just token_metrics when no reflection exists.

    This ensures token usage data is captured even for sessions without
    a Framework Reflection output.
    """
    # Generate ISO 8601 timestamp
    if timestamp:
        date_iso = timestamp.isoformat()
    else:
        date_iso = datetime.now().astimezone().replace(microsecond=0).isoformat()

    # Build minimal insights with token_metrics
    insights = {
        "session_id": session_id,
        "date": date_iso,
        "project": project,
        "summary": None,  # No reflection = no summary
        "outcome": None,  # No reflection = unknown outcome
        "accomplishments": [],
        "friction_points": [],
        "proposed_changes": [],
        "token_metrics": usage_stats.to_token_metrics(session_duration_minutes),
    }

    try:
        # Check for existing insights
        existing = find_existing_insights(date_str, session_id)
        if existing:
            print(
                f"⏭️  Insights already exist for session {session_id}: {existing.name}"
            )
            return

        insights_path = get_insights_file_path(
            date_str, session_id, slug, None, project
        )
        write_insights_file(insights_path, insights, session_id=session_id)
        print(f"📊 Token metrics saved (no reflection): {insights_path}")
    except Exception as e:
        print(f"⚠️  Failed to save token metrics: {e}", file=sys.stderr)


def _process_reflection(
    entries: list,
    session_id: str,
    date_str: str,
    project: str,
    slug: str = "",
    agent_entries: dict | None = None,
    timestamp: datetime | None = None,
    usage_stats: "UsageStats | None" = None,
    session_duration_minutes: float | None = None,
) -> tuple[str | None, list[dict] | None]:
    """Extract reflections from entries and save to insights JSON files.

    Args:
        entries: List of parsed session entries
        session_id: 8-char session ID
        date_str: Date in YYYY-MM-DD format
        project: Project name
        slug: Short descriptive slug for the session filename
        agent_entries: Optional dict of agent/subagent entries
        timestamp: Optional datetime for ISO 8601 timestamp in insights
        usage_stats: Optional UsageStats for token_metrics field in insights
        session_duration_minutes: Optional session duration for efficiency metrics

    Returns:
        Tuple of (combined_reflection_header_markdown, list_of_reflection_dicts)
        Both are None if no reflections found
    """
    reflections = extract_reflection_from_entries(entries, agent_entries)
    if not reflections:
        # No reflection found, but still save token_metrics if available
        if usage_stats and usage_stats.has_data():
            _save_minimal_token_summary(
                session_id,
                date_str,
                project,
                slug,
                timestamp,
                usage_stats,
                session_duration_minutes,
            )
        return None, None

    # Collect headers for all reflections
    headers = []
    for i, reflection in enumerate(reflections):
        # Format header for display
        header = format_reflection_header(reflection)
        if len(reflections) > 1:
            header = f"### Reflection {i + 1} of {len(reflections)}\n\n{header}"
        headers.append(header)

        # Convert to insights format and save
        insights = reflection_to_insights(
            reflection,
            session_id,
            date_str,
            project,
            timestamp=timestamp,
            usage_stats=usage_stats,
            session_duration_minutes=session_duration_minutes,
        )

        try:
            validate_insights_schema(insights)
            # Use index for multi-reflection sessions (index > 0 gets suffix)
            idx = i if len(reflections) > 1 else None

            # Check for existing insights (avoid duplicates with different slugs)
            existing = find_existing_insights(date_str, session_id)
            if existing:
                print(
                    f"⏭️  Insights already exist for session {session_id}: {existing.name}"
                )
                continue

            insights_path = get_insights_file_path(
                date_str, session_id, slug, idx, project
            )
            write_insights_file(insights_path, insights, session_id=session_id)
            print(f"💡 Reflection {i + 1}/{len(reflections)} saved to: {insights_path}")
        except InsightsValidationError as e:
            print(f"⚠️  Reflection {i + 1} validation failed: {e}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Failed to save reflection {i + 1}: {e}", file=sys.stderr)

    # Combine headers with separator
    combined_header = "\n\n---\n\n".join(headers)
    return combined_header, reflections


def _is_test_session(p: Path) -> bool:
    """Heuristically detect obvious test/demo sessions to exclude from batch runs.

    Excludes paths under /tmp and filenames or parent folders containing
    keywords like test, demo, scratch, sample, example, tmp, local, dev.
    """
    s = str(p).lower()

    # Whitelist Gemini tmp directory
    if ".gemini/tmp" in s:
        return False

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


def _compute_session_duration(entries: list) -> float | None:
    """Compute session duration in minutes from entry timestamps.

    Args:
        entries: List of parsed session entries

    Returns:
        Duration in minutes, or None if timestamps unavailable
    """
    first_ts = None
    last_ts = None

    for entry in entries:
        if entry.timestamp:
            if first_ts is None:
                first_ts = entry.timestamp
            last_ts = entry.timestamp

    if first_ts and last_ts and first_ts != last_ts:
        delta = last_ts - first_ts
        return delta.total_seconds() / 60.0

    return None


def _output_exists(out_dir: Path, slug: str) -> bool:
    """Check if output files already exist for this session."""
    pattern = f"*{slug}*-full.md"
    return any(out_dir.glob(pattern))


def _filter_recent_sessions(sessions: list, days: int = 7) -> list:
    """Filter sessions to those modified within the last N days.

    Args:
        sessions: List of session objects (with .path attribute) or Path objects
        days: Number of days to look back (default: 7)

    Returns:
        Filtered list of sessions with mtime within the cutoff period
    """
    # Cutoff: midnight N days ago (local timezone)
    cutoff = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=days)
    cutoff_ts = cutoff.timestamp()

    filtered = []
    for s in sessions:
        session_path = s.path if hasattr(s, "path") else Path(str(s))
        if session_path.exists() and session_path.stat().st_mtime >= cutoff_ts:
            filtered.append(s)
    return filtered


def _get_session_id(session_path: Path) -> str:
    """Extract session ID from filename without parsing the file.

    Args:
        session_path: Path to session file

    Returns:
        8-character session ID
    """
    session_id = session_path.stem
    if len(session_id) > 8:
        if session_id.startswith("session-"):
            # Gemini format: session-2026-01-08T08-18-a5234d3e -> a5234d3e
            parts = session_id.split("-")
            session_id = parts[-1]
        else:
            # Claude format: UUID -> first 8 chars
            session_id = session_id[:8]
    return session_id


def _find_existing_transcripts(out_dir: Path, session_id: str) -> list[Path]:
    """Find all existing transcript files by session ID.

    Args:
        out_dir: Output directory to search
        session_id: 8-character session ID

    Returns:
        List of all matching transcript files (both -full.md and -abridged.md)
    """
    # Search for transcripts with this session_id
    # v3.7.0+ Pattern: with hour (e.g., 20260105-17-writing-3bf94f77-session-full.md)
    # Legacy Pattern: without hour (e.g., 20260105-writing-3bf94f77-session-full.md)
    matches = []
    for suffix in ("-full.md", "-abridged.md"):
        # New format with hour
        matches.extend(out_dir.glob(f"*-??-*-{session_id}-*{suffix}"))
        matches.extend(out_dir.glob(f"*-??-*-{session_id}{suffix}"))
        # Legacy format without hour
        matches.extend(out_dir.glob(f"*-{session_id}-*{suffix}"))
        matches.extend(out_dir.glob(f"*-{session_id}{suffix}"))
    return list(set(matches))  # Deduplicate


def _find_existing_transcript(out_dir: Path, session_id: str) -> Path | None:
    """Find existing transcript file by session ID.

    Args:
        out_dir: Output directory to search
        session_id: 8-character session ID

    Returns:
        Path to existing -full.md transcript if found, None otherwise
    """
    matches = [
        p
        for p in _find_existing_transcripts(out_dir, session_id)
        if p.name.endswith("-full.md")
    ]
    return matches[0] if matches else None


def _transcript_is_current(session_path: Path, transcript_path: Path) -> bool:
    """Check if transcript is current (newer than session file).

    Args:
        session_path: Path to source session file
        transcript_path: Path to transcript file

    Returns:
        True if transcript mtime >= session mtime
    """
    return transcript_path.stat().st_mtime >= session_path.stat().st_mtime


def _infer_project(
    session_path: Path,
    entries: list | None = None,
) -> str:
    """Infer project name from session path and/or entries.

    Uses multiple strategies:
    1. For Claude sessions: decode the project folder name (-home-nic-src-myproject)
    2. For Antigravity brain directories: try to extract from content
    3. For Gemini sessions: use hash prefix
    4. Fallback: extract from path or use "unknown"

    Args:
        session_path: Path to session file or directory
        entries: Optional list of parsed session entries for content-based extraction

    Returns:
        Project name string
    """
    # Handle Antigravity brain directories
    if session_path.is_dir():
        # Try to extract working dir from brain content
        if entries:
            working_dir = extract_working_dir_from_entries(entries)
            if working_dir:
                project = infer_project_from_working_dir(working_dir)
                if project:
                    return project

        # Try to extract from markdown content in the brain directory
        for md_file in ["task.md", "implementation_plan.md"]:
            md_path = session_path / md_file
            if md_path.exists():
                try:
                    content = md_path.read_text(encoding="utf-8")
                    working_dir = extract_working_dir_from_content(content)
                    if working_dir:
                        project = infer_project_from_working_dir(working_dir)
                        if project:
                            return project
                except OSError:
                    continue

        return "antigravity"  # Default for brain directories

    # Handle Gemini JSON sessions
    if session_path.suffix == ".json":
        project = session_path.parent.name
        if project == "chats":
            hash_dir = session_path.parent.parent.name
            return f"gemini-{hash_dir[:6]}"
        return "gemini"

    # Handle Claude JSONL sessions
    project = session_path.parent.name

    # Try to extract project from entries first
    if entries:
        working_dir = extract_working_dir_from_entries(entries)
        if working_dir:
            inferred = infer_project_from_working_dir(working_dir)
            if inferred:
                return inferred

    # Decode Claude project path format: -home-nic-src-myproject
    if project.startswith("-"):
        decoded = decode_claude_project_path(project)
        if decoded:
            inferred = infer_project_from_working_dir(decoded)
            if inferred:
                return inferred

    # Fallback: extract last segment
    project_parts = project.strip("-").split("-")
    return project_parts[-1] if project_parts else "unknown"


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
  python transcript.py                                  # Process recent sessions (last 7 days, default)
  python transcript.py --all                            # Process ALL sessions in ~/.claude/projects/
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
        "--recent",
        action="store_true",
        default=True,
        help="Process sessions from last 7 days (default behavior)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process ALL sessions (overrides --recent filter)",
    )

    args = parser.parse_args()

    # Default output directory
    sessions_claude = get_sessions_dir() / "claude"
    sessions_claude.mkdir(parents=True, exist_ok=True)

    processor = SessionProcessor()

    # Batch mode: process sessions (default when no file specified)
    # --recent (default): last 7 days only
    # --all: all sessions regardless of date
    if args.all or not args.session_file:
        sessions = find_sessions()
        if not sessions:
            print("No sessions found.", file=sys.stderr)
            return 0

        # Exclude obvious test/demo sessions
        sessions = [
            s
            for s in sessions
            if not _is_test_session(s.path if hasattr(s, "path") else Path(str(s)))
        ]

        # Apply --recent filter (default) unless --all specified
        if not args.all:
            original_count = len(sessions)
            sessions = _filter_recent_sessions(sessions, days=7)
            print(
                f"📅 Filtering to last 7 days: {len(sessions)} of {original_count} sessions"
            )

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

                # Early mtime check: skip if transcript already exists and is current
                session_id = _get_session_id(session_path)
                existing_transcript = _find_existing_transcript(
                    sessions_claude, session_id
                )
                if existing_transcript and _transcript_is_current(
                    session_path, existing_transcript
                ):
                    skipped += 1
                    continue

                # Delete stale transcripts before regenerating (prevents duplicates
                # when filename format changes, e.g., slug added/changed)
                if existing_transcript:
                    stale_files = _find_existing_transcripts(
                        sessions_claude, session_id
                    )
                    for stale in stale_files:
                        print(f"🗑️  Removing stale transcript: {stale.name}")
                        stale.unlink()

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

                # Generate output name with date and hour for better sorting
                date_str = None
                hour_str = None
                for entry in entries:
                    if entry.timestamp:
                        date_str = entry.timestamp.strftime("%Y%m%d")
                        hour_str = entry.timestamp.strftime("%H")
                        break
                if not date_str:
                    mtime = datetime.fromtimestamp(session_path.stat().st_mtime)
                    date_str = mtime.strftime("%Y%m%d")
                    hour_str = mtime.strftime("%H")

                # Get short project name (using entries for working dir extraction)
                short_project = _infer_project(session_path, entries)

                # Get session ID
                if session_path.is_dir():
                    # Antigravity brain directory - use directory name
                    session_id = session_path.name[:8]
                else:
                    session_id = session_path.stem
                    if len(session_id) > 8:
                        if session_id.startswith("session-"):
                            parts = session_id.split("-")
                            session_id = parts[-1]
                        else:
                            session_id = session_id[:8]

                # Get slug
                slug = processor.generate_session_slug(entries)
                filename = f"{date_str}-{hour_str}-{short_project}-{session_id}-{slug}"

                # Note: _output_exists() check removed - early mtime check handles
                # both "already current" (skip) and "stale" (regenerate) cases

                base_name = str(sessions_claude / filename)

                # Extract and process reflection (if present)
                # Convert date format from YYYYMMDD to YYYY-MM-DD for insights
                date_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                # Get timestamp from entries for ISO 8601 output
                session_timestamp = None
                for entry in entries:
                    if entry.timestamp:
                        session_timestamp = entry.timestamp
                        break

                # Compute usage stats and session duration for token_metrics
                usage_stats = processor._aggregate_session_usage(entries, agent_entries)
                session_duration_minutes = _compute_session_duration(entries)

                reflection_header, _ = _process_reflection(
                    entries,
                    session_id,
                    date_iso,
                    short_project,
                    slug,
                    agent_entries,
                    session_timestamp,
                    usage_stats,
                    session_duration_minutes,
                )

                # Generate full version
                full_path = Path(f"{base_name}-full.md")
                markdown_full = processor.format_session_as_markdown(
                    session_summary,
                    entries,
                    agent_entries,
                    include_tool_results=True,
                    variant="full",
                    source_file=str(session_path.resolve()),
                    reflection_header=reflection_header,
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
                    reflection_header=reflection_header,
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

    # Single session mode (specific file provided)
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
        output_dir = None
        base_name = None

        if args.output:
            output_path = Path(args.output)

            # Check if -o is a directory path
            if output_path.is_dir():
                # Use the directory but auto-generate filename
                output_dir = output_path
                # Will fall through to auto-generation logic below
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

        # If base_name was set (explicit output file specified), use explicit path logic
        if base_name:
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

            # Extract reflection (get date and project from path for insights)
            date_iso = datetime.now().astimezone().replace(microsecond=0).isoformat()
            session_timestamp = None
            for entry in entries:
                if entry.timestamp:
                    date_iso = entry.timestamp.strftime("%Y-%m-%d")
                    session_timestamp = entry.timestamp
                    break
            # Get session ID from path
            sid = session_path.stem[:8]
            proj = (
                session_path.parent.name.split("-")[-1]
                if session_path.parent.name
                else "unknown"
            )
            slug = processor.generate_session_slug(entries)

            # Compute usage stats and session duration for token_metrics
            usage_stats = processor._aggregate_session_usage(entries, agent_entries)
            session_duration_minutes = _compute_session_duration(entries)

            reflection_header, _ = _process_reflection(
                entries,
                sid,
                date_iso,
                proj,
                slug,
                agent_entries,
                session_timestamp,
                usage_stats,
                session_duration_minutes,
            )

            # Generate transcripts and return
            full_path = Path(f"{base_name}-full.md")
            markdown_full = processor.format_session_as_markdown(
                session_summary,
                entries,
                agent_entries,
                include_tool_results=True,
                variant="full",
                source_file=str(session_path.resolve()),
                reflection_header=reflection_header,
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
                reflection_header=reflection_header,
            )
            with open(abridged_path, "w", encoding="utf-8") as f:
                f.write(markdown_abridged)
            format_markdown(abridged_path)
            file_size = abridged_path.stat().st_size
            print(f"✅ Abridged transcript: {abridged_path} ({file_size:,} bytes)")

            return 0

        # If output_dir not set yet (no -o specified), use default
        if not output_dir:
            output_dir = sessions_claude

        # Auto-generate filename: YYYYMMDD-HH-shortproject-sessionid-slug
        # (Used when -o is a directory or not specified)
        date_str = None
        hour_str = None
        if session_path.suffix == ".json":
            # Try to get timestamp from filename for Gemini: session-YYYY-MM-DDTHH-MM...
            try:
                parts = session_path.stem.split("-")
                if len(parts) >= 4:
                    # 2026-01-08T08
                    date_part = "".join(parts[1:4])
                    if date_part.isdigit():
                        date_str = date_part
                    # Extract hour from Gemini filename format
                    if len(parts) >= 5 and parts[4][:2].isdigit():
                        hour_str = parts[4][:2]
            except Exception:
                pass

        if not date_str:
            for entry in entries:
                if entry.timestamp:
                    date_str = entry.timestamp.strftime("%Y%m%d")
                    hour_str = entry.timestamp.strftime("%H")
                    break

                if hasattr(entry, "message") and entry.message:
                    ts = entry.message.get("timestamp")
                    if ts:
                        try:
                            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            date_str = parsed.strftime("%Y%m%d")
                            hour_str = parsed.strftime("%H")
                            break
                        except (ValueError, TypeError):
                            continue
        if not date_str:
            mtime = datetime.fromtimestamp(session_path.stat().st_mtime)
            date_str = mtime.strftime("%Y%m%d")
            hour_str = mtime.strftime("%H")
        if not hour_str:
            hour_str = datetime.now().astimezone().strftime("%H")

        # Get short project name (using entries for working dir extraction)
        short_project = _infer_project(session_path, entries)

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

        filename = f"{date_str}-{hour_str}-{short_project}-{session_id}-{slug}"

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

        # Extract and process reflection (if present)
        # Convert date format from YYYYMMDD to YYYY-MM-DD for insights
        date_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        # Get timestamp from entries for ISO 8601 output
        session_timestamp = None
        for entry in entries:
            if entry.timestamp:
                session_timestamp = entry.timestamp
                break

        # Compute usage stats and session duration for token_metrics
        usage_stats = processor._aggregate_session_usage(entries, agent_entries)
        session_duration_minutes = _compute_session_duration(entries)

        reflection_header, _ = _process_reflection(
            entries,
            session_id,
            date_iso,
            short_project,
            slug,
            agent_entries,
            session_timestamp,
            usage_stats,
            session_duration_minutes,
        )

        # Generate full version
        full_path = Path(f"{base_name}-full.md")
        markdown_full = processor.format_session_as_markdown(
            session_summary,
            entries,
            agent_entries,
            include_tool_results=True,
            variant="full",
            source_file=str(session_path.resolve()),
            reflection_header=reflection_header,
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
            reflection_header=reflection_header,
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
