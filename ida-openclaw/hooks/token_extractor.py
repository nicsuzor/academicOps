"""Antigravity Gemini token extraction and estimation.

Antigravity persists exact token usage metrics in per-conversation SQLite
databases at ``conversations/<session_id>.db`` within ``step_payload`` blobs.
This module extracts ground-truth token counts (prompt, completion, cached,
and thought tokens) when the database is available, and falls back to a defensible
heuristic estimate (~4 chars per token) when it is not.

Every result explicitly states its provenance (``type``: "reported" or "estimated")
and ``estimate_method``.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def _decode_protobuf_varint(data: bytes, i: int) -> tuple[int, int]:
    val = 0
    shift = 0
    n = len(data)
    while i < n:
        b = data[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
        if shift > 64:
            break
    return val, i


def _decode_fields(data: bytes) -> dict[int, tuple[str, Any]]:
    fields: dict[int, tuple[str, Any]] = {}
    i = 0
    n = len(data)
    while i < n:
        try:
            key, i = _decode_protobuf_varint(data, i)
            fn = key >> 3
            wt = key & 7
            if fn == 0:
                break
            if wt == 0:
                val, i = _decode_protobuf_varint(data, i)
                fields[fn] = ("varint", val)
            elif wt == 2:
                length, i = _decode_protobuf_varint(data, i)
                if i + length > n:
                    break
                chunk = data[i : i + length]
                i += length
                fields[fn] = ("bytes", chunk)
            elif wt == 1:
                if i + 8 > n:
                    break
                i += 8
            elif wt == 5:
                if i + 4 > n:
                    break
                i += 4
            else:
                break
        except Exception:
            break
    return fields


def _extract_tokens_from_payload(payload: bytes) -> dict[str, Any] | None:
    if not payload:
        return None
    try:
        f = _decode_fields(payload)
        if 5 not in f:
            return None
        f5 = _decode_fields(f[5][1])
        if 9 not in f5:
            return None
        f9 = _decode_fields(f5[9][1])
        fresh = f9.get(2, ("varint", 0))[1]
        cached = f9.get(5, ("varint", 0))[1]
        completion = f9.get(3, ("varint", 0))[1]
        thoughts = f9.get(9, ("varint", 0))[1]
        prompt = fresh + cached
        total = prompt + completion
        if prompt == 0 and completion == 0:
            return None
        return {
            "prompt": prompt,
            "completion": completion,
            "total": total,
            "cache_read": cached,
            "cache_write": 0,
            "thoughts": thoughts,
            "type": "reported",
            "estimate_method": "reported: antigravity conversation db steps payload",
        }
    except Exception:
        return None


def _estimate_tokens(input_text: str, output_text: str, thinking_text: str = "") -> dict[str, Any]:
    in_len = len(input_text or "")
    out_len = len(output_text or "") + len(thinking_text or "")
    prompt = max(1, in_len // 4)
    completion = max(1, out_len // 4)
    return {
        "prompt": prompt,
        "completion": completion,
        "total": prompt + completion,
        "cache_read": 0,
        "cache_write": 0,
        "thoughts": max(0, len(thinking_text or "") // 4),
        "type": "estimated",
        "estimate_method": f"estimated: character length ratio (~4 chars/token, in={in_len}, out={out_len})",
    }


def _resolve_candidate_db_paths(
    session_id: str | None = None,
    transcript_path: str | Path | None = None,
) -> list[Path]:
    candidate_db_paths: list[Path] = []
    app_data_dir = os.environ.get("ANTIGRAVITY_APP_DATA_DIR")
    if app_data_dir and session_id:
        candidate_db_paths.append(Path(app_data_dir) / "conversations" / f"{session_id}.db")

    if session_id:
        candidate_db_paths.append(
            Path.home() / ".gemini" / "antigravity" / "conversations" / f"{session_id}.db"
        )
        candidate_db_paths.append(
            Path.home() / ".gemini" / "antigravity-cli" / "conversations" / f"{session_id}.db"
        )

    if transcript_path:
        tp = Path(transcript_path).resolve()
        if len(tp.parents) >= 5 and tp.parents[3].name == "brain":
            app_dir = tp.parents[4]
            if session_id:
                candidate_db_paths.append(app_dir / "conversations" / f"{session_id}.db")
            candidate_db_paths.append(app_dir / "conversations" / f"{tp.parents[2].name}.db")
        for parent in tp.parents:
            conv_dir = parent / "conversations"
            if conv_dir.is_dir():
                if session_id:
                    candidate_db_paths.append(conv_dir / f"{session_id}.db")
                break
    return candidate_db_paths


def _extract_model_from_gen_payload(payload: bytes) -> tuple[str | None, int | None]:
    if not payload:
        return None, None
    try:
        f = _decode_fields(payload)
        if 1 not in f or f[1][0] != "bytes":
            return None, None
        f1_bytes = f[1][1]

        i = 0
        n = len(f1_bytes)
        model = None
        last_step = None
        while i < n:
            key, i = _decode_protobuf_varint(f1_bytes, i)
            fn = key >> 3
            wt = key & 7
            if fn == 0:
                break
            if wt == 0:
                _, i = _decode_protobuf_varint(f1_bytes, i)
            elif wt == 2:
                length, i = _decode_protobuf_varint(f1_bytes, i)
                chunk = f1_bytes[i : i + length]
                i += length
                if fn == 19:
                    decoded = chunk.decode("utf-8", errors="replace").strip()
                    if decoded:
                        model = decoded
                elif fn == 20:
                    sub_f = _decode_fields(chunk)
                    k_val = sub_f.get(1, ("", None))[1]
                    v_val = sub_f.get(2, ("", None))[1]
                    if k_val == b"last_step_index" and v_val:
                        try:
                            last_step = int(v_val.decode("utf-8", errors="replace").strip())
                        except Exception:
                            pass
            elif wt == 1:
                i += 8
            elif wt == 5:
                i += 4
            else:
                break
        return model, last_step
    except Exception:
        return None, None


def resolve_gemini_model(
    session_id: str | None = None,
    transcript_path: str | Path | None = None,
    step_index: int | None = None,
    reported_model: str | None = None,
) -> str | None:
    """Resolve Gemini model identifier for a step or session.

    Checks:
    1. Explicit reported model from transcript entry (if non-empty).
    2. The Antigravity conversation SQLite database at ``conversations/<session_id>.db``
       within ``gen_metadata`` table. When ``step_index`` is provided, matches the row
       whose ``last_step_index`` matches or immediately precedes ``step_index``.
       Falls back to the most recent generation metadata row in the database.
    """
    if reported_model and str(reported_model).strip():
        return str(reported_model).strip()

    candidate_db_paths = _resolve_candidate_db_paths(session_id, transcript_path)
    seen = set()
    for db_path in candidate_db_paths:
        if db_path in seen:
            continue
        seen.add(db_path)
        if db_path.is_file():
            try:
                uri = f"file:{db_path.as_posix()}?mode=ro"
                conn = sqlite3.connect(uri, uri=True, timeout=2.0)
                cur = conn.cursor()
                has_gen = cur.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='gen_metadata'"
                ).fetchone()
                if not has_gen:
                    conn.close()
                    continue

                rows = cur.execute(
                    "SELECT idx, data FROM gen_metadata ORDER BY idx DESC"
                ).fetchall()
                conn.close()

                if not rows:
                    continue

                best_model = None
                matched_model = None
                for _, data in rows:
                    if not data:
                        continue
                    model, last_step = _extract_model_from_gen_payload(data)
                    if model and best_model is None:
                        best_model = model
                    if step_index is not None and model and last_step is not None:
                        if last_step == step_index - 1 or last_step <= step_index:
                            matched_model = model
                            break

                if matched_model:
                    return matched_model
                if best_model:
                    return best_model
            except Exception:
                pass

    return None


def resolve_gemini_tokens(
    session_id: str | None = None,
    transcript_path: str | Path | None = None,
    step_index: int | None = None,
    input_text: str = "",
    output_text: str = "",
    thinking_text: str = "",
    reported_input_tokens: int | None = None,
    reported_cache_read_tokens: int | None = None,
    reported_output_tokens: int | None = None,
) -> dict[str, Any]:
    """Resolve token usage for a Gemini step.

    Checks the Antigravity conversation SQLite database for reported usage,
    then inline reported token counts on the transcript step entry, and falls
    back to a heuristic estimate (~4 chars/token) when neither is available.
    """
    candidate_db_paths = _resolve_candidate_db_paths(session_id, transcript_path)
    seen = set()
    for db_path in candidate_db_paths:
        if db_path in seen:
            continue
        seen.add(db_path)
        if db_path.is_file() and step_index is not None:
            try:
                uri = f"file:{db_path.as_posix()}?mode=ro"
                conn = sqlite3.connect(uri, uri=True, timeout=2.0)
                cur = conn.cursor()
                row = cur.execute(
                    "SELECT step_payload FROM steps WHERE idx = ?", (step_index,)
                ).fetchone()
                conn.close()
                if row and row[0]:
                    tok = _extract_tokens_from_payload(row[0])
                    if tok:
                        return tok
            except Exception:
                pass

    if reported_input_tokens is not None or reported_output_tokens is not None:
        fresh = int(reported_input_tokens or 0)
        cached = int(reported_cache_read_tokens or 0)
        completion = int(reported_output_tokens or 0)
        prompt = fresh + cached
        total = prompt + completion
        if prompt > 0 or completion > 0:
            return {
                "prompt": prompt,
                "completion": completion,
                "total": total,
                "cache_read": cached,
                "cache_write": 0,
                "thoughts": max(0, len(thinking_text or "") // 4),
                "type": "reported",
                "estimate_method": "reported: antigravity transcript.jsonl step usage",
            }

    return _estimate_tokens(input_text, output_text, thinking_text)
