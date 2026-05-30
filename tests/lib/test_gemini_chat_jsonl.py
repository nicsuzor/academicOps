"""Parse Gemini CLI chat-jsonl session files (aops-aca5ce9a).

Gemini's interactive chat history uses JSON Lines where each line is an
entry of the form ``{"role": "user"|"model", "parts": [...]}``. Until this
fix, ``.jsonl`` files fell through to the Claude parser and produced empty
transcripts ("Original Request: (not found)") with malformed permalinks
(``sessions/gemini/session--abridged``).
"""

from __future__ import annotations

import json
from pathlib import Path

from lib.transcript_parser import SessionProcessor, _is_gemini_chat_jsonl


def _write_gemini_chat_jsonl(tmp_path: Path) -> Path:
    """Write a fixture mirroring ``~/.gemini/tmp/<repo>/chats/session-*.jsonl``."""
    chats_dir = tmp_path / ".gemini" / "tmp" / "academicops" / "chats"
    chats_dir.mkdir(parents=True)
    path = chats_dir / "session-2026-05-05T00-15-62cbdf27.jsonl"

    lines = [
        {
            "role": "user",
            "parts": [{"text": "Help me ship the gemini transcript fix."}],
            "timestamp": "2026-05-05T00:15:01Z",
        },
        {
            "role": "model",
            "parts": [
                {"text": "I'll start by inspecting the parser."},
                {"functionCall": {"name": "read_file", "args": {"path": "transcript_parser.py"}}},
            ],
            "model": "gemini-3-flash-preview",
            "tokens": {"input": 1200, "output": 30, "cached": 0, "thoughts": 60},
            "timestamp": "2026-05-05T00:15:08Z",
        },
        {
            "role": "user",
            "parts": [
                {
                    "functionResponse": {
                        "name": "read_file",
                        "response": {"output": "# transcript_parser.py\n..."},
                    }
                }
            ],
            "timestamp": "2026-05-05T00:15:09Z",
        },
        {
            "role": "model",
            "parts": [{"text": "Found it — adding a chat-jsonl detector."}],
            "model": "gemini-3-flash-preview",
            "tokens": {"input": 1450, "output": 18},
            "timestamp": "2026-05-05T00:15:14Z",
        },
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    return path


def test_detects_gemini_chat_jsonl(tmp_path: Path) -> None:
    path = _write_gemini_chat_jsonl(tmp_path)
    assert _is_gemini_chat_jsonl(path) is True


def test_detects_via_first_line_sniff(tmp_path: Path) -> None:
    """Even outside ``.gemini/tmp/`` we recognise the role+parts schema."""
    path = tmp_path / "session-foreign.jsonl"
    path.write_text(
        json.dumps({"role": "user", "parts": [{"text": "hi"}]}) + "\n",
        encoding="utf-8",
    )
    assert _is_gemini_chat_jsonl(path) is True


def test_does_not_misdetect_claude_jsonl(tmp_path: Path) -> None:
    """Claude JSONL must not be classified as Gemini chat-jsonl."""
    path = tmp_path / "claude-session.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "user",
                "uuid": "u1",
                "message": {"content": [{"type": "text", "text": "hi"}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert _is_gemini_chat_jsonl(path) is False


def test_detects_polecat_bind_mount_path(tmp_path: Path) -> None:
    """Bind-mounted gemini chats land outside ``.gemini/tmp/``.

    For polecat workers, the chats dir bind-mounts to
    ``<sessions_repo>/polecats/<task>/<project>/chats/session-*.jsonl``
    so the legacy path heuristic (``.gemini/tmp/`` substring) misses
    them. Detection must work from the ``chats/session-`` shape alone.
    """
    chats_dir = tmp_path / "sessions" / "polecats" / "aops-7cf3cd1a" / "aops" / "chats"
    chats_dir.mkdir(parents=True)
    path = chats_dir / "session-2026-05-23T08-18-a5234d3e.jsonl"
    # Real gemini files lead with a metadata header before the first role/parts line.
    path.write_text(
        "\n".join(
            json.dumps(line)
            for line in [
                {
                    "sessionId": "abc123",
                    "projectHash": "deadbeef",
                    "startTime": "2026-05-23T08:18:00Z",
                },
                {"$set": {"lastUpdated": "2026-05-23T08:18:01Z"}},
                {"role": "user", "parts": [{"text": "hi"}]},
            ]
        ),
        encoding="utf-8",
    )
    assert _is_gemini_chat_jsonl(path) is True


def test_detects_through_metadata_header(tmp_path: Path) -> None:
    """First non-empty line is a Gemini metadata header — must not bail.

    Real gemini chat-jsonl files start with a ``{sessionId, projectHash,
    startTime, ...}`` header (and sometimes ``$set`` updates) before the
    first conversational entry. The detector must skip past those to find
    the role+parts evidence rather than declaring the file Claude-shaped.
    """
    path = tmp_path / "session-2026-05-23T08-18-foo123.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(line)
            for line in [
                {
                    "sessionId": "foo123",
                    "projectHash": "deadbeef",
                    "startTime": "2026-05-23T08:18:00Z",
                },
                {"$set": {"lastUpdated": "2026-05-23T08:18:01Z"}},
                {"role": "model", "parts": [{"text": "ack"}]},
            ]
        ),
        encoding="utf-8",
    )
    assert _is_gemini_chat_jsonl(path) is True


def test_detects_message_style_schema(tmp_path: Path) -> None:
    """Newer message-style gemini chat-jsonl ({type, content, ...}) detected."""
    path = tmp_path / "session-msgstyle-deadbeef.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "1",
                "type": "user",
                "timestamp": "2026-05-23T08:18:00Z",
                "content": "hello",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert _is_gemini_chat_jsonl(path) is True


def test_parses_chat_jsonl_entries(tmp_path: Path) -> None:
    path = _write_gemini_chat_jsonl(tmp_path)
    proc = SessionProcessor()
    summary, entries, _ = proc.parse_session_file(path)

    # Session id derives from the trailing 8-char hash in the filename.
    assert summary.uuid == "62cbdf27"
    assert summary.provider == "gemini"

    # Entries: 4 source lines, plus a synthetic user entry is NOT created
    # (the user-role line that carried only functionResponse becomes a
    # tool_result-bearing user entry directly).
    assert len(entries) == 4

    # First entry is the user prompt.
    first_user = entries[0]
    assert first_user.type == "user"
    text_blocks = [b for b in first_user.message["content"] if b.get("type") == "text"]
    assert text_blocks
    assert "ship the gemini transcript fix" in text_blocks[0]["text"]

    # Second entry is model with text + tool_use.
    model_entry = entries[1]
    assert model_entry.type == "assistant"
    block_types = [b.get("type") for b in model_entry.message["content"]]
    assert "text" in block_types
    assert "tool_use" in block_types
    assert model_entry.model == "gemini-3-flash-preview"
    assert model_entry.input_tokens == 1200

    # Third entry is the user tool_result.
    tool_result_entry = entries[2]
    assert tool_result_entry.type == "user"
    blocks = tool_result_entry.message["content"]
    assert isinstance(blocks, list)
    assert blocks[0]["type"] == "tool_result"
    assert "transcript_parser.py" in blocks[0]["content"]


def test_transcript_round_trip_has_request_and_tool_calls(tmp_path: Path) -> None:
    """Output transcript markdown must contain prompt content and a rendered
    tool call — matching the task's acceptance criteria."""
    path = _write_gemini_chat_jsonl(tmp_path)
    proc = SessionProcessor()
    summary, entries, agents = proc.parse_session_file(path)

    md = proc.format_session_as_markdown(
        summary,
        entries,
        agents,
        include_tool_results=False,
        variant="abridged",
        source_file=str(path),
    )

    # Permalink slug must NOT be empty (regression guard for "session--abridged").
    assert "permalink: sessions/gemini/--abridged" not in md
    assert "permalink: sessions/gemini/-abridged" not in md
    assert "permalink: sessions/gemini/62cbdf27-abridged" in md

    # Body has the original request and at least one tool call rendered.
    assert "ship the gemini transcript fix" in md
    assert "read_file" in md
    # Empty-fallback was ~466 bytes (frontmatter only). Even a tiny 4-entry
    # fixture must clearly exceed that once chronological turns + tool calls
    # are rendered.
    assert len(md) > 700


def _write_polecat_gemini_session(tmp_path: Path) -> Path:
    """Write a minimal polecat Gemini chat-jsonl (1 user + 1 agent turn).

    Polecat sessions are single-turn by design: one user dispatch message
    and one agent response. This is the smallest legal session that must
    NOT be skipped by the meaningful-entry counter.

    Path layout mirrors the polecat bind-mount:
    ``<sessions_repo>/polecats/<task>/<project>/chats/session-*.jsonl``
    """
    chats_dir = tmp_path / "sessions" / "polecats" / "aops-b7e6630a" / "aops" / "chats"
    chats_dir.mkdir(parents=True)
    path = chats_dir / "session-2026-05-23T20-30-c8bffa1d.jsonl"

    lines = [
        {
            "sessionId": "c8bffa1d",
            "projectHash": "aops",
            "startTime": "2026-05-23T20:30:00Z",
        },
        {
            "role": "user",
            "parts": [{"text": "Implement the polecat short-session fix."}],
            "timestamp": "2026-05-23T20:30:01Z",
        },
        {
            "role": "model",
            "parts": [{"text": "Done — filed PR #1482."}],
            "model": "gemini-2-5-pro",
            "tokens": {"input": 800, "output": 12, "cached": 0, "thoughts": 0},
            "timestamp": "2026-05-23T20:31:45Z",
        },
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    return path


def test_polecat_single_turn_meaningful_count(tmp_path: Path) -> None:
    """Polecat sessions (1 user + 1 agent turn) must yield meaningful_count >= 1.

    Regression guard for the counter bug (aops-b7e6630a) where the
    meaningful-entry check reported 0 for a genuine user+agent exchange.
    """
    path = _write_polecat_gemini_session(tmp_path)
    proc = SessionProcessor()
    _, entries, _ = proc.parse_session_file(path)

    meaningful_count = sum(
        1
        for e in entries
        if e.type in ("user", "assistant")
        and not (
            hasattr(e, "message")
            and e.message
            and e.message.get("subtype") in ("system", "informational")
        )
    )
    assert meaningful_count >= 1, (
        f"Polecat single-turn session yielded {meaningful_count} meaningful entries; "
        "must be >= 1 to avoid spurious skip"
    )
    # Exact count: 1 user + 1 assistant = 2
    assert meaningful_count == 2
