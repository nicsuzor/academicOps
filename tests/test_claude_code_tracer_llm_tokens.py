"""Tests for LLM span emission with transcript-joined token counts in claude_code_tracer.

Guards:
- AC1: Tracer emits one LLM span per model call with input, output, cache token counts and model matching the transcript.
- AC2: Every span field other than token counts and model comes from hook inputs; fails if any other transcript field is read.
- AC3: Calls whose usage is not yet in the transcript when a hook fires still get their counts on a later span or flush.
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

CONFIG = {"endpoint": "http://collector.invalid:4318", "project_name": "academicOps"}
SESSION = "sess-llm-tokens"


class _CollectingExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def named(self, name: str) -> list:
        return [s for s in self.spans if s.name == name]

    def kind(self, kind_name: str) -> list:
        return [
            s
            for s in self.spans
            if (s.attributes or {}).get("openinference.span.kind") == kind_name
        ]


@pytest.fixture
def tracer_env(tmp_path, monkeypatch):
    monkeypatch.setattr(cct, "STATE_DIR", tmp_path / "tracer")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("")
    return transcript


@pytest.fixture
def exporter():
    exp = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exp):
        yield exp


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


def _assistant_entry(
    msg_id: str,
    model: str,
    usage: dict,
    content: list | None = None,
    ts: str = "2026-10-24T00:00:01.000Z",
) -> dict:
    msg: dict = {
        "id": msg_id,
        "model": model,
        "role": "assistant",
        "usage": usage,
    }
    if content is not None:
        msg["content"] = content
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": msg,
    }


def _user_entry(text: str, ts: str = "2026-10-24T00:00:00.000Z") -> dict:
    return {
        "type": "user",
        "timestamp": ts,
        "message": {"role": "user", "content": text},
    }


# ---------------------------------------------------------------------------
# AC1: One LLM span per model call with input, output, cache counts and model
# ---------------------------------------------------------------------------


def test_one_llm_span_per_model_call_with_token_counts_and_model(tracer_env, exporter):
    """Tracer emits one LLM span per model call carrying token counts and model from transcript."""
    usage_1 = {
        "input_tokens": 150,
        "output_tokens": 25,
        "cache_read_input_tokens": 1000,
        "cache_creation_input_tokens": 200,
    }
    usage_2 = {
        "input_tokens": 250,
        "output_tokens": 40,
        "cache_read_input_tokens": 1200,
        "cache_creation_input_tokens": 0,
    }

    # 1. User submits prompt (fires before Claude Code writes prompt to transcript)
    cct.handle_user_prompt_submit(
        {
            "session_id": SESSION,
            "prompt": "Run command and finish",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )

    _write_transcript(
        tracer_env,
        [
            _user_entry("Run command and finish"),
            _assistant_entry("msg_1", "claude-opus-5-5", usage_1),
            {
                "type": "user",
                "timestamp": "2026-10-24T00:00:02.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "hi\n"}
                    ],
                },
            },
            _assistant_entry("msg_2", "claude-opus-5-5", usage_2),
        ],
    )
    # 2. Model call 1 returns tool call -> PreToolUse fires
    cct.handle_pre_tool(
        {
            "session_id": SESSION,
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_use_id": "toolu_1",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )
    # 3. Tool runs and finishes -> PostToolUse fires
    cct.handle_post_tool(
        {
            "session_id": SESSION,
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_response": "hi\n",
            "tool_use_id": "toolu_1",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )
    # 4. Model call 2 returns final answer -> Stop fires
    cct.handle_stop(
        {
            "session_id": SESSION,
            "last_assistant_message": "Command finished successfully.",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )

    llm_spans = exporter.kind("LLM")
    assert len(llm_spans) == 2, f"Expected 2 LLM spans, got {len(llm_spans)}"

    # First LLM span (issued tool call)
    span_1 = llm_spans[0]
    attrs_1 = span_1.attributes or {}
    assert attrs_1["llm.model_name"] == "claude-opus-5-5"
    assert attrs_1["llm.token_count.prompt"] == 150 + 1000 + 200
    assert attrs_1["llm.token_count.completion"] == 25
    assert attrs_1["llm.token_count.total"] == 150 + 1000 + 200 + 25
    assert attrs_1["llm.token_count.prompt_details.cache_read"] == 1000
    assert attrs_1["llm.token_count.prompt_details.cache_write"] == 200
    assert attrs_1["input.value"] == "Run command and finish"
    assert "echo hi" in attrs_1["output.value"]

    # Second LLM span (issued final response)
    span_2 = llm_spans[1]
    attrs_2 = span_2.attributes or {}
    assert attrs_2["llm.model_name"] == "claude-opus-5-5"
    assert attrs_2["llm.token_count.prompt"] == 250 + 1200 + 0
    assert attrs_2["llm.token_count.completion"] == 40
    assert attrs_2["llm.token_count.total"] == 250 + 1200 + 40
    assert attrs_2["llm.token_count.prompt_details.cache_read"] == 1200
    assert attrs_2["llm.token_count.prompt_details.cache_write"] == 0
    assert attrs_2["input.value"] == "hi\n"
    assert attrs_2["output.value"] == "Command finished successfully."


# ---------------------------------------------------------------------------
# AC2: Span content fields come strictly from hook inputs, not transcript
# ---------------------------------------------------------------------------


def test_span_content_fields_come_from_hook_inputs_not_transcript(tracer_env, exporter):
    """Every span field other than token counts and model comes from hook inputs."""
    usage = {
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_input_tokens": 10,
        "cache_creation_input_tokens": 5,
    }

    # 1. User submits prompt via hook input
    cct.handle_user_prompt_submit(
        {
            "session_id": SESSION,
            "prompt": "Authentic prompt from hook input",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )

    # 2. Transcript carries adversarial content and future timestamps
    _write_transcript(
        tracer_env,
        [
            _user_entry("TRANSCRIPT_USER_PROMPT_THAT_MUST_NOT_BE_READ"),
            _assistant_entry(
                msg_id="msg_adversarial",
                model="claude-sonnet-4",
                usage=usage,
                content=[{"type": "text", "text": "CORRUPT_TRANSCRIPT_CONTENT_FORBIDDEN"}],
                ts="2099-01-01T00:00:00.000Z",
            ),
        ],
    )
    cct.handle_stop(
        {
            "session_id": SESSION,
            "last_assistant_message": "Authentic assistant reply from hook input",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )

    llm_spans = exporter.kind("LLM")
    assert len(llm_spans) == 1, f"Expected 1 LLM span, got {len(llm_spans)}"
    span = llm_spans[0]
    attrs = span.attributes or {}

    # Content fields MUST come from hook inputs
    assert attrs["input.value"] == "Authentic prompt from hook input"
    assert attrs["output.value"] == "Authentic assistant reply from hook input"

    # Transcript adversarial content MUST NOT appear in any attribute
    for k, v in attrs.items():
        assert "CORRUPT_TRANSCRIPT_CONTENT_FORBIDDEN" not in str(v), (
            f"Leaked transcript content in {k}"
        )
        assert "TRANSCRIPT_USER_PROMPT_THAT_MUST_NOT_BE_READ" not in str(v), f"Leaked prompt in {k}"

    # Timing must come from hook execution, NOT from transcript 2099 timestamp
    # 2099 timestamp in ns is > 4_000_000_000_000_000_000
    assert span.start_time < 3_000_000_000_000_000_000
    assert span.end_time < 3_000_000_000_000_000_000

    # Token counts and model MUST match transcript
    assert attrs["llm.model_name"] == "claude-sonnet-4"
    assert attrs["llm.token_count.prompt"] == 115
    assert attrs["llm.token_count.completion"] == 50
    assert attrs["llm.token_count.total"] == 165


def test_transcript_without_content_or_timestamp_fields_succeeds(tracer_env, exporter):
    """Tracer succeeds when transcript has only usage and model without content or timestamps."""
    raw_entry = {
        "type": "assistant",
        "message": {
            "model": "claude-haiku-3-5",
            "usage": {
                "input_tokens": 80,
                "output_tokens": 20,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        },
    }
    tracer_env.write_text(json.dumps(raw_entry) + "\n", encoding="utf-8")

    cct.handle_user_prompt_submit(
        {"session_id": SESSION, "prompt": "Quick check", "transcript_path": str(tracer_env)},
        CONFIG,
    )
    cct.handle_stop(
        {
            "session_id": SESSION,
            "last_assistant_message": "All good.",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )

    llm_spans = exporter.kind("LLM")
    assert len(llm_spans) == 1
    attrs = llm_spans[0].attributes or {}
    assert attrs["input.value"] == "Quick check"
    assert attrs["output.value"] == "All good."
    assert attrs["llm.model_name"] == "claude-haiku-3-5"
    assert attrs["llm.token_count.prompt"] == 80
    assert attrs["llm.token_count.completion"] == 20


# ---------------------------------------------------------------------------
# AC3: Delayed usage in transcript resolves on later span or flush
# ---------------------------------------------------------------------------


def test_delayed_transcript_usage_resolves_on_later_flush(tracer_env, exporter):
    """When usage is missing at tool completion, it resolves when transcript is flushed at turn stop."""
    # 1. User submits prompt
    cct.handle_user_prompt_submit(
        {"session_id": SESSION, "prompt": "Start task", "transcript_path": str(tracer_env)},
        CONFIG,
    )
    # Initially, transcript has user message but NO assistant usage yet (simulating write buffer lag)
    _write_transcript(tracer_env, [_user_entry("Start task")])
    cct.handle_pre_tool(
        {
            "session_id": SESSION,
            "tool_name": "Read",
            "tool_input": {"path": "file.txt"},
            "tool_use_id": "toolu_read",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )
    # When post_tool fires, the transcript still lacks usage
    cct.handle_post_tool(
        {
            "session_id": SESSION,
            "tool_name": "Read",
            "tool_input": {"path": "file.txt"},
            "tool_response": "file content\n",
            "tool_use_id": "toolu_read",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )

    # At this point, tool span was emitted, but LLM span was held open because usage wasn't written yet
    assert len(exporter.kind("TOOL")) == 1

    # Now the transcript writer flushes both model calls to disk
    usage_1 = {
        "input_tokens": 100,
        "output_tokens": 15,
        "cache_read_input_tokens": 50,
        "cache_creation_input_tokens": 0,
    }
    usage_2 = {
        "input_tokens": 150,
        "output_tokens": 30,
        "cache_read_input_tokens": 60,
        "cache_creation_input_tokens": 0,
    }
    _write_transcript(
        tracer_env,
        [
            _user_entry("Start task"),
            _assistant_entry("msg_1", "claude-sonnet-4", usage_1),
            {
                "type": "user",
                "timestamp": "2026-10-24T00:00:02.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_read",
                            "content": "file content\n",
                        }
                    ],
                },
            },
            _assistant_entry("msg_2", "claude-sonnet-4", usage_2),
        ],
    )

    # Turn completes with stop hook
    cct.handle_stop(
        {
            "session_id": SESSION,
            "last_assistant_message": "Task complete with file content.",
            "transcript_path": str(tracer_env),
        },
        CONFIG,
    )

    # Now both LLM spans have been emitted with their resolved counts
    llm_spans = exporter.kind("LLM")
    assert len(llm_spans) == 2, f"Expected 2 LLM spans, got {len(llm_spans)}"

    attrs_1 = llm_spans[0].attributes or {}
    assert attrs_1["llm.token_count.prompt"] == 150
    assert attrs_1["llm.token_count.completion"] == 15

    attrs_2 = llm_spans[1].attributes or {}
    assert attrs_2["llm.token_count.prompt"] == 210
    assert attrs_2["llm.token_count.completion"] == 30
