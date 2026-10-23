#!/usr/bin/env python3
"""
agy_tracer.py — OpenInference tracer for Antigravity (agy) hooks.

Uses the same OpenTelemetry core as claude_code_tracer but maps
agy's native hook lifecycle (PreInvocation, PreToolUse, PostToolUse, Stop) to traces.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("orchestrate.agy_tracer")

try:
    from token_extractor import resolve_gemini_model, resolve_gemini_tokens
except ImportError:
    try:
        from .token_extractor import resolve_gemini_model, resolve_gemini_tokens
    except Exception:
        resolve_gemini_tokens = None
        resolve_gemini_model = None

from claude_code_tracer import (
    _build_and_export_spans,
    _build_tool_span_record,
    _delete_state,
    _load_state,
    _new_span_id,
    _new_trace_id,
    _resolve_agent_and_parent_ids,
    _save_state,
    _session_lock,
    _truncate,
    resolve_agent_name,
    resolve_client_agent_name,
    resolve_session_id,
)
from claude_code_tracer import discover_config as discover_config  # re-exported for handlers.py

# Maximum input messages attached as llm.input_messages.{i}.* on a single LLM span.
# OpenTelemetry's BoundedAttributes defaults to maxlen=128 with FIFO eviction;
# capping at 32 messages (64 attributes) ensures core OpenInference attributes
# (openinference.span.kind, input.value, output.value, session.id) are never evicted.
MAX_INPUT_MESSAGES_PER_SPAN = 32


def _is_human_message_agy(entry: dict) -> bool:
    return entry.get("type") == "USER_INPUT"


def _is_turn_start_entry_agy(entry: dict) -> bool:
    return entry.get("type") in ("USER_INPUT", "SYSTEM_MESSAGE")


def _resolve_transcript_path_agy(data: dict, state: dict, session_id: str) -> str:
    transcript_path = (
        data.get("transcriptPath")
        or data.get("transcript_path")
        or state.get("transcript_path")
        or ""
    )
    if transcript_path:
        return transcript_path
    for app_dir_name in ("antigravity", "antigravity-cli"):
        possible_path = (
            Path.home()
            / ".gemini"
            / app_dir_name
            / "brain"
            / session_id
            / ".system_generated"
            / "logs"
            / "transcript.jsonl"
        )
        if possible_path.exists():
            return str(possible_path)
    return ""


def _read_transcript_entries_agy(transcript_path: str) -> list[dict]:
    if not transcript_path or not os.path.exists(transcript_path):
        return []
    entries: list[dict] = []
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    except Exception as e:
        log.debug("Failed to read agy transcript %s: %s", transcript_path, e)
    return entries


def _find_pending_tool_entry_for_agy(
    state: dict,
    tool_name: str,
    tool_input: dict | None = None,
) -> tuple[dict, str]:
    pt = state.get("pending_tools", {})
    if tool_input is not None:
        for k, v in pt.items():
            if v.get("tool_name") == tool_name and v.get("tool_input") == tool_input:
                return v, k
    if tool_name in pt:
        return pt[tool_name], tool_name
    for k, v in pt.items():
        if v.get("tool_name") == tool_name:
            return v, k
    return {}, tool_name


def _extract_tool_output_from_transcript_agy(
    transcript_path: str,
) -> tuple[Any, bool, str]:
    """Extract the latest tool execution output from transcript.jsonl.

    Returns (tool_response, is_failure, error_msg).
    """
    entries = _read_transcript_entries_agy(transcript_path)
    for entry in reversed(entries):
        if entry.get("type") == "GENERIC":
            content = entry.get("content", "")
            status = entry.get("status", "DONE")
            is_err = status == "ERROR"
            err_msg = content if is_err else ""
            return content, is_err, err_msg
    return {}, False, ""


def _extract_tool_output_for_call_agy(
    transcript_path: str,
    expected_generic_ordinal: int | None,
) -> tuple[bool, Any, bool, str]:
    """Extract the specific GENERIC entry for a tool call by its 0-based ordinal.

    agy fires PostToolUse before appending the tool's GENERIC entry to
    transcript.jsonl. Matching by ``expected_generic_ordinal`` ensures a tool
    span never reads the previous tool call's GENERIC entry when its own entry
    has not been flushed yet.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return False, {}, False, ""
    entries = _read_transcript_entries_agy(transcript_path)
    generics = [e for e in entries if e.get("type") == "GENERIC"]
    if expected_generic_ordinal is None:
        if not generics:
            return False, {}, False, ""
        target = generics[-1]
    else:
        if expected_generic_ordinal < 0 or expected_generic_ordinal >= len(generics):
            return False, {}, False, ""
        target = generics[expected_generic_ordinal]

    content = target.get("content", "")
    status = target.get("status", "DONE")
    is_err = status == "ERROR"
    err_msg = content if is_err else ""
    return True, content, is_err, err_msg


