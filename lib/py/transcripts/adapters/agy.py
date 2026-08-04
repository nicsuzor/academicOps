"""agy parse adapter.

This module parses agy JSONL transcripts into the common NormalizedSession model.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from transcripts.adapters.classifier import classify_user_prompt
from transcripts.model import (
    NormalizedEvent,
    NormalizedRawEntry,
    NormalizedSession,
    NormalizedToolCall,
)

logger = logging.getLogger(__name__)

# Known agy entry types that can be parsed into NormalizedEvents.
# Any other type is preserved as a NormalizedRawEntry.
KNOWN_AGY_TYPES = frozenset(
    {
        "USER_INPUT",
        "CONVERSATION_HISTORY",
        "PLANNER_RESPONSE",
        "CHECKPOINT",
        "VIEW_FILE",
        "LIST_DIRECTORY",
        "GREP_SEARCH",
        "MCP_TOOL",
        "RUN_COMMAND",
        "WRITE_TO_FILE",
        "REPLACE_FILE_CONTENT",
        "MULTI_REPLACE_FILE_CONTENT",
        "GENERATE_IMAGE",
        "READ_URL_CONTENT",
        "SEARCH_WEB",
        "ASK_QUESTION",
        "ASK_PERMISSION",
        "SCHEDULE",
        "MANAGE_TASK",
        "DEFINE_SUBAGENT",
        "INVOKE_SUBAGENT",
        "SEND_MESSAGE",
        "MANAGE_SUBAGENTS",
    }
)


def _clean_val(v: Any) -> Any:
    """Clean string values that have outer double quotes."""
    if isinstance(v, str) and v.startswith('"') and v.endswith('"') and len(v) >= 2:
        return v[1:-1]
    return v


def load_agy_transcript(jsonl_path: Path) -> NormalizedSession:
    """Tolerantly parse an agy JSONL transcript into a NormalizedSession.

    Audit note (task aops_6d2abff5, criterion S6): agy JSONL log streams are event
    logs emitted by the agy TUI and do not carry LLM API usage blocks (input_tokens,
    cache_creation, etc.). Therefore, load_agy_transcript initializes NormalizedSession
    with tokens_used=0 and cost_usd=0.0. Token and cost accounting applies only to
    Claude Code transcripts.
    """
    session_id = "unknown"
    for i, part in enumerate(jsonl_path.parts):
        if part == ".system_generated" and i > 0:
            session_id = jsonl_path.parts[i - 1]
            break
    if session_id == "unknown":
        session_id = jsonl_path.stem

    events: list[NormalizedEvent] = []
    raw_events: list[NormalizedRawEntry] = []

    try:
        text = jsonl_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        logger.warning("could not read %s", jsonl_path, exc_info=True)
        return NormalizedSession(session_id=session_id, source_file=jsonl_path)

    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("%s:%d is not valid JSON, skipping", jsonl_path, line_no)
            continue

        if not isinstance(obj, dict):
            continue

        entry_type = obj.get("type")
        if entry_type not in KNOWN_AGY_TYPES:
            logger.warning(
                "%s:%d: unrecognized transcript entry type %r, preserving as raw",
                jsonl_path,
                line_no,
                entry_type,
            )
            raw_events.append(
                NormalizedRawEntry(
                    line_no=line_no,
                    type=entry_type,
                    raw=obj,
                )
            )
            continue

        try:
            step_index = obj.get("step_index", 0)
            created_at = obj.get("created_at", "")
            source = obj.get("source", "")
            content = obj.get("content", "")

            # Normalize source
            norm_source = "system"
            if source == "USER_EXPLICIT":
                norm_source = "user"
            elif source == "MODEL":
                norm_source = "model"
            elif entry_type in KNOWN_AGY_TYPES - {
                "USER_INPUT",
                "CONVERSATION_HISTORY",
                "PLANNER_RESPONSE",
                "CHECKPOINT",
            }:
                norm_source = "tool"

            # Normalize event type
            if entry_type == "USER_INPUT":
                norm_type = "message"
            elif entry_type == "PLANNER_RESPONSE":
                norm_type = "message"
            elif entry_type == "CHECKPOINT":
                norm_type = "checkpoint"
            elif entry_type == "CONVERSATION_HISTORY":
                norm_type = "system"
            else:
                norm_type = "tool_output"

            thinking = obj.get("thinking")
            if thinking is not None:
                thinking = str(thinking)

            tool_calls_raw = obj.get("tool_calls")
            tool_calls = None
            if isinstance(tool_calls_raw, list):
                tool_calls = []
                for tc in tool_calls_raw:
                    if isinstance(tc, dict):
                        tc_name = _clean_val(tc.get("name", ""))
                        args_raw = tc.get("args", {})
                        cleaned_args = {}
                        if isinstance(args_raw, dict):
                            cleaned_args = {k: _clean_val(v) for k, v in args_raw.items()}
                        tool_calls.append(
                            NormalizedToolCall(
                                name=tc_name,
                                args=cleaned_args,
                            )
                        )

            meta = {}
            for k, v in obj.items():
                if k not in {
                    "step_index",
                    "created_at",
                    "source",
                    "content",
                    "thinking",
                    "tool_calls",
                    "type",
                    "status",
                }:
                    meta[k] = v

            if entry_type not in {
                "USER_INPUT",
                "CONVERSATION_HISTORY",
                "PLANNER_RESPONSE",
                "CHECKPOINT",
            }:
                meta["tool_name"] = entry_type

            if norm_source == "user":
                classification = classify_user_prompt(content, meta)
                meta.update(classification)

            events.append(
                NormalizedEvent(
                    event_id=f"step_{step_index}",
                    timestamp=created_at,
                    source=norm_source,
                    type=norm_type,
                    content=content,
                    thinking=thinking,
                    tool_calls=tool_calls,
                    meta=meta,
                )
            )
        except Exception:
            logger.exception("failed to parse agy transcript line %d; preserving as raw", line_no)
            raw_events.append(
                NormalizedRawEntry(
                    line_no=line_no,
                    type=entry_type,
                    raw=obj,
                )
            )

    return NormalizedSession(
        session_id=session_id,
        source_file=jsonl_path,
        events=events,
        raw_events=raw_events,
    )
