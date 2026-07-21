"""Regression tests for the transcript-pipeline fixes bundled in PR #2297:

1. `tool_result` content blocks are surfaced as `tool_output` events instead
   of being silently dropped (`transcripts.adapters.claude`).
2. `infer_insights` always returns a sensible non-None summary, even when no
   session carries an explicit VERDICT/MECHANISM marker
   (`transcripts.domain.insights`).
3. `tokens_used` / `cost_usd` are accumulated correctly from per-entry usage
   data (`transcripts.adapters.claude.normalize_claude_transcript`).
4. The Event Index table in the rendered Markdown summary is capped for
   large sessions instead of growing unboundedly
   (`transcripts.domain.renderer.render_to_markdown`).
"""

from __future__ import annotations

from pathlib import Path

from transcripts.adapters.claude import load_claude_transcript, normalize_claude_transcript
from transcripts.domain.insights import infer_insights
from transcripts.domain.renderer import MAX_EVENT_INDEX_ROWS, render_to_markdown
from transcripts.model import NormalizedEvent, NormalizedSession, NormalizedToolCall

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TOOL_RESULT_FIXTURE = FIXTURES_DIR / "claude_session_tool_result.jsonl"


# --- 1. tool_result -> tool_output event -------------------------------------


def test_tool_result_normalized_to_tool_output_event() -> None:
    transcript = load_claude_transcript(TOOL_RESULT_FIXTURE)
    session = normalize_claude_transcript(transcript)

    tool_output_events = [e for e in session.events if e.type == "tool_output"]
    assert len(tool_output_events) == 1

    event = tool_output_events[0]
    assert event.source == "tool"
    assert event.content == "file1.txt\nfile2.txt"
    assert event.meta["tool_use_id"] == "toolu_1"
    assert event.meta["is_error"] is False


# --- 2. infer_insights unconditional fallback --------------------------------


def test_infer_insights_never_none_for_empty_session() -> None:
    session = NormalizedSession(session_id="s1", source_file=Path("dummy.jsonl"), events=[])

    insights = infer_insights(session)

    assert insights is not None
    assert "No tools executed" in insights
    assert "No assistant messages recorded" in insights


def test_infer_insights_fallback_summarizes_tools_and_last_message() -> None:
    session = NormalizedSession(
        session_id="s2",
        source_file=Path("dummy.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-07-10T00:00:00Z",
                source="user",
                type="message",
                content="Please check the build.",
            ),
            NormalizedEvent(
                event_id="e2",
                timestamp="2026-07-10T00:00:05Z",
                source="model",
                type="message",
                content="Build passed.",
                tool_calls=[NormalizedToolCall(name="Bash", args={"command": "make test"})],
            ),
        ],
    )

    insights = infer_insights(session)

    # Never None, and never empty for a real session — this is the fallback
    # invariant: no VERDICT/MECHANISM marker present anywhere, so infer_insights
    # must synthesize a summary rather than returning None.
    assert insights is not None
    assert "Bash (x1)" in insights
    assert "Build passed." in insights


# --- 3. tokens_used / cost_usd arithmetic ------------------------------------


def test_tokens_used_and_cost_usd_accumulate_correctly() -> None:
    transcript = load_claude_transcript(TOOL_RESULT_FIXTURE)
    session = normalize_claude_transcript(transcript)

    # Fixture carries two assistant `usage` entries:
    #   entry 1: input=100, cache_creation=10, cache_read=5, output=20
    #   entry 2: input=0,   cache_creation=0,  cache_read=0,  output=5
    # tokens_used = sum of all four fields across both entries.
    assert session.tokens_used == 140

    # cost_usd = (input*3.0 + cache_creation*3.75 + cache_read*0.3 + output*15.0) / 1e6
    # totals: input=100, cache_creation=10, cache_read=5, output=25
    expected_cost = (100 * 3.0 + 10 * 3.75 + 5 * 0.3 + 25 * 15.0) / 1_000_000
    assert session.cost_usd == expected_cost
    assert round(session.cost_usd, 6) == 0.000714


# --- 4. Event Index cap for large sessions -----------------------------------


def _make_large_session(event_count: int) -> NormalizedSession:
    events = [
        NormalizedEvent(
            event_id=f"e{i}",
            timestamp=f"2026-07-10T00:{i % 60:02d}:00Z",
            source="tool",
            type="tool_output",
            content=f"synthetic tool output line {i}",
        )
        for i in range(event_count)
    ]
    return NormalizedSession(session_id="big-session", source_file=Path("big.jsonl"), events=events)


def test_event_index_capped_and_points_to_full_md() -> None:
    event_count = 1000
    session = _make_large_session(event_count)

    md = render_to_markdown(
        session,
        slug="bigsess",
        started_at="2026-07-10T00:00:00Z",
        last_modified="2026-07-10T01:00:00Z",
        ended_at="2026-07-10T01:00:00Z",
        has_user_context=True,
        correlation={"project": "test", "task_id": None, "pr_number": None},
        insights=None,
    )

    # Comfortably under ~25K tokens; ~4 chars/token gives a generous ~100K
    # char ceiling, but a capped table should land far below that.
    assert len(md) < 100_000

    remaining = event_count - MAX_EVENT_INDEX_ROWS
    assert f"+{remaining} more events" in md
    assert ".full.md" in md

    # Table itself must not contain more indexed rows than the cap.
    table_rows = [line for line in md.splitlines() if line.startswith("| ") and " | `" in line]
    assert len(table_rows) == MAX_EVENT_INDEX_ROWS


def test_event_index_uncapped_for_small_sessions() -> None:
    """Preserve current behavior: small sessions render one row per event, no truncation."""
    event_count = 5
    session = _make_large_session(event_count)

    md = render_to_markdown(
        session,
        slug="smallsess",
        started_at="2026-07-10T00:00:00Z",
        last_modified="2026-07-10T01:00:00Z",
        ended_at="2026-07-10T01:00:00Z",
        has_user_context=True,
        correlation={"project": "test", "task_id": None, "pr_number": None},
        insights=None,
    )

    assert "more events" not in md
    table_rows = [line for line in md.splitlines() if line.startswith("| ") and " | `" in line]
    assert len(table_rows) == event_count
