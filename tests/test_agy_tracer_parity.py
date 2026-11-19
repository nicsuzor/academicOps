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


def test_agy_subagent_parent_link_and_child_session_id(tmp_path: Path):
    """When parent invokes invoke_subagent, the tool span carries subagent.child_session_id.
    When child subagent runs, its spans carry parent.session_id and session.id equal to parent
    session id, extracted from sender= in the child's first SYSTEM_MESSAGE."""
    state_store: dict[str, dict] = {}

    def load_state(sid: str) -> dict:
        return json.loads(json.dumps(state_store.get(sid, {})))

    def save_state(sid: str, st: dict) -> None:
        state_store[sid] = json.loads(json.dumps(st))

    def delete_state(sid: str) -> None:
        state_store.pop(sid, None)

    exported_records: list[dict] = []

    def mock_export(config, session_id, username, span_records, parent_session_id=None, **kwargs):
        for r in span_records:
            r["_exported_session_id"] = session_id
            r["_exported_parent_session_id"] = parent_session_id
            exported_records.append(r)

    parent_session = "parent-sess-uuid"
    child_session = "child-subagent-uuid"
    config = {"endpoint": "localhost:4317"}

    parent_transcript = tmp_path / "parent_transcript.jsonl"
    parent_transcript.write_text("", encoding="utf-8")

    child_transcript = tmp_path / "child_transcript.jsonl"
    child_transcript.write_text("", encoding="utf-8")

    with (
        patch("agy_tracer._load_state", side_effect=load_state),
        patch("agy_tracer._save_state", side_effect=save_state),
        patch("agy_tracer._delete_state", side_effect=delete_state),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        # 1. Parent initiates invoke_subagent tool call
        _append_jsonl(
            parent_transcript, {"step_index": 0, "type": "USER_INPUT", "content": "Delegate task"}
        )
        agy_tracer.handle_pre_invocation(
            {
                "conversationId": parent_session,
                "transcriptPath": str(parent_transcript),
            },
            config,
        )

        subagent_output = (
            "Created At: 2026-10-30T22:38:53Z\n"
            "Completed At: 2026-10-30T22:38:54Z\n"
            "Created the following subagent:\n"
            "{\n"
            f'  "conversationId":  "{child_session}",\n'
            f'  "logAbsoluteUri":  "file:///home/nic/.gemini/antigravity-cli/brain/{child_session}/.system_generated/logs/transcript.jsonl"\n'
            "}\n"
        )
        _append_jsonl(
            parent_transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "tool_calls": [
                    {
                        "name": "invoke_subagent",
                        "args": {"TypeName": "research", "Prompt": "Investigate"},
                    }
                ],
            },
        )
        agy_tracer.handle_pre_tool(
            {
                "conversationId": parent_session,
                "transcriptPath": str(parent_transcript),
                "toolCall": {
                    "name": "invoke_subagent",
                    "args": {"TypeName": "research", "Prompt": "Investigate"},
                },
            },
            config,
        )
        _append_jsonl(
            parent_transcript,
            {
                "step_index": 2,
                "source": "MODEL",
                "type": "GENERIC",
                "content": subagent_output,
            },
        )
        agy_tracer.handle_post_tool(
            {
                "conversationId": parent_session,
                "transcriptPath": str(parent_transcript),
                "toolCall": {
                    "name": "invoke_subagent",
                    "args": {"TypeName": "research", "Prompt": "Investigate"},
                },
            },
            config,
        )

        # Verify parent's invoke_subagent span
        invoke_spans = [
            r
            for r in exported_records
            if r.get("attributes", {}).get("tool.name") == "invoke_subagent"
        ]
        assert len(invoke_spans) == 1
        assert invoke_spans[0]["attributes"].get("subagent.child_session_id") == child_session

        # 2. Child runs: receives prompt from parent via SYSTEM_MESSAGE with sender=parent-sess-uuid
        exported_records.clear()
        _append_jsonl(
            child_transcript,
            {
                "step_index": 0,
                "source": "SYSTEM",
                "type": "SYSTEM_MESSAGE",
                "content": f"[Message] timestamp=2026-10-30T22:38:53Z sender={parent_session} priority=MESSAGE_PRIORITY_HIGH content=Investigate",
            },
        )
        agy_tracer.handle_pre_invocation(
            {
                "conversationId": child_session,
                "transcriptPath": str(child_transcript),
            },
            config,
        )

        # Child executes a tool
        _append_jsonl(
            child_transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "tool_calls": [{"name": "run_command", "args": {"CommandLine": "ls"}}],
            },
        )
        agy_tracer.handle_pre_tool(
            {
                "conversationId": child_session,
                "transcriptPath": str(child_transcript),
                "toolCall": {"name": "run_command", "args": {"CommandLine": "ls"}},
            },
            config,
        )
        _append_jsonl(
            child_transcript,
            {"step_index": 2, "source": "MODEL", "type": "GENERIC", "content": "file1.txt\n"},
        )
        agy_tracer.handle_post_tool(
            {
                "conversationId": child_session,
                "transcriptPath": str(child_transcript),
                "toolCall": {"name": "run_command", "args": {"CommandLine": "ls"}},
            },
            config,
        )

        # Child completes turn
        _append_jsonl(
            child_transcript,
            {
                "step_index": 3,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "All done.",
            },
        )
        agy_tracer.handle_stop(
            {
                "conversationId": child_session,
                "transcriptPath": str(child_transcript),
                "last_assistant_message": "All done.",
            },
            config,
        )

        # Every child span must carry parent.session_id and session.id equal to parent
        assert len(exported_records) >= 2
        for r in exported_records:
            assert r["_exported_session_id"] == parent_session
            assert r["_exported_parent_session_id"] == parent_session
            assert r["attributes"].get("parent.session_id") == parent_session
            assert r["attributes"].get("session.id") == parent_session


