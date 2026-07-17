"""Contract + snapshot tests for the Claude adapter (aops/lib/transcripts/adapters/claude.py).

Runs the LIVE claude-code-log library against the committed fixture corpus.
A break here means upstream drifted — a localized, diffable CI failure
instead of a silent production regression.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from transcripts.adapters.claude import (
    KNOWN_ENTRY_TYPES,
    ClaudeTranscript,
    RawEntry,
    load_claude_transcript,
    render_claude_session,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"
SESSION_ID = "19cb8a50-7d62-4936-aef9-6861ad8967a4"
SESSION_TITLE = "Session 19cb8a50"


# --- Contract tests -------------------------------------------------------


def test_load_claude_transcript_parses_known_entry_types() -> None:
    transcript = load_claude_transcript(CLAUDE_FIXTURE)

    assert isinstance(transcript, ClaudeTranscript)
    assert transcript.source == CLAUDE_FIXTURE
    assert len(transcript.entries) == 16
    for entry in transcript.entries:
        assert entry.type in KNOWN_ENTRY_TYPES


def test_unknown_type_preserved_as_raw_not_dropped() -> None:
    transcript = load_claude_transcript(CLAUDE_FIXTURE)

    # The fixture carries two `last-prompt` lines — a type claude-code-log
    # does not parse into a typed model. They must survive as raw entries,
    # not vanish.
    assert len(transcript.raw_entries) == 2
    for raw in transcript.raw_entries:
        assert isinstance(raw, RawEntry)
        assert raw.type == "last-prompt"
        assert raw.type not in KNOWN_ENTRY_TYPES
        assert raw.raw.get("type") == "last-prompt"


def test_unknown_type_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="transcripts.adapters.claude"):
        load_claude_transcript(CLAUDE_FIXTURE)

    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("last-prompt" in message for message in warnings)


def test_loader_never_raises_on_malformed_lines(tmp_path: Path) -> None:
    """The batch degrades — it never dies — on garbage input."""
    jsonl_path = tmp_path / "malformed.jsonl"
    jsonl_path.write_text(
        "\n".join(
            [
                "not json at all {{{",
                '{"type": "totally-unknown-future-type", "payload": 1}',
                '["not", "an", "object"]',
                "",  # blank line
                '{"type": "queue-operation", "operation": "enqueue", '
                '"timestamp": "2026-07-05T06:45:18.550Z", "sessionId": "s1", "content": "hi"}',
            ]
        ),
        encoding="utf-8",
    )

    transcript = load_claude_transcript(jsonl_path)

    assert len(transcript.entries) == 1
    assert transcript.entries[0].type == "queue-operation"
    assert len(transcript.raw_entries) == 1
    assert transcript.raw_entries[0].type == "totally-unknown-future-type"


def test_loader_never_raises_on_missing_file(tmp_path: Path) -> None:
    transcript = load_claude_transcript(tmp_path / "does-not-exist.jsonl")

    assert transcript.entries == []
    assert transcript.raw_entries == []


def test_render_smoke_all_formats() -> None:
    transcript = load_claude_transcript(CLAUDE_FIXTURE)

    for fmt in ("markdown", "html", "json"):
        rendered = render_claude_session(
            transcript.entries, SESSION_ID, format=fmt, title=SESSION_TITLE
        )
        assert isinstance(rendered, str)
        assert rendered.strip()
        assert SESSION_ID.split("-")[0] in rendered


# --- Snapshot tests ---------------------------------------------------------


def _assert_matches_snapshot(actual: str, snapshot_path: Path) -> None:
    expected = snapshot_path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"Rendered output no longer matches committed snapshot {snapshot_path.name}. "
        "If this is an intentional upstream/behavior change, review the diff and "
        "regenerate the snapshot fixture."
    )


def test_markdown_snapshot() -> None:
    transcript = load_claude_transcript(CLAUDE_FIXTURE)
    markdown = render_claude_session(
        transcript.entries, SESSION_ID, format="markdown", title=SESSION_TITLE
    )
    _assert_matches_snapshot(markdown, FIXTURES_DIR / "claude_session.snapshot.md")


def test_json_snapshot() -> None:
    transcript = load_claude_transcript(CLAUDE_FIXTURE)
    rendered_json = render_claude_session(
        transcript.entries, SESSION_ID, format="json", title=SESSION_TITLE
    )
    _assert_matches_snapshot(rendered_json, FIXTURES_DIR / "claude_session.snapshot.json")