def _export_tool_span_agy(
    state: dict,
    data: dict,
    config: dict,
    tool_record: dict,
    tool_response: Any,
    is_failure: bool,
    error_msg: str,
) -> None:
    if tool_response is None:
        tool_response = {"error": error_msg} if is_failure else {}

    span_record = _build_tool_span_record(
        tool_name=tool_record["tool_name"],
        tool_input=tool_record.get("tool_input", {}),
        tool_response=tool_response,
        start_ns=tool_record["start_ns"],
        end_ns=tool_record["end_ns"],
        trace_id=tool_record["trace_id"],
        root_span_id=tool_record["root_span_id"],
        span_id=tool_record["span_id"],
        is_failure=is_failure,
        error_msg=error_msg,
        tool_call_id=tool_record.get("tool_call_id"),
    )

    phoenix_session_id, agent_id, parent_session_id = _resolve_agent_and_parent_ids(
        state,
        data,
        "conversationId",
    )

    _build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=state.get("username"),
        span_records=[span_record],
        agent_id=agent_id,
        parent_session_id=parent_session_id,
        agent_name=state.get("agent_name")
        or config.get("agent_name", "")
        or resolve_agent_name(data),
        cwd=state.get("cwd") or config.get("cwd"),
        service_name="aops-agy-hooks",
        surface="agy",
    )


def _flush_deferred_tool_spans(
    state: dict,
    transcript_path: str,
    data: dict,
    config: dict,
    *,
    flush_unmatched: bool = False,
) -> None:
    """Export any deferred tool spans whose GENERIC output is now in transcript.jsonl."""
    deferred = state.get("deferred_tool_spans") or []
    if not deferred:
        return

    remaining: list[dict] = []
    for item in deferred:
        found, tr_out, tr_err, tr_msg = _extract_tool_output_for_call_agy(
            transcript_path,
            item.get("expected_generic_ordinal"),
        )
        if found:
            is_failure = bool(item.get("is_failure")) or tr_err
            error_msg = item.get("error_msg") or tr_msg
            _export_tool_span_agy(
                state=state,
                data=data,
                config=config,
                tool_record=item,
                tool_response=tr_out,
                is_failure=is_failure,
                error_msg=error_msg,
            )
        elif flush_unmatched:
            is_failure = bool(item.get("is_failure"))
            error_msg = item.get("error_msg", "")
            _export_tool_span_agy(
                state=state,
                data=data,
                config=config,
                tool_record=item,
                tool_response={"error": error_msg} if is_failure else {},
                is_failure=is_failure,
                error_msg=error_msg,
            )
        else:
            remaining.append(item)

    state["deferred_tool_spans"] = remaining


