"""Tests for the skip-cache's invalidation behaviour.

The five-minute cron reaches a new session seconds after it starts, when it is
still legitimately empty. A cache that records only "this session was empty"
blacklists it for the rest of its life: it is parsed and discarded on every
subsequent run no matter how much work it accumulates. The cache must record
what the source looked like when it rendered to nothing, so any change to it
brings the session back — while a finished, genuinely empty session stays
skipped for free.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from transcripts import runner
from transcripts.domain.cache import SkipCache, is_session_empty, source_fingerprint
from transcripts.model import NormalizedEvent, NormalizedSession

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"
SUBAGENT_FIXTURE = FIXTURES_DIR / "claude_subagent.jsonl"

PARENT_SESSION_ID = "19cb8a50-7d62-4936-aef9-6861ad8967a4"


def _touch_later(path: Path) -> None:
    """Advance a file's mtime past the resolution of any earlier stat()."""
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns + 2_000_000_000, stat.st_mtime_ns + 2_000_000_000))


def _session(source: Path, *, empty: bool) -> NormalizedSession:
    events = (
        []
        if empty
        else [
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-07-05T06:45:18Z",
                source="user",
                type="message",
                content="Now there is something to say.",
            )
        ]
    )
    return NormalizedSession(session_id=PARENT_SESSION_ID, source_file=source, events=events)


# --- Fingerprint invalidation -------------------------------------------------


def test_growing_source_file_invalidates_the_entry(tmp_path: Path) -> None:
    source = tmp_path / "session.jsonl"
    source.write_text("", encoding="utf-8")
    cache = SkipCache(tmp_path / "cache.json")
    key = str(source)

    cache.mark_empty(key, source_fingerprint([source]))
    assert cache.is_skipped(key, source_fingerprint([source]))

    source.write_text('{"type": "user"}\n', encoding="utf-8")
    assert not cache.is_skipped(key, source_fingerprint([source]))


def test_touched_source_file_invalidates_the_entry(tmp_path: Path) -> None:
    """Same size, newer mtime — a rewritten file must still be re-examined."""
    source = tmp_path / "session.jsonl"
    source.write_text("aaaa", encoding="utf-8")
    cache = SkipCache(tmp_path / "cache.json")
    key = str(source)

    cache.mark_empty(key, source_fingerprint([source]))
    source.write_text("bbbb", encoding="utf-8")
    _touch_later(source)

    assert not cache.is_skipped(key, source_fingerprint([source]))


def test_new_subagent_file_invalidates_the_entry(tmp_path: Path) -> None:
    """Work that happens entirely in a subagent must un-skip the session."""
    trunk = tmp_path / f"{PARENT_SESSION_ID}.jsonl"
    trunk.write_text("", encoding="utf-8")
    subagents = tmp_path / PARENT_SESSION_ID / "subagents"
    subagents.mkdir(parents=True)

    cache = SkipCache(tmp_path / "cache.json")
    key = str(trunk)
    cache.mark_empty(key, source_fingerprint(runner.session_source_files(trunk)))
    assert cache.is_skipped(key, source_fingerprint(runner.session_source_files(trunk)))

    shutil.copy(SUBAGENT_FIXTURE, subagents / "agent-a270f5ac9ef8b3a95.jsonl")

    assert not cache.is_skipped(key, source_fingerprint(runner.session_source_files(trunk)))


def test_unchanged_empty_session_stays_skipped(tmp_path: Path) -> None:
    """The cache's legitimate purpose: a finished, empty session costs nothing."""
    source = tmp_path / "session.jsonl"
    source.write_text("", encoding="utf-8")
    cache_file = tmp_path / "cache.json"
    key = str(source)

    SkipCache(cache_file).mark_empty(key, source_fingerprint([source]))

    # A later run, fresh process, same untouched file.
    assert SkipCache(cache_file).is_skipped(key, source_fingerprint([source]))


