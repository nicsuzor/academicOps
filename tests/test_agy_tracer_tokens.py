"""Tests for Gemini token extraction and span attributes in agy_tracer."""

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

HOOKS_DIR = Path(__file__).resolve().parent.parent / "plugins" / "ida" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

import agy_tracer
import token_extractor


def _encode_varint(value: int) -> bytes:
    bits = value & 0x7F
    value >>= 7
    out = bytearray()
    while value:
        out.append(0x80 | bits)
        bits = value & 0x7F
        value >>= 7
    out.append(bits)
    return bytes(out)


def _encode_key(field_num: int, wire_type: int) -> bytes:
    return _encode_varint((field_num << 3) | wire_type)


def _encode_len_delimited(field_num: int, payload: bytes) -> bytes:
    return _encode_key(field_num, 2) + _encode_varint(len(payload)) + payload


def _encode_varint_field(field_num: int, value: int) -> bytes:
    return _encode_key(field_num, 0) + _encode_varint(value)


def build_mock_usage_payload(
    fresh_prompt: int, cached: int, completion: int, thoughts: int
) -> bytes:
    """Constructs protobuf payload matching Antigravity step_payload structure:
    Field 5 (bytes) -> Subfield 9 (bytes) ->
        Sub-tag 2: fresh prompt tokens
        Sub-tag 5: cached prompt tokens
        Sub-tag 3: completion tokens
        Sub-tag 9: thoughts tokens
    """
    f9_bytes = (
        _encode_varint_field(2, fresh_prompt)
        + _encode_varint_field(5, cached)
        + _encode_varint_field(3, completion)
        + _encode_varint_field(9, thoughts)
    )
    f5_bytes = _encode_len_delimited(9, f9_bytes)
    return _encode_len_delimited(5, f5_bytes)


def test_token_extractor_reported_from_sqlite(tmp_path: Path):
    conv_dir = tmp_path / "conversations"
    conv_dir.mkdir(parents=True, exist_ok=True)
    db_file = conv_dir / "test-session.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_payload BLOB)")
    payload = build_mock_usage_payload(fresh_prompt=120, cached=80, completion=45, thoughts=25)
    cur.execute("INSERT INTO steps VALUES (?, ?)", (2, payload))
    conn.commit()
    conn.close()

    transcript_path = (
        tmp_path / "brain" / "test-session" / ".system_generated" / "logs" / "transcript.jsonl"
    )
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text("")

    result = token_extractor.resolve_gemini_tokens(
        session_id="test-session",
        transcript_path=transcript_path,
        step_index=2,
    )

    assert result["prompt"] == 200  # 120 + 80
    assert result["completion"] == 45
    assert result["total"] == 245
    assert result["cache_read"] == 80
    assert result["thoughts"] == 25
    assert result["type"] == "reported"
    assert "antigravity conversation db steps payload" in result["estimate_method"]


def test_token_extractor_fallback_estimated():
    input_text = "a" * 400
    output_text = "b" * 200
    thinking_text = "t" * 80

    result = token_extractor.resolve_gemini_tokens(
        session_id="nonexistent-session",
        transcript_path="/nonexistent/path/transcript.jsonl",
        step_index=99,
        input_text=input_text,
        output_text=output_text,
        thinking_text=thinking_text,
    )

    assert result["prompt"] == 100
    assert result["completion"] == 70  # (200 + 80) // 4
    assert result["total"] == 170
    assert result["thoughts"] == 20
    assert result["type"] == "estimated"
    assert "character length ratio" in result["estimate_method"]


def test_extract_llm_spans_for_turn_agy_with_tokens(tmp_path: Path):
    transcript = (
        tmp_path / "brain" / "test_session_id" / ".system_generated" / "logs" / "transcript.jsonl"
    )
    transcript.parent.mkdir(parents=True, exist_ok=True)
    conv_dir = tmp_path / "conversations"
    conv_dir.mkdir(parents=True, exist_ok=True)
    db_file = conv_dir / "test_session_id.db"

    # Create DB
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_payload BLOB)")
    payload = build_mock_usage_payload(fresh_prompt=500, cached=100, completion=50, thoughts=15)
    cur.execute("INSERT INTO steps VALUES (?, ?)", (1, payload))
    conn.commit()
    conn.close()

    entries = [
        {"type": "USER_INPUT", "content": "What is the square root of 144?"},
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "content": "12",
            "thinking": "Calculating sqrt(144) = 12",
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    spans = agy_tracer._extract_llm_spans_for_turn_agy(
        transcript_path=str(transcript),
        human_count_at_start=0,
        trace_id_hex="0123456789abcdef0123456789abcdef",
        root_span_id_hex="0123456789abcdef",
        session_id="test_session_id",
    )

    assert len(spans) == 1
    attrs = spans[0]["attributes"]
    assert attrs["openinference.span.kind"] == "LLM"
    assert attrs["llm.token_count.prompt"] == 600
    assert attrs["llm.token_count.completion"] == 50
    assert attrs["llm.token_count.total"] == 650
    assert attrs["llm.token_count.prompt_details.cache_read"] == 100
    assert attrs["llm.token_count.type"] == "reported"
    assert attrs["token_count.type"] == "reported"
    assert "antigravity conversation db steps payload" in attrs["llm.token_count.estimate_method"]


def test_handle_stop_accumulates_and_preserves_token_counts(tmp_path: Path):
    transcript = (
        tmp_path / "brain" / "test_session_stop" / ".system_generated" / "logs" / "transcript.jsonl"
    )
    transcript.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {"type": "USER_INPUT", "content": "Say hello"},
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "content": "Hello there!",
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    state = {
        "session_id": "test_session_stop",
        "current_trace": {
            "trace_id": "0123456789abcdef0123456789abcdef",
            "root_span_id": "0123456789abcdef",
            "turn_start_ns": 1000000,
            "human_count_at_start": 0,
        },
        "transcript_path": str(transcript),
    }

    exported_records = []

    def mock_export(config, session_id, username, span_records, **kwargs):
        exported_records.extend(span_records)

    with (
        patch("agy_tracer._load_state", return_value=state),
        patch("agy_tracer._save_state"),
        patch("agy_tracer._delete_state"),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        data = {"conversationId": "test_session_stop", "transcriptPath": str(transcript)}
        config = {"endpoint": "localhost:4317"}
        agy_tracer.handle_stop(data, config)

    assert len(exported_records) == 2  # 1 CHAIN + 1 LLM
    chain_span = exported_records[0]
    llm_span = exported_records[1]

    # Verify chain span received accumulated token counts
    assert "llm.token_count.prompt" in chain_span["attributes"]
    assert "llm.token_count.completion" in chain_span["attributes"]
    assert "llm.token_count.total" in chain_span["attributes"]
    assert chain_span["attributes"]["llm.token_count.type"] in ("reported", "estimated")
    assert "llm.token_count.estimate_method" in chain_span["attributes"]

    # Verify LLM span retained token counts (NOT deleted!)
    assert "llm.token_count.prompt" in llm_span["attributes"]
    assert "llm.token_count.completion" in llm_span["attributes"]
    assert "llm.token_count.total" in llm_span["attributes"]
    assert llm_span["attributes"]["llm.token_count.type"] in ("reported", "estimated")
    assert "llm.token_count.estimate_method" in llm_span["attributes"]
