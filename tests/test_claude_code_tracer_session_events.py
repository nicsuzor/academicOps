"""Tool spans are redacted and capped, turn numbers carry across a session's
turns, and permission, notification, compaction and failed-turn events reach
Phoenix as spans under the turn they happened in.

The hooks are driven the way Claude Code drives them: one call per hook
event, a fresh state load each time, exports captured by a collecting
exporter in place of OTLP.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer as cct
import dispatch
import handlers

CONFIG = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}
SESSION = "sess-session-events"
SECRET = "ghp_supersecretvalue123456"


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


def _hook(handler, transcript: Path, **payload) -> None:
    handler({"session_id": SESSION, "transcript_path": str(transcript), **payload}, CONFIG)


def _hex(span_id: int) -> str:
    return f"{span_id:016x}"


# --- Tool span input and output: redaction and size cap ----------------------


def test_tool_span_input_and_output_redact_secrets(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", SECRET)
    rec = cct._build_tool_span_record(
        tool_name="Bash",
        tool_input={"command": f"curl -H 'Authorization: {SECRET}' https://x"},
        tool_response={"stdout": f"token={SECRET}"},
        start_ns=1,
        end_ns=2,
        trace_id="0" * 32,
        root_span_id="0" * 16,
    )
    attrs = rec["attributes"]
    assert SECRET not in attrs["input.value"]
    assert SECRET not in attrs["output.value"]
    assert "<REDACTED_SECRET>" in attrs["input.value"]
    assert "<REDACTED_SECRET>" in attrs["output.value"]


def test_failed_tool_span_redacts_error_message_and_status(monkeypatch):
    monkeypatch.setenv("SOME_API_KEY", SECRET)
    rec = cct._build_tool_span_record(
        tool_name="Bash",
        tool_input={"command": "x"},
        tool_response=f"denied for {SECRET}",
        start_ns=1,
        end_ns=2,
        trace_id="0" * 32,
        root_span_id="0" * 16,
        is_failure=True,
        error_msg=f"bad key {SECRET}",
    )
    assert SECRET not in rec["attributes"]["output.value"]
    assert SECRET not in rec["error_msg"]


def test_tool_span_input_and_output_are_capped(monkeypatch):
    monkeypatch.setattr(cct, "_MAX_ATTR_BYTES", 100)
    rec = cct._build_tool_span_record(
        tool_name="Read",
        tool_input={"file_path": "/a" * 200},
        tool_response="x" * 1000,
        start_ns=1,
        end_ns=2,
        trace_id="0" * 32,
        root_span_id="0" * 16,
    )
    for key in ("input.value", "output.value"):
        value = rec["attributes"][key]
        assert value.endswith("...[truncated]")
        assert len(value.encode()) == 100 + len("...[truncated]")


def test_retriever_input_is_redacted(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", SECRET)
    rec = cct._build_tool_span_record(
        tool_name="WebFetch",
        tool_input={"url": f"https://x/?t={SECRET}"},
        tool_response="ok",
        start_ns=1,
        end_ns=2,
        trace_id="0" * 32,
        root_span_id="0" * 16,
    )
    assert SECRET not in rec["attributes"]["input.value"]


def test_exported_tool_span_is_redacted(tracer_env, exporter, monkeypatch):
    """Through the real PreToolUse/PostToolUse hooks, not just the record builder."""
    monkeypatch.setenv("GH_TOKEN", SECRET)
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="go")
    tin = {"command": f"echo {SECRET}"}
    _hook(cct.handle_pre_tool, tracer_env, tool_name="Bash", tool_input=tin, tool_use_id="t1")
    _hook(
        cct.handle_post_tool,
        tracer_env,
        tool_name="Bash",
        tool_input=tin,
        tool_use_id="t1",
        tool_response={"stdout": SECRET},
    )
    (span,) = exporter.named("Bash")
    assert SECRET not in span.attributes["input.value"]
    assert SECRET not in span.attributes["output.value"]


def test_llm_span_input_redacts_prompt_and_tool_output(tmp_path, monkeypatch):
    """The LLM span after a tool call carries the tool output as its input,
    and the first LLM span carries the prompt; both are redacted."""
    monkeypatch.setenv("GH_TOKEN", SECRET)
    usage = {"input_tokens": 1, "output_tokens": 1}

    def assistant(msg_id, block):
        return {
            "type": "assistant",
            "timestamp": "2026-10-08T08:00:01.000Z",
            "message": {"id": msg_id, "model": "m", "content": [block], "usage": usage},
        }

    entries = [
        {"type": "user", "message": {"role": "user", "content": f"use token {SECRET}"}},
        assistant("msg_1", {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {}}),
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": f"GH_TOKEN={SECRET}",
                    },
                ],
            },
        },
        assistant("msg_2", {"type": "text", "text": "done"}),
    ]
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    spans = cct._extract_llm_spans_for_turn(str(transcript), 0, "0" * 31 + "1", "00000000000000aa")
    prompt_span, tool_span = (s["attributes"] for s in spans)
    assert prompt_span["llm.input_messages.0.message.role"] == "user"
    assert tool_span["llm.input_messages.0.message.role"] == "tool"
    for attrs in (prompt_span, tool_span):
        assert SECRET not in attrs["input.value"]
        assert "<REDACTED_SECRET>" in attrs["input.value"]
        assert SECRET not in attrs["llm.input_messages.0.message.content"]


def test_llm_span_input_redacts_a_secret_cut_by_the_preview_limit(tmp_path, monkeypatch):
    """Redaction runs before the 500-character preview cut, so no prefix of
    the secret survives."""
    monkeypatch.setenv("GH_TOKEN", SECRET)
    prompt = "x" * 490 + SECRET
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": prompt}})
        + "\n"
        + json.dumps(
            {
                "type": "assistant",
                "timestamp": "2026-10-08T08:00:01.000Z",
                "message": {
                    "id": "msg_1",
                    "model": "m",
                    "content": [{"type": "text", "text": "ok"}],
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                },
            },
        )
        + "\n",
    )
    (span,) = cct._extract_llm_spans_for_turn(
        str(transcript), 0, "0" * 31 + "1", "00000000000000aa"
    )
    assert SECRET[:10] not in span["attributes"]["input.value"]


# --- turn_number across turns -------------------------------------------------


def _turn_numbers(exporter: _CollectingExporter) -> list[int]:
    return [s.attributes["turn_number"] for s in exporter.named("claude-code-turn")]


def test_turn_number_increments_across_turns(tracer_env, exporter):
    for prompt in ("one", "two", "three"):
        _hook(cct.handle_user_prompt_submit, tracer_env, prompt=prompt)
        _hook(cct.handle_stop, tracer_env)
    assert _turn_numbers(exporter) == [1, 2, 3]


def test_turn_number_increments_when_a_turn_starts_without_user_prompt_submit(tracer_env, exporter):
    """The PreToolUse fallback that opens a turn reads the same counter."""
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="one")
    _hook(cct.handle_stop, tracer_env)
    _hook(cct.handle_pre_tool, tracer_env, tool_name="Bash", tool_input={}, tool_use_id="t")
    _hook(cct.handle_stop, tracer_env)
    assert _turn_numbers(exporter) == [1, 2]


def test_stop_keeps_session_state_and_drops_the_turn(tracer_env, exporter):
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="one")
    _hook(cct.handle_stop, tracer_env)
    state = cct._load_state(SESSION)
    assert state["turn_number"] == 1
    assert "current_trace" not in state
    assert "pending_tools" not in state


def test_session_end_deletes_state(tracer_env, exporter):
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="one")
    _hook(cct.handle_stop, tracer_env)
    _hook(cct.handle_session_end, tracer_env)
    assert not cct._state_path(SESSION).exists()


def test_session_end_sends_a_turn_left_open(tracer_env, exporter):
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="one")
    _hook(cct.handle_session_end, tracer_env)
    assert _turn_numbers(exporter) == [1]
    assert not cct._state_path(SESSION).exists()


def _append_prompt(transcript: Path, text: str) -> None:
    """Write a human prompt the way Claude Code does once UserPromptSubmit returns."""
    entry = {"type": "user", "message": {"role": "user", "content": text}}
    with transcript.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _prompted_turn(transcript: Path, text: str) -> None:
    _hook(cct.handle_user_prompt_submit, transcript, prompt=text)
    _append_prompt(transcript, text)
    _hook(cct.handle_stop, transcript)


def test_turn_number_continues_after_session_end_and_resume(tracer_env, exporter):
    """``claude --resume`` reuses the session id and transcript, but SessionEnd
    deleted the state file holding the counter."""
    _prompted_turn(tracer_env, "one")
    _prompted_turn(tracer_env, "two")
    _hook(cct.handle_session_end, tracer_env)
    assert not cct._state_path(SESSION).exists()

    _prompted_turn(tracer_env, "three")
    assert _turn_numbers(exporter) == [1, 2, 3]


def test_turn_opened_by_pre_tool_continues_after_resume(tracer_env, exporter):
    _prompted_turn(tracer_env, "one")
    _hook(cct.handle_session_end, tracer_env)

    _append_prompt(tracer_env, "two")
    _hook(cct.handle_pre_tool, tracer_env, tool_name="Bash", tool_input={}, tool_use_id="t")
    _hook(cct.handle_stop, tracer_env)
    assert _turn_numbers(exporter) == [1, 2]


# --- turn_number: entries that are not prompts ----------------------------------
#
# Entry shapes as Claude Code writes them. A typed or skill prompt carries
# promptId/turnOrigin/turnPosition and fires UserPromptSubmit; a local slash
# command (/model, /usage, /compact) writes string-content user entries
# without them and fires no UserPromptSubmit.

_CAVEAT = (
    "<local-command-caveat>Caveat: The messages below were generated by the user while"
    " running local commands. DO NOT respond to these messages or otherwise consider them"
    " in your response unless the user explicitly asks you to.</local-command-caveat>"
)


def _append(transcript: Path, *entries: dict) -> None:
    with transcript.open("a") as f:
        for entry in entries:
            f.write(json.dumps({"sessionId": SESSION, **entry}) + "\n")


def _real_prompted_turn(transcript: Path, text: str, index: int) -> None:
    _hook(cct.handle_user_prompt_submit, transcript, prompt=text)
    _append(
        transcript,
        {
            "type": "user",
            "promptId": f"p{index}",
            "turnOrigin": "user",
            "turnPosition": {"promptIndex": index, "turnIndex": 1},
            "message": {"role": "user", "content": text},
        },
    )
    _hook(cct.handle_stop, transcript)


def _local_command(transcript: Path, name: str, stdout: str) -> None:
    _append(
        transcript,
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": _CAVEAT}},
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": (
                    f"<command-name>/{name}</command-name>\n"
                    f"            <command-message>{name}</command-message>\n"
                    "            <command-args></command-args>"
                ),
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": f"<local-command-stdout>{stdout}</local-command-stdout>",
            },
        },
    )


def _compact_summary(trigger: str) -> list[dict]:
    return [
        {
            "type": "system",
            "subtype": "compact_boundary",
            "content": "Conversation compacted",
            "compactMetadata": {"trigger": trigger, "preTokens": 12345},
        },
        {
            "type": "user",
            "isCompactSummary": True,
            "isVisibleInTranscriptOnly": True,
            "message": {
                "role": "user",
                "content": "This session is being continued from a previous conversation"
                " that ran out of context. The conversation is summarized below: ...",
            },
        },
    ]


def test_local_slash_commands_between_prompts_do_not_advance_turn_number(tracer_env, exporter):
    _real_prompted_turn(tracer_env, "one", 0)
    _real_prompted_turn(tracer_env, "two", 1)
    _local_command(tracer_env, "usage", "Session usage: ...")
    _local_command(tracer_env, "model", "Set model to opus")
    _real_prompted_turn(tracer_env, "three", 2)
    assert _turn_numbers(exporter) == [1, 2, 3]


def test_local_slash_command_before_the_first_prompt_does_not_advance_turn_number(
    tracer_env, exporter
):
    _local_command(tracer_env, "model", "Set model to opus")
    _real_prompted_turn(tracer_env, "one", 0)
    assert _turn_numbers(exporter) == [1]


def test_manual_compact_does_not_advance_turn_number(tracer_env, exporter):
    _real_prompted_turn(tracer_env, "one", 0)
    # /compact: PreCompact and PostCompact fire, no UserPromptSubmit.
    _hook(cct.handle_pre_compact, tracer_env, trigger="manual")
    _local_command(tracer_env, "compact", "Compacted")
    _append(tracer_env, *_compact_summary("manual"))
    _hook(cct.handle_post_compact, tracer_env, trigger="manual")
    _real_prompted_turn(tracer_env, "two", 1)
    assert _turn_numbers(exporter) == [1, 2]


def test_auto_compact_mid_turn_keeps_one_turn(tracer_env, exporter):
    """Auto-compaction inside a turn writes a summary entry; the turn goes on."""
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="one")
    _append(
        tracer_env,
        {
            "type": "user",
            "promptId": "p0",
            "turnOrigin": "user",
            "turnPosition": {"promptIndex": 0, "turnIndex": 1},
            "message": {"role": "user", "content": "one"},
        },
        *_compact_summary("auto"),
    )
    _hook(cct.handle_pre_tool, tracer_env, tool_name="Bash", tool_input={}, tool_use_id="t")
    _hook(cct.handle_stop, tracer_env)
    _real_prompted_turn(tracer_env, "two", 1)
    assert _turn_numbers(exporter) == [1, 2]


def test_skill_prompt_counts_as_a_turn(tracer_env, exporter):
    """Skill invocations fire UserPromptSubmit and write a ``<command-message>`` entry."""
    _real_prompted_turn(tracer_env, "one", 0)
    _real_prompted_turn(
        tracer_env,
        "<command-message>ida:pull</command-message>\n<command-name>/ida:pull</command-name>\n"
        "<command-args>aops_0a08acad</command-args>",
        1,
    )
    _hook(cct.handle_session_end, tracer_env)
    _local_command(tracer_env, "model", "Set model to opus")
    _real_prompted_turn(tracer_env, "three", 2)
    assert _turn_numbers(exporter) == [1, 2, 3]


# --- Permission, notification, compaction spans --------------------------------


def _open_turn(transcript: Path) -> dict:
    _hook(cct.handle_user_prompt_submit, transcript, prompt="go")
    return cct._load_state(SESSION)["current_trace"]


def _assert_child_of_turn(span, current_trace: dict) -> None:
    assert _hex(span.parent.span_id) == current_trace["root_span_id"]
    assert f"{span.context.trace_id:032x}" == current_trace["trace_id"]
    assert span.attributes["openinference.span.kind"] == "CHAIN"
    assert span.attributes["session.id"] == SESSION


def test_permission_request_span(tracer_env, exporter, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", SECRET)
    ct = _open_turn(tracer_env)
    _hook(
        cct.handle_permission_request,
        tracer_env,
        tool_name="Bash",
        tool_input={"command": f"rm -rf /tmp/x {SECRET}"},
        permission_mode="default",
        permission_suggestions=[
            {
                "type": "addRules",
                "rules": [{"toolName": "Bash", "ruleContent": "rm -rf /tmp/x:*"}],
                "behavior": "allow",
                "destination": "localSettings",
            },
        ],
    )
    (span,) = exporter.named("Permission Request")
    _assert_child_of_turn(span, ct)
    assert span.attributes["permission.tool"] == "Bash"
    assert span.attributes["permission.mode"] == "default"
    assert "permission.type" not in span.attributes
    assert json.loads(span.attributes["permission.suggestions"])[0]["behavior"] == "allow"
    assert "rm -rf /tmp/x" in span.attributes["input.value"]
    assert SECRET not in span.attributes["input.value"]
    assert "permission.denied" not in span.attributes


def test_permission_denied_span(tracer_env, exporter):
    ct = _open_turn(tracer_env)
    _hook(
        cct.handle_permission_denied,
        tracer_env,
        tool_name="Write",
        tool_input={"file_path": "/etc/passwd"},
        tool_use_id="toolu_9",
        reason="auto mode classifier denied",
        permission_mode="auto",
    )
    (span,) = exporter.named("Permission Denied")
    _assert_child_of_turn(span, ct)
    assert span.attributes["permission.denied"] == "true"
    assert span.attributes["permission.mode"] == "auto"
    assert "permission.suggestions" not in span.attributes
    assert span.attributes["permission.tool"] == "Write"
    assert span.attributes["permission.reason"] == "auto mode classifier denied"
    assert span.attributes["tool.call_id"] == "toolu_9"


def test_notification_span(tracer_env, exporter):
    ct = _open_turn(tracer_env)
    _hook(
        cct.handle_notification,
        tracer_env,
        notification_type="permission_prompt",
        message="Claude needs your permission to use Bash",
        title="Permission needed",
    )
    (span,) = exporter.named("Notification: permission_prompt")
    _assert_child_of_turn(span, ct)
    assert span.attributes["notification.type"] == "permission_prompt"
    assert span.attributes["notification.message"] == "Claude needs your permission to use Bash"
    assert span.attributes["notification.title"] == "Permission needed"
    assert span.attributes["input.value"] == "Claude needs your permission to use Bash"


def test_compaction_span_covers_pre_to_post_compact(tracer_env, exporter):
    ct = _open_turn(tracer_env)
    _hook(cct.handle_pre_compact, tracer_env, trigger="auto")
    pre_ns = cct._load_state(SESSION)["current_trace"]["compact_start_ns"]
    _hook(cct.handle_post_compact, tracer_env, trigger="auto", compact_summary="summary text")
    (span,) = exporter.named("Compact (auto)")
    _assert_child_of_turn(span, ct)
    assert span.start_time == pre_ns
    assert span.end_time >= pre_ns
    assert span.attributes["compact.trigger"] == "auto"
    assert span.attributes["output.value"] == "summary text"
    assert "compact_start_ns" not in cct._load_state(SESSION)["current_trace"]


def test_compaction_trigger_falls_back_to_pre_compact(tracer_env, exporter):
    _open_turn(tracer_env)
    _hook(cct.handle_pre_compact, tracer_env, trigger="manual")
    _hook(cct.handle_post_compact, tracer_env)
    assert len(exporter.named("Compact (manual)")) == 1


@pytest.mark.parametrize(
    ("handler", "payload"),
    [
        ("handle_permission_request", {"tool_name": "Bash", "tool_input": {}}),
        ("handle_permission_denied", {"tool_name": "Bash", "tool_input": {}}),
        ("handle_notification", {"notification_type": "idle_prompt", "message": "m"}),
        ("handle_post_compact", {"trigger": "manual"}),
    ],
)
def test_events_outside_a_turn_emit_nothing(tracer_env, exporter, handler, payload):
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="go")
    _hook(cct.handle_stop, tracer_env)
    before = len(exporter.spans)
    _hook(getattr(cct, handler), tracer_env, **payload)
    assert len(exporter.spans) == before


# --- Failed turn (StopFailure) -------------------------------------------------


def test_stop_failure_sends_the_turn_root_with_error_status(tracer_env, exporter):
    ct = _open_turn(tracer_env)
    _hook(
        cct.handle_stop_failure,
        tracer_env,
        error="rate_limit",
        error_details="429 Too Many Requests",
        last_assistant_message="API Error: Rate limit reached",
    )
    (root,) = exporter.named("claude-code-turn")
    assert _hex(root.context.span_id) == ct["root_span_id"]
    assert root.status.status_code == StatusCode.ERROR
    assert root.status.description == "rate_limit"
    assert root.attributes["error.type"] == "rate_limit"
    assert root.attributes["error.message"] == "429 Too Many Requests"
    assert root.attributes["turn.failed"] is True
    assert root.attributes["output.value"] == "API Error: Rate limit reached"
    assert root.attributes["turn_number"] == 1


def test_stop_failure_without_message_names_the_error(tracer_env, exporter):
    _open_turn(tracer_env)
    _hook(cct.handle_stop_failure, tracer_env, error="authentication_failed")
    (root,) = exporter.named("claude-code-turn")
    assert root.attributes["output.value"] == "(Stop failed: authentication_failed)"


def test_turn_after_a_failed_turn_is_numbered_next(tracer_env, exporter):
    _open_turn(tracer_env)
    _hook(cct.handle_stop_failure, tracer_env, error="server_error")
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="retry")
    _hook(cct.handle_stop, tracer_env)
    roots = exporter.named("claude-code-turn")
    assert [r.attributes["turn_number"] for r in roots] == [1, 2]
    assert roots[1].status.status_code != StatusCode.ERROR


# --- Wiring: each event reaches the tracer through handlers.HANDLERS ----------


@pytest.mark.parametrize(
    ("event", "payload", "span_name"),
    [
        ("PermissionRequest", {"tool_name": "Bash", "tool_input": {}}, "Permission Request"),
        ("PermissionDenied", {"tool_name": "Bash", "tool_input": {}}, "Permission Denied"),
        ("Notification", {"notification_type": "idle_prompt", "message": "m"}, None),
        ("PostCompact", {"trigger": "auto"}, "Compact (auto)"),
        ("StopFailure", {"error": "server_error"}, "claude-code-turn"),
    ],
)
def test_handlers_route_event_to_tracer(
    tracer_env, exporter, monkeypatch, event, payload, span_name
):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector.invalid:4318")
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="go")
    raw = {"session_id": SESSION, "transcript_path": str(tracer_env), **payload}
    ctx = dispatch.HookContext(client="claude", event=event, session_id=SESSION, raw=raw)
    for handler in handlers.HANDLERS[event]:
        handler(ctx)
    name = span_name or "Notification: idle_prompt"
    assert len(exporter.named(name)) == 1


def test_handlers_route_session_end_to_tracer(tracer_env, exporter, monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector.invalid:4318")
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="go")
    raw = {"session_id": SESSION, "transcript_path": str(tracer_env)}
    ctx = dispatch.HookContext(client="claude", event="SessionEnd", session_id=SESSION, raw=raw)
    for handler in handlers.HANDLERS["SessionEnd"]:
        handler(ctx)
    assert not cct._state_path(SESSION).exists()


def test_pre_compact_is_wired(tracer_env, exporter, monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector.invalid:4318")
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt="go")
    raw = {"session_id": SESSION, "transcript_path": str(tracer_env), "trigger": "auto"}
    ctx = dispatch.HookContext(client="claude", event="PreCompact", session_id=SESSION, raw=raw)
    for handler in handlers.HANDLERS["PreCompact"]:
        handler(ctx)
    assert "compact_start_ns" in cct._load_state(SESSION)["current_trace"]


def test_manifest_wires_every_new_event():
    manifest = json.loads((REPO_ROOT / "plugins/ida/manifest/hooks.json").read_text())
    wired = manifest["clients"]["claude"]["hooks"]
    for event in (
        "StopFailure",
        "PermissionRequest",
        "PermissionDenied",
        "Notification",
        "PreCompact",
        "PostCompact",
        "SessionEnd",
    ):
        (entry,) = wired[event]
        assert entry["hooks"][0]["command"].endswith(f'dispatch.py" claude {event}')