def test_agy_handback_turn_names_subagent(tmp_path: Path):
    """When a message arrives from a subagent, the hand-back turn root span names the subagent."""
    state_store: dict[str, dict] = {}

    def load_state(sid: str) -> dict:
        return json.loads(json.dumps(state_store.get(sid, {})))

    def save_state(sid: str, st: dict) -> None:
        state_store[sid] = json.loads(json.dumps(st))

    exported_records: list[dict] = []

    def mock_export(config, session_id, username, span_records, **kwargs):
        exported_records.extend(span_records)

    session_id = "parent-session-handback"
    child_subagent_id = "subagent-worker-1"
    config = {"endpoint": "localhost:4317"}
    transcript = tmp_path / "transcript.jsonl"

    with (
        patch("agy_tracer._load_state", side_effect=load_state),
        patch("agy_tracer._save_state", side_effect=save_state),
        patch("agy_tracer._delete_state"),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        # A subagent message arrives in parent
        msg_content = f"<SYSTEM_MESSAGE>\n[Message] timestamp=2026-10-30T22:39:38Z sender={child_subagent_id} priority=MESSAGE_PRIORITY_HIGH content=Done work\n</SYSTEM_MESSAGE>"
        _append_jsonl(
            transcript,
            {"step_index": 0, "type": "SYSTEM_MESSAGE", "content": msg_content},
        )
        agy_tracer.handle_pre_invocation(
            {
                "conversationId": session_id,
                "transcriptPath": str(transcript),
            },
            config,
        )
        _append_jsonl(
            transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "Acknowledged result.",
            },
        )
        agy_tracer.handle_stop(
            {
                "conversationId": session_id,
                "transcriptPath": str(transcript),
                "last_assistant_message": "Acknowledged result.",
            },
            config,
        )

        turn_roots = [
            r
            for r in exported_records
            if r.get("attributes", {}).get("openinference.span.kind") == "CHAIN"
        ]
        assert len(turn_roots) == 1
        assert turn_roots[0]["attributes"].get("subagent.id") == child_subagent_id


