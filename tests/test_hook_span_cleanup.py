"""Behavioural tests for hook-span cleanup across Claude Code and agy surfaces."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

LIB_HOOKS = Path(__file__).resolve().parent.parent / "lib" / "hooks"
if str(LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(LIB_HOOKS))

import agy_tracer
import claude_code_tracer as cct

CONFIG = {
    "endpoint": "http://collector.invalid:4318",
    "project_name": "academicOps",
    "task_id": "task_1234abcd",
}


class _CollectingExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


@pytest.fixture
def exporter(monkeypatch):
    exp = _CollectingExporter()
    monkeypatch.setattr(cct, "_create_exporter", lambda *a, **kw: exp)
    return exp


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(cct, "STATE_DIR", tmp_path / "tracer")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("AOPS_AGENT_NAME", raising=False)
    return tmp_path


def test_agy_turn_span_uses_short_event_name_mime_types_and_agy_scope(isolated_state, exporter):
    session_id = "11111111-1111-1111-1111-111111111111"
    transcript = isolated_state / "agy_transcript.jsonl"
    long_prompt = "The following is a <SYSTEM_MESSAGE> " + ("x" * 1200)
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "SYSTEM_MESSAGE",
                        "source": "SYSTEM",
                        "content": long_prompt,
                    }
                ),
                json.dumps(
                    {
                        "type": "PLANNER_RESPONSE",
                        "source": "MODEL",
                        "step_index": 0,
                        "content": "Final reply",
                        "created_at": "2026-11-18T09:40:22Z",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with patch("agy_tracer._session_lock"):
        agy_tracer.handle_pre_invocation(
            {"conversationId": session_id, "transcriptPath": str(transcript), "invocationNum": 0},
            CONFIG,
        )
        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            CONFIG,
        )

    chain_spans = [
        s for s in exporter.spans if s.attributes.get("openinference.span.kind") == "CHAIN"
    ]
    assert len(chain_spans) == 1
    root = chain_spans[0]
    assert root.name == "agy-turn"
    assert "<SYSTEM_MESSAGE>" not in root.name
    assert root.attributes.get("input.mime_type") == "text/plain"
    assert root.attributes.get("output.mime_type") == "text/plain"
    assert root.instrumentation_scope.name == "agy-tracer"
    for span in exporter.spans:
        assert not any(k.startswith("lmnr.") for k in span.attributes)
        assert not any(k.startswith("gen_ai.") for k in span.attributes)


def test_claude_root_turn_omits_subagent_id_and_uses_claude_scope(isolated_state, exporter):
    session_id = "22222222-2222-2222-2222-222222222222"
    transcript = isolated_state / "claude_transcript.jsonl"
    transcript.write_text("", encoding="utf-8")

    with patch("claude_code_tracer._session_lock"):
        cct.handle_user_prompt_submit(
            {
                "session_id": session_id,
                "transcript_path": str(transcript),
                "prompt": "Check status",
            },
            CONFIG,
        )
        cct.handle_stop(
            {
                "session_id": session_id,
                "transcript_path": str(transcript),
                "last_assistant_message": "All good.",
            },
            CONFIG,
        )

    assert len(exporter.spans) >= 1
    root = next(s for s in exporter.spans if s.name == "claude-code-turn")
    assert root.instrumentation_scope.name == "claude-code-tracer"
    assert "subagent.id" not in root.attributes
    assert "subagent.id" not in root.resource.attributes
    assert not any(k.startswith("lmnr.") for k in root.attributes)
    assert not any(k.startswith("gen_ai.") for k in root.attributes)


def test_subagent_sets_subagent_id_when_distinct_from_root_session(
    isolated_state, exporter, monkeypatch
):
    root_session = "33333333-3333-3333-3333-333333333333"
    sub_session = "44444444-4444-4444-4444-444444444444"
    monkeypatch.setenv("AOPS_SESSION_ID", root_session)

    with patch("claude_code_tracer._session_lock"):
        cct.emit_debug_hook_span(
            {"session_id": sub_session, "hook_event_name": "PreToolUse", "tool_name": "Read"},
            CONFIG,
            client="claude",
            event="PreToolUse",
            raw_payload={"session_id": sub_session, "tool_name": "Read"},
        )

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.attributes["session.id"] == root_session
    assert span.attributes["subagent.id"] == sub_session


def test_service_instance_id_is_stable_per_session_and_tag_task_id_is_absent(
    isolated_state, exporter
):
    session_id = "55555555-5555-5555-5555-555555555555"
    for event in ("SessionStart", "UserPromptSubmit"):
        with patch("claude_code_tracer._session_lock"):
            cct.emit_debug_hook_span(
                {"session_id": session_id, "hook_event_name": event},
                CONFIG,
                client="claude",
                event=event,
                raw_payload={"session_id": session_id},
            )

    assert len(exporter.spans) == 2
    inst_ids = {s.resource.attributes.get("service.instance.id") for s in exporter.spans}
    assert inst_ids == {session_id}
    for s in exporter.spans:
        assert s.attributes.get("task.id") == "task_1234abcd"
        assert "tag.task_id" not in s.attributes
        assert "tag.task_id" not in s.resource.attributes


def test_payload_context_attributes_attached_when_present(isolated_state, exporter):
    session_id = "66666666-6666-6666-6666-666666666666"
    payload = {
        "session_id": session_id,
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Hello",
        "prompt_id": "prompt-abc-123",
        "permission_mode": "bypassPermissions",
        "agent_type": "ida:james",
        "session_title": "Hook tracing cleanup",
    }
    with patch("claude_code_tracer._session_lock"):
        cct.emit_debug_hook_span(
            payload,
            CONFIG,
            client="claude",
            event="UserPromptSubmit",
            raw_payload=payload,
        )

    span = exporter.spans[0]
    assert span.attributes.get("prompt.id") == "prompt-abc-123"
    assert span.attributes.get("permission.mode") == "bypassPermissions"
    assert span.attributes.get("agent.type") == "ida:james"
    assert span.attributes.get("session.title") == "Hook tracing cleanup"


@pytest.mark.parametrize(
    "prompt,expected_origin,extra_key,extra_val",
    [
        ("Check the build", "user", None, None),
        (
            '<agent-message from="sub-99">finished</agent-message>',
            "handback",
            "handback.subagent_id",
            "sub-99",
        ),
        (
            '<channel source="telegram" chat_id="42">ping</channel>',
            "channel",
            "channel.source",
            "telegram",
        ),
        ("The following is a <SYSTEM_MESSAGE> notice", "system", None, None),
        (
            "<SYSTEM_MESSAGE>\n[Message] sender=system content=Subagent went idle\n</SYSTEM_MESSAGE>",
            "system",
            None,
            None,
        ),
    ],
)
def test_prompt_origin_classification_on_user_prompt_submit(
    isolated_state, exporter, prompt, expected_origin, extra_key, extra_val
):
    session_id = f"77777777-7777-7777-7777-{expected_origin:>012}"[:36]
    payload = {
        "session_id": session_id,
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }
    with patch("claude_code_tracer._session_lock"):
        cct.emit_debug_hook_span(
            payload,
            CONFIG,
            client="claude",
            event="UserPromptSubmit",
            raw_payload=payload,
        )

    span = exporter.spans[-1]
    assert span.attributes.get("prompt.origin") == expected_origin
    if extra_key:
        assert span.attributes.get(extra_key) == extra_val
    else:
        assert "handback.subagent_id" not in span.attributes
