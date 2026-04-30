"""Render Gemini ``thoughts`` and Claude ``thinking`` blocks in markdown transcripts.

Acceptance criteria for task-df03f1d9:

- Gemini ``thoughts`` arrays (each item has ``subject`` and ``description``) are
  rendered as blockquotes in markdown transcripts (full and abridged variants).
- Claude ``thinking`` blocks are rendered equivalently.
- Token counts per turn (input/cached/thoughts/output) are shown next to the
  model name as a token-block badge in the agent header.
- The model name appears per turn.
- Existing transcripts without thoughts still render correctly (no regression).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from lib.transcript_parser import SessionProcessor


def _gemini_session_with_thoughts(tmp_path: Path) -> Path:
    """Build a minimal Gemini chat JSON containing thoughts + tokens + model.

    Mirrors the schema seen in production sessions
    (~/.aops/sessions/.../chats/session-*.json).
    """
    payload = {
        "sessionId": "abc12345",
        "projectHash": "deadbeef",
        "startTime": "2026-04-20T03:47:00.000Z",
        "lastUpdated": "2026-04-20T03:50:00.000Z",
        "kind": "interactive",
        "messages": [
            {
                "id": "u1",
                "type": "user",
                "timestamp": "2026-04-20T03:47:00.000Z",
                "content": "Help me design the handover contract.",
            },
            {
                "id": "g1",
                "type": "gemini",
                "timestamp": "2026-04-20T03:48:05.000Z",
                "content": "Here is my plan to design the contract.",
                "model": "gemini-3-flash-preview",
                "tokens": {
                    "input": 17481,
                    "output": 94,
                    "cached": 1024,
                    "thoughts": 440,
                    "tool": 0,
                    "total": 18015,
                },
                "thoughts": [
                    {
                        "subject": "Analyzing Specifications",
                        "description": "Sketching out the contract elements.",
                        "timestamp": "2026-04-20T03:48:02.693Z",
                    },
                    {
                        "subject": "Defining Contract Elements",
                        "description": "Focusing on the agent's output at session end.",
                        "timestamp": "2026-04-20T03:48:03.978Z",
                    },
                ],
                "toolCalls": [],
            },
        ],
    }
    path = tmp_path / "session-2026-04-20T03-47-abc12345.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _gemini_session_without_thoughts(tmp_path: Path) -> Path:
    """Backward-compat fixture: a Gemini session with no ``thoughts`` field."""
    payload = {
        "sessionId": "old67890",
        "startTime": "2026-04-20T03:47:00.000Z",
        "lastUpdated": "2026-04-20T03:50:00.000Z",
        "messages": [
            {
                "id": "u1",
                "type": "user",
                "timestamp": "2026-04-20T03:47:00.000Z",
                "content": "Hello",
            },
            {
                "id": "g1",
                "type": "gemini",
                "timestamp": "2026-04-20T03:48:00.000Z",
                "content": "Hi there",
                "toolCalls": [],
            },
        ],
    }
    path = tmp_path / "session-2026-04-20T03-47-old67890.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _claude_session_with_thinking(tmp_path: Path) -> Path:
    """Build a minimal Claude JSONL session containing a ``thinking`` block."""
    lines = [
        {
            "type": "user",
            "uuid": "u1",
            "timestamp": "2026-04-20T03:47:00.000Z",
            "message": {"content": [{"type": "text", "text": "Hello, please think."}]},
        },
        {
            "type": "assistant",
            "uuid": "a1",
            "parentUuid": "u1",
            "timestamp": "2026-04-20T03:47:30.000Z",
            "message": {
                "model": "claude-opus-4-7",
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "Let me reason carefully about this problem.",
                        "signature": "abcd",
                    },
                    {"type": "text", "text": "Here is my answer."},
                ],
                "usage": {
                    "input_tokens": 1500,
                    "output_tokens": 250,
                    "cache_read_input_tokens": 800,
                    "cache_creation_input_tokens": 0,
                },
            },
        },
    ]
    path = tmp_path / "claude-session.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


# ---------------------------------------------------------------------------
# Gemini thoughts


@pytest.mark.parametrize("variant", ["full", "abridged"])
def test_gemini_thoughts_render_as_blockquotes(tmp_path, variant):
    """Each Gemini thought should render as a `> **subject**: description` blockquote."""
    path = _gemini_session_with_thoughts(tmp_path)
    processor = SessionProcessor()
    summary, entries, agents = processor.parse_session_file(path)

    md = processor.format_session_as_markdown(
        summary,
        entries,
        agents,
        include_tool_results=(variant == "full"),
        variant=variant,
    )

    assert "> **Analyzing Specifications**: Sketching out the contract elements." in md
    assert "> **Defining Contract Elements**: Focusing on the agent's output at session end." in md
    # The actual response text still appears.
    assert "Here is my plan to design the contract." in md


def test_gemini_token_block_and_model_in_agent_header(tmp_path):
    """The agent header line should include model name and `[in= cached= think= out=]`."""
    path = _gemini_session_with_thoughts(tmp_path)
    processor = SessionProcessor()
    summary, entries, agents = processor.parse_session_file(path)
    md = processor.format_session_as_markdown(summary, entries, agents, variant="full")

    # Find the Agent header line
    agent_lines = [line for line in md.splitlines() if line.startswith("## Agent")]
    assert agent_lines, "no agent header was emitted"
    header = agent_lines[0]

    assert "gemini-3-flash-preview" in header
    assert "in=17,481" in header
    assert "cached=1,024" in header
    assert "think=440" in header
    assert "out=94" in header


def test_gemini_entry_extraction(tmp_path):
    """Parser must hydrate Entry.thoughts/tokens/model from Gemini messages."""
    path = _gemini_session_with_thoughts(tmp_path)
    processor = SessionProcessor()
    _, entries, _ = processor.parse_session_file(path)

    assistant_entries = [e for e in entries if e.type == "assistant"]
    assert len(assistant_entries) == 1
    e = assistant_entries[0]
    assert e.model == "gemini-3-flash-preview"
    assert e.input_tokens == 17481
    assert e.output_tokens == 94
    assert e.cache_read_input_tokens == 1024
    assert e.thoughts_tokens == 440
    assert len(e.thoughts) == 2
    assert e.thoughts[0]["subject"] == "Analyzing Specifications"


# ---------------------------------------------------------------------------
# Claude thinking


def test_claude_thinking_renders_as_blockquote(tmp_path):
    """Claude ``thinking`` blocks should render as a blockquote ABOVE the answer."""
    path = _claude_session_with_thinking(tmp_path)
    processor = SessionProcessor()
    summary, entries, agents = processor.parse_session_file(path)

    md = processor.format_session_as_markdown(summary, entries, agents, variant="full")

    assert "> **Thinking**" in md
    assert "Let me reason carefully about this problem." in md
    # Order: thinking blockquote must appear BEFORE the answer text.
    thinking_idx = md.find("Let me reason carefully")
    answer_idx = md.find("Here is my answer.")
    assert thinking_idx != -1 and answer_idx != -1
    assert thinking_idx < answer_idx


def test_claude_model_and_tokens_in_agent_header(tmp_path):
    """Claude transcripts also surface model + token block in the agent header."""
    path = _claude_session_with_thinking(tmp_path)
    processor = SessionProcessor()
    summary, entries, agents = processor.parse_session_file(path)
    md = processor.format_session_as_markdown(summary, entries, agents, variant="full")

    agent_lines = [line for line in md.splitlines() if line.startswith("## Agent")]
    assert agent_lines, "no agent header was emitted"
    header = agent_lines[0]

    assert "claude-opus-4-7" in header
    assert "in=1,500" in header
    assert "cached=800" in header
    assert "out=250" in header


# ---------------------------------------------------------------------------
# Backward compatibility


def test_session_without_thoughts_renders_cleanly(tmp_path):
    """A Gemini session without ``thoughts`` must still render — no blockquote, no crash."""
    path = _gemini_session_without_thoughts(tmp_path)
    processor = SessionProcessor()
    summary, entries, agents = processor.parse_session_file(path)
    md = processor.format_session_as_markdown(summary, entries, agents, variant="full")

    # No thoughts blockquote should be present.
    assert "> **" not in md.split("## Agent")[1] if "## Agent" in md else True
    # The actual response still appears.
    assert "Hi there" in md


def test_claude_session_without_thinking_renders_cleanly(tmp_path):
    """A Claude session without ``thinking`` blocks renders as before — no regression."""
    lines = [
        {
            "type": "user",
            "uuid": "u1",
            "timestamp": "2026-04-20T03:47:00.000Z",
            "message": {"content": [{"type": "text", "text": "Hello"}]},
        },
        {
            "type": "assistant",
            "uuid": "a1",
            "parentUuid": "u1",
            "timestamp": "2026-04-20T03:47:30.000Z",
            "message": {
                "model": "claude-opus-4-7",
                "content": [{"type": "text", "text": "Hi there"}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        },
    ]
    path = tmp_path / "claude-no-thinking.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")

    processor = SessionProcessor()
    summary, entries, agents = processor.parse_session_file(path)
    md = processor.format_session_as_markdown(summary, entries, agents, variant="full")

    assert "Hi there" in md
    # No thinking blockquote.
    assert "> **Thinking**" not in md
    # Model still shows up in header.
    assert "claude-opus-4-7" in md


# ---------------------------------------------------------------------------
# Real-session integration (only runs if a known fixture exists locally)


_REAL_GEMINI = Path(
    "/home/nic/.aops/sessions/polecats/task-efe468c0/aops/workspace/chats/"
    "session-2026-04-20T03-47-fbf3b4cb.json"
)


@pytest.mark.skipif(not _REAL_GEMINI.exists(), reason="real Gemini session not available")
def test_real_gemini_session_thoughts_surface():
    """Smoke-test rendering against a real Gemini session if the fixture exists."""
    processor = SessionProcessor()
    summary, entries, agents = processor.parse_session_file(_REAL_GEMINI)
    md = processor.format_session_as_markdown(summary, entries, agents, variant="full")

    # At least one thought blockquote must surface.
    assert "> **" in md
    # Token-block badge present somewhere in the doc.
    assert "in=" in md and "out=" in md
