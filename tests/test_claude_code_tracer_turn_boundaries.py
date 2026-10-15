"""Every turn keeps its LLM spans and its final answer, whatever its prompt shape.

The fixtures are a real Claude Code transcript, replayed through the tracer's
hooks in the order Claude Code fires them. ``injected_turns.jsonl`` holds one
session's typed prompts, an idle ``<task-notification>``, a ``<channel>``
message and a ``<cross-session-message>`` (both written ``isMeta``), each
followed by a typed prompt. ``midturn_notification.jsonl`` holds a
``<task-notification>`` that arrived while a turn was running, written as a
``queued_command`` attachment. ``queued_prompt_during_notification.jsonl``
holds a typed prompt queued while a ``<task-notification>`` turn ran.

The replay fires UserPromptSubmit before the turn's prompt is written, and
Stop before the turn's final response is written: Claude Code awaits the
transcript write before running a tool, not before Stop hooks.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer as cct

FIXTURES = Path(__file__).parent / "fixtures" / "claude_transcripts"
CONFIG = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}
SESSION = "sess-turn-boundaries"


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


def _lines(name: str) -> list[str]:
    return (FIXTURES / name).read_text().splitlines(keepends=True)


def _entry(line: str) -> dict:
    return json.loads(line)


def _is_prompt(entry: dict) -> bool:
    """A prompt that fired UserPromptSubmit: it carries an ``origin``, or is a queued command."""
    if entry.get("type") == "attachment":
        return (entry.get("attachment") or {}).get("type") == "queued_command"
    return (
        entry.get("type") == "user"
        and "origin" in entry
        and isinstance(entry["message"].get("content"), str)
    )


def _prompt_text(entry: dict) -> str:
    if entry.get("type") == "attachment":
        return entry["attachment"]["prompt"]
    return entry["message"]["content"]


def _response_ids(lines: list[str]) -> list[str]:
    ids: list[str] = []
    for line in lines:
        e = _entry(line)
        if e.get("type") == "assistant" and e["message"]["id"] not in ids:
            ids.append(e["message"]["id"])
    return ids


def _final_text(lines: list[str]) -> str:
    """Text of the last response in *lines*, as Stop's ``last_assistant_message`` carries it."""
    final_id = _response_ids(lines)[-1]
    return "".join(
        block["text"]
        for line in lines
        if (e := _entry(line)).get("type") == "assistant" and e["message"]["id"] == final_id
        for block in e["message"]["content"]
        if block.get("type") == "text"
    )


def _final_start(lines: list[str]) -> int:
    """Index of the first line of the last response in *lines*."""
    final_id = _response_ids(lines)[-1]
    return next(
        i
        for i, line in enumerate(lines)
        if _entry(line).get("type") == "assistant" and _entry(line)["message"]["id"] == final_id
    )


