from pathlib import Path

from transcripts.domain.cache import SkipCache
from transcripts.domain.classification import has_user_context
from transcripts.domain.selection import select_recent_interactive_sessions
from transcripts.domain.slug import get_session_slug
from transcripts.domain.timestamps import get_session_timestamps
from transcripts.model import NormalizedEvent, NormalizedSession


# 1. Stable Slug Test
def test_stable_slug_invariant() -> None:
    session_id = "test-session-12345"
    slug_1 = get_session_slug(session_id)
    slug_2 = get_session_slug(session_id)

    # same id -> same slug
    assert slug_1 == slug_2
    assert slug_1 == "test-session-12345"

    # Empty/weird characters -> stable safe fallback
    assert get_session_slug("test!@#$session") == "testsession"


# 2. Semantic has_user_context Test
def test_semantic_user_context_classification() -> None:
    # Automated / cron session with human words (contains <USER_REQUEST> XML or external userType)
    automated_event = NormalizedEvent(
        event_id="e1",
        timestamp="2026-07-20T10:00:00Z",
        source="user",
        type="message",
        content="<USER_REQUEST>\nPlease run the test suite and fix any bugs.\n</USER_REQUEST>",
        meta={"user_type": "external"},
    )
    automated_session = NormalizedSession(
        session_id="s1", source_file=Path("s1.jsonl"), events=[automated_event]
    )
    assert not has_user_context(automated_session)

    # Genuine interactive session (normal human input, userType != external)
    human_event = NormalizedEvent(
        event_id="e2",
        timestamp="2026-07-20T10:05:00Z",
        source="user",
        type="message",
        content="hello, can you help me write some tests?",
        meta={"user_type": "human"},
    )
    human_session = NormalizedSession(
        session_id="s2", source_file=Path("s2.jsonl"), events=[human_event]
    )
    assert has_user_context(human_session)


# 3. Event-Time Timestamps Test
def test_event_time_timestamps_invariant(tmp_path: Path) -> None:
    # Set up events spanning from 10:00 to 10:10
    event_1 = NormalizedEvent(
        event_id="e1",
        timestamp="2026-07-20T10:00:00Z",
        source="system",
        type="checkpoint",
        content="startup",
    )
    event_2 = NormalizedEvent(
        event_id="e2",
        timestamp="2026-07-20T10:10:00Z",
        source="user",
        type="message",
        content="exit /handover",
    )

    session_file = tmp_path / "session.jsonl"
    session_file.write_text("dummy content", encoding="utf-8")

    session = NormalizedSession(
        session_id="s1", source_file=session_file, events=[event_1, event_2]
    )

    # The file modification time is now, but timestamps should be event-derived
    started_at, last_modified, ended_at = get_session_timestamps(session)

    assert started_at == "2026-07-20T10:00:00Z"
    assert last_modified == "2026-07-20T10:10:00Z"
    assert ended_at == "2026-07-20T10:10:00Z"  # handover detected


# 4. Skip-Cache Test
def test_skip_cache_logic(tmp_path: Path) -> None:
    cache_file = tmp_path / "skip_cache.json"
    cache = SkipCache(cache_file)

    session_id = "empty-session-999"

    # Initially not marked empty
    assert not cache.is_empty(session_id)

    # Mark it empty
    cache.mark_empty(session_id)
    assert cache.is_empty(session_id)

    # Re-instantiate the cache to simulate next pass / run persistence
    cache_2 = SkipCache(cache_file)
    assert cache_2.is_empty(session_id)

    # Unmark empty
    cache_2.unmark_empty(session_id)
    assert not cache_2.is_empty(session_id)


# 5. recent/ Interactive-Only View Selection Test
def test_recent_interactive_view_selection() -> None:
    # 1. Automated session (excluded)
    automated = NormalizedSession(
        session_id="s1",
        source_file=Path("s1.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-07-20T10:00:00Z",
                source="user",
                type="message",
                content="<USER_REQUEST>cron</USER_REQUEST>",
                meta={"user_type": "external"},
            )
        ],
    )

    # 2. Older interactive session
    older_interactive = NormalizedSession(
        session_id="s2",
        source_file=Path("s2.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e2",
                timestamp="2026-07-20T09:00:00Z",
                source="user",
                type="message",
                content="hello older",
                meta={"user_type": "human"},
            )
        ],
    )

    # 3. Newer interactive session
    newer_interactive = NormalizedSession(
        session_id="s3",
        source_file=Path("s3.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e3",
                timestamp="2026-07-20T11:00:00Z",
                source="user",
                type="message",
                content="hello newer",
                meta={"user_type": "human"},
            )
        ],
    )

    sessions = [automated, older_interactive, newer_interactive]
    selected = select_recent_interactive_sessions(sessions)

    # Should exclude automated session, and return interactive sorted most-recent-first (s3, then s2)
    assert len(selected) == 2
    assert selected[0].session_id == "s3"
    assert selected[1].session_id == "s2"
