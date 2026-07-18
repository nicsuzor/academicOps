"""Contract tests for the agy adapter and normalized model mapping."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from transcripts.adapters.agy import load_agy_transcript
from transcripts.adapters.claude import load_claude_transcript, normalize_claude_transcript
from transcripts.model import (
    NormalizedEvent,
    NormalizedRawEntry,
    NormalizedSession,
    NormalizedToolCall,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
AGY_FIXTURE = FIXTURES_DIR / "agy_session.jsonl"
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"


# --- agy Adapter Tests --------------------------------------------------------


def test_load_agy_transcript_parses_known_entry_types() -> None:
    session = load_agy_transcript(AGY_FIXTURE)

    assert isinstance(session, NormalizedSession)
    assert session.source_file == AGY_FIXTURE
    assert session.session_id == "agy_session"

    # The fixture has 20 lines. Let's make sure they parsed correctly
    assert len(session.events) == 20
    assert len(session.raw_events) == 0

    for event in session.events:
        assert isinstance(event, NormalizedEvent)
        assert event.event_id.startswith("step_")
        assert event.timestamp.endswith("Z")
        assert event.source in {"user", "model", "system", "tool"}
        assert event.type in {"message", "system", "checkpoint", "tool_output"}
        assert isinstance(event.content, str)

        # Check a specific tool call parsing in PLANNER_RESPONSE
        if event.event_id == "step_2":
            assert event.source == "model"
            assert event.type == "message"
            assert event.tool_calls is not None
            assert len(event.tool_calls) == 1
            tc = event.tool_calls[0]
            assert isinstance(tc, NormalizedToolCall)
            assert tc.name == "view_file"
            assert tc.args == {
                "AbsolutePath": "/home/<user>/.gemini/config/plugins/aops/skills/pull/SKILL.md",
                "toolAction": "Viewing pull skill instructions",
                "toolSummary": "View pull SKILL.md",
            }


def test_agy_unknown_type_preserved_as_raw(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "unknown_type.jsonl"
    jsonl_path.write_text(
        '{"step_index":0,"source":"MODEL","type":"TOTALLY_NEW_ACTION_TYPE","status":"DONE","created_at":"2026-07-16T09:11:18Z","content":"hello"}\n',
        encoding="utf-8",
    )

    session = load_agy_transcript(jsonl_path)
    assert len(session.events) == 0
    assert len(session.raw_events) == 1
    raw = session.raw_events[0]
    assert isinstance(raw, NormalizedRawEntry)
    assert raw.line_no == 1
    assert raw.type == "TOTALLY_NEW_ACTION_TYPE"
    assert raw.raw.get("content") == "hello"


def test_agy_unknown_type_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    jsonl_path = FIXTURES_DIR / "temp_unknown.jsonl"
    try:
        jsonl_path.write_text(
            '{"step_index":0,"source":"MODEL","type":"TOTALLY_NEW_ACTION_TYPE","status":"DONE","created_at":"2026-07-16T09:11:18Z","content":"hello"}\n',
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING, logger="transcripts.adapters.agy"):
            load_agy_transcript(jsonl_path)

        warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("TOTALLY_NEW_ACTION_TYPE" in message for message in warnings)
    finally:
        if jsonl_path.exists():
            jsonl_path.unlink()


def test_agy_loader_never_raises_on_malformed_lines(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "malformed.jsonl"
    jsonl_path.write_text(
        "\n".join(
            [
                "not json at all {{{",
                '{"step_index":0,"source":"MODEL","type":"TOTALLY_NEW_ACTION_TYPE","status":"DONE"}',
                '["not", "an", "object"]',
                "",  # blank line
                '{"step_index":1,"source":"USER_EXPLICIT","type":"USER_INPUT","status":"DONE",'
                '"created_at":"2026-07-16T09:11:18Z","content":"hi"}',
            ]
        ),
        encoding="utf-8",
    )

    session = load_agy_transcript(jsonl_path)

    assert len(session.events) == 1
    assert session.events[0].event_id == "step_1"
    assert session.events[0].source == "user"
    assert session.events[0].type == "message"
    assert session.events[0].content == "hi"

    assert len(session.raw_events) == 1
    assert session.raw_events[0].type == "TOTALLY_NEW_ACTION_TYPE"


def test_agy_loader_never_raises_on_missing_file(tmp_path: Path) -> None:
    session = load_agy_transcript(tmp_path / "does-not-exist.jsonl")

    assert session.events == []
    assert session.raw_events == []


# --- Claude to Normalized Seam Tests ------------------------------------------


def test_normalize_claude_transcript() -> None:
    claude_transcript = load_claude_transcript(CLAUDE_FIXTURE)
    session = normalize_claude_transcript(claude_transcript)

    assert isinstance(session, NormalizedSession)
    assert session.session_id == "19cb8a50-7d62-4936-aef9-6861ad8967a4"
    assert session.source_file == CLAUDE_FIXTURE

    # Verified 16 parsed events and 2 raw events in claude_session.jsonl
    assert len(session.events) == 16
    assert len(session.raw_events) == 2

    # Verify event fields and types mapping
    user_msgs = [e for e in session.events if e.source == "user"]
    assert len(user_msgs) == 2
    assert user_msgs[0].type == "message"
    assert "pre-dispatch safety check" in user_msgs[0].content

    model_msgs = [e for e in session.events if e.source == "model"]
    assert len(model_msgs) == 2
    assert model_msgs[0].type == "message"
    assert model_msgs[0].content == "MECHANISM: none\nVERDICT: valid"

    tool_outputs = [e for e in session.events if e.source == "tool"]
    assert len(tool_outputs) == 10
    for tool_output in tool_outputs:
        assert tool_output.type == "tool_output"
        assert "attachment" in tool_output.meta

    checkpoints = [e for e in session.events if e.type == "checkpoint"]
    assert len(checkpoints) == 2
    for cp in checkpoints:
        assert cp.source == "system"

    # Verify the raw entries from Claude mapped to NormalizedRawEntry
    for raw in session.raw_events:
        assert isinstance(raw, NormalizedRawEntry)
        assert raw.type == "last-prompt"
        assert raw.raw.get("type") == "last-prompt"
