#!/usr/bin/env python3
"""
agy_tracer.py — OpenInference tracer for Antigravity (agy) hooks.

Uses the same OpenTelemetry core as claude_code_tracer but maps
agy's native hook lifecycle (PreInvocation, PostInvocation, Stop) to traces.
"""

import json
import os
import time

from claude_code_tracer import (
    _build_and_export_spans,
    _build_tool_span_record,
    _delete_state,
    _load_state,
    _new_span_id,
    _new_trace_id,
    _save_state,
    _session_lock,
    _truncate,
)


def _find_pending_tool_entry_for_agy(state: dict, tool_name: str) -> tuple[dict, str]:
    pt = state.get("pending_tools", {})
    if tool_name in pt:
        return pt[tool_name], tool_name
    for k, v in pt.items():
        if v.get("tool_name") == tool_name:
            return v, k
    return {}, tool_name


def _is_human_message_agy(entry: dict) -> bool:
    return entry.get("type") == "USER_INPUT"


def _extract_llm_spans_for_turn_agy(
    transcript_path: str, human_count_at_start: int, trace_id_hex: str, root_span_id_hex: str
) -> list[dict]:
    spans = []
    try:
        lines = open(transcript_path).read().splitlines()
        human_count = 0
        in_turn = False

        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)

                if _is_human_message_agy(entry):
                    human_count += 1
                    if human_count == human_count_at_start + 1:
                        in_turn = True
                    elif in_turn:
                        break  # Next turn started

                if not in_turn:
                    continue

                if entry.get("source") == "MODEL" and entry.get("type") == "PLANNER_RESPONSE":
                    content = entry.get("content", "")
                    tool_calls = entry.get("tool_calls", [])
                    ts = entry.get("created_at", "")
                    start_ns = time.time_ns()
                    if ts:
                        from datetime import datetime

                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        start_ns = int(dt.timestamp() * 1_000_000_000)

                    attrs = {
                        "openinference.span.kind": "LLM",
                        "llm.model_name": "gemini-pro-agent",
                        "llm.output_messages.0.message.role": "assistant",
                    }
                    if content:
                        attrs["llm.output_messages.0.message.content"] = _truncate(content)

                    if tool_calls:
                        attrs["output.mime_type"] = "application/json"
                        attrs["output.value"] = _truncate(json.dumps(tool_calls))
                        for i, tc in enumerate(tool_calls):
                            attrs[
                                f"llm.output_messages.0.message.tool_calls.{i}.tool_call.function.name"
                            ] = tc.get("name", "")
                            attrs[
                                f"llm.output_messages.0.message.tool_calls.{i}.tool_call.function.arguments"
                            ] = _truncate(json.dumps(tc.get("args", {})))
                    else:
                        attrs["output.mime_type"] = "text/plain"
                        attrs["output.value"] = _truncate(content)

                    spans.append(
                        {
                            "name": "LLM",
                            "kind": None,
                            "start_ns": start_ns,
                            "end_ns": start_ns + 1_000_000,  # Fake 1ms duration
                            "trace_id_hex": trace_id_hex,
                            "span_id_hex": _new_span_id(),
                            "attrs": attrs,
                        }
                    )
            except Exception:
                pass
    except Exception:
        pass
    return spans


def handle_pre_invocation(data: dict, config: dict) -> None:
    """Handle PreInvocation (turn start)."""
    session_id = data.get("conversationId", "unknown")
    invocation_num = data.get("invocationNum")
    now_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)

        # Turn boundary: invocationNum == 0 or no active trace
        if invocation_num == 0 or not state.get("current_trace"):
            state["session_id"] = session_id
            state["session_start_ns"] = state.get("session_start_ns") or now_ns

            transcript_path = data.get("transcriptPath", "")
            if transcript_path:
                state["transcript_path"] = transcript_path

            human_count = 0
            if transcript_path and os.path.exists(transcript_path):
                try:
                    for line in open(transcript_path).read().splitlines():
                        if not line.strip():
                            continue
                        try:
                            if _is_human_message_agy(json.loads(line)):
                                human_count += 1
                        except Exception:
                            pass
                except Exception:
                    pass

            turn_number = state.get("turn_number", 0) + 1
            state["turn_number"] = turn_number
            state["human_msg_count"] = human_count
            state["current_trace"] = {
                "trace_id": _new_trace_id(),
                "root_span_id": _new_span_id(),
                "turn_start_ns": now_ns,
                "turn_number": turn_number,
                "human_count_at_start": max(0, human_count - 1),
                "prompt_preview": "",  # filled at stop
            }
            state["pending_tools"] = {}
        _save_state(session_id, state)


