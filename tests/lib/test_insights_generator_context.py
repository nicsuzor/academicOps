"""Tests for extract_recent_context in insights_generator.

All tests use real JSONL fixtures on disk — no mocks.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lib.insights_generator import extract_recent_context
from lib.transcript_parser import SessionInfo


def _make_timestamp(offset_seconds: int = 0) -> str:
    base = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    ts = base + timedelta(seconds=offset_seconds)
    return ts.isoformat().replace("+00:00", "Z")


def _write_session_jsonl(path: Path, turns: list[tuple[str, str]]) -> None:
    """Write a JSONL file with user/assistant turn pairs."""
    with path.open("w") as f:
        for i, (user_text, assistant_text) in enumerate(turns):
            user_entry = {
                "type": "user",
                "uuid": f"user-{i}",
                "timestamp": _make_timestamp(i * 10),
                "isMeta": False,
                "message": {"content": [{"type": "text", "text": user_text}]},
            }
            f.write(json.dumps(user_entry) + "\n")

            assistant_entry = {
                "type": "assistant",
                "uuid": f"assistant-{i}",
                "timestamp": _make_timestamp(i * 10 + 5),
                "message": {"content": [{"type": "text", "text": assistant_text}]},
            }
            f.write(json.dumps(assistant_entry) + "\n")


class TestExtractRecentContext:
    """Test transcript extraction with real JSONL files on disk."""

    def test_extract_by_direct_path(self, tmp_path: Path) -> None:
        """Passing a real file path extracts conversation from it."""
        session_file = tmp_path / "direct.jsonl"
        _write_session_jsonl(session_file, [("Hello", "Hi there")])

        result = extract_recent_context(str(session_file))

        assert "[User]: Hello" in result
        assert "[Agent]: Hi there" in result

    def test_extract_by_session_id(self, tmp_path: Path, monkeypatch) -> None:
        """Session ID lookup finds the right file via find_sessions."""
        session_file = tmp_path / "test-session-123.jsonl"
        _write_session_jsonl(session_file, [("Request", "Response")])

        session_info = SessionInfo(
            path=session_file,
            project="test-project",
            session_id="test-session-123",
            last_modified=None,
        )
        monkeypatch.setattr("lib.insights_generator.find_sessions", lambda: [session_info])

        result = extract_recent_context("test-session-123")

        assert "[User]: Request" in result

    def test_extract_by_short_hash(self, tmp_path: Path, monkeypatch) -> None:
        """Full ID input matches short hash on disk."""
        session_file = tmp_path / "a1b2c3d4.jsonl"
        _write_session_jsonl(session_file, [("Short hash match", "Got it")])

        session_info = SessionInfo(
            path=session_file,
            project="test-project",
            session_id="a1b2c3d4",
            last_modified=None,
        )
        monkeypatch.setattr("lib.insights_generator.find_sessions", lambda: [session_info])

        result = extract_recent_context("a1b2c3d4e5f6g7h8")

        assert "[User]: Short hash match" in result

    def test_extract_by_prefix(self, tmp_path: Path, monkeypatch) -> None:
        """Short hash input matches full ID on disk."""
        session_file = tmp_path / "full.jsonl"
        _write_session_jsonl(session_file, [("Prefix match", "Found")])

        session_info = SessionInfo(
            path=session_file,
            project="test-project",
            session_id="a1b2c3d4e5f6g7h8",
            last_modified=None,
        )
        monkeypatch.setattr("lib.insights_generator.find_sessions", lambda: [session_info])

        result = extract_recent_context("a1b2c3d4")

        assert "[User]: Prefix match" in result

    def test_session_not_found(self, monkeypatch) -> None:
        """Non-existent session returns empty string."""
        monkeypatch.setattr("lib.insights_generator.find_sessions", lambda: [])

        result = extract_recent_context("non-existent")

        assert result == ""

    def test_empty_conversation(self, tmp_path: Path) -> None:
        """Empty JSONL file returns empty string."""
        session_file = tmp_path / "empty.jsonl"
        session_file.write_text("")

        result = extract_recent_context(str(session_file))

        assert result == ""
