"""Batch runner for the session transcript pipeline."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import find_subagent_files, load_claude_session
from transcripts.domain.cache import SkipCache, is_session_empty, source_fingerprint
from transcripts.domain.context import has_user_context
from transcripts.domain.correlation import infer_correlation
from transcripts.domain.insights import infer_insights
from transcripts.domain.ledger import generate_prompt_ledger
from transcripts.domain.renderer import render_session_to_all_formats, render_to_full_markdown
from transcripts.domain.secret_redaction import redact_secrets
from transcripts.domain.slug import get_stable_slug
from transcripts.domain.sync import git_sync_sessions
from transcripts.domain.time import get_event_timestamps
from transcripts.model import NormalizedSession

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("transcripts.runner")


def find_session_files() -> list[Path]:
    """Find all Claude Code and agy session log files.

    Claude Code writes one trunk log per session directly under the project
    directory, and everything below it — subagent sidechains, workflow
    journals — belongs to that session rather than standing alone. Globbing
    deeper would yield sidechain logs that carry the parent's `session_id`,
    and therefore the parent's slug and output filename, so whichever was
    written last would replace the real transcript.
    """
    files: list[Path] = []

    # 1. Claude session files: ~/.claude/projects/<project>/<session-id>.jsonl
    claude_dir = Path.home() / ".claude" / "projects"
    if claude_dir.is_dir():
        for p in claude_dir.glob("*/*.jsonl"):
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


def _is_agy_path(path: Path) -> bool:
    return path.name == "transcript.jsonl" or "brain" in path.parts


def load_session(path: Path) -> NormalizedSession | None:
    """Load a session file using the correct adapter based on path structure."""
    if _is_agy_path(path):
        return load_agy_transcript(path)
    # Assume Claude Code transcript
    return load_claude_session(path)


def session_source_files(path: Path) -> list[Path]:
    """Every file a session rooted at `path` is reconstructed from.

    Resolved without parsing, so the skip-cache can decide whether a session
    is worth loading at all.
    """
    if _is_agy_path(path):
        return [path]
    return [path, *find_subagent_files(path)]


def process_single_session(
    session: NormalizedSession,
    output_dir: Path,
    skip_cache: SkipCache,
    force: bool = False,
    fingerprint: str | None = None,
) -> bool:
    """Process a single NormalizedSession and write outputs."""
    session_id = session.session_id
    if not session_id or session_id == "unknown":
        # Fallback to file stem
        session_id = session.source_file.stem
        session.session_id = session_id

    cache_key = str(session.source_file)
    if fingerprint is None:
        fingerprint = source_fingerprint(session.source_files)

    # Check cache
    if not force and skip_cache.is_skipped(cache_key, fingerprint):
        logger.debug("Skipping session %s via cache", session_id)
        return False

    # Check if empty. The fingerprint is recorded alongside, so the session is
    # re-examined the moment anything is appended to it — a session caught
    # seconds after it started must not be blacklisted for its whole life.
    if is_session_empty(session):
        logger.debug("Session %s is empty, marking in skip cache", session_id)
        skip_cache.mark_empty(cache_key, fingerprint)
        return False

    skip_cache.forget(cache_key)

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

    # Write files. Redaction is applied here, at the single write chokepoint,
    # rather than inside each renderer: these four artifacts are the only
    # things that leave the machine, so scrubbing here means a new renderer
    # cannot accidentally ship an unredacted format. See
    # transcripts/domain/secret_redaction.py for what is scrubbed and why.
    (dest_dir / f"{filename_base}.md").write_text(redact_secrets(md), encoding="utf-8")
    (dest_dir / f"{filename_base}.full.md").write_text(redact_secrets(full_md), encoding="utf-8")
    (dest_dir / f"{filename_base}.html").write_text(redact_secrets(html), encoding="utf-8")
    (dest_dir / f"{filename_base}.json").write_text(redact_secrets(json_sidecar), encoding="utf-8")

    logger.info(
        "Processed session %s -> %s (%d trunk events, %d subagents, %d total events)",
        session_id,
        filename_base,
        len(session.events),
        len(session.subagents),
        session.total_event_count,
    )
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

    # Identify sessions directory. There is no default: the transcripts
    # repository is site-specific, and guessing a path means silently writing
    # session content somewhere the operator did not choose.
    sessions_env = os.environ.get("AOPS_SESSIONS")
    if not sessions_env:
        logger.error(
            "AOPS_SESSIONS is not set. Set it to the sessions repository this host "
            "should publish transcripts to; there is no default."
        )
        return 1
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
            # Fingerprint before parsing: a session known to be empty and
            # unchanged since costs a couple of stat() calls, not a parse.
            fingerprint = source_fingerprint(session_source_files(path))
            if not args.force and skip_cache.is_skipped(str(path), fingerprint):
                logger.debug("Skipping unchanged empty session file %s via cache", path)
                continue

            session = load_session(path)
            if not session:
                # Parsed to nothing. Record it against the same fingerprint so
                # the next run skips it until the file changes.
                logger.debug("No session could be loaded from %s, marking in skip cache", path)
                skip_cache.mark_empty(str(path), fingerprint)
                continue
            if process_single_session(
                session,
                sessions_dir,
                skip_cache,
                force=args.force,
                fingerprint=fingerprint,
            ):
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