def test_agy_root_session_not_corrupted_by_background_task_or_subagent_handback(tmp_path: Path):
    """A root agy session (started with USER_INPUT) must keep its own session.id when woken by
    a background task (sender=<root>/task-1) or a child subagent handback (sender=<child>)."""
    state_store: dict[str, dict] = {}

    def load_state(sid: str) -> dict:
        return json.loads(json.dumps(state_store.get(sid, {})))

    def save_state(sid: str, st: dict) -> None:
        state_store[sid] = json.loads(json.dumps(st))

    exported_records: list[dict] = []

    def mock_export(config, session_id, username, span_records, parent_session_id=None, **kwargs):
        for r in span_records:
            r["_exported_session_id"] = session_id
            r["_exported_parent_session_id"] = parent_session_id
            r["_exported_agent_id"] = kwargs.get("agent_id")
            exported_records.append(r)

    root_session = "root-uuid-1111"
    child_subagent = "child-uuid-2222"
    config = {"endpoint": "localhost:4317"}
    transcript = tmp_path / "root_transcript.jsonl"

    with (
        patch("agy_tracer._load_state", side_effect=load_state),
        patch("agy_tracer._save_state", side_effect=save_state),
        patch("agy_tracer._delete_state"),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        # Turn 1: Root session starts with USER_INPUT
        _append_jsonl(
            transcript,
            {"step_index": 0, "type": "USER_INPUT", "content": "Run a background check"},
        )
        agy_tracer.handle_pre_invocation(
            {"conversationId": root_session, "transcriptPath": str(transcript)},
            config,
        )
        _append_jsonl(
            transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "Started background task.",
            },
        )
        agy_tracer.handle_stop(
            {
                "conversationId": root_session,
                "transcriptPath": str(transcript),
                "last_assistant_message": "Started background task.",
            },
            config,
        )

        # Turn 2: Background task completion arrives with sender=<root_session>/task-1
        exported_records.clear()
        bg_msg = (
            "<SYSTEM_MESSAGE>\n"
            f'[Message] timestamp=2026-10-30T22:40:00Z sender={root_session}/task-1 priority=MESSAGE_PRIORITY_HIGH content=Task id "{root_session}/task-1" finished\n'
            "</SYSTEM_MESSAGE>"
        )
        _append_jsonl(
            transcript,
            {"step_index": 2, "type": "SYSTEM_MESSAGE", "content": bg_msg},
        )
        agy_tracer.handle_pre_invocation(
            {"conversationId": root_session, "transcriptPath": str(transcript)},
            config,
        )
        _append_jsonl(
            transcript,
            {
                "step_index": 3,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "Background task finished.",
            },
        )
        agy_tracer.handle_stop(
            {
                "conversationId": root_session,
                "transcriptPath": str(transcript),
                "last_assistant_message": "Background task finished.",
            },
            config,
        )

        assert len(exported_records) >= 2
        for r in exported_records:
            assert r["_exported_session_id"] == root_session
            assert r["_exported_parent_session_id"] is None
            assert r["_exported_agent_id"] == root_session
            assert r["attributes"].get("session.id") == root_session
            assert "parent.session_id" not in r["attributes"]
            assert "handback.subagent_id" not in r["attributes"]
            assert r["attributes"].get("subagent.id") != f"{root_session}/task-1"
            assert r["attributes"].get("agent.task_id") == "task-1"

        # Turn 3: Child subagent handback arrives with sender=<child_subagent>
        exported_records.clear()
        hb_msg = (
            "<SYSTEM_MESSAGE>\n"
            f"[Message] timestamp=2026-10-30T22:41:00Z sender={child_subagent} priority=MESSAGE_PRIORITY_HIGH content=Subagent report\n"
            "</SYSTEM_MESSAGE>"
        )
        _append_jsonl(
            transcript,
            {"step_index": 4, "type": "SYSTEM_MESSAGE", "content": hb_msg},
        )
        agy_tracer.handle_pre_invocation(
            {"conversationId": root_session, "transcriptPath": str(transcript)},
            config,
        )
        _append_jsonl(
            transcript,
            {
                "step_index": 5,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "Processed subagent report.",
            },
        )
        agy_tracer.handle_stop(
            {
                "conversationId": root_session,
                "transcriptPath": str(transcript),
                "last_assistant_message": "Processed subagent report.",
            },
            config,
        )

        assert len(exported_records) >= 2
        for r in exported_records:
            assert r["_exported_session_id"] == root_session
            assert r["_exported_parent_session_id"] is None
            assert r["_exported_agent_id"] == root_session
            assert r["attributes"].get("session.id") == root_session
            assert "parent.session_id" not in r["attributes"]

        chain_spans = [
            r
            for r in exported_records
            if r.get("attributes", {}).get("openinference.span.kind") == "CHAIN"
        ]
        assert len(chain_spans) == 1
        assert chain_spans[0]["attributes"].get("subagent.id") == child_subagent
        assert chain_spans[0]["attributes"].get("handback.subagent_id") == child_subagent


