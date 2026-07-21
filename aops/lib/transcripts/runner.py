"""Batch runner for the session transcript pipeline."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import load_claude_transcript, normalize_claude_transcript
from transcripts.domain.cache import SkipCache, is_session_empty
from transcripts.domain.context import has_user_context
from transcripts.domain.correlation import infer_correlation
from transcripts.domain.insights import infer_insights
from transcripts.domain.ledger import generate_prompt_ledger
from transcripts.domain.renderer import render_session_to_all_formats, render_to_full_markdown
from transcripts.domain.slug import get_stable_slug
from transcripts.domain.sync import git_sync_sessions
from transcripts.domain.time import get_event_timestamps
from transcripts.model import NormalizedSession

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("transcripts.runner")


def find_session_files() -> list[Path]:
    """Find all Claude Code and agy session log files."""
    files: list[Path] = []

    # 1. Claude session files: ~/.claude/projects/**/*.jsonl
    claude_dir = Path.home() / ".claude" / "projects"
    if claude_dir.is_dir():
        for p in claude_dir.glob("**/*.jsonl"):
            if p.is_file() and not p.name.endswith("-hooks.jsonl"):
                files.append(p)

    # 2. agy session files: ~/.gemini/antigravity-cli/brain/**/transcript.jsonl
    # and ~/.gemini/tmp/workspace/agy-brain/**/transcript.jsonl
    agy_dirs = [
        Path.home() / ".gemini" / "antigravity-cli" / "brain",
        Path.home() / ".gemini" / "tmp" / "workspace" / "agy-brain",
    ]
    for d in agy_dirs:
        if d.is_dir():
            for p in d.glob("**/transcript.jsonl"):
                if p.is_file():
                    files.append(p)

    # De-duplicate files
    unique_files = list(set(files))
    return sorted(unique_files, key=lambda x: x.stat().st_mtime, reverse=True)


def load_session(path: Path) -> NormalizedSession | None:
    """Load a session file using the correct adapter based on path structure."""
    if path.name == "transcript.jsonl" or "brain" in path.parts:
        return load_agy_transcript(path)
    else:
        # Assume Claude Code transcript
        claude_t = load_claude_transcript(path)
        if not claude_t.entries and not claude_t.raw_entries:
            return None
        return normalize_claude_transcript(claude_t)


def process_single_session(
    session: NormalizedSession,
    output_dir: Path,
    skip_cache: SkipCache,
    force: bool = False,
) -> bool:
    """Process a single NormalizedSession and write outputs."""
    session_id = session.session_id
    if not session_id or session_id == "unknown":
        # Fallback to file stem
        session_id = session.source_file.stem
        session.session_id = session_id

    # Check cache
    if not force and skip_cache.is_skipped(session_id):
        logger.debug("Skipping session %s via cache", session_id)
        return False

    # Check if empty
    if is_session_empty(session):
        logger.debug("Session %s is empty, marking in skip cache", session_id)
        skip_cache.mark_empty(session_id)
        return False

    # Extract domain attributes
    slug = get_stable_slug(session_id)
    started_at, last_modified, ended_at = get_event_timestamps(session.events)
    has_user = has_user_context(session)
    correlation = infer_correlation(session)
    insights = infer_insights(session)

    # Format filename: YYYYMMDD-HH-project-slug
    try:
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(UTC)

    date_str = dt.strftime("%Y%m%d")
    hour_str = dt.strftime("%H")
    project = correlation.get("project") or "adhoc"
    filename_base = f"{date_str}-{hour_str}-{project}-{slug}"

    # Determine YYYY-MM directory
    year_month = dt.strftime("%Y-%m")
    dest_dir = output_dir / "transcripts" / year_month
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Render all outputs
    md, html, json_sidecar = render_session_to_all_formats(
        session, slug, started_at, last_modified, ended_at, has_user, correlation, insights
    )
    full_md = render_to_full_markdown(
        session, slug, started_at, last_modified, ended_at, has_user, correlation, insights
    )

    # Write files
    (dest_dir / f"{filename_base}.md").write_text(md, encoding="utf-8")
    (dest_dir / f"{filename_base}.full.md").write_text(full_md, encoding="utf-8")
    (dest_dir / f"{filename_base}.html").write_text(html, encoding="utf-8")
    (dest_dir / f"{filename_base}.json").write_text(json_sidecar, encoding="utf-8")

    logger.info("Processed session %s -> %s", session_id, filename_base)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="AcademicOps transcript pipeline batch runner")
    parser.add_argument(
        "session_file", nargs="?", type=str, help="Path to single session file to process"
    )
    parser.add_argument("-o", "--output", type=str, help="Override output directory or file name")
    parser.add_argument(
        "--recent", action="store_true", help="Only process recent sessions (last 7 days)"
    )
    parser.add_argument("--all", action="store_true", help="Process all sessions")
    parser.add_argument(
        "--force", action="store_true", help="Force reprocessing (ignore skip cache)"
    )
    parser.add_argument("--no-sync", action="store_true", help="Skip git push / sync")
    parser.add_argument("--ledger", action="store_true", help="Generate prompt ledger only")
    parser.add_argument("--since", type=str, help="Since YYYY-MM-DD for prompt ledger")
    args = parser.parse_args()

    # Identify sessions directory
    sessions_env = os.environ.get("AOPS_SESSIONS")
    if not sessions_env:
        # Fallback to default ~/src/sessions
        default_sessions = Path.home() / "src" / "sessions"
        if default_sessions.is_dir():
            sessions_dir = default_sessions
        else:
            logger.error("AOPS_SESSIONS environment variable must be set")
            return 1
    else:
        sessions_dir = Path(sessions_env)

    if args.ledger:
        return generate_prompt_ledger(sessions_dir, args.since)

    # Setup skip-cache
    cache_path = sessions_dir / ".transcripts_skip_cache.json"
    skip_cache = SkipCache(cache_path)

    # Process single file mode
    if args.session_file:
        file_path = Path(args.session_file)
        if not file_path.is_file():
            logger.error("Session file not found: %s", file_path)
            return 1

        session = load_session(file_path)
        if not session:
            logger.error("Failed to load session from %s", file_path)
            return 1

        out_dir = Path(args.output) if args.output else sessions_dir
        process_single_session(session, out_dir, skip_cache, force=True)
        return 0

    # Batch processing mode
    session_files = find_session_files()
    if not session_files:
        logger.info("No session files found to process")
        return 0

    # Filter recent if requested (default to last 7 days unless --all is set)
    if args.recent or not args.all:
        cutoff = datetime.now(UTC).timestamp() - (7 * 24 * 3600)
        session_files = [f for f in session_files if f.stat().st_mtime >= cutoff]

    processed_count = 0
    for path in session_files:
        try:
            session = load_session(path)
            if not session:
                continue
            if process_single_session(session, sessions_dir, skip_cache, force=args.force):
                processed_count += 1
        except Exception:
            logger.exception("Failed to process session file %s", path)

    logger.info("Batch run complete. Processed %d sessions.", processed_count)

    # Git sync
    if not args.no_sync:
        git_sync_sessions(sessions_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