def _turns(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) line ranges, one per prompt that fired UserPromptSubmit."""
    starts = [i for i, line in enumerate(lines) if _is_prompt(_entry(line))]
    return list(zip(starts, [*starts[1:], len(lines)], strict=True))


def _hook(handler, transcript: Path, **payload) -> None:
    handler({"session_id": SESSION, "transcript_path": str(transcript), **payload}, CONFIG)


def _replay(transcript: Path, lines: list[str], turns: list[tuple[int, int]]) -> None:
    """Fire UserPromptSubmit and Stop for each turn, with the final response written after Stop."""
    for start, end in turns:
        turn = lines[start:end]
        _hook(cct.handle_user_prompt_submit, transcript, prompt=_prompt_text(_entry(lines[start])))
        final = start + _final_start(turn)
        with transcript.open("a") as fh:
            fh.writelines(lines[start:final])
        _hook(cct.handle_stop, transcript, last_assistant_message=_final_text(turn))
        with transcript.open("a") as fh:
            fh.writelines(lines[final:end])


def _by_trace(exporter: _CollectingExporter) -> list[tuple[object, list[str]]]:
    """(root span, LLM message ids in its trace) per turn, in turn order."""
    roots = [sp for sp in exporter.spans if sp.name == "claude-code-turn"]
    return [
        (
            root,
            sorted(
                sp.attributes["llm.message.id"]
                for sp in exporter.spans
                if sp.context.trace_id == root.context.trace_id and sp.name.startswith("claude/")
            ),
        )
        for root in roots
    ]


def _assert_every_turn_complete(lines, turns, exporter) -> None:
    traced = _by_trace(exporter)
    assert len(traced) == len(turns)
    for (start, end), (root, llm_ids) in zip(turns, traced, strict=True):
        turn = lines[start:end]
        assert llm_ids == sorted(_response_ids(turn)), _prompt_text(_entry(lines[start]))[:60]
        assert root.attributes.get("output.value") == _final_text(turn)
        assert root.attributes["output.value"]


PROMPT_SHAPES = {
    "typed": "Reply with exactly: T1-ok",
    "task-notification": "<task-notification>",
    "channel": "<channel ",
    "cross-session": "Another Claude session sent a message:",
    "typed after injected": "Reply with exactly: T4-after-notification",
}


def test_fixture_holds_every_prompt_shape():
    lines = _lines("injected_turns.jsonl")
    prompts = [_prompt_text(_entry(lines[s])) for s, _ in _turns(lines)]
    for shape, opening in PROMPT_SHAPES.items():
        assert any(p.startswith(opening) for p in prompts), shape
    meta = [_entry(lines[s]) for s, _ in _turns(lines) if _entry(lines[s]).get("isMeta")]
    assert sorted(e["origin"]["kind"] for e in meta) == ["channel", "peer"]


def test_every_turn_has_one_llm_span_per_response_and_its_final_answer(tracer_env, monkeypatch):
    """Final responses reach the transcript only after Stop has given up waiting."""
    monkeypatch.setattr(cct, "FINAL_RESPONSE_WAIT_S", 0.0, raising=False)
    lines = _lines("injected_turns.jsonl")
    turns = _turns(lines)
    transcript = tracer_env / "session.jsonl"
    transcript.write_text("".join(lines[: turns[0][0]]))
    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _replay(transcript, lines, turns)
        _hook(cct.handle_session_end, transcript)
    _assert_every_turn_complete(lines, turns, exporter)


@pytest.mark.parametrize("shape", sorted(PROMPT_SHAPES))
def test_final_response_flushed_while_stop_waits_is_sent_at_stop(tracer_env, shape):
    """Stop waits for the final response and sends its LLM span before the next prompt."""
    lines = _lines("injected_turns.jsonl")
    start, end = next(
        (s, e)
        for s, e in _turns(lines)
        if _prompt_text(_entry(lines[s])).startswith(PROMPT_SHAPES[shape])
    )
    turn = lines[start:end]
    final = start + _final_start(turn)
    transcript = tracer_env / "session.jsonl"
    with transcript.open("w") as fh:
        fh.writelines(lines[:start])

    def flush_final() -> None:
        with transcript.open("a") as fh:
            fh.writelines(lines[final:end])

    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _hook(cct.handle_user_prompt_submit, transcript, prompt=_prompt_text(_entry(lines[start])))
        with transcript.open("a") as fh:
            fh.writelines(lines[start:final])
        timer = threading.Timer(0.3, flush_final)
        timer.start()
        _hook(cct.handle_stop, transcript, last_assistant_message=_final_text(turn))
        timer.join()
        sent_at_stop = list(exporter.spans)

    ((root, llm_ids),) = _by_trace(_with(sent_at_stop))
    assert llm_ids == sorted(_response_ids(turn))
    assert root.attributes["output.value"] == _final_text(turn)


def _with(spans) -> _CollectingExporter:
    exporter = _CollectingExporter()
    exporter.spans = spans
    return exporter


def test_notification_arriving_mid_turn_opens_a_turn_with_its_llm_spans(tracer_env, monkeypatch):
    """The ``queued_command`` attachment fires UserPromptSubmit while the previous turn runs."""
    monkeypatch.setattr(cct, "FINAL_RESPONSE_WAIT_S", 0.0, raising=False)
    lines = _lines("midturn_notification.jsonl")
    turns = _turns(lines)
    kinds = [_entry(lines[s]).get("type") for s, _ in turns]
    q = kinds.index("attachment")
    assert q > 0 and q < len(turns) - 1
    before, (interrupted, queued), after = turns[: q - 1], turns[q - 1], turns[q:]
    transcript = tracer_env / "session.jsonl"
    transcript.write_text("".join(lines[: turns[0][0]]))
    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _replay(transcript, lines, before)
        # This turn runs until the notification is queued; the queued prompt closes it, not Stop.
        prompt = _prompt_text(_entry(lines[interrupted]))
        _hook(cct.handle_user_prompt_submit, transcript, prompt=prompt)
        with transcript.open("a") as fh:
            fh.writelines(lines[interrupted:queued])
        _replay(transcript, lines, after)
        _hook(cct.handle_session_end, transcript)

    traced = _by_trace(exporter)
    root, llm_ids = traced[q - 1]
    assert llm_ids == sorted(_response_ids(lines[interrupted:queued]))
    assert root.attributes["output.value"]
    others = [sp for i, (r, _) in enumerate(traced) if i != q - 1 for sp in _trace_of(exporter, r)]
    _assert_every_turn_complete(lines, before + after, _with(others))


def _trace_of(exporter: _CollectingExporter, root) -> list:
    return [sp for sp in exporter.spans if sp.context.trace_id == root.context.trace_id]


def test_prompt_queued_during_a_turn_leaves_that_turns_responses_in_its_own_trace(tracer_env):
    """A typed prompt queued while a notification turn runs fires UserPromptSubmit at once.

    The notification turn's last response is written after that, and the
    queued prompt's entry only after the response; the one Stop that follows
    ends the notification turn.
    """
    lines = _lines("queued_prompt_during_notification.jsonl")
    turns = _turns(lines)
    *answered, (notification, queued_prompt) = turns[:-1]
    enqueued = next(
        i
        for i in range(notification, queued_prompt)
        if (e := _entry(lines[i])).get("type") == "queue-operation"
        and e.get("operation") == "enqueue"
        and e.get("content") == _prompt_text(_entry(lines[queued_prompt]))
    )
    transcript = tracer_env / "session.jsonl"
    transcript.write_text("".join(lines[: turns[0][0]]))
    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _replay(transcript, lines, answered)
        prompt = _prompt_text(_entry(lines[notification]))
        _hook(cct.handle_user_prompt_submit, transcript, prompt=prompt)
        with transcript.open("a") as fh:
            fh.writelines(lines[notification:enqueued])
        _hook(
            cct.handle_user_prompt_submit,
            transcript,
            prompt=_prompt_text(_entry(lines[queued_prompt])),
        )
        with transcript.open("a") as fh:
            fh.writelines(lines[enqueued:queued_prompt])
        notification_turn = lines[notification:queued_prompt]
        _hook(cct.handle_stop, transcript, last_assistant_message=_final_text(notification_turn))
        with transcript.open("a") as fh:
            fh.writelines(lines[queued_prompt:])
        _hook(cct.handle_session_end, transcript)

    traced = _by_trace(exporter)
    assert len(traced) == len(turns)
    root, llm_ids = traced[len(answered)]
    assert llm_ids == sorted(_response_ids(notification_turn))
    assert root.attributes["output.value"]
    queued_root, queued_ids = traced[-1]
    assert queued_ids == []
    assert queued_root.attributes["input.value"] == _prompt_text(_entry(lines[queued_prompt]))
    every_id = [mid for _, ids in traced for mid in ids]
    assert len(every_id) == len(set(every_id))


def test_final_response_never_written_is_sent_from_stop_payload_at_session_end(
    tracer_env, monkeypatch
):
    """Claude Code can exit before writing the last turn's response."""
    monkeypatch.setattr(cct, "FINAL_RESPONSE_WAIT_S", 0.0, raising=False)
    lines = _lines("injected_turns.jsonl")
    start, end = _turns(lines)[0]
    turn = lines[start:end]
    final = start + _final_start(turn)
    transcript = tracer_env / "session.jsonl"
    transcript.write_text("".join(lines[:start]))
    exporter = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exporter):
        _hook(cct.handle_user_prompt_submit, transcript, prompt=_prompt_text(_entry(lines[start])))
        with transcript.open("a") as fh:
            fh.writelines(lines[start:final])
        _hook(cct.handle_stop, transcript, last_assistant_message=_final_text(turn))
        _hook(cct.handle_session_end, transcript)

    (root,) = [sp for sp in exporter.spans if sp.name == "claude-code-turn"]
    llm = [
        sp
        for sp in exporter.spans
        if sp.context.trace_id == root.context.trace_id
        and sp.attributes.get("openinference.span.kind") == "LLM"
    ]
    assert [sp.attributes["output.value"] for sp in llm] == [_final_text(turn)]
    assert llm[0].attributes["aops.llm.source"] == "stop.last_assistant_message"
    assert llm[0].parent.span_id == root.context.span_id
    assert root.attributes["output.value"] == _final_text(turn)