def test_agy_subagent_preserves_own_subagent_id_and_multihop_root_session_id(tmp_path: Path):
    """Multi-hop agy subagents (root -> sub1 -> sub2) all roll up to root session.id,
    preserve their own subagent.id on Turn 1, and parent under invoke_subagent tool spans."""
    state_store: dict[str, dict] = {}

    def load_state(sid: str) -> dict:
        return json.loads(json.dumps(state_store.get(sid, {})))

    def save_state(sid: str, st: dict) -> None:
        state_store[sid] = json.loads(json.dumps(st))

    exported_records: list[dict] = []

    def mock_export(config, session_id, username, span_records, parent_session_id=None, **kwargs):
        for r in span_records:
            r["_exported_session_id"] = session_id
            r["_exported_parent_session_id"] = parent_session_id
            r["_exported_agent_id"] = kwargs.get("agent_id")
            exported_records.append(r)

    root_session = "root-sess-000"
    sub1_session = "sub1-sess-111"
    sub2_session = "sub2-sess-222"
    config = {"endpoint": "localhost:4317"}

    root_transcript = tmp_path / "root.jsonl"
    sub1_transcript = tmp_path / "sub1.jsonl"
    sub2_transcript = tmp_path / "sub2.jsonl"

    with (
        patch("agy_tracer._load_state", side_effect=load_state),
        patch("agy_tracer._save_state", side_effect=save_state),
        patch("agy_tracer._delete_state"),
        patch("agy_tracer._build_and_export_spans", side_effect=mock_export),
        patch("agy_tracer._session_lock"),
    ):
        # 1. Root starts and invokes sub1
        _append_jsonl(
            root_transcript,
            {"step_index": 0, "type": "USER_INPUT", "content": "Start root"},
        )
        agy_tracer.handle_pre_invocation(
            {"conversationId": root_session, "transcriptPath": str(root_transcript)},
            config,
        )
        _append_jsonl(
            root_transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "tool_calls": [{"name": "invoke_subagent", "args": {"TypeName": "james"}}],
            },
        )
        agy_tracer.handle_pre_tool(
            {
                "conversationId": root_session,
                "transcriptPath": str(root_transcript),
                "toolCall": {"name": "invoke_subagent", "args": {"TypeName": "james"}},
            },
            config,
        )
        _append_jsonl(
            root_transcript,
            {
                "step_index": 2,
                "source": "MODEL",
                "type": "GENERIC",
                "content": f'{{"conversationId": "{sub1_session}"}}',
            },
        )
        agy_tracer.handle_post_tool(
            {
                "conversationId": root_session,
                "transcriptPath": str(root_transcript),
                "toolCall": {"name": "invoke_subagent", "args": {"TypeName": "james"}},
            },
            config,
        )
        root_invoke_span_id = exported_records[-1]["span_id_hex"]

        # 2. Sub1 runs Turn 1 (sender=root_session) and invokes sub2
        exported_records.clear()
        _append_jsonl(
            sub1_transcript,
            {
                "step_index": 0,
                "source": "SYSTEM",
                "type": "SYSTEM_MESSAGE",
                "content": f"[Message] sender={root_session} content=Delegate to sub1",
            },
        )
        agy_tracer.handle_pre_invocation(
            {"conversationId": sub1_session, "transcriptPath": str(sub1_transcript)},
            config,
        )
        _append_jsonl(
            sub1_transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "tool_calls": [{"name": "invoke_subagent", "args": {"TypeName": "pauli"}}],
            },
        )
        agy_tracer.handle_pre_tool(
            {
                "conversationId": sub1_session,
                "transcriptPath": str(sub1_transcript),
                "toolCall": {"name": "invoke_subagent", "args": {"TypeName": "pauli"}},
            },
            config,
        )
        _append_jsonl(
            sub1_transcript,
            {
                "step_index": 2,
                "source": "MODEL",
                "type": "GENERIC",
                "content": f'{{"conversationId": "{sub2_session}"}}',
            },
        )
        agy_tracer.handle_post_tool(
            {
                "conversationId": sub1_session,
                "transcriptPath": str(sub1_transcript),
                "toolCall": {"name": "invoke_subagent", "args": {"TypeName": "pauli"}},
            },
            config,
        )
        sub1_invoke_span_id = exported_records[-1]["span_id_hex"]
        _append_jsonl(
            sub1_transcript,
            {
                "step_index": 3,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "Sub1 turn 1 done",
            },
        )
        agy_tracer.handle_stop(
            {
                "conversationId": sub1_session,
                "transcriptPath": str(sub1_transcript),
                "last_assistant_message": "Sub1 turn 1 done",
            },
            config,
        )

        sub1_turn_roots = [
            r
            for r in exported_records
            if r.get("attributes", {}).get("openinference.span.kind") in ("CHAIN", "AGENT")
        ]
        assert len(sub1_turn_roots) == 1
        sub1_root = sub1_turn_roots[0]
        assert sub1_root["attributes"].get("session.id") == root_session
        assert sub1_root["attributes"].get("parent.session_id") == root_session
        assert sub1_root["attributes"].get("agent.id") == sub1_session
        assert sub1_root["attributes"].get("subagent.id") == sub1_session
        assert "handback.subagent_id" not in sub1_root["attributes"]
        assert sub1_root["parent_span_id_hex"] == root_invoke_span_id

        # 3. Sub2 runs Turn 1 (sender=sub1_session)
        exported_records.clear()
        _append_jsonl(
            sub2_transcript,
            {
                "step_index": 0,
                "source": "SYSTEM",
                "type": "SYSTEM_MESSAGE",
                "content": f"[Message] sender={sub1_session} content=Hydrate context",
            },
        )
        agy_tracer.handle_pre_invocation(
            {"conversationId": sub2_session, "transcriptPath": str(sub2_transcript)},
            config,
        )
        _append_jsonl(
            sub2_transcript,
            {
                "step_index": 1,
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "Sub2 turn 1 done",
            },
        )
        agy_tracer.handle_stop(
            {
                "conversationId": sub2_session,
                "transcriptPath": str(sub2_transcript),
                "last_assistant_message": "Sub2 turn 1 done",
            },
            config,
        )

        assert len(exported_records) >= 2
        for r in exported_records:
            assert r["_exported_session_id"] == root_session
            assert r["_exported_parent_session_id"] == sub1_session
            assert r["_exported_agent_id"] == sub2_session
            assert r["attributes"].get("session.id") == root_session
            assert r["attributes"].get("parent.session_id") == sub1_session

        sub2_turn_roots = [
            r
            for r in exported_records
            if r.get("attributes", {}).get("openinference.span.kind") in ("CHAIN", "AGENT")
        ]
        assert len(sub2_turn_roots) == 1
        sub2_root = sub2_turn_roots[0]
        assert sub2_root["attributes"].get("agent.id") == sub2_session
        assert sub2_root["attributes"].get("subagent.id") == sub2_session
        assert "handback.subagent_id" not in sub2_root["attributes"]
        assert sub2_root["parent_span_id_hex"] == sub1_invoke_span_id