def _extract_llm_spans_for_turn_agy(
    transcript_path: str,
    human_count_at_start: int,
    trace_id_hex: str,
    root_span_id_hex: str,
    session_id: str | None = None,
    start_line_index: int | None = None,
    emitted_llm_steps: list[int] | set[int] | None = None,
) -> list[dict]:
    spans: list[dict] = []
    emitted_set = set(emitted_llm_steps) if emitted_llm_steps else set()
    try:
        entries = _read_transcript_entries_agy(transcript_path)
        human_count = 0
        in_turn = False
        seen_turn_opener = False

        # Track input for the next LLM call in the turn (reset after each PLANNER_RESPONSE
        # so attribute count stays bounded well under OpenTelemetry's 128-attribute cap).
        last_input_value = ""
        last_input_mime = "text/plain"
        last_input_content = ""
        step_input_messages: list[dict[str, str]] = []

        for idx, entry in enumerate(entries):
            try:
                entry_type = entry.get("type", "")
                entry_source = entry.get("source", "")

                if start_line_index is not None:
                    if idx < start_line_index:
                        continue
                    if not in_turn:
                        in_turn = True
                        if _is_turn_start_entry_agy(entry):
                            seen_turn_opener = True
                            opener_text = entry.get("content", "")
                            role = "user" if entry_type == "USER_INPUT" else "system"
                            last_input_value = json.dumps(
                                {"role": role, "content": opener_text[:500]}
                            )
                            last_input_mime = "application/json"
                            last_input_content = _truncate(opener_text)
                            step_input_messages.append({"role": role, "content": opener_text})
                            continue
                    elif _is_human_message_agy(entry) and seen_turn_opener:
                        break  # Next turn started
                    elif _is_human_message_agy(entry) and not seen_turn_opener:
                        seen_turn_opener = True
                        human_text = entry.get("content", "")
                        last_input_value = json.dumps({"role": "user", "content": human_text[:500]})
                        last_input_mime = "application/json"
                        last_input_content = _truncate(human_text)
                        step_input_messages.append({"role": "user", "content": human_text})
                        continue
                else:
                    if _is_human_message_agy(entry):
                        human_count += 1
                        if human_count == human_count_at_start + 1:
                            in_turn = True
                            seen_turn_opener = True
                            human_text = entry.get("content", "")
                            last_input_value = json.dumps(
                                {"role": "user", "content": human_text[:500]}
                            )
                            last_input_mime = "application/json"
                            last_input_content = _truncate(human_text)
                            step_input_messages = [{"role": "user", "content": human_text}]
                        elif in_turn:
                            break  # Next turn started
                        continue

                if not in_turn:
                    continue

                if entry_type == "GENERIC" or entry_source == "TOOL":
                    tool_content = entry.get("content", "")
                    if tool_content:
                        last_input_value = json.dumps(
                            {"role": "tool", "content": tool_content[:500]}
                        )
                        last_input_mime = "application/json"
                        last_input_content = _truncate(tool_content)
                        step_input_messages.append({"role": "tool", "content": tool_content})
                    continue

                if entry_type in ("EPHEMERAL_MESSAGE", "CHECKPOINT"):
                    continue
                if entry_source == "SYSTEM" or entry_type == "SYSTEM_MESSAGE":
                    sys_text = entry.get("content", "")
                    if sys_text:
                        last_input_value = json.dumps({"role": "system", "content": sys_text[:500]})
                        last_input_mime = "application/json"
                        last_input_content = _truncate(sys_text)
                        step_input_messages.append({"role": "system", "content": sys_text})
                    continue

                if entry_source == "MODEL" and entry_type == "PLANNER_RESPONSE":
                    step_index = entry.get("step_index")
                    if step_index is not None and step_index in emitted_set:
                        step_input_messages = []
                        continue

                    content = entry.get("content", "")
                    tool_calls = entry.get("tool_calls", [])
                    ts = entry.get("created_at", "")
                    thinking = entry.get("thinking", "")
                    start_ns = time.time_ns()
                    if ts:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        start_ns = int(dt.timestamp() * 1_000_000_000)

                    attrs: dict[str, Any] = {
                        "openinference.span.kind": "LLM",
                        "llm.provider": "google",
                        "input.value": last_input_value,
                        "input.mime_type": last_input_mime,
                        "llm.output_messages.0.message.role": "assistant",
                    }
                    if resolve_gemini_model is not None:
                        model_id = resolve_gemini_model(
                            session_id=session_id,
                            transcript_path=transcript_path,
                            step_index=step_index,
                            reported_model=entry.get("model") or entry.get("model_name"),
                        )
                        if model_id:
                            attrs["llm.model_name"] = model_id
                    bounded_msgs = step_input_messages[-MAX_INPUT_MESSAGES_PER_SPAN:]
                    for i, m in enumerate(bounded_msgs):
                        attrs[f"llm.input_messages.{i}.message.role"] = m["role"]
                        attrs[f"llm.input_messages.{i}.message.content"] = _truncate(m["content"])

                    if content:
                        attrs["llm.output_messages.0.message.content"] = _truncate(content)
                    if thinking:
                        attrs["llm.reasoning"] = _truncate(thinking)

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

                    if resolve_gemini_tokens is not None:
                        tok = resolve_gemini_tokens(
                            session_id=session_id,
                            transcript_path=transcript_path,
                            step_index=step_index,
                            input_text=last_input_content,
                            output_text=content,
                            thinking_text=thinking,
                            reported_input_tokens=entry.get("input_tokens"),
                            reported_cache_read_tokens=entry.get("cache_read_tokens"),
                            reported_output_tokens=entry.get("output_tokens"),
                        )
                        attrs["llm.token_count.prompt"] = tok["prompt"]
                        attrs["llm.token_count.completion"] = tok["completion"]
                        attrs["llm.token_count.total"] = tok["total"]
                        if tok.get("cache_read"):
                            attrs["llm.token_count.prompt_details.cache_read"] = tok["cache_read"]
                            attrs["llm.token_count.prompt_details.cache_write"] = 0
                        attrs["llm.token_count.type"] = tok["type"]
                        attrs["llm.token_count.provenance"] = tok["type"]
                        attrs["llm.token_count.estimate_method"] = tok["estimate_method"]
                        attrs["llm.token_count.estimation_method"] = tok["estimate_method"]
                        attrs["token_count.type"] = tok["type"]
                        attrs["token_count.provenance"] = tok["type"]
                        attrs["token_count.estimate_method"] = tok["estimate_method"]

                    spans.append(
                        {
                            "name": "LLM",
                            "kind": None,
                            "start_ns": start_ns,
                            "end_ns": start_ns + 1_000_000,  # Fake 1ms duration
                            "trace_id_hex": trace_id_hex,
                            "span_id_hex": _new_span_id(),
                            "parent_span_id_hex": root_span_id_hex,
                            "attributes": attrs,
                            "step_index": step_index,
                            "assistant_text": content,
                        }
                    )
                    step_input_messages = []
            except Exception:
                pass
    except Exception:
        pass
    return spans


