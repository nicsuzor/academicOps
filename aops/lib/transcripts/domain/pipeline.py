import time
from pathlib import Path

from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import load_claude_transcript, normalize_claude_transcript
from transcripts.domain.cache import SkipCache
from transcripts.domain.renderer import render_html, render_json_sidecar, render_markdown
from transcripts.domain.slug import get_session_slug
from transcripts.domain.sync import git_sync
from transcripts.domain.timestamps import get_session_timestamps
from transcripts.model import NormalizedSession


def find_raw_sessions(
    claude_base: Path, agy_base: Path, recent_only: bool = False
) -> list[tuple[Path, str]]:
    """Find all raw session transcript files.

    Returns a list of (file_path, source_type) where source_type is 'claude' or 'agy'.
    """
    sessions = []

    # 1. Claude Code sessions
    if claude_base.exists():
        for proj_dir in claude_base.iterdir():
            if not proj_dir.is_dir() or proj_dir.name.endswith("-hooks"):
                continue
            for session_file in proj_dir.glob("*.jsonl"):
                if session_file.name.startswith("agent-") or session_file.name.endswith(
                    "-hooks.jsonl"
                ):
                    continue
                sessions.append((session_file, "claude"))

    # 2. agy sessions
    if agy_base.exists():
        for brain_dir in agy_base.iterdir():
            if not brain_dir.is_dir():
                continue
            logs_dir = brain_dir / ".system_generated" / "logs"
            t_file = logs_dir / "transcript.jsonl"
            if t_file.exists():
                sessions.append((t_file, "agy"))
            else:
                t_full = logs_dir / "transcript_full.jsonl"
                if t_full.exists():
                    sessions.append((t_full, "agy"))

    # Filter by mtime if recent_only is True
    if recent_only:
        now = time.time()
        # Lookback 48 hours to be safe for cron runs
        cutoff = now - 48 * 3600
        sessions = [(path, src) for path, src in sessions if path.stat().st_mtime >= cutoff]

    return sessions


def is_session_empty(session: NormalizedSession) -> bool:
    """A session is empty if it contains no meaningful user, model, or tool events."""
    meaningful = [e for e in session.events if e.source in {"user", "model", "tool"}]
    return len(meaningful) == 0


def run_batch_pipeline(sessions_repo_path: Path, recent_only: bool = False) -> int:
    """Run the batch transcript generation and sync pipeline.

    Returns the number of sessions successfully processed.
    """
    claude_base = Path.home() / ".claude" / "projects"
    agy_base = Path.home() / ".gemini" / "antigravity-cli" / "brain"

    # Also support secondary agy path just in case
    if not agy_base.exists():
        agy_base = Path.home() / ".gemini" / "antigravity" / "brain"

    cache_path = sessions_repo_path / ".skip-cache.json"
    cache = SkipCache(cache_path)

    raw_sessions = find_raw_sessions(claude_base, agy_base, recent_only)
    processed_count = 0

    for path, source_type in raw_sessions:
        # Resolve a temporary session_id for skip-cache check
        # (stable slug deterministic from session_id check runs first)
        temp_session_id = "unknown"
        if source_type == "agy":
            # agy structure: brain/<full-uuid>/.system_generated/logs/transcript.jsonl
            # session_id is the directory name of the brain/
            for i, part in enumerate(path.parts):
                if part == ".system_generated" and i > 0:
                    temp_session_id = path.parts[i - 1]
                    break
            if temp_session_id == "unknown":
                temp_session_id = path.stem
        else:
            # claude session_id will be parsed from the file content.
            # We can check cache after loading it.
            pass

        if source_type == "agy" and cache.is_empty(temp_session_id):
            continue

        # Load and normalize session
        try:
            if source_type == "claude":
                claude_transcript = load_claude_transcript(path)
                session = normalize_claude_transcript(claude_transcript)
            else:
                session = load_agy_transcript(path)
        except Exception as e:
            print(f"Error loading session {path}: {e}")
            continue

        if not session.session_id or session.session_id == "unknown":
            continue

        # Check cache now that we have real session_id
        if cache.is_empty(session.session_id):
            continue

        # Check if the session is empty
        if is_session_empty(session):
            cache.mark_empty(session.session_id)
            continue

        # If it was marked empty but now has content, unmark it
        cache.unmark_empty(session.session_id)

        # Generate outputs
        started_at, _, _ = get_session_timestamps(session)
        # Determine year-month directory
        ym_dir = "unknown-date"
        if started_at:
            # format: YYYY-MM
            ym_dir = started_at[:7]

        out_dir = sessions_repo_path / "transcripts" / ym_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        slug = get_session_slug(session.session_id)

        # Write 3 formats
        try:
            md_path = out_dir / f"session-{slug}.md"
            html_path = out_dir / f"session-{slug}.html"
            json_path = out_dir / f"session-{slug}.json"

            md_path.write_text(render_markdown(session), encoding="utf-8")
            html_path.write_text(render_html(session), encoding="utf-8")
            json_path.write_text(render_json_sidecar(session), encoding="utf-8")

            processed_count += 1
        except Exception as e:
            print(f"Error writing outputs for session {session.session_id}: {e}")

    # Sync the repository
    git_sync(sessions_repo_path)

    return processed_count