def handle_post_invocation(data: dict, config: dict) -> None:
    """Handle PostInvocation. Nothing needed for OTel."""
    pass


def handle_pre_tool(data: dict, config: dict) -> None:
    """Handle PreToolUse."""
    tool_call = data.get("toolCall")
    if not tool_call:
        return

    session_id = data.get("conversationId", "unknown")
    now_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state.get("current_trace"):
            return

        tool_name = tool_call.get("name", "unknown")
        tool_input = tool_call.get("args", {})

        trace_id = state["current_trace"]["trace_id"]
        root_span_id = state["current_trace"]["root_span_id"]

        pending_key = f"{tool_name}_{now_ns}"
        pt = state.setdefault("pending_tools", {})
        pt[pending_key] = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "start_ns": now_ns,
            "pre_allocated_span_id": _new_span_id(),
            "trace_id": trace_id,
            "root_span_id": root_span_id,
        }
        _save_state(session_id, state)


def handle_post_tool(data: dict, config: dict) -> None:
    """Handle PostToolUse."""
    tool_call = data.get("toolCall")
    if not tool_call:
        return

    session_id = data.get("conversationId", "unknown")
    end_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state.get("current_trace"):
            return

        tool_name = tool_call.get("name", "unknown")
        tool_input = tool_call.get("args", {})
        error_msg = data.get("error", "")

        current_tool, pending_key = _find_pending_tool_entry_for_agy(state, tool_name)
        start_ns = current_tool.get("start_ns", end_ns - 1_000_000)
        span_id = current_tool.get("pre_allocated_span_id") or _new_span_id()

        is_failure = bool(error_msg)

        span_record = _build_tool_span_record(
            tool_name=tool_name,
            tool_input=current_tool.get("tool_input", tool_input),
            tool_response={"error": error_msg} if is_failure else {},
            start_ns=start_ns,
            end_ns=end_ns,
            trace_id=state["current_trace"]["trace_id"],
            root_span_id=state["current_trace"]["root_span_id"],
            span_id=span_id,
            is_failure=is_failure,
            error_msg=error_msg,
        )

        _build_and_export_spans(
            config=config,
            session_id=session_id,
            username=state.get("username", "unknown"),
            span_records=[span_record],
        )

        pt = state.get("pending_tools", {})
        pt.pop(pending_key, None)
        pt.pop(tool_name, None)
        _save_state(session_id, state)


def handle_stop(data: dict, config: dict) -> None:
    """Handle Stop event (turn end)."""
    session_id = data.get("conversationId", "unknown")
    end_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state.get("current_trace"):
            return

        transcript_path = data.get("transcriptPath") or state.get("transcript_path")
        if not transcript_path or not os.path.exists(transcript_path):
            _delete_state(session_id)
            return

        ct = state["current_trace"]
        trace_id = ct["trace_id"]
        root_span_id = ct["root_span_id"]

        # We need to construct LLM spans for the turn.
        # agy doesn't have token counts, so _extract_llm_spans_for_turn will return spans with 0 tokens.
        llm_spans = _extract_llm_spans_for_turn_agy(
            transcript_path=transcript_path,
            human_count_at_start=ct.get("human_count_at_start", 0),
            trace_id_hex=trace_id,
            root_span_id_hex=root_span_id,
        )

        # Find the user prompt preview to set as CHAIN name
        prompt_preview = "agy session"
        if llm_spans and llm_spans[0].get("llm.input_messages.0.message.content"):
            prompt_preview = _truncate(llm_spans[0]["llm.input_messages.0.message.content"])
        elif ct.get("prompt_preview"):
            prompt_preview = ct["prompt_preview"]

        # Emit CHAIN span
        chain_span = {
            "name": prompt_preview,
            "kind": None,  # Will be set to INTERNAL or similar
            "start_ns": ct["turn_start_ns"],
            "end_ns": end_ns,
            "trace_id_hex": trace_id,
            "span_id_hex": root_span_id,
            "force_span_id": True,
            "attrs": {
                "openinference.span.kind": "CHAIN",
                "session.id": session_id,
            },
        }

        records = [chain_span]
        for span in llm_spans:
            # agy doesn't have usage attributes, remove them if we want to be clean
            for k in list(span["attrs"].keys()):
                if k.startswith("llm.token_count"):
                    del span["attrs"][k]
            records.append(span)

        _build_and_export_spans(
            config=config,
            session_id=session_id,
            username=state.get("username", "unknown"),
            span_records=records,
        )

        _delete_state(session_id)
