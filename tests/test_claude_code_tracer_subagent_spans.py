"""An in-process subagent's LLM calls get spans, and its spans carry its own identity.

A subagent dispatched through the Agent tool runs inside the main Claude Code
process. Its API calls are written to a sidechain transcript,
``<session>/subagents/agent-<agent_id>.jsonl``, never to the main one, and its
tool hooks carry the main thread's ``session_id`` plus the subagent's own
``agent_id`` and ``agent_type``. These tests drive the real hook handlers and
the real OTel SDK through a session shaped like one observed on Claude Code
2.1.291: payload keys, the ``agent-<id>.meta.json`` sidecar naming the
dispatching ``toolUseId``, and one transcript record per content block, each
repeating a growing usage snapshot.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer as cct

CONFIG = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}
SESSION = "bc5187fe-0000-4000-8000-000000000001"
AGENT_ID = "a6a0e6d7fd0ab1b06"
AGENT_TOOL_USE = "toolu_agent"
AGENT_INPUT = {
    "description": "probe",
    "prompt": "Run echo hi.",
    "subagent_type": "ida:james",
}


class _CollectingExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setattr(cct, "STATE_DIR", tmp_path / "tracer")
    monkeypatch.setenv("HOME", str(tmp_path))
    for var in (
        "AOPS_SESSION_ID",
        "CLAUDE_PROJECT_DIR",
        "CLAUDE_AGENT_NAME",
        "AOPS_AGENT_NAME",
        "AGENT_NAME",
    ):
        monkeypatch.delenv(var, raising=False)
    project = tmp_path / ".claude" / "projects" / "-work"
    project.mkdir(parents=True)
    main = project / f"{SESSION}.jsonl"
    sub = project / SESSION / "subagents" / f"agent-{AGENT_ID}.jsonl"
    sub.parent.mkdir(parents=True)
    sub.with_suffix(".meta.json").write_text(
        json.dumps({"agentType": "ida:james", "toolUseId": AGENT_TOOL_USE})
    )
    return main, sub


def _write(path: Path, entries: list[dict]) -> None:
    path.write_text("".join(json.dumps(e) + "\n" for e in entries))


def _prompt(text: str, ts: str, **extra) -> dict:
    return {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}, **extra}


def _assistant(msg_id: str, ts: str, block: dict, output_tokens: int, **extra) -> dict:
    return {
        "type": "assistant",
        "timestamp": ts,
        "requestId": f"req_{msg_id}",
        "message": {
            "id": msg_id,
            "model": "claude-haiku-4-5-20251001" if extra.get("isSidechain") else "claude-opus-5-5",
            "content": [block],
            "stop_reason": None,
            "usage": {
                "input_tokens": 8,
                "cache_read_input_tokens": 12738,
                "cache_creation_input_tokens": 1398,
                "output_tokens": output_tokens,
            },
        },
        **extra,
    }


def _tool_use(tool_use_id: str, name: str, tool_input: dict) -> dict:
    return {"type": "tool_use", "id": tool_use_id, "name": name, "input": tool_input}


def _tool_result(tool_use_id: str, ts: str, **extra) -> dict:
    return {
        "type": "user",
        "timestamp": ts,
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}],
        },
        **extra,
    }


def _sidechain() -> dict:
    return {"isSidechain": True, "agentId": AGENT_ID}


def _main_payload(main: Path, **fields) -> dict:
    return {"session_id": SESSION, "transcript_path": str(main), "cwd": "/work", **fields}


def _sub_payload(main: Path, **fields) -> dict:
    return _main_payload(main, agent_id=AGENT_ID, agent_type="ida:james", **fields)


def _run_session(main: Path, sub: Path, *, subagent_stop: bool) -> list[ReadableSpan]:
    """One turn: the main thread dispatches a subagent that makes two API calls and one Bash call."""
    bash_input = {"command": "echo hi"}
    main.touch()
    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        # UserPromptSubmit fires before the prompt is written to the transcript.
        cct.handle_user_prompt_submit(_main_payload(main, prompt="dispatch a probe"), CONFIG)
        main_entries = [_prompt("dispatch a probe", "2026-10-08T10:46:40.000Z")]
        main_entries.append(
            _assistant(
                "msg_main1",
                "2026-10-08T10:46:41.000Z",
                _tool_use(AGENT_TOOL_USE, "Agent", AGENT_INPUT),
                40,
            )
        )
        _write(main, main_entries)
        cct.handle_pre_tool(
            _main_payload(
                main, tool_name="Agent", tool_input=AGENT_INPUT, tool_use_id=AGENT_TOOL_USE
            ),
            CONFIG,
        )

        # The subagent's first API call streams thinking, then the tool_use;
        # each record repeats the usage, and the last one is the full count.
        side = _sidechain()
        sub_entries = [
            _prompt("Run echo hi.", "2026-10-08T10:46:42.336Z", **side),
            _assistant("msg_sub1", "2026-10-08T10:46:44.706Z", {"type": "thinking"}, 6, **side),
            _assistant(
                "msg_sub1",
                "2026-10-08T10:46:45.033Z",
                _tool_use("toolu_sub_bash", "Bash", bash_input),
                6,
                **side,
            ),
        ]
        _write(sub, sub_entries)
        cct.handle_pre_tool(
            _sub_payload(
                main, tool_name="Bash", tool_input=bash_input, tool_use_id="toolu_sub_bash"
            ),
            CONFIG,
        )
        sub_entries[-1]["message"]["usage"]["output_tokens"] = 212
        sub_entries.append(_tool_result("toolu_sub_bash", "2026-10-08T10:46:45.501Z", **side))
        _write(sub, sub_entries)
        cct.handle_post_tool(
            _sub_payload(
                main,
                tool_name="Bash",
                tool_input=bash_input,
                tool_use_id="toolu_sub_bash",
                tool_response={"stdout": "hi", "stderr": ""},
            ),
            CONFIG,
        )
        sub_entries += [
            _assistant("msg_sub2", "2026-10-08T10:46:47.688Z", {"type": "thinking"}, 1, **side),
            _assistant(
                "msg_sub2", "2026-10-08T10:46:47.796Z", {"type": "text", "text": "hi"}, 111, **side
            ),
        ]
        _write(sub, sub_entries)
        if subagent_stop:
            cct.handle_subagent_stop(
                _sub_payload(main, agent_transcript_path=str(sub), hook_event_name="SubagentStop"),
                CONFIG,
            )

        cct.handle_post_tool(
            _main_payload(
                main,
                tool_name="Agent",
                tool_input=AGENT_INPUT,
                tool_use_id=AGENT_TOOL_USE,
                tool_response={
                    "status": "completed",
                    "agentId": AGENT_ID,
                    "agentType": "ida:james",
                    "content": [{"type": "text", "text": "hi"}],
                },
            ),
            CONFIG,
        )
        main_entries += [
            _tool_result(AGENT_TOOL_USE, "2026-10-08T10:46:48.000Z"),
            _assistant(
                "msg_main2", "2026-10-08T10:46:49.000Z", {"type": "text", "text": "done"}, 5
            ),
        ]
        _write(main, main_entries)
        cct.handle_stop(_main_payload(main), CONFIG)
    return exporter.spans


def _llm_spans(spans: list[ReadableSpan], prefix: str) -> list[ReadableSpan]:
    return [
        sp
        for sp in spans
        if (sp.attributes or {}).get("openinference.span.kind") == "LLM"
        and str((sp.attributes or {}).get("llm.message.id", "")).startswith(prefix)
    ]


def _only(spans: list[ReadableSpan], name: str) -> ReadableSpan:
    (span,) = [sp for sp in spans if sp.name == name]
    return span


def _span_id(span: ReadableSpan) -> int:
    assert span.context is not None
    return span.context.span_id


def _parent_id(span: ReadableSpan) -> int | None:
    return span.parent.span_id if span.parent else None


@pytest.mark.parametrize("subagent_stop", [True, False], ids=["SubagentStop", "Agent-PostToolUse"])
def test_one_llm_span_per_subagent_api_call_nested_under_the_agent_span(session, subagent_stop):
    main, sub = session
    spans = _run_session(main, sub, subagent_stop=subagent_stop)

    agent = _only(spans, "Agent")
    sub_llm = _llm_spans(spans, "msg_sub")
    print(
        "subagent LLM spans:",
        [((sp.attributes or {})["llm.message.id"], f"{_parent_id(sp):016x}") for sp in sub_llm],
        "Agent span:",
        f"{_span_id(agent):016x}",
    )
    assert sorted((sp.attributes or {})["llm.message.id"] for sp in sub_llm) == [
        "msg_sub1",
        "msg_sub2",
    ], "exactly one LLM span per subagent API call"
    assert all(_parent_id(sp) == _span_id(agent) for sp in sub_llm)
    assert {sp.context.trace_id for sp in sub_llm if sp.context} == {agent.context.trace_id}
    completion = {
        (sp.attributes or {})["llm.message.id"]: (sp.attributes or {})["llm.token_count.completion"]
        for sp in sub_llm
    }
    assert completion == {"msg_sub1": 212, "msg_sub2": 111}

    bash = _only(spans, "Bash")
    (issuer,) = [sp for sp in sub_llm if (sp.attributes or {})["llm.message.id"] == "msg_sub1"]
    assert _parent_id(bash) == _span_id(issuer), "the subagent's Bash nests under its LLM call"

    assert len(_llm_spans(spans, "msg_main")) == 2


def test_subagent_spans_carry_the_subagent_name_and_id(session):
    main, sub = session
    spans = _run_session(main, sub, subagent_stop=True)

    subagent_spans = [_only(spans, "Bash"), *_llm_spans(spans, "msg_sub")]
    for sp in subagent_spans:
        attrs = sp.attributes or {}
        print(sp.name, {k: attrs.get(k) for k in ("agent.name", "agent.id", "parent.session_id")})
        assert attrs["agent.name"] == "james"
        assert attrs["agent.id"] == AGENT_ID
        assert attrs["subagent.id"] == AGENT_ID
        assert attrs["parent.session_id"] == SESSION
        assert attrs["session.id"] == SESSION, "grouped in the main thread's Phoenix session"

    agent_attrs = _only(spans, "Agent").attributes or {}
    assert agent_attrs["agent.name"] == "ida:james"
    assert agent_attrs["subagent.id"] == AGENT_ID

    main_spans = [*_llm_spans(spans, "msg_main"), _only(spans, "claude-code-turn")]
    assert len(main_spans) == 3
    for sp in main_spans:
        attrs = sp.attributes or {}
        assert attrs["agent.name"] == "ida", "main-thread spans keep the main thread's name"
        assert attrs["agent.id"] == SESSION
        assert "parent.session_id" not in attrs


def test_subagent_and_main_thread_calls_of_one_tool_pend_apart(session):
    """A main-thread Bash pending while a subagent's Bash runs keeps its own start time."""
    main, _sub = session
    main.touch()
    cct.handle_user_prompt_submit(_main_payload(main, prompt="go"), CONFIG)
    _write(main, [_prompt("go", "2026-10-08T10:46:40.000Z")])
    cct.handle_pre_tool(_main_payload(main, tool_name="Bash", tool_input={"command": "a"}), CONFIG)
    cct.handle_pre_tool(_sub_payload(main, tool_name="Bash", tool_input={"command": "b"}), CONFIG)

    pending = cct._load_state(SESSION)["pending_tools"]
    assert pending["Bash"]["tool_input"] == {"command": "a"}
    assert pending[f"Bash@{AGENT_ID}"]["tool_input"] == {"command": "b"}

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        cct.handle_post_tool(
            _sub_payload(main, tool_name="Bash", tool_input={"command": "b"}, tool_response={}),
            CONFIG,
        )
    assert "Bash" in cct._load_state(SESSION)["pending_tools"], "main-thread call still pending"