def test_legacy_cache_without_fingerprints_is_discarded(tmp_path: Path) -> None:
    """A cache written before fingerprints cannot prove anything; re-examine instead."""
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps([PARENT_SESSION_ID]), encoding="utf-8")
    source = tmp_path / "session.jsonl"
    source.write_text("", encoding="utf-8")

    cache = SkipCache(cache_file)

    assert cache.empty_sessions == {}
    assert not cache.is_skipped(PARENT_SESSION_ID, source_fingerprint([source]))


# --- End-to-end through the runner --------------------------------------------


def test_session_cached_while_empty_is_reprocessed_once_it_has_content(tmp_path: Path) -> None:
    """The reported failure, start to finish.

    A session is caught seconds after it starts, cached as empty, then grows.
    The next run must publish it rather than skipping it forever.
    """
    source = tmp_path / f"{PARENT_SESSION_ID}.jsonl"
    source.write_text("", encoding="utf-8")
    output_dir = tmp_path / "sessions"
    cache = SkipCache(tmp_path / "cache.json")

    # Run 1: caught while still empty.
    assert not runner.process_single_session(_session(source, empty=True), output_dir, cache)
    assert cache.empty_sessions

    # Run 2: nothing has changed, so it is still skipped — the cache still works.
    assert not runner.process_single_session(_session(source, empty=True), output_dir, cache)

    # The session accumulates real content.
    shutil.copy(CLAUDE_FIXTURE, source)

    # Run 3: the source changed, so it is re-examined and published.
    assert runner.process_single_session(_session(source, empty=False), output_dir, cache)
    assert list(output_dir.glob("transcripts/**/*.md"))
    # A processed session must not be left behind in the cache.
    assert str(source) not in cache.empty_sessions


def test_batch_run_skips_unchanged_empty_files_without_parsing(tmp_path: Path, monkeypatch) -> None:
    """The pre-parse check is the point: an unchanged empty session costs stats, not a parse."""
    home = tmp_path / "home"
    claude_projects = home / ".claude" / "projects" / "-home-user-src-aops"
    claude_projects.mkdir(parents=True)
    source = claude_projects / f"{PARENT_SESSION_ID}.jsonl"
    source.write_text("", encoding="utf-8")

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))
    monkeypatch.setattr(runner.sys, "argv", ["transcripts.runner", "--all", "--no-sync"])

    loads: list[Path] = []
    real_load = runner.load_session

    def counting_load(path: Path):
        loads.append(path)
        return real_load(path)

    monkeypatch.setattr(runner, "load_session", counting_load)

    assert runner.main() == 0
    assert loads == [source], "first run must parse the file to discover it is empty"

    loads.clear()
    assert runner.main() == 0
    assert loads == [], "unchanged empty session was parsed again"


# --- Emptiness accounts for delegated work ------------------------------------


def test_session_with_only_subagent_activity_is_not_empty(tmp_path: Path) -> None:
    from transcripts.adapters.claude import load_subagent_transcripts

    trunk = tmp_path / f"{PARENT_SESSION_ID}.jsonl"
    trunk.write_text("", encoding="utf-8")
    subagents = tmp_path / PARENT_SESSION_ID / "subagents"
    subagents.mkdir(parents=True)
    shutil.copy(SUBAGENT_FIXTURE, subagents / "agent-a270f5ac9ef8b3a95.jsonl")

    session = NormalizedSession(session_id=PARENT_SESSION_ID, source_file=trunk)
    assert is_session_empty(session)

    session.subagents = load_subagent_transcripts(trunk, session.events)
    assert session.subagents
    assert not is_session_empty(session)


# --- No baked sessions path ---------------------------------------------------


def test_missing_aops_sessions_fails_loudly(tmp_path: Path, monkeypatch, caplog) -> None:
    """A shipped artifact carries no default path; absence must be an error, not a guess."""
    monkeypatch.delenv("AOPS_SESSIONS", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / "src" / "sessions").mkdir(parents=True)
    monkeypatch.setattr(runner.sys, "argv", ["transcripts.runner", "--no-sync"])

    with caplog.at_level("ERROR"):
        assert runner.main() == 1

    assert "AOPS_SESSIONS" in caplog.text
    # Nothing may have been written to the path that used to be guessed.
    assert not list((tmp_path / "src" / "sessions").iterdir())
