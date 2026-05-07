"""Regression tests for timeline_events deduplication.

Closes task-955f405d. Reproduces the bug where Cowork audit.jsonl files
emit user prompts twice — once as the original, once as a "replay" with
the same UUID and a slightly later `_audit_timestamp`. Both copies were
flowing through the parser → turn grouping → `extract_timeline_events`,
producing duplicate `user_prompt` entries 1–4 seconds apart in
`timeline_events` arrays.

Fix layers covered:
  1. `_parse_jsonl_file` skips entries with `isReplay: true`.
  2. `_parse_jsonl_file` dedupes user/assistant entries by UUID.
  3. `extract_timeline_events` emits idempotently, deduping by content key.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from lib.transcript_parser import (
    ConversationTurn,
    SessionProcessor,
    extract_timeline_events,
)


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


def _user_entry(uuid: str, ts: str, text: str, is_replay: bool = False) -> dict:
    """Build a Cowork-style user audit entry."""
    entry = {
        "type": "user",
        "uuid": uuid,
        "session_id": "abcd1234-aaaa-bbbb-cccc-ddddeeeeffff",
        "parent_tool_use_id": None,
        "message": {"role": "user", "content": text},
        "_audit_timestamp": ts,
        "timestamp": ts,
    }
    if is_replay:
        entry["isReplay"] = True
    return entry


def _assistant_entry(uuid: str, ts: str, text: str) -> dict:
    return {
        "type": "assistant",
        "uuid": uuid,
        "session_id": "abcd1234-aaaa-bbbb-cccc-ddddeeeeffff",
        "parent_tool_use_id": None,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
        },
        "_audit_timestamp": ts,
        "timestamp": ts,
    }


class TestParserSkipsReplay:
    """Bug-mode: a replay user entry (isReplay=True) must be dropped."""

    def test_replay_user_entry_dropped(self, tmp_path: Path) -> None:
        """Entry with isReplay=true MUST NOT produce a turn or event."""
        audit = tmp_path / "audit.jsonl"
        _write_jsonl(
            audit,
            [
                _user_entry("u1", "2026-04-28T02:10:04.657Z", "first prompt"),
                _user_entry("u1", "2026-04-28T02:10:08.787Z", "first prompt", is_replay=True),
                _assistant_entry("a1", "2026-04-28T02:10:12.241Z", "ok"),
            ],
        )

        proc = SessionProcessor()
        _, entries, agents = proc.parse_session_file(audit)

        # Only one user entry survives the replay drop.
        user_entries = [e for e in entries if e.type == "user"]
        assert len(user_entries) == 1, (
            f"Replay entry leaked into parser output: {len(user_entries)} user entries"
        )

        turns = proc.group_entries_into_turns(entries, agents)
        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        assert len(prompts) == 1, f"Expected 1 user_prompt, got {len(prompts)}: {prompts}"
        assert prompts[0]["description"] == "first prompt"


class TestParserDedupesByUuid:
    """Bug-mode: a duplicate entry shares UUID but lacks isReplay flag."""

    def test_duplicate_uuid_user_entry_dropped(self, tmp_path: Path) -> None:
        """Two user entries with the same UUID collapse to one."""
        audit = tmp_path / "audit.jsonl"
        _write_jsonl(
            audit,
            [
                _user_entry("u1", "2026-04-28T02:10:04.657Z", "duped prompt"),
                # Same UUID, different timestamp, NO isReplay flag.
                _user_entry("u1", "2026-04-28T02:10:08.787Z", "duped prompt"),
                _assistant_entry("a1", "2026-04-28T02:10:12.241Z", "ack"),
            ],
        )

        proc = SessionProcessor()
        _, entries, agents = proc.parse_session_file(audit)

        user_entries = [e for e in entries if e.type == "user"]
        assert len(user_entries) == 1, (
            f"UUID dedupe failed: kept {len(user_entries)} user entries with same UUID"
        )

        turns = proc.group_entries_into_turns(entries, agents)
        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        assert len(prompts) == 1

    def test_distinct_uuids_preserved(self, tmp_path: Path) -> None:
        """Different UUIDs with identical content are NOT collapsed by parser."""
        audit = tmp_path / "audit.jsonl"
        _write_jsonl(
            audit,
            [
                _user_entry("u1", "2026-04-28T02:10:04Z", "same words"),
                _assistant_entry("a1", "2026-04-28T02:10:05Z", "ok"),
                _user_entry("u2", "2026-04-28T02:11:00Z", "same words"),
                _assistant_entry("a2", "2026-04-28T02:11:01Z", "ok"),
            ],
        )

        proc = SessionProcessor()
        _, entries, agents = proc.parse_session_file(audit)

        user_entries = [e for e in entries if e.type == "user"]
        assert len(user_entries) == 2, (
            "Parser must not collapse distinct UUIDs with identical content"
        )

        turns = proc.group_entries_into_turns(entries, agents)
        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        # Distinct timestamps -> distinct dedupe keys -> both kept.
        assert len(prompts) == 2


class TestExtractTimelineEventsIdempotent:
    """Belt-and-braces: extract_timeline_events itself is dedupe-safe."""

    def _make_turn(self, text: str, ts: datetime) -> ConversationTurn:
        return ConversationTurn(
            user_message=text,
            assistant_sequence=[],
            start_time=ts,
            end_time=ts,
        )

    def test_identical_turns_emit_one_user_prompt(self) -> None:
        """Two turns with the same (timestamp, text) produce one event."""
        ts = datetime(2026, 4, 28, 2, 10, 4, tzinfo=UTC)
        turns = [
            self._make_turn("hello world", ts),
            self._make_turn("hello world", ts),
        ]

        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        assert len(prompts) == 1, (
            f"extract_timeline_events failed to dedupe identical turns: {prompts}"
        )

    def test_different_timestamps_kept(self) -> None:
        """Same text, different timestamps remain distinct events."""
        turns = [
            self._make_turn("hello", datetime(2026, 4, 28, 2, 10, 4, tzinfo=UTC)),
            self._make_turn("hello", datetime(2026, 4, 28, 2, 11, 0, tzinfo=UTC)),
        ]

        events = extract_timeline_events(turns, "abcd1234")
        prompts = [e for e in events if e.get("type") == "user_prompt"]
        assert len(prompts) == 2

    def test_task_create_dedupe(self) -> None:
        """Duplicate pkb__create_task tool calls collapse to one event."""
        ts = datetime(2026, 4, 28, 2, 10, 4, tzinfo=UTC)
        tool_block = {
            "type": "tool",
            "tool_name": "mcp__plugin_aops-core_pkb__create_task",
            "tool_input": {"title": "demo task", "project": "demo"},
        }
        turn = ConversationTurn(
            user_message="please make a task",
            assistant_sequence=[tool_block, tool_block],  # duplicated tool call
            start_time=ts,
            end_time=ts,
        )

        events = extract_timeline_events([turn], "abcd1234")
        creates = [e for e in events if e.get("type") == "task_create"]
        assert len(creates) == 1, f"Duplicate task_create not deduped: {creates}"
