"""Contract + snapshot tests for the Claude adapter (aops/lib/transcripts/adapters/claude.py).

Runs the pinned claude-code-log library against the committed fixture corpus.
A break here means the adapter drifted from the library — a localized, diffable
failure in the normal test suite instead of a silent production regression.
Bumping the claude-code-log pin re-runs these against the new release, so an
upstream change surfaces here whenever the dependency is upgraded.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from transcripts.adapters.claude import (
    KNOWN_ENTRY_TYPES,
    ROUTINE_RAW_TYPES,
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


def test_unknown_type_is_logged(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    # Routine raw entry types (like last-prompt) are logged at DEBUG
    with caplog.at_level(logging.DEBUG, logger="transcripts.adapters.claude"):
        load_claude_transcript(CLAUDE_FIXTURE)

    debug_msgs = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
    assert any("last-prompt" in message for message in debug_msgs)

    # Unexpected raw entry types produce a WARNING
    caplog.clear()
    unknown_file = tmp_path / "unknown.jsonl"
    unknown_file.write_text('{"type": "totally-unknown-future-type"}\n', encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="transcripts.adapters.claude"):
        load_claude_transcript(unknown_file)

    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("totally-unknown-future-type" in message for message in warnings)


def test_routine_raw_types_are_logged_at_debug(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """Routine raw entry types (progress, file-history-snapshot, agent-color) log at DEBUG, not WARNING."""
    target_types = {"progress", "file-history-snapshot", "agent-color"}
    assert target_types.issubset(ROUTINE_RAW_TYPES)

    jsonl_lines = [
        json.dumps({"type": "progress", "data": "building"}),
        json.dumps({"type": "file-history-snapshot", "snapshotId": "s1"}),
        json.dumps({"type": "agent-color", "color": "blue"}),
    ]
    jsonl_path = tmp_path / "routine_types.jsonl"
    jsonl_path.write_text("\n".join(jsonl_lines) + "\n", encoding="utf-8")

    with caplog.at_level(logging.DEBUG, logger="transcripts.adapters.claude"):
        transcript = load_claude_transcript(jsonl_path)

    raw_types = {raw.type for raw in transcript.raw_entries}
    assert raw_types == target_types
    for raw in transcript.raw_entries:
        assert isinstance(raw, RawEntry)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert not warnings

    debug_msgs = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
    for raw_type in target_types:
        assert any(raw_type in msg for msg in debug_msgs)


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