def _init_turn_state_agy(
    state: dict,
    data: dict,
    session_id: str,
    now_ns: int,
    *,
    from_mid_turn: bool = False,
) -> None:
    state["session_id"] = session_id
    state["phoenix_session_id"] = state.get("phoenix_session_id") or resolve_session_id(
        data,
        "conversationId",
        prefer_env=True,
    )
    state["session_start_ns"] = state.get("session_start_ns") or now_ns
    state["username"] = os.environ.get("USER") or os.environ.get("USERNAME") or None
    state["cwd"] = data.get("cwd") or state.get("cwd") or os.getcwd()
    client_agent = resolve_client_agent_name(data)
    if client_agent:
        state["agent_name"] = client_agent

    transcript_path = _resolve_transcript_path_agy(data, state, session_id)
    if transcript_path:
        state["transcript_path"] = transcript_path

    entries = _read_transcript_entries_agy(transcript_path)
    human_count = sum(1 for e in entries if _is_human_message_agy(e))

    # Anchor turn at the latest USER_INPUT or SYSTEM_MESSAGE entry in transcript.jsonl
    start_line_index = len(entries)
    turn_prompt = ""
    for idx in range(len(entries) - 1, -1, -1):
        if _is_turn_start_entry_agy(entries[idx]):
            start_line_index = idx
            turn_prompt = entries[idx].get("content", "")
            break

    # Count GENERIC entries before this turn (or before the latest PLANNER_RESPONSE if mid-turn)
    if from_mid_turn and entries:
        last_pr_idx = None
        for idx in range(len(entries) - 1, -1, -1):
            if (
                entries[idx].get("source") == "MODEL"
                and entries[idx].get("type") == "PLANNER_RESPONSE"
            ):
                last_pr_idx = idx
                break
        if last_pr_idx is not None:
            generic_base = sum(1 for e in entries[:last_pr_idx] if e.get("type") == "GENERIC")
        else:
            generic_base = sum(1 for e in entries[:start_line_index] if e.get("type") == "GENERIC")
    else:
        generic_base = sum(1 for e in entries[:start_line_index] if e.get("type") == "GENERIC")

    state["next_generic_ordinal"] = max(state.get("next_generic_ordinal", 0), generic_base)

    turn_number = state.get("turn_number", 0) + 1
    state["turn_number"] = turn_number
    state["human_msg_count"] = human_count

    parent_trace_id = None
    parent_span_id = None
    psid = state.get("phoenix_session_id")
    if psid and psid != session_id:
        try:
            pstate = _load_state(psid)
            if pstate and pstate.get("current_trace"):
                parent_trace_id = pstate["current_trace"]["trace_id"]

            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
            if project_dir:
                sanitized = project_dir.replace("/", "-")
                sidecar = (
                    Path.home()
                    / ".claude"
                    / "projects"
                    / sanitized
                    / psid
                    / "subagents"
                    / f"agent-{session_id}.meta.json"
                )
                if sidecar.exists():
                    sdata = json.loads(sidecar.read_text(encoding="utf-8"))
                    tuid = sdata.get("toolUseId")
                    if tuid:
                        parent_span_id = hashlib.sha256(tuid.encode()).hexdigest()[:16]
        except Exception as e:
            log.debug("Failed to parent agy subagent: %s", e)

    state["current_trace"] = {
        "trace_id": parent_trace_id if parent_trace_id else _new_trace_id(),
        "root_span_id": _new_span_id(),
        "parent_span_id": parent_span_id,
        "turn_start_ns": now_ns,
        "turn_number": turn_number,
        "human_count_at_start": max(0, human_count - 1),
        "start_line_index": start_line_index,
        "turn_prompt": turn_prompt,
        "prompt_preview": _truncate(turn_prompt) if turn_prompt else "",
    }
    state["surface"] = "agy"
    state["pending_tools"] = {}
    state.setdefault("deferred_tool_spans", [])
    state.setdefault("emitted_llm_steps", [])


