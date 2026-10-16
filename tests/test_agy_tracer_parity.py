"""Behavioral tests for agy_tracer tool output attribution, turn state, and span parity."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

HOOKS_DIR = Path(__file__).resolve().parent.parent / "plugins" / "ida" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

import agy_tracer


def _append_jsonl(path: Path, entry: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def test_consecutive_tool_calls_attach_own_output_when_generic_flushes_after_post_tool(
    tmp_path: Path,
):
    """agy fires PostToolUse before appending the tool's GENERIC entry to
    transcript.jsonl. Each tool span must still receive its own output, never
    the previous command's output.
    """
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("", encoding="utf-8")
    state_store: dict[str, dict] = {}

    def load_state(sid: str) -> dict:
        return json.loads(json.dumps(state_store.get(sid, {})))

    def save_state(sid: str, st: dict) -> None:
        state_store[sid] = json.loads(json.dumps(st))

    def delete_state(sid: str) -> None:
        state_store.pop(sid, None)

    exported_records: list[dict] = []

    def mock_export(config, session_id, username, span_records, **kwargs):
        exported_records.extend(span_records)

    session_id = "session-tool-offset"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("agy_tracer._load_state", side_effect=load_state),
        patch("agy_tracer._save_state", side_effect=save_state),
        patch("agy_tracer._delete_state", side_effect=delete_state),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        # 1. User prompt written, then PreInvocation fires
        _append_jsonl(
            transcript,
            {"step_index": 0, "type": "USER_INPUT", "content": "Run three commands"},
        )
        agy_tracer.handle_pre_invocation(
            {
                "conversationId": session_id,
                "invocationNum": 0,
                "transcriptPath": str(transcript),
                "cwd": "/workspace/academicOps",
            },
            config,
        )

        # 2. Model issues command 1 (hostname); PostToolUse runs BEFORE GENERIC is written
        _append_jsonl(
            transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "tool_calls": [{"name": "run_command", "args": {"CommandLine": "hostname"}}],
            },
        )
        agy_tracer.handle_pre_tool(
            {
                "conversationId": session_id,
                "transcriptPath": str(transcript),
                "toolCall": {"name": "run_command", "args": {"CommandLine": "hostname"}},
            },
            config,
        )
        agy_tracer.handle_post_tool(
            {
                "conversationId": session_id,
                "transcriptPath": str(transcript),
                "toolCall": {"name": "run_command", "args": {"CommandLine": "hostname"}},
            },
            config,
        )
        # Now agy flushes command 1's GENERIC result
        _append_jsonl(
            transcript,
            {"step_index": 2, "source": "MODEL", "type": "GENERIC", "content": "d73c99a6793d\n"},
        )

        # 3. Model issues command 2 (bash test_polecat_isolation.sh); PostToolUse runs BEFORE GENERIC
        _append_jsonl(
            transcript,
            {
                "step_index": 3,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "tool_calls": [
                    {
                        "name": "run_command",
                        "args": {"CommandLine": "bash test_polecat_isolation.sh"},
                    }
                ],
            },
        )
        agy_tracer.handle_pre_tool(
            {
                "conversationId": session_id,
                "transcriptPath": str(transcript),
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": "bash test_polecat_isolation.sh"},
                },
            },
            config,
        )
        agy_tracer.handle_post_tool(
            {
                "conversationId": session_id,
                "transcriptPath": str(transcript),
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": "bash test_polecat_isolation.sh"},
                },
            },
            config,
        )
        # Now agy flushes command 2's GENERIC result
        _append_jsonl(
            transcript,
            {
                "step_index": 4,
                "source": "MODEL",
                "type": "GENERIC",
                "content": "isolation check: PASS\n",
            },
        )

        # 4. Model issues command 3 (uv pip install httpx); PostToolUse runs BEFORE GENERIC
        _append_jsonl(
            transcript,
            {
                "step_index": 5,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "tool_calls": [
                    {"name": "run_command", "args": {"CommandLine": "uv pip install httpx"}}
                ],
            },
        )
        agy_tracer.handle_pre_tool(
            {
                "conversationId": session_id,
                "transcriptPath": str(transcript),
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": "uv pip install httpx"},
                },
            },
            config,
        )
        agy_tracer.handle_post_tool(
            {
                "conversationId": session_id,
                "transcriptPath": str(transcript),
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": "uv pip install httpx"},
                },
            },
            config,
        )
        # Now agy flushes command 3's GENERIC result and final PLANNER_RESPONSE, then Stop fires
        _append_jsonl(
            transcript,
            {
                "step_index": 6,
                "source": "MODEL",
                "type": "GENERIC",
                "content": "Successfully installed httpx-0.28.1\n",
            },
        )
        _append_jsonl(
            transcript,
            {
                "step_index": 7,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "All three commands succeeded.",
            },
        )
        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

    tool_spans = [
        r
        for r in exported_records
        if r.get("attributes", {}).get("openinference.span.kind") == "TOOL"
    ]
    assert len(tool_spans) == 3
    assert "hostname" in tool_spans[0]["attributes"]["input.value"]
    assert "d73c99a6793d" in tool_spans[0]["attributes"]["output.value"]

    assert "test_polecat_isolation.sh" in tool_spans[1]["attributes"]["input.value"]
    assert "isolation check: PASS" in tool_spans[1]["attributes"]["output.value"]
    assert "d73c99a6793d" not in tool_spans[1]["attributes"]["output.value"]

    assert "uv pip install httpx" in tool_spans[2]["attributes"]["input.value"]
    assert "Successfully installed httpx-0.28.1" in tool_spans[2]["attributes"]["output.value"]
    assert "isolation check: PASS" not in tool_spans[2]["attributes"]["output.value"]


def test_handle_stop_sets_chain_input_output_and_passes_state_cwd(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {"step_index": 0, "type": "USER_INPUT", "content": "Explain OTel context propagation"},
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "content": "W3C TraceContext uses the traceparent header.",
            "input_tokens": 120,
            "cache_read_tokens": 30,
            "output_tokens": 40,
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

    state_store: dict[str, dict] = {}
    exported_calls: list[dict] = []

    def mock_export(config, session_id, username, span_records, **kwargs):
        exported_calls.append({"records": span_records, "kwargs": kwargs})

    session_id = "session-chain-io"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("agy_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch("agy_tracer._save_state", side_effect=lambda sid, st: state_store.update({sid: st})),
        patch("agy_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        agy_tracer.handle_pre_invocation(
            {
                "conversationId": session_id,
                "invocationNum": 0,
                "transcriptPath": str(transcript),
                "cwd": "/workspace/academicOps",
            },
            config,
        )
        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

    assert len(exported_calls) == 1
    assert exported_calls[0]["kwargs"]["cwd"] == "/workspace/academicOps"
    records = exported_calls[0]["records"]
    chain_span = records[0]
    llm_span = records[1]

    assert "Explain OTel context propagation" in chain_span["name"]
    assert "Explain OTel context propagation" in chain_span["attributes"]["input.value"]
    assert (
        chain_span["attributes"]["output.value"] == "W3C TraceContext uses the traceparent header."
    )
    assert llm_span["attributes"]["llm.token_count.prompt"] == 150
    assert llm_span["attributes"]["llm.token_count.completion"] == 40
    assert llm_span["attributes"]["llm.token_count.prompt_details.cache_read"] == 30
    assert llm_span["attributes"]["llm.token_count.type"] == "reported"


def test_system_message_wakeup_after_wait_does_not_reemit_prior_llm_spans(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_batches: list[list[dict]] = []

    def load_state(sid: str) -> dict:
        return json.loads(json.dumps(state_store.get(sid, {})))

    def save_state(sid: str, st: dict) -> None:
        state_store[sid] = json.loads(json.dumps(st))

    def delete_state(sid: str) -> None:
        state_store.pop(sid, None)

    def mock_export(config, session_id, username, span_records, **kwargs):
        exported_batches.append(span_records)

    session_id = "session-wait-wakeup"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("agy_tracer._load_state", side_effect=load_state),
        patch("agy_tracer._save_state", side_effect=save_state),
        patch("agy_tracer._delete_state", side_effect=delete_state),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        # Part 1: user prompt -> model calls wait -> Stop fires
        _append_jsonl(transcript, {"step_index": 0, "type": "USER_INPUT", "content": "Run review"})
        agy_tracer.handle_pre_invocation(
            {"conversationId": session_id, "invocationNum": 0, "transcriptPath": str(transcript)},
            config,
        )
        _append_jsonl(
            transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "",
                "tool_calls": [{"name": "wait", "args": {}}],
            },
        )
        _append_jsonl(
            transcript,
            {"step_index": 2, "source": "MODEL", "type": "GENERIC", "content": "Waiting."},
        )
        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

        # Part 2: subagent finishes -> SYSTEM_MESSAGE wakes agy -> PreInvocation -> model replies -> Stop
        _append_jsonl(
            transcript,
            {
                "step_index": 3,
                "source": "SYSTEM",
                "type": "SYSTEM_MESSAGE",
                "content": "<SYSTEM_MESSAGE>Subagent review: PASS</SYSTEM_MESSAGE>",
            },
        )
        agy_tracer.handle_pre_invocation(
            {"conversationId": session_id, "invocationNum": 0, "transcriptPath": str(transcript)},
            config,
        )
        _append_jsonl(
            transcript,
            {
                "step_index": 4,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "Review passed.",
            },
        )
        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

    assert len(exported_batches) == 2
    part1_llm = [
        s
        for s in exported_batches[0]
        if s.get("attributes", {}).get("openinference.span.kind") == "LLM"
    ]
    part2_llm = [
        s
        for s in exported_batches[1]
        if s.get("attributes", {}).get("openinference.span.kind") == "LLM"
    ]
    assert len(part1_llm) == 1
    assert len(part2_llm) == 1
    assert part2_llm[0]["attributes"]["output.value"] == "Review passed."
    part2_chain = exported_batches[1][0]
    assert part2_chain["attributes"]["output.value"] == "Review passed."


def test_long_turn_llm_span_attributes_stay_within_otel_128_limit(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    entries: list[dict] = [{"step_index": 0, "type": "USER_INPUT", "content": "Start long turn"}]
    step = 1
    for i in range(70):
        entries.append(
            {
                "step_index": step,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": f"Step {i}",
                "tool_calls": [{"name": "view_file", "args": {"path": f"file_{i}.py"}}],
            }
        )
        step += 1
        entries.append(
            {
                "step_index": step,
                "source": "MODEL",
                "type": "GENERIC",
                "content": f"Contents of file_{i}.py",
            }
        )
        step += 1

    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

    spans = agy_tracer._extract_llm_spans_for_turn_agy(
        transcript_path=str(transcript),
        human_count_at_start=0,
        trace_id_hex="0123456789abcdef0123456789abcdef",
        root_span_id_hex="0123456789abcdef",
        session_id="session-long-turn",
    )

    assert len(spans) == 70
    for sp in spans:
        attrs = sp["attributes"]
        assert len(attrs) <= 128
        assert attrs.get("openinference.span.kind") == "LLM"
        assert "input.value" in attrs
        assert "output.value" in attrs


def test_agy_tracer_passes_service_name_and_surface(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("", encoding="utf-8")
    state_store: dict[str, dict] = {}

    def load_state(sid: str) -> dict:
        return json.loads(json.dumps(state_store.get(sid, {})))

    def save_state(sid: str, st: dict) -> None:
        state_store[sid] = json.loads(json.dumps(st))

    def delete_state(sid: str) -> None:
        state_store.pop(sid, None)

    export_kwargs: dict = {}

    def mock_export(config, session_id, username, span_records, **kwargs):
        nonlocal export_kwargs
        export_kwargs = dict(kwargs)

    session_id = "session-agy-attrs"
    config = {"endpoint": "localhost:4317", "project_name": "academicOps"}

    with (
        patch("agy_tracer._load_state", side_effect=load_state),
        patch("agy_tracer._save_state", side_effect=save_state),
        patch("agy_tracer._delete_state", side_effect=delete_state),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        _append_jsonl(transcript, {"step_index": 0, "type": "USER_INPUT", "content": "Hello"})
        agy_tracer.handle_pre_invocation(
            {"conversationId": session_id, "invocationNum": 1, "transcriptPath": str(transcript)},
            config,
        )
        _append_jsonl(
            transcript, {"step_index": 1, "source": "MODEL", "type": "GENERIC", "content": "Done"}
        )
        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

    assert export_kwargs.get("service_name") == "aops-agy-hooks"
    assert export_kwargs.get("surface") == "agy"
