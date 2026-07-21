"""Unit tests for the Layer B transcripts domain modules."""

from __future__ import annotations

import json
from pathlib import Path

from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import load_claude_transcript, normalize_claude_transcript
from transcripts.domain.cache import SkipCache
from transcripts.domain.context import has_user_context
from transcripts.domain.correlation import infer_correlation
from transcripts.domain.insights import infer_insights
from transcripts.domain.renderer import render_session_to_all_formats
from transcripts.domain.slug import get_stable_slug
from transcripts.domain.time import get_event_timestamps
from transcripts.domain.view import select_recent_interactive
from transcripts.model import NormalizedEvent, NormalizedSession

FIXTURES_DIR = Path(__file__).parent / "fixtures"
AGY_FIXTURE = FIXTURES_DIR / "agy_session.jsonl"
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"


# --- Invariant 1: Stable slug ------------------------------------------------


def test_stable_slug() -> None:
    # Same id -> same slug
    id1 = "19cb8a50-7d62-4936-aef9-6861ad8967a4"
    assert get_stable_slug(id1) == "19cb8a50"
    assert get_stable_slug(id1) == "19cb8a50"

    id2 = "cc5a6fb3-7b04-4aa0-ba60-265fa94c22c7"
    assert get_stable_slug(id2) == "cc5a6fb3"

    # Same id across runs with content change still yields same slug
    assert get_stable_slug("test-session") == "test"


# --- Invariant 2: Semantic has_user_context ---------------------------------


def test_semantic_user_context() -> None:
    # 1. Automated/cron session with human-looking words -> automated (False)
    automated_session = NormalizedSession(
        session_id="s1",
        source_file=Path("dummy.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-07-20T10:00:00Z",
                source="user",
                type="message",
                content="<USER_REQUEST>\nplease sync repo now\n</USER_REQUEST>\n<ADDITIONAL_METADATA>\nhost: local\n</ADDITIONAL_METADATA>",
            )
        ],
    )
    assert not has_user_context(automated_session)

    # 2. Genuine interactive session -> human (True)
    interactive_session = NormalizedSession(
        session_id="s2",
        source_file=Path("dummy.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-07-20T10:00:00Z",
                source="user",
                type="message",
                content="Hello agent, please help me build this feature.",
            )
        ],
    )
    assert has_user_context(interactive_session)


# --- Invariant 3: Event-time timestamps --------------------------------------


def test_event_time_timestamps() -> None:
    # Event timestamps span 2026-07-05 06:00 to 07:00
    events = [
        NormalizedEvent(
            event_id="1",
            timestamp="2026-07-05T06:00:00Z",
            source="user",
            type="message",
            content="hi",
        ),
        NormalizedEvent(
            event_id="2",
            timestamp="2026-07-05T06:30:00Z",
            source="model",
            type="message",
            content="hello",
        ),
        NormalizedEvent(
            event_id="3",
            timestamp="2026-07-05T07:00:00Z",
            source="user",
            type="message",
            content="bye",
        ),
    ]

    started_at, _, ended_at = get_event_timestamps(events)
    assert started_at == "2026-07-05T06:00:00Z"
    assert ended_at == "2026-07-05T07:00:00Z"


# --- Invariant 4: Skip-cache -------------------------------------------------


def test_skip_cache(tmp_path: Path) -> None:
    cache_file = tmp_path / "cache.json"
    cache = SkipCache(cache_file)

    session_id = "test-session-123"
    assert not cache.is_skipped(session_id)

    # Mark empty
    cache.mark_empty(session_id)
    assert cache.is_skipped(session_id)

    # Reload and test persistence
    cache2 = SkipCache(cache_file)
    assert cache2.is_skipped(session_id)


# --- Invariant 5: recent/ interactive-only view ------------------------------


def test_recent_interactive_view() -> None:
    # Interactive session 1 (earlier)
    s1 = NormalizedSession(
        session_id="s1",
        source_file=Path("s1.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-07-10T12:00:00Z",
                source="user",
                type="message",
                content="hello",
            )
        ],
    )

    # Interactive session 2 (later)
    s2 = NormalizedSession(
        session_id="s2",
        source_file=Path("s2.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e2",
                timestamp="2026-07-11T12:00:00Z",
                source="user",
                type="message",
                content="hi",
            )
        ],
    )

    # Automated session (ignored)
    s3 = NormalizedSession(
        session_id="s3",
        source_file=Path("s3.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e3",
                timestamp="2026-07-12T12:00:00Z",
                source="user",
                type="message",
                content="<USER_REQUEST>...</USER_REQUEST><ADDITIONAL_METADATA>...</ADDITIONAL_METADATA>",
            )
        ],
    )

    selected = select_recent_interactive([s1, s2, s3])
    assert len(selected) == 2
    # Sorted most-recent-first (s2 then s1)
    assert selected[0].session_id == "s2"
    assert selected[1].session_id == "s1"


# --- Outputs Integration: Both fixtures parse & render in all 3 formats -----


def test_both_fixtures_produce_all_three_output_formats() -> None:
    # Load agy session (Layer A)
    agy_session = load_agy_transcript(AGY_FIXTURE)
    assert isinstance(agy_session, NormalizedSession)

    # Render agy (Layer B)
    slug_agy = get_stable_slug(agy_session.session_id)
    start_agy, mod_agy, end_agy = get_event_timestamps(agy_session.events)
    has_user_agy = has_user_context(agy_session)
    corr_agy = infer_correlation(agy_session)
    insights_agy = infer_insights(agy_session)

    md_agy, html_agy, json_agy = render_session_to_all_formats(
        agy_session, slug_agy, start_agy, mod_agy, end_agy, has_user_agy, corr_agy, insights_agy
    )

    assert md_agy.startswith("---")
    assert "slug: " in md_agy
    assert "</html>" in html_agy
    data_agy = json.loads(json_agy)
    assert data_agy["session_id"] == agy_session.session_id

    # Load Claude session (Layer A)
    claude_t = load_claude_transcript(CLAUDE_FIXTURE)
    claude_session = normalize_claude_transcript(claude_t)
    assert isinstance(claude_session, NormalizedSession)

    # Render Claude (Layer B)
    slug_claude = get_stable_slug(claude_session.session_id)
    start_claude, mod_claude, end_claude = get_event_timestamps(claude_session.events)
    has_user_claude = has_user_context(claude_session)
    corr_claude = infer_correlation(claude_session)
    insights_claude = infer_insights(claude_session)

    md_claude, html_claude, json_claude = render_session_to_all_formats(
        claude_session,
        slug_claude,
        start_claude,
        mod_claude,
        end_claude,
        has_user_claude,
        corr_claude,
        insights_claude,
    )

    assert md_claude.startswith("---")
    assert "slug: " in md_claude
    assert "</html>" in html_claude
    data_claude = json.loads(json_claude)
    assert data_claude["session_id"] == claude_session.session_id
