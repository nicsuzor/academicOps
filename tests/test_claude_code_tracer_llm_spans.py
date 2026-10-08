"""LLM spans carry the response's real usage, timing and message id, and tool
spans nest under the LLM call that issued them.

Claude Code writes one streamed API response to the transcript as one entry
per content block (thinking / text / each tool_use), every entry sharing the
response's ``message.id`` and repeating its ``usage``. The fixtures below
reproduce that shape. The figures in the first test are LLM call 1 of
session 2cadea10 (142 completion tokens, written as two entries), which the
tracer used to report as 284.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer as cct

CONFIG = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}
SESSION = "sess-llm-spans"
TRACE = "0" * 31 + "1"
ROOT = "00000000000000aa"


def _usage(output_tokens: int, input_tokens: int = 3) -> dict:
    return {
        "input_tokens": input_tokens,
        "cache_read_input_tokens": 1000,
        "cache_creation_input_tokens": 200,
        "output_tokens": output_tokens,
    }


def _human(text: str, ts: str) -> dict:
    return {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}}


def _assistant(msg_id: str, ts: str, block: dict, usage: dict, stop_reason=None) -> dict:
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "id": msg_id,
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": [block],
            "usage": usage,
            "stop_reason": stop_reason,
        },
    }


def _tool_result(tool_use_id: str, ts: str) -> dict:
    return {
        "type": "user",
        "timestamp": ts,
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}],
        },
    }


def _tool_use(tool_use_id: str, name: str = "Bash", tool_input: dict | None = None) -> dict:
    return {"type": "tool_use", "id": tool_use_id, "name": name, "input": tool_input or {}}


def _write(path: Path, entries: list[dict]) -> str:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return str(path)


def _extract(path: str) -> list[dict]:
    return cct._extract_llm_spans_for_turn(path, 0, TRACE, ROOT)


def _ns(ts: str) -> int:
    return cct._iso_to_ns(ts)


# --- Defect 1: output tokens -------------------------------------------------


def test_completion_tokens_are_counted_once_per_response_not_per_entry(tmp_path):
    path = _write(
        tmp_path / "t.jsonl",
        [
            _human("hi", "2026-10-08T00:26:07.000Z"),
            _assistant(
                "msg_1",
                "2026-10-08T00:26:12.000Z",
                {"type": "text", "text": "Let me look."},
                _usage(142),
            ),
            _assistant(
                "msg_1", "2026-10-08T00:26:13.000Z", _tool_use("toolu_1"), _usage(142), "tool_use"
            ),
        ],
    )
    (span,) = _extract(path)
    attrs = span["attributes"]
    assert attrs["llm.token_count.completion"] == 142
    assert attrs["llm.token_count.prompt"] == 3 + 1000 + 200
    assert attrs["llm.token_count.total"] == 3 + 1000 + 200 + 142


def test_fullest_usage_snapshot_wins_when_earlier_entries_are_partial(tmp_path):
    path = _write(
        tmp_path / "t.jsonl",
        [
            _human("hi", "2026-10-08T00:00:00.000Z"),
            _assistant(
                "msg_1", "2026-10-08T00:00:01.000Z", {"type": "thinking", "thinking": ""}, _usage(1)
            ),
            _assistant(
                "msg_1", "2026-10-08T00:00:02.000Z", {"type": "text", "text": "a"}, _usage(9)
            ),
            _assistant(
                "msg_1", "2026-10-08T00:00:03.000Z", _tool_use("toolu_1"), _usage(381), "tool_use"
            ),
        ],
    )
    (span,) = _extract(path)
    assert span["attributes"]["llm.token_count.completion"] == 381


# --- Defect 2: LLM timing ----------------------------------------------------


def test_llm_span_runs_from_first_to_last_entry_of_the_response(tmp_path):
    first, last = "2026-10-08T00:26:43.500Z", "2026-10-08T00:26:58.500Z"
    path = _write(
        tmp_path / "t.jsonl",
        [
            _human("hi", "2026-10-08T00:26:40.000Z"),
            _assistant("msg_1", first, {"type": "text", "text": "x"}, _usage(2107)),
            _assistant(
                "msg_1", "2026-10-08T00:26:50.000Z", {"type": "text", "text": "y"}, _usage(2107)
            ),
            _assistant("msg_1", last, _tool_use("toolu_1"), _usage(2107), "tool_use"),
        ],
    )
    (span,) = _extract(path)
    assert span["start_ns"] == _ns(first)
    assert span["end_ns"] == _ns(last)
    # The old heuristic would have given 2107 tokens x 10 ms = 21.07 s.
    assert span["end_ns"] - span["start_ns"] == 15_000_000_000


def test_single_entry_response_is_not_stretched_by_its_token_count(tmp_path):
    ts = "2026-10-08T00:27:10.000Z"
    path = _write(
        tmp_path / "t.jsonl",
        [
            _human("hi", "2026-10-08T00:27:00.000Z"),
            _assistant("msg_1", ts, {"type": "text", "text": "done"}, _usage(500), "end_turn"),
        ],
    )
    (span,) = _extract(path)
    assert span["start_ns"] == span["end_ns"] == _ns(ts)


# --- Defect 3: llm.message.id ------------------------------------------------


def test_llm_span_carries_message_id_and_a_span_id_derived_from_it(tmp_path):
    path = _write(
        tmp_path / "t.jsonl",
        [
            _human("hi", "2026-10-08T00:00:00.000Z"),
            _assistant(
                "msg_011CfopaJSvy6cfvLYpz6s3M",
                "2026-10-08T00:00:01.000Z",
                _tool_use("toolu_1"),
                _usage(5),
            ),
            _tool_result("toolu_1", "2026-10-08T00:00:02.000Z"),
            _assistant(
                "msg_2", "2026-10-08T00:00:03.000Z", {"type": "text", "text": "ok"}, _usage(7)
            ),
        ],
    )
    first, second = _extract(path)
    assert first["attributes"]["llm.message.id"] == "msg_011CfopaJSvy6cfvLYpz6s3M"
    assert second["attributes"]["llm.message.id"] == "msg_2"
    assert first["span_id_hex"] == cct._llm_span_id("msg_011CfopaJSvy6cfvLYpz6s3M")
    assert first["force_span_id"] is True
    assert first["parent_span_id_hex"] == ROOT
    assert first["tool_call_ids"] == ["toolu_1"]
    # Stable across re-extraction, which every post_tool hook repeats.
    assert _extract(path)[0]["span_id_hex"] == first["span_id_hex"]


def test_entry_without_message_id_gets_no_message_id_attribute(tmp_path):
    entry = _assistant("", "2026-10-08T00:00:01.000Z", {"type": "text", "text": "x"}, _usage(4))
    path = _write(tmp_path / "t.jsonl", [_human("hi", "2026-10-08T00:00:00.000Z"), entry])
    (span,) = _extract(path)
    assert "llm.message.id" not in span["attributes"]
    assert span["force_span_id"] is False


# --- Defect 4: TOOL spans nest under the issuing LLM span --------------------


class _CollectingExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


@pytest.fixture
def tracer_env(tmp_path, monkeypatch):
    monkeypatch.setattr(cct, "STATE_DIR", tmp_path / "tracer")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    return tmp_path


def _hook(handler, transcript: str, **payload) -> None:
    handler({"session_id": SESSION, "transcript_path": transcript, **payload}, CONFIG)


def test_tool_spans_are_children_of_the_llm_call_that_issued_them(tracer_env):
    """Drives the real hooks: two parallel Reads from one response, then a Bash from the next."""
    transcript = tracer_env / "session.jsonl"
    # UserPromptSubmit fires before the prompt is written to the transcript.
    transcript.write_text("")
    _hook(cct.handle_user_prompt_submit, str(transcript), prompt="go")
    entries = [_human("go", "2026-10-08T00:00:00.000Z")]

    read_a, read_b = {"file_path": "/a"}, {"file_path": "/b"}
    entries += [
        _assistant(
            "msg_A", "2026-10-08T00:00:01.000Z", _tool_use("toolu_a", "Read", read_a), _usage(30)
        ),
        _assistant(
            "msg_A",
            "2026-10-08T00:00:02.000Z",
            _tool_use("toolu_b", "Read", read_b),
            _usage(30),
            "tool_use",
        ),
    ]
    _write(transcript, entries)

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        for tuid, tin in (("toolu_a", read_a), ("toolu_b", read_b)):
            _hook(
                cct.handle_pre_tool,
                str(transcript),
                tool_name="Read",
                tool_input=tin,
                tool_use_id=tuid,
            )
        for tuid, tin in (("toolu_a", read_a), ("toolu_b", read_b)):
            _hook(
                cct.handle_post_tool,
                str(transcript),
                tool_name="Read",
                tool_input=tin,
                tool_use_id=tuid,
                tool_response="x",
            )

        bash_in = {"command": "wc -l /a /b"}
        entries += [
            _tool_result("toolu_a", "2026-10-08T00:00:03.000Z"),
            _tool_result("toolu_b", "2026-10-08T00:00:03.100Z"),
            _assistant(
                "msg_B",
                "2026-10-08T00:00:04.000Z",
                _tool_use("toolu_c", "Bash", bash_in),
                _usage(12),
                "tool_use",
            ),
        ]
        _write(transcript, entries)
        _hook(
            cct.handle_pre_tool,
            str(transcript),
            tool_name="Bash",
            tool_input=bash_in,
            tool_use_id="toolu_c",
        )
        _hook(
            cct.handle_post_tool,
            str(transcript),
            tool_name="Bash",
            tool_input=bash_in,
            tool_use_id="toolu_c",
            tool_response="2",
        )

        entries += [
            _tool_result("toolu_c", "2026-10-08T00:00:05.000Z"),
            _assistant(
                "msg_C",
                "2026-10-08T00:00:06.000Z",
                {"type": "text", "text": "done"},
                _usage(8),
                "end_turn",
            ),
        ]
        _write(transcript, entries)
        _hook(cct.handle_stop, str(transcript))

    llm = {
        sp.attributes["llm.message.id"]: sp
        for sp in exporter.spans
        if sp.name.startswith("claude/")
    }
    assert sorted(llm) == ["msg_A", "msg_B", "msg_C"], "each LLM span is emitted exactly once"
    (root,) = [sp for sp in exporter.spans if sp.name == "claude-code-turn"]
    for sp in llm.values():
        assert sp.context.span_id == int(cct._llm_span_id(sp.attributes["llm.message.id"]), 16)
        assert sp.parent.span_id == root.context.span_id

    tools = {
        sp.attributes["tool.call_id"]: sp for sp in exporter.spans if sp.name in ("Read", "Bash")
    }
    assert tools["toolu_a"].parent.span_id == llm["msg_A"].context.span_id
    assert tools["toolu_b"].parent.span_id == llm["msg_A"].context.span_id
    assert tools["toolu_c"].parent.span_id == llm["msg_B"].context.span_id
    assert {sp.context.trace_id for sp in exporter.spans} == {root.context.trace_id}


def test_tool_span_falls_back_to_turn_root_when_its_tool_use_is_not_in_the_transcript(tracer_env):
    transcript = tracer_env / "session.jsonl"
    transcript.write_text("")
    _hook(cct.handle_user_prompt_submit, str(transcript), prompt="go")
    _write(transcript, [_human("go", "2026-10-08T00:00:00.000Z")])
    root = int(cct._load_state(SESSION)["current_trace"]["root_span_id"], 16)

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _hook(
            cct.handle_pre_tool,
            str(transcript),
            tool_name="Read",
            tool_input={},
            tool_use_id="toolu_x",
        )
        _hook(
            cct.handle_post_tool,
            str(transcript),
            tool_name="Read",
            tool_input={},
            tool_use_id="toolu_x",
        )

    (read_span,) = [sp for sp in exporter.spans if sp.name == "Read"]
    assert read_span.parent.span_id == root


# --- Found replaying session c710709d against the Arize harness ---------------


def test_tool_result_between_records_of_one_response_does_not_split_it(tmp_path):
    """A tool can finish before its response streams the next tool_use block."""
    path = _write(
        tmp_path / "t.jsonl",
        [
            _human("go", "2026-10-08T00:00:00.000Z"),
            _assistant("msg_A", "2026-10-08T00:00:01.000Z", _tool_use("toolu_a"), _usage(552)),
            _tool_result("toolu_a", "2026-10-08T00:00:01.500Z"),
            _assistant(
                "msg_A", "2026-10-08T00:00:02.000Z", _tool_use("toolu_b"), _usage(552), "tool_use"
            ),
            _tool_result("toolu_b", "2026-10-08T00:00:02.500Z"),
            _assistant(
                "msg_B", "2026-10-08T00:00:03.000Z", {"type": "text", "text": "ok"}, _usage(5)
            ),
        ],
    )
    spans = _extract(path)
    assert [sp["attributes"]["llm.message.id"] for sp in spans] == ["msg_A", "msg_B"]
    assert spans[0]["attributes"]["llm.token_count.completion"] == 552
    assert spans[0]["start_ns"] == _ns("2026-10-08T00:00:01.000Z")
    assert spans[0]["end_ns"] == _ns("2026-10-08T00:00:02.000Z")
    assert spans[0]["tool_call_ids"] == ["toolu_a", "toolu_b"]


def test_iso_to_ns_is_exact_to_the_millisecond():
    # dt.timestamp() * 1e9 gives ...308999936 here, which floors to the wrong ms.
    assert cct._iso_to_ns("2026-10-08T06:22:12.309Z") == 1_791_440_532_309_000_000


def test_response_still_streaming_at_post_tool_use_is_emitted_once_complete(tracer_env):
    """PostToolUse for toolu_a fires before msg_A has written toolu_b."""
    transcript = tracer_env / "session.jsonl"
    transcript.write_text("")
    _hook(cct.handle_user_prompt_submit, str(transcript), prompt="go")
    entries = [
        _human("go", "2026-10-08T00:00:00.000Z"),
        _assistant("msg_A", "2026-10-08T00:00:01.000Z", _tool_use("toolu_a"), _usage(40)),
    ]
    _write(transcript, entries)

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        for tuid, ts_use, ts_result in (
            ("toolu_a", None, "2026-10-08T00:00:01.500Z"),
            ("toolu_b", "2026-10-08T00:00:02.000Z", "2026-10-08T00:00:02.500Z"),
        ):
            if ts_use:
                entries.append(_assistant("msg_A", ts_use, _tool_use(tuid), _usage(40), "tool_use"))
                _write(transcript, entries)
            _hook(
                cct.handle_pre_tool,
                str(transcript),
                tool_name="Bash",
                tool_input={},
                tool_use_id=tuid,
            )
            _hook(
                cct.handle_post_tool,
                str(transcript),
                tool_name="Bash",
                tool_input={},
                tool_use_id=tuid,
                tool_response="x",
            )
            entries.append(_tool_result(tuid, ts_result))
            _write(transcript, entries)
        assert not [sp for sp in exporter.spans if sp.name.startswith("claude/")], (
            "the open response is held back mid-turn"
        )

        entries.append(
            _assistant(
                "msg_B", "2026-10-08T00:00:03.000Z", {"type": "text", "text": "ok"}, _usage(5)
            )
        )
        _write(transcript, entries)
        _hook(cct.handle_stop, str(transcript))

    llm = [sp for sp in exporter.spans if sp.name.startswith("claude/")]
    assert [sp.attributes["llm.message.id"] for sp in llm] == ["msg_A", "msg_B"]
    msg_a = llm[0]
    assert msg_a.attributes["llm.token_count.completion"] == 40
    assert msg_a.end_time == _ns("2026-10-08T00:00:02.000Z")
    tools = [sp for sp in exporter.spans if sp.name == "Bash"]
    assert [sp.parent.span_id for sp in tools] == [msg_a.context.span_id] * 2


def test_tool_issued_by_a_response_without_message_id_never_gets_a_dangling_parent(tracer_env):
    """A response with no message.id gets a fresh span id on every re-extraction.

    PostToolUse and Stop each re-extract the turn, so the id a tool would be
    parented to at PostToolUse is not the id the LLM span is exported under.
    """
    transcript = tracer_env / "session.jsonl"
    transcript.write_text("")
    _hook(cct.handle_user_prompt_submit, str(transcript), prompt="go")
    entries = [
        _human("go", "2026-10-08T00:00:00.000Z"),
        _assistant("", "2026-10-08T00:00:01.000Z", _tool_use("toolu_a"), _usage(9), "tool_use"),
    ]
    _write(transcript, entries)

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _hook(
            cct.handle_pre_tool,
            str(transcript),
            tool_name="Bash",
            tool_input={},
            tool_use_id="toolu_a",
        )
        _hook(
            cct.handle_post_tool,
            str(transcript),
            tool_name="Bash",
            tool_input={},
            tool_use_id="toolu_a",
            tool_response="x",
        )
        entries += [
            _tool_result("toolu_a", "2026-10-08T00:00:02.000Z"),
            _assistant(
                "msg_B",
                "2026-10-08T00:00:03.000Z",
                {"type": "text", "text": "done"},
                _usage(5),
                "end_turn",
            ),
        ]
        _write(transcript, entries)
        _hook(cct.handle_stop, str(transcript))

    exported = {sp.context.span_id for sp in exporter.spans}
    (root,) = [sp for sp in exporter.spans if sp.name == "claude-code-turn"]
    (bash,) = [sp for sp in exporter.spans if sp.name == "Bash"]
    assert bash.parent.span_id in exported, "tool span parent was never exported (dangling)"
    assert bash.parent.span_id == root.context.span_id


def test_pending_inline_agent_outranks_the_issuing_llm_span_as_tool_parent(tracer_env):
    """Precedence rule 1: a tool run while an Agent is pending nests under the Agent."""
    transcript = tracer_env / "session.jsonl"
    transcript.write_text("")
    _hook(cct.handle_user_prompt_submit, str(transcript), prompt="go")
    agent_in = {"description": "look", "prompt": "look", "subagent_type": "Explore"}
    entries = [
        _human("go", "2026-10-08T00:00:00.000Z"),
        _assistant(
            "msg_A",
            "2026-10-08T00:00:01.000Z",
            _tool_use("toolu_agent", "Agent", agent_in),
            _usage(20),
        ),
        _assistant(
            "msg_A",
            "2026-10-08T00:00:02.000Z",
            _tool_use("toolu_read", "Read", {"file_path": "/a"}),
            _usage(20),
            "tool_use",
        ),
    ]
    _write(transcript, entries)

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _hook(
            cct.handle_pre_tool,
            str(transcript),
            tool_name="Agent",
            tool_input=agent_in,
            tool_use_id="toolu_agent",
        )
        _hook(
            cct.handle_pre_tool,
            str(transcript),
            tool_name="Read",
            tool_input={"file_path": "/a"},
            tool_use_id="toolu_read",
        )
        _hook(
            cct.handle_post_tool,
            str(transcript),
            tool_name="Read",
            tool_input={"file_path": "/a"},
            tool_use_id="toolu_read",
            tool_response="x",
        )
        _hook(
            cct.handle_post_tool,
            str(transcript),
            tool_name="Agent",
            tool_input=agent_in,
            tool_use_id="toolu_agent",
            tool_response="found it",
        )

    (agent,) = [sp for sp in exporter.spans if sp.name.startswith("Agent")]
    (read,) = [sp for sp in exporter.spans if sp.name == "Read"]
    assert cct._load_state(SESSION)["current_trace"]["llm_span_by_tool_call"]["toolu_read"] == (
        cct._llm_span_id("msg_A")
    ), "the issuing LLM span is known, so the Agent must win on precedence"
    assert read.parent.span_id == agent.context.span_id
    assert agent.parent.span_id == int(cct._llm_span_id("msg_A"), 16)