def _end_turn_agy(session_id: str, state: dict) -> None:
    """Clear per-turn trace state while preserving session-level counters and emitted steps."""
    state.pop("current_trace", None)
    state.pop("pending_tools", None)
    state.pop("deferred_tool_spans", None)
    _save_state(session_id, state)


def handle_pre_invocation(data: dict, config: dict) -> None:
    """Handle PreInvocation (turn start)."""
    session_id = resolve_session_id(data, "conversationId")
    if session_id is None:
        log.warning(
            "handle_pre_invocation: no session id in payload ('conversationId' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    invocation_num = data.get("invocationNum")
    now_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        transcript_path = _resolve_transcript_path_agy(data, state, session_id)
        if transcript_path:
            state["transcript_path"] = transcript_path
            _flush_deferred_tool_spans(
                state,
                transcript_path,
                data,
                config,
                flush_unmatched=False,
            )

        # Turn boundary: invocationNum == 0 or no active trace
        if invocation_num == 0 or not state.get("current_trace"):
            _init_turn_state_agy(state, data, session_id, now_ns, from_mid_turn=False)
        _save_state(session_id, state)


def handle_post_invocation(data: dict, config: dict) -> None:
    """Handle PostInvocation. Nothing needed for OTel."""
    pass


def handle_pre_tool(data: dict, config: dict) -> None:
    """Handle PreToolUse."""
    tool_call = data.get("toolCall")
    if not tool_call:
        return

    session_id = resolve_session_id(data, "conversationId")
    if session_id is None:
        log.warning(
            "handle_pre_tool: no session id in payload ('conversationId' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    now_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state.get("current_trace"):
            _init_turn_state_agy(state, data, session_id, now_ns, from_mid_turn=True)

        transcript_path = _resolve_transcript_path_agy(data, state, session_id)
        if transcript_path:
            state["transcript_path"] = transcript_path
            _flush_deferred_tool_spans(
                state,
                transcript_path,
                data,
                config,
                flush_unmatched=False,
            )

        tool_name = tool_call.get("name", "unknown")
        tool_input = tool_call.get("args", {})

        trace_id = state["current_trace"]["trace_id"]
        root_span_id = state["current_trace"]["root_span_id"]

        # Assign the 0-based GENERIC ordinal this tool call will occupy in transcript.jsonl
        expected_generic_ordinal = state.get("next_generic_ordinal", 0)
        if transcript_path:
            entries = _read_transcript_entries_agy(transcript_path)
            if entries:
                # If the latest entry is a PLANNER_RESPONSE (live agy execution), ensure
                # next_generic_ordinal is at least the count of GENERIC entries before it.
                last_pr_idx = None
                for idx in range(len(entries) - 1, -1, -1):
                    if (
                        entries[idx].get("source") == "MODEL"
                        and entries[idx].get("type") == "PLANNER_RESPONSE"
                    ):
                        last_pr_idx = idx
                        break
                if last_pr_idx is not None and not any(
                    e.get("source") == "MODEL" and e.get("type") == "PLANNER_RESPONSE"
                    for e in entries[last_pr_idx + 1 :]
                ):
                    g_before_last_pr = sum(
                        1 for e in entries[:last_pr_idx] if e.get("type") == "GENERIC"
                    )
                    if expected_generic_ordinal < g_before_last_pr:
                        expected_generic_ordinal = g_before_last_pr
        state["next_generic_ordinal"] = expected_generic_ordinal + 1

        pending_key = f"{tool_name}_{now_ns}"
        pt = state.setdefault("pending_tools", {})

        agent_span_id = _new_span_id()
        if tool_name in ("Agent", "Task", "invoke_subagent"):
            tuid = tool_call.get("id") or tool_call.get("toolUseId")
            if tuid:
                agent_span_id = hashlib.sha256(tuid.encode()).hexdigest()[:16]

        pt[pending_key] = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "start_ns": now_ns,
            "pre_allocated_span_id": agent_span_id,
            "trace_id": trace_id,
            "root_span_id": root_span_id,
            "expected_generic_ordinal": expected_generic_ordinal,
        }
        _save_state(session_id, state)


def handle_post_tool(data: dict, config: dict) -> None:
    """Handle PostToolUse."""
    tool_call = data.get("toolCall")
    if not tool_call:
        return

    session_id = resolve_session_id(data, "conversationId")
    if session_id is None:
        log.warning(
            "handle_post_tool: no session id in payload ('conversationId' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    end_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state.get("current_trace"):
            _init_turn_state_agy(state, data, session_id, end_ns, from_mid_turn=True)

        transcript_path = _resolve_transcript_path_agy(data, state, session_id)
        if transcript_path:
            state["transcript_path"] = transcript_path
            _flush_deferred_tool_spans(
                state,
                transcript_path,
                data,
                config,
                flush_unmatched=False,
            )

        tool_name = tool_call.get("name", "unknown")
        tool_input = tool_call.get("args", {})
        error_msg = data.get("error", "")

        current_tool, pending_key = _find_pending_tool_entry_for_agy(state, tool_name, tool_input)
        start_ns = current_tool.get("start_ns", end_ns - 1_000_000)
        span_id = current_tool.get("pre_allocated_span_id") or _new_span_id()
        expected_generic_ordinal = current_tool.get("expected_generic_ordinal")

        pt = state.get("pending_tools", {})
        pt.pop(pending_key, None)
        pt.pop(tool_name, None)

        tool_call_id = data.get("tool_call_id") or data.get("id") or data.get("tool_use_id")
        tool_record = {
            "tool_name": tool_name,
            "tool_input": current_tool.get("tool_input", tool_input),
            "start_ns": start_ns,
            "end_ns": end_ns,
            "trace_id": state["current_trace"]["trace_id"],
            "root_span_id": state["current_trace"]["root_span_id"],
            "span_id": span_id,
            "tool_call_id": tool_call_id,
            "expected_generic_ordinal": expected_generic_ordinal,
            "is_failure": bool(error_msg),
            "error_msg": error_msg,
        }

        tool_response = data.get("tool_response") or data.get("toolResponse")
        is_failure = bool(error_msg)

        if tool_response is not None or is_failure:
            _export_tool_span_agy(
                state=state,
                data=data,
                config=config,
                tool_record=tool_record,
                tool_response=tool_response,
                is_failure=is_failure,
                error_msg=error_msg,
            )
            _save_state(session_id, state)
            return

        if transcript_path:
            found, tr_out, tr_err, tr_msg = _extract_tool_output_for_call_agy(
                transcript_path,
                expected_generic_ordinal,
            )
            if found:
                _export_tool_span_agy(
                    state=state,
                    data=data,
                    config=config,
                    tool_record=tool_record,
                    tool_response=tr_out,
                    is_failure=tr_err,
                    error_msg=tr_msg,
                )
            else:
                state.setdefault("deferred_tool_spans", []).append(tool_record)
        else:
            _export_tool_span_agy(
                state=state,
                data=data,
                config=config,
                tool_record=tool_record,
                tool_response={},
                is_failure=False,
                error_msg="",
            )

        _save_state(session_id, state)


def handle_stop(data: dict, config: dict) -> None:
    """Handle Stop event (turn end)."""
    session_id = resolve_session_id(data, "conversationId")
    if session_id is None:
        log.warning(
            "handle_stop: no session id in payload ('conversationId' missing) "
            "and $AOPS_SESSION_ID unset — skipping span emission",
        )
        return
    end_ns = time.time_ns()

    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state.get("current_trace"):
            return

        transcript_path = _resolve_transcript_path_agy(data, state, session_id)
        if not transcript_path or not os.path.exists(transcript_path):
            _delete_state(session_id)
            return

        # Flush any tool spans whose GENERIC output was written after PostToolUse
        _flush_deferred_tool_spans(
            state,
            transcript_path,
            data,
            config,
            flush_unmatched=True,
        )

        ct = state["current_trace"]
        trace_id = ct["trace_id"]
        root_span_id = ct["root_span_id"]

        llm_spans = _extract_llm_spans_for_turn_agy(
            transcript_path=transcript_path,
            human_count_at_start=ct.get("human_count_at_start", 0),
            trace_id_hex=trace_id,
            root_span_id_hex=root_span_id,
            session_id=session_id,
            start_line_index=ct.get("start_line_index"),
            emitted_llm_steps=state.get("emitted_llm_steps"),
        )

        emitted_steps = state.setdefault("emitted_llm_steps", [])
        for sp in llm_spans:
            step_idx = sp.get("step_index")
            if step_idx is not None and step_idx not in emitted_steps:
                emitted_steps.append(step_idx)

        # Find the user prompt and preview to set as CHAIN name and input.value
        first_llm_attrs = llm_spans[0].get("attributes", {}) if llm_spans else {}
        turn_input_text = (
            ct.get("turn_prompt")
            or first_llm_attrs.get("llm.input_messages.0.message.content")
            or first_llm_attrs.get("input.value")
            or ""
        )
        prompt_preview = "agy session"
        if turn_input_text:
            prompt_preview = _truncate(turn_input_text)
        elif ct.get("prompt_preview"):
            prompt_preview = ct["prompt_preview"]

        turn_output_text = data.get("last_assistant_message") or ""
        if not turn_output_text and llm_spans:
            for sp in reversed(llm_spans):
                sp_attrs = sp.get("attributes", {})
                candidate = (
                    sp.get("assistant_text")
                    or sp_attrs.get("llm.output_messages.0.message.content")
                    or sp_attrs.get("output.value")
                    or ""
                )
                if candidate:
                    turn_output_text = candidate
                    break

        phoenix_session_id, agent_id, parent_session_id = _resolve_agent_and_parent_ids(
            state,
            data,
            "conversationId",
        )
        agent_name = state.get("agent_name") or resolve_agent_name(data)

        chain_attrs: dict[str, Any] = {
            "openinference.span.kind": "AGENT" if ct.get("parent_span_id") else "CHAIN",
            "session.id": phoenix_session_id,
        }
        if turn_input_text:
            chain_attrs["input.value"] = _truncate(turn_input_text)
        if turn_output_text:
            chain_attrs["output.value"] = _truncate(turn_output_text)
        if agent_id:
            chain_attrs["agent.id"] = agent_id
            chain_attrs["subagent.id"] = agent_id
        if parent_session_id:
            chain_attrs["parent.session_id"] = parent_session_id
        if agent_name:
            chain_attrs["agent.name"] = agent_name

        # Token counts stay on the LLM spans only: Phoenix's cumulative counts
        # add a span's own tokens to its descendants', so totals on the CHAIN
        # root would count every turn twice.
        other_records: list[dict[str, Any]] = list(llm_spans)

        # Emit CHAIN span
        chain_span = {
            "name": prompt_preview,
            "kind": None,
            "start_ns": ct["turn_start_ns"],
            "end_ns": end_ns,
            "trace_id_hex": trace_id,
            "span_id_hex": root_span_id,
            "parent_span_id_hex": ct.get("parent_span_id"),
            "force_span_id": True,
            "attributes": chain_attrs,
        }
        records: list[dict[str, Any]] = [chain_span] + other_records

        _build_and_export_spans(
            config=config,
            session_id=phoenix_session_id,
            username=state.get("username"),
            span_records=records,
            agent_id=agent_id,
            parent_session_id=parent_session_id,
            agent_name=agent_name or config.get("agent_name", ""),
            cwd=state.get("cwd") or config.get("cwd"),
            service_name="aops-agy-hooks",
            surface="agy",
        )

        _end_turn_agy(session_id, state)
