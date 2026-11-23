"""Tests for the premise-check verdict script and its gate.

Covers:
1. A verdict is one token (PASS, REVISE, FAIL) plus a free-text reason; the
   reason may come inline, from a file, or from stdin. A malformed verdict
   never disarms the gate.
2. record_verdict() emits a TOOL span (via a stubbed claude_code_tracer)
   carrying the token and the reason, and disarms the gate.
3. A failed span emission (unconfigured tracer or unacknowledged export)
   fails the verdict call and leaves the gate armed.
4. premise_check_handler refuses the next dispatch, message or stop while
   armed, allows it once disarmed, and respects mode=warn/off and overrides.
5. premise_check_arm arms only for the gated agents (ida, sara), and only on
   an incoming peer or worker report -- never on the agent's own outgoing tool
   calls, subagent dispatches included, and never on the user's own messages.
"""

from __future__ import annotations

import importlib.util
import json
import shlex
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugins" / "ida"
_HOOKS_DIR = _PLUGIN_ROOT / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_POLICY = tomllib.loads((_REPO_ROOT / "tests" / "policy.toml").read_text(encoding="utf-8"))

import dispatch
import hearsay_gate as hg
import premise_check_gate as pcg
import premise_check_verdict as pcv


def _pass_reason(claim_id: str) -> str:
    """A natural-language PASS reason for an armed claim."""
    return (
        f"PASS {claim_id}: the cited evidence supports the conclusion directly "
        "and answers the stated ask."
    )


_SAMPLE_VALID_BLOCK = (
    "\n```argdown\n"
    "===\n"
    "asks:\n"
    "  tg-1: is it done?\n"
    "answers:\n"
    "  tg-1: 2\n"
    "===\n\n"
    "(1) p -- rule\n"
    "-- warrant --\n"
    "(2) c\n"
    "```\n"
)


def _load_plugin_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate_state"))
    monkeypatch.delenv("PREMISE_CHECK_GATE_MODE", raising=False)
    monkeypatch.delenv("PREMISE_CHECK_GATE_OVERRIDE", raising=False)
    monkeypatch.delenv("AOP_FORCE", raising=False)
    monkeypatch.delenv("AOP_OVERRIDE", raising=False)
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    yield


class _StubTracer:
    """A minimal stand-in for claude_code_tracer, recording what it was asked to export."""

    def __init__(
        self,
        config: dict[str, Any] | None,
        export_ok: bool = True,
        raises: BaseException | None = None,
    ):
        self._config = config
        self._export_ok = export_ok
        self._raises = raises
        self.exported: list[dict[str, Any]] = []

    def discover_config(self):
        return self._config

    def _new_trace_id(self):
        return "1" * 32

    def _new_span_id(self):
        return "2" * 16

    def _load_state(self, session_id):
        return {}

    def _truncate(self, value):
        return value if isinstance(value, str) else str(value)

    def _build_tool_span_record(self, **kwargs):
        return {
            "trace_id_hex": kwargs["trace_id"],
            "span_id_hex": self._new_span_id(),
            "parent_span_id_hex": kwargs["root_span_id"],
            "name": kwargs["tool_name"],
            "kind": None,
            "start_ns": kwargs["start_ns"],
            "end_ns": kwargs["end_ns"],
            "attributes": {
                "openinference.span.kind": "TOOL",
                "tool.name": kwargs["tool_name"],
            },
            "force_span_id": False,
        }

    def _build_and_export_spans(self, *, config, session_id, username, span_records, **_kw):
        if self._raises is not None:
            raise self._raises
        self.exported.append(
            {
                "config": config,
                "session_id": session_id,
                "username": username,
                "spans": span_records,
            }
        )
        return self._export_ok


# ---------------------------------------------------------------------------
# 2. Verdict format: an enum token plus free text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", ["PASS", "REVISE", "FAIL"])
def test_record_verdict_accepts_each_token_with_reason_and_disarms(token):
    session_id = f"sess-{token}"
    pcg.arm(session_id, claim_id="claim-1")
    tracer = _StubTracer(config={"endpoint": "http://x"})

    reason = (
        _pass_reason("claim-1")
        if token == "PASS"
        else "The cited diff supports each claim; the conclusion answers the ask."
    )
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="claim-1",
        verdict=token,
        reason=reason,
        tracer_mod=tracer,
    )

    assert result["ok"] is True
    assert result["verdict"] == token
    assert result["disarmed"] is True
    attrs = tracer.exported[0]["spans"][0]["attributes"]
    assert attrs["premise_check.verdict"] == token
    assert attrs["premise_check.reason_text"] == reason
    assert attrs["premise_check.claim_id"] == "claim-1"
    assert pcg.is_armed(session_id) is False
    last = pcg.get_state(session_id)["last_verdict"]
    assert last["verdict"] == token
    assert last["reason"] == reason


def test_record_verdict_normalises_token_case():
    session_id = "sess-case"
    pcg.arm(session_id, claim_id="claim-1")
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="claim-1",
        verdict="revise",
        reason="r",
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    assert result["verdict"] == "REVISE"


def test_record_verdict_rejects_unknown_token_and_stays_armed():
    session_id = "sess-bad-token"
    pcg.arm(session_id, claim_id="claim-1")

    with pytest.raises(ValueError, match="PASS, REVISE, FAIL"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-1",
            verdict="Looks fine to me",
            reason="r",
            tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        )
    assert pcg.is_armed(session_id) is True


def test_record_verdict_rejects_empty_reason_and_stays_armed():
    session_id = "sess-no-reason"
    pcg.arm(session_id, claim_id="claim-1")

    with pytest.raises(ValueError, match="reason"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-1",
            verdict="PASS",
            reason="   ",
            tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        )
    assert pcg.is_armed(session_id) is True


def test_cli_reads_reason_from_stdin(monkeypatch, capsys):
    """Free text can stay off the command line, where harness guards scan it."""
    import io
    import json

    session_id = "sess-cli-stdin"
    pcg.arm(session_id, claim_id="claim-1")
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )
    reason = _pass_reason("claim-1")
    monkeypatch.setattr("sys.stdin", io.StringIO(reason))

    rc = pcv.main(
        ["--report", "claim-1", "--verdict", "PASS", "--reason-file", "-", "--session", session_id]
    )

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "PASS"
    assert pcg.get_state(session_id)["last_verdict"]["reason"] == reason
    assert pcg.is_armed(session_id) is False


def test_cli_reads_reason_from_file(tmp_path, monkeypatch):
    session_id = "sess-cli-file"
    pcg.arm(session_id, claim_id="claim-1")
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )
    reason_file = tmp_path / "reason.txt"
    reason_file.write_text("Claims follow from the cited evidence.\n", encoding="utf-8")

    rc = pcv.main(
        [
            "--report",
            "claim-1",
            "--verdict",
            "FAIL",
            "--reason-file",
            str(reason_file),
            "--session",
            session_id,
        ]
    )

    assert rc == 0
    last = pcg.get_state(session_id)["last_verdict"]
    assert last["verdict"] == "FAIL"
    assert last["reason"] == "Claims follow from the cited evidence."


def test_cli_rejects_free_text_as_the_verdict(monkeypatch):
    session_id = "sess-cli-bad"
    pcg.arm(session_id, claim_id="claim-1")
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )

    with pytest.raises(SystemExit):
        pcv.main(
            [
                "--report",
                "claim-1",
                "--verdict",
                "it is fine",
                "--reason",
                "r",
                "--session",
                session_id,
            ]
        )
    assert pcg.is_armed(session_id) is True


def test_record_verdict_refuses_wrong_report_id_and_stays_armed():
    session_id = "sess-wrong-id"
    report_id = "report-expected-123"
    pcg.arm(session_id, claim_id=report_id)
    assert pcg.is_armed(session_id) is True

    with pytest.raises(ValueError, match="unknown or mismatched report id 'report-wrong-999'"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="report-wrong-999",
            verdict="PASS",
            reason="Logic holds.",
            tracer_mod=_StubTracer(config=None),
        )
    assert pcg.is_armed(session_id) is True


def test_record_verdict_refuses_when_not_armed():
    session_id = "sess-not-armed"
    assert pcg.is_armed(session_id) is False

    with pytest.raises(ValueError, match="no premise check is currently armed"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="report-123",
            verdict="PASS",
            reason="Logic holds.",
            tracer_mod=_StubTracer(config=None),
        )


def test_cli_refuses_wrong_report_id_and_exits_one(capsys, monkeypatch):
    session_id = "sess-cli-wrong"
    report_id = "report-real-123"
    pcg.arm(session_id, claim_id=report_id)
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )

    rc = pcv.main(
        [
            "--report",
            "report-wrong-456",
            "--verdict",
            "PASS",
            "--reason",
            "holds",
            "--session",
            session_id,
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown or mismatched report id 'report-wrong-456'" in err
    assert pcg.is_armed(session_id) is True


def test_cli_refuses_unknown_report_id_when_not_armed(capsys, monkeypatch):
    session_id = "sess-cli-not-armed"
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )

    rc = pcv.main(
        [
            "--report",
            "report-unknown",
            "--verdict",
            "PASS",
            "--reason",
            "holds",
            "--session",
            session_id,
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "no premise check is currently armed" in err


# ---------------------------------------------------------------------------
# 4. Failed span emission halts loudly and leaves gate armed (no fallbacks)
# ---------------------------------------------------------------------------


def test_record_verdict_fails_and_stays_armed_when_tracer_unconfigured():
    session_id = "sess-unconfigured"
    pcg.arm(session_id, claim_id="claim-3")

    tracer = _StubTracer(config=None)

    with pytest.raises(RuntimeError, match="tracing is not configured"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-3",
            verdict="PASS",
            reason=_pass_reason("claim-3"),
            tracer_mod=tracer,
        )

    assert tracer.exported == []
    assert pcg.is_armed(session_id) is True


def test_record_verdict_fails_and_stays_armed_on_unacknowledged_export():
    session_id = "sess-export-failed"
    pcg.arm(session_id, claim_id="claim-4")

    tracer = _StubTracer(config={"endpoint": "http://collector:4317"}, export_ok=False)

    with pytest.raises(RuntimeError, match="span export failed"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-4",
            verdict="PASS",
            reason=_pass_reason("claim-4"),
            tracer_mod=tracer,
        )

    assert len(tracer.exported) == 1
    assert pcg.is_armed(session_id) is True


def test_cli_verdict_fails_and_stays_armed_when_span_emission_fails(monkeypatch):
    session_id = "sess-cli-span-fail"
    pcg.arm(session_id, claim_id="claim-cli-fail")
    tracer = _StubTracer(config={"endpoint": "http://collector:4317"}, export_ok=False)
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)

    rc = pcv.main(
        [
            "--report",
            "claim-cli-fail",
            "--verdict",
            "PASS",
            "--reason",
            _pass_reason("claim-cli-fail"),
            "--session",
            session_id,
        ]
    )

    assert rc != 0
    assert pcg.is_armed(session_id) is True


def test_cli_verdict_succeeds_and_disarms_when_span_emission_succeeds(monkeypatch):
    session_id = "sess-cli-span-success"
    pcg.arm(session_id, claim_id="claim-cli-success")
    tracer = _StubTracer(config={"endpoint": "http://collector:4317"}, export_ok=True)
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)

    rc = pcv.main(
        [
            "--report",
            "claim-cli-success",
            "--verdict",
            "PASS",
            "--reason",
            _pass_reason("claim-cli-success"),
            "--session",
            session_id,
        ]
    )

    assert rc == 0
    assert pcg.is_armed(session_id) is False


# ---------------------------------------------------------------------------
# 5. The forcing mechanism
# ---------------------------------------------------------------------------


def _agent_dispatch_ctx(session_id: str, agent_type: str = "ida:ida") -> dispatch.HookContext:
    return dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Agent",
        session_id=session_id,
        agent_type=agent_type,
    )


def test_handler_refuses_next_dispatch_while_armed_default_mode():
    session_id = "sess-gate-1"
    pcg.arm(session_id, claim_id="claim-4")

    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert res is not None
    assert res.kind == dispatch.Kind.REFUSE
    assert "claim-4" in res.inject_text


def test_handler_allows_dispatch_once_disarmed():
    session_id = "sess-gate-2"
    pcg.arm(session_id, claim_id="claim-5")
    pcg.disarm(session_id, "claim-5", "PASS", "r")

    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


def test_handler_ignores_non_gated_tool():
    session_id = "sess-gate-3"
    pcg.arm(session_id, claim_id="claim-6")

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        session_id=session_id,
        agent_type="ida:ida",
    )
    assert pcg.premise_check_handler(ctx) is None


def test_handler_holds_regardless_of_agent_type():
    session_id = "sess-gate-4"
    pcg.arm(session_id, claim_id="claim-7")

    ctx = _agent_dispatch_ctx(session_id, agent_type="aops:james")
    res = pcg.premise_check_handler(ctx)
    assert res is not None and res.kind == dispatch.Kind.REFUSE


def test_handler_mode_off(monkeypatch):
    session_id = "sess-gate-5"
    pcg.arm(session_id, claim_id="claim-8")
    monkeypatch.setenv("PREMISE_CHECK_GATE_MODE", "off")

    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


def test_handler_mode_warn(monkeypatch):
    session_id = "sess-gate-6"
    pcg.arm(session_id, claim_id="claim-9")
    monkeypatch.setenv("PREMISE_CHECK_GATE_MODE", "warn")

    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert res is not None
    assert res.kind == dispatch.Kind.ADVISE


@pytest.mark.parametrize("var", ["PREMISE_CHECK_GATE_OVERRIDE", "AOP_FORCE", "AOP_OVERRIDE"])
def test_handler_override(monkeypatch, var):
    session_id = "sess-gate-7"
    pcg.arm(session_id, claim_id="claim-10")
    monkeypatch.setenv(var, "1")

    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


@pytest.mark.parametrize(
    "tool",
    [
        "telegram_reply",
        "telegram_send_message",
        "discord_reply",
        "discord_send_message",
        "ask_user_question",
        "ask_question",
        "ask_user",
        "reply",
        "mcp__plugin_ida-telegram_telegram__reply",
        "mcp__plugin_telegram_telegram__reply",
        "mcp__telegram__reply",
        "mcp__telegram__send_message",
    ],
)
def test_handler_refuses_channel_reply_tools_while_armed(tool):
    session_id = f"sess-chan-block-{tool}"
    pcg.arm(session_id, claim_id="claim-chan-1")
    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool=tool,
        session_id=session_id,
        agent_type="ida:ida",
    )
    res = pcg.premise_check_handler(ctx)
    assert res is not None, f"expected refusal for {tool} while armed"
    assert res.kind == dispatch.Kind.REFUSE
    assert "claim-chan-1" in res.inject_text


# ---------------------------------------------------------------------------
# 6. The agent's own outgoing tool calls never arm the check
# ---------------------------------------------------------------------------

_OUTGOING_NON_DISPATCH_CALLS = [
    ("Agent", {"description": "background worker", "run_in_background": True}),
    ("Agent", {"description": "background worker", "run_in_background": "true"}),
    ("SendMessage", {"to": "twin-a", "message": "status?"}),
    ("Bash", {"command": "ls"}),
]

_FOREGROUND_DISPATCH_CALLS = [
    ("Agent", {"description": "verify the claim"}),
    ("Agent", {"description": "verify the claim", "run_in_background": False}),
    ("Task", {"description": "research X"}),
    ("invoke_subagent", {"prompt": "research X"}),
]


@pytest.mark.parametrize("tool,tool_input", _OUTGOING_NON_DISPATCH_CALLS)
def test_outgoing_post_tool_use_leaves_check_disarmed(tool, tool_input):
    session_id = f"sess-out-{tool}-{sorted(tool_input.items())}"
    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        tool=tool,
        session_id=session_id,
        agent_type="ida:ida",
        raw={"tool_input": tool_input},
    )
    handlers = _load_plugin_module("ida_handlers_gate", _HOOKS_DIR / "handlers.py")
    handlers.post_tool(ctx)
    assert pcg.is_armed(session_id) is False
    assert pcg.premise_check_arm(ctx) is None
    assert pcg.is_armed(session_id) is False
    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


@pytest.mark.parametrize("tool,tool_input", _FOREGROUND_DISPATCH_CALLS)
def test_foreground_post_tool_use_arms_check(tool, tool_input):
    session_id = f"sess-fg-{tool}-{sorted(tool_input.items())}"
    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        tool=tool,
        session_id=session_id,
        agent_type="ida:ida",
        raw={
            "tool_input": tool_input,
            "tool_response": {"status": "completed", "content": [{"type": "text", "text": "X"}]},
        },
    )
    handlers = _load_plugin_module("ida_handlers_gate", _HOOKS_DIR / "handlers.py")
    res = handlers.post_tool(ctx)
    assert res is not None
    assert pcg.is_armed(session_id) is True
    res_arm = pcg.premise_check_arm(ctx)
    assert res_arm is not None
    assert res_arm.kind == dispatch.Kind.ADVISE
    assert _POLICY["premise_check"]["armed_indicator"] in res_arm.inject_text
    refuse_res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert refuse_res is not None and refuse_res.kind == dispatch.Kind.REFUSE


@pytest.mark.parametrize("tool,tool_input", _OUTGOING_NON_DISPATCH_CALLS)
def test_outgoing_post_tool_batch_leaves_check_disarmed(tool, tool_input):
    session_id = f"sess-batch-{tool}-{sorted(tool_input.items())}"
    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolBatch",
        session_id=session_id,
        agent_type="ida:ida",
        tool_calls=({"tool_name": tool, "tool_input": tool_input},),
    )
    assert pcg.premise_check_arm(ctx) is None
    assert pcg.is_armed(session_id) is False
    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


# ---------------------------------------------------------------------------
# 7. The gate arms only when a report or direction arrives
#
# Payload shapes follow Claude Code's documented `Agent` tool_response:
# `completed` for a foreground subagent that returned, `async_launched` for a
# background launch (the default when `run_in_background` is omitted), and
# `teammate_spawned` for a named teammate. Notifications follow the harness's
# `<task-notification>` and `<agent-message>` envelopes.
# ---------------------------------------------------------------------------

_SPAWN_ACKS = {
    "teammate_spawned": (
        {
            "description": "Why mini app broke again",
            "prompt": "diagnose",
            "name": "sara-mini",
            "run_in_background": "true",
        },
        {
            "status": "teammate_spawned",
            "prompt": "diagnose",
            "agentId": "asara-mini-0000000000000001",
            "teammate_id": "sara-mini@session-x",
            "agent_id": "asara-mini-0000000000000001",
            "agent_type": "ida:sara",
            "name": "sara-mini",
            "team_name": "session-x",
        },
    ),
    "async_launched_by_default": (
        {"description": "Fix premise-check gate arming", "prompt": "fix it"},
        {
            "isAsync": True,
            "status": "async_launched",
            "agentId": "a0000000000000001",
            "description": "Fix premise-check gate arming",
            "prompt": "fix it",
            "outputFile": "/tmp/tasks/a0000000000000001.output",
            "canReadOutputFile": False,
        },
    ),
    "spawned_text": ({"description": "Why mini app broke again"}, "Spawned successfully."),
}


def _post_tool_ctx(
    session_id: str, tool_input: dict[str, Any], tool_response: Any, tool: str = "Agent"
) -> dispatch.HookContext:
    return dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        tool=tool,
        session_id=session_id,
        agent_type="ida:ida",
        raw={
            "tool_input": tool_input,
            "tool_response": tool_response,
            "tool_use_id": "toolu_spawn",
        },
    )


@pytest.mark.parametrize("ack", sorted(_SPAWN_ACKS))
def test_spawn_ack_leaves_gate_unarmed_and_actions_proceed(ack):
    session_id = f"sess-ack-{ack}"
    tool_input, tool_response = _SPAWN_ACKS[ack]
    handlers = _load_plugin_module("ida_handlers_gate", _HOOKS_DIR / "handlers.py")

    assert handlers.post_tool(_post_tool_ctx(session_id, tool_input, tool_response)) is None
    assert pcg.is_armed(session_id) is False

    for tool in ("Agent", "AskUserQuestion"):
        ctx = dispatch.HookContext(
            client="claude",
            event="PreToolUse",
            tool=tool,
            session_id=session_id,
            agent_type="ida:ida",
        )
        assert handlers.pre_tool(ctx) is None, f"{tool} refused after a spawn ack"
    stop_ctx = dispatch.HookContext(
        client="claude", event="Stop", session_id=session_id, agent_type="ida:ida"
    )
    assert handlers.stop(stop_ctx) is None


_BACKGROUND_COMMAND_DONE = (
    "<task-notification>\n<task-id>b0000001</task-id>\n"
    "<tool-use-id>toolu_bg_command</tool-use-id>\n"
    "<output-file>/tmp/tasks/b0000001.output</output-file>\n<status>completed</status>\n"
    '<summary>Background command "Run the tests" completed (exit code 0)'
    "</summary>\n</task-notification>"
)
_HANDBACK_POINTER = (
    "<task-notification>\n<task-id>a1b2c3d4e5f600112</task-id>\n"
    "<status>completed</status>\n"
    '<summary>Agent "Check the claim" finished</summary>\n'
    "<result>This agent's report was delivered to you as a message from "
    '"a1b2c3d4e5f600112" (its SubagentHandback call). Read it there; it is not '
    "repeated here.\n</result>\n</task-notification>"
)


@pytest.mark.parametrize(
    "prompt",
    [_BACKGROUND_COMMAND_DONE, _HANDBACK_POINTER],
    ids=["background_command", "handback_pointer"],
)
def test_notification_without_a_report_leaves_gate_unarmed(prompt):
    session_id = f"sess-noreport-{abs(hash(prompt))}"
    assert pcg.premise_check_arm(_prompt_ctx(session_id, prompt)) is None
    assert pcg.is_armed(session_id) is False
    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


_ARRIVING_REPORTS = {
    "foreground_result": (
        "Verify the mini app",
        {"description": "Verify the mini app", "prompt": "check it"},
        {
            "status": "completed",
            "agentId": "a0000000000000002",
            "content": [{"type": "text", "text": "The mini app loads; PR #12 fixed it."}],
            "totalDurationMs": 48211,
        },
    ),
    "background_agent_result": (
        None,
        None,
        "<task-notification>\n<task-id>a7c7c7c7c7c7c7c70</task-id>\n"
        "<status>completed</status>\n"
        '<summary>Agent "Diagnose the mini app" finished</summary>\n'
        "<result>The mini app loads; PR #12 fixed it.</result>\n</task-notification>",
    ),
    "subagent_handback": (
        None,
        None,
        '<agent-message from="a1b2c3d4e5f600112">\n[Subagent hand-back] The text below '
        "is the final report of a subagent this session delegated to.\n"
        "The mini app loads; PR #12 fixed it.\n</agent-message>",
    ),
    "teammate_direction": (
        None,
        None,
        '<teammate-message teammate_id="team-lead">Fix the mini app; '
        "the mini app loads after PR #12.</teammate-message>",
    ),
}


@pytest.mark.parametrize("kind", sorted(_ARRIVING_REPORTS))
def test_arriving_report_or_direction_arms_gate(kind):
    session_id = f"sess-arrive-{kind}"
    claim, tool_input, payload = _ARRIVING_REPORTS[kind]
    if tool_input is not None:
        handlers = _load_plugin_module("ida_handlers_gate", _HOOKS_DIR / "handlers.py")
        handlers.post_tool(_post_tool_ctx(session_id, tool_input, payload))
    else:
        assert pcg.premise_check_arm(_prompt_ctx(session_id, payload)) is not None
    assert pcg.is_armed(session_id) is True
    claim_id = claim or pcg.get_state(session_id)["claim_id"]
    judged_text, _ = pcg.get_judged(session_id, claim_id)
    assert "the mini app loads" in judged_text.lower()
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert res is not None and res.kind == dispatch.Kind.REFUSE


def test_spawn_while_claim_pending_keeps_that_claim_and_its_verdict_records():
    session_id = "sess-pending-spawn"
    report = (
        f'<teammate-message teammate_id="sara" id="why-mini-app">report'
        f"{_SAMPLE_VALID_BLOCK}</teammate-message>"
    )
    pcg.premise_check_arm(_prompt_ctx(session_id, report))
    assert pcg.get_state(session_id)["claim_ids"] == ["why-mini-app"]

    handlers = _load_plugin_module("ida_handlers_gate", _HOOKS_DIR / "handlers.py")
    tool_input, tool_response = _SPAWN_ACKS["async_launched_by_default"]
    handlers.post_tool(_post_tool_ctx(session_id, tool_input, tool_response))

    state = pcg.get_state(session_id)
    assert state["claim_id"] == "why-mini-app"
    assert state["claim_ids"] == ["why-mini-app"]

    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="why-mini-app",
        verdict="PASS",
        reason=_pass_reason("why-mini-app"),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    assert result["ok"] is True
    assert pcg.is_armed(session_id) is False


# ---------------------------------------------------------------------------
# End-to-end: full claim -> refusal -> verdict -> allowed cycle
# ---------------------------------------------------------------------------


def test_end_to_end_claim_blocks_next_dispatch_until_verdicted():
    session_id = "sess-e2e"

    # A worker's report arrives at Ida.
    report_ctx = _prompt_ctx(
        session_id,
        f'<task-notification id="researched-X"><result>worker finished{_SAMPLE_VALID_BLOCK}</result></task-notification>',
    )
    arm_res = pcg.premise_check_arm(report_ctx)
    assert arm_res is not None
    assert pcg.is_armed(session_id) is True

    # Dispatching another subagent before the verdict is refused.
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert res is not None and res.kind == dispatch.Kind.REFUSE

    # The verdict script runs and disarms the check.
    pcv.record_verdict(
        session_id=session_id,
        claim_id="researched-X",
        verdict="PASS",
        reason=_pass_reason("researched-X"),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )

    # Now the dispatch is permitted.
    assert pcg.is_armed(session_id) is False
    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


# ---------------------------------------------------------------------------
# Incoming messages: peer reports arm the check; the user's messages do not
# ---------------------------------------------------------------------------


def _prompt_ctx(session_id: str, prompt: str, agent_type: str = "ida:ida") -> dispatch.HookContext:
    return dispatch.HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id=session_id,
        agent_type=agent_type,
        raw={"prompt": prompt},
    )


@pytest.mark.parametrize(
    "prompt",
    [
        f'<cross-session-message from="twin-a">PR #12 is merged.{_SAMPLE_VALID_BLOCK}</cross-session-message>',
        f'<teammate-message teammate_id="worker">done{_SAMPLE_VALID_BLOCK}</teammate-message>',
        f"\n  <task-notification>\n<result>worker finished{_SAMPLE_VALID_BLOCK}</result>\n</task-notification>",
        f'<subagent-handback from="worker">subagent finished{_SAMPLE_VALID_BLOCK}</subagent-handback>',
    ],
)
def test_arm_handler_arms_on_peer_report(prompt):
    session_id = f"sess-peer-{abs(hash(prompt))}"
    res = pcg.premise_check_arm(_prompt_ctx(session_id, prompt))
    assert res is not None
    assert pcg.is_armed(session_id) is True
    assert _POLICY["premise_check"]["direction_checklist_indicator"] in res.inject_text
    refuse_res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert refuse_res is not None and refuse_res.kind == dispatch.Kind.REFUSE


_AGY_CONV = "00000000-0000-4000-8000-00000000c0de"
_AGY_PEER = "00000000-0000-4000-8000-0000000beef1"


def _agy_system_message(body: str) -> str:
    """A SYSTEM_MESSAGE turn-start as agy writes it to the transcript."""
    return (
        "The following is a <SYSTEM_MESSAGE> not actually sent by the user. It is "
        "provided by the system as important information to pay attention to.\n\n"
        f"<SYSTEM_MESSAGE>\n{body}\n</SYSTEM_MESSAGE>"
    )


def _agy_message(sender: str, content: str, priority: str = "HIGH") -> str:
    return _agy_system_message(
        f"[Message] timestamp=2026-10-20T01:02:03Z sender={sender} "
        f"priority=MESSAGE_PRIORITY_{priority} content={content}"
    )


# Turn-starts that wake agy without any report or direction arriving.
_AGY_WAKES_WITHOUT_REPORT = {
    "own_command_finished": _agy_message(
        f"{_AGY_CONV}/task-11",
        f'Task id "{_AGY_CONV}/task-11" finished with result:\n\n\t\t\t\t'
        "The command exited with code 0.\n\t\t\t\tOutput:\n\t\t\t\tok",
    ),
    "own_command_canceled": _agy_message(
        f"{_AGY_CONV}/task-12",
        f'Task id "{_AGY_CONV}/task-12" was canceled with result: Step was canceled.',
        priority="LOW",
    ),
    "output_stabilized": _agy_message(
        f"{_AGY_CONV}/task-13",
        "The command output has stabilized for 5s. The output delta since last check is:\nbuilding",
    ),
    "own_timer": _agy_message(f"{_AGY_CONV}/task-14", "Check build task completion"),
    "system_notice": _agy_message(
        "system",
        "[Notice] All your subagents and background tasks have been stopped due to server restart.",
        priority="LOW",
    ),
    "stop_hook_blocked": _agy_system_message(
        "stop hook blocked termination due to reason: The user has automatically "
        "approved the artifact through their review policy. Proceed to execution."
    ),
    "subagent_idle_with_response": _agy_message(
        "system",
        f"Subagent {_AGY_PEER} has gone idle. This was the subagent's most recent "
        "response: I have completed the fix; the mini app loads [observed].",
    ),
}

# Turn-starts that deliver another agent's report or direction.
_AGY_ARRIVALS = {
    "peer_report": _agy_message(
        _AGY_PEER, "### Fix Report\n\nI fixed the build; the mini app loads [observed]."
    ),
    "peer_direction": _agy_message(
        _AGY_PEER, "Use the hydrate skill against this ask, then report: the mini app loads?"
    ),
}


def _agy_turn_ctx(tmp_path: Path, session_id: str, turn_start: str) -> dispatch.HookContext:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"step_index": 0, "type": "USER_INPUT", "content": "initial"})
        + "\n"
        + json.dumps({"step_index": 1, "type": "SYSTEM_MESSAGE", "content": turn_start})
        + "\n",
        encoding="utf-8",
    )
    return dispatch.HookContext(
        client="agy",
        event="UserPromptSubmit",
        session_id=session_id,
        agent_type="ida:ida",
        transcript_path=str(transcript),
        raw={"invocationNum": 0, "transcriptPath": str(transcript), "conversationId": _AGY_CONV},
    )


@pytest.mark.parametrize("wake", sorted(_AGY_WAKES_WITHOUT_REPORT))
def test_agy_wake_without_report_leaves_gate_unarmed(tmp_path: Path, wake):
    session_id = f"sess-agy-wake-{wake}"
    ctx = _agy_turn_ctx(tmp_path, session_id, _AGY_WAKES_WITHOUT_REPORT[wake])
    assert pcg.premise_check_arm(ctx) is None
    assert pcg.is_armed(session_id) is False


@pytest.mark.parametrize("arrival", sorted(_AGY_ARRIVALS))
def test_agy_report_or_direction_arms_check(tmp_path: Path, arrival):
    session_id = f"sess-agy-arrival-{arrival}"
    ctx = _agy_turn_ctx(tmp_path, session_id, _AGY_ARRIVALS[arrival])
    assert pcg.premise_check_arm(ctx) is not None
    assert pcg.is_armed(session_id) is True
    claim_id = pcg.get_state(session_id)["claim_id"]
    judged_text, _ = pcg.get_judged(session_id, claim_id)
    assert "the mini app loads" in judged_text


def test_agy_preinvocation_captures_send_message_without_transcript_lag(tmp_path: Path):
    """AC1: In agy, PreInvocation gating ingests incoming subagent send_message reports on the turn

    they arrive even when <SYSTEM_MESSAGE> entries have not flushed to transcript_full.jsonl (#3500),
    and ignores subsequent sender=system 'Subagent <uuid> has gone idle' notices (#3544).
    """
    session_id = "sess-agy-lag-repro"
    transcript_compact = tmp_path / "transcript.jsonl"
    transcript_full = tmp_path / "transcript_full.jsonl"

    report_argdown = (
        "## Report\n"
        "```argdown\n"
        "===\n"
        "asks:\n"
        "  tg-1: 1\n"
        "answers:\n"
        "  tg-1: 1\n"
        "===\n\n"
        "(1) Fix delivered\n"
        "-- rule --\n"
        "(2) Verified\n"
        "```"
    )
    subagent_msg = _agy_message(_AGY_PEER, report_argdown)

    # Initial state: step 0 (initial prompt) in both transcripts
    initial_step = {"step_index": 0, "type": "USER_INPUT", "content": "initial prompt"}
    transcript_compact.write_text(json.dumps(initial_step) + "\n", encoding="utf-8")
    transcript_full.write_text(json.dumps(initial_step) + "\n", encoding="utf-8")

    # Turn 1: subagent send_message is appended to compact transcript,
    # BUT has NOT flushed to transcript_full.jsonl yet!
    handback_step = {"step_index": 1, "type": "SYSTEM_MESSAGE", "content": subagent_msg}
    with transcript_compact.open("a", encoding="utf-8") as f:
        f.write(json.dumps(handback_step) + "\n")

    # PreInvocation fires on Turn 1 (even if transcriptPath points to transcript_full.jsonl or transcript.jsonl)
    ctx1 = dispatch.HookContext(
        client="agy",
        event="UserPromptSubmit",
        session_id=session_id,
        agent_type="ida:sara",
        transcript_path=str(transcript_full),
        raw={
            "invocationNum": 0,
            "transcriptPath": str(transcript_full),
            "conversationId": session_id,
        },
    )

    # Must capture Report 1 on the exact turn it arrives
    res1 = pcg.premise_check_arm(ctx1)
    assert res1 is not None
    assert pcg.is_armed(session_id) is True
    claim_id_1 = pcg.get_state(session_id)["claim_id"]
    judged_text_1, _ = pcg.get_judged(session_id, claim_id_1)
    assert "Fix delivered" in judged_text_1
    assert "Verified" in judged_text_1

    # Turn 2: Subagent calls finish and agy delivers sender=system idle notice
    idle_msg = _agy_message(
        "system",
        f"Subagent {_AGY_PEER} has gone idle. This was the subagent's most recent response: Brief finish prose.",
    )
    idle_step = {"step_index": 2, "type": "SYSTEM_MESSAGE", "content": idle_msg}
    with transcript_compact.open("a", encoding="utf-8") as f:
        f.write(json.dumps(idle_step) + "\n")
    # Also flushes to transcript_full
    with transcript_full.open("a", encoding="utf-8") as f:
        f.write(json.dumps(handback_step) + "\n")
        f.write(json.dumps(idle_step) + "\n")

    ctx2 = dispatch.HookContext(
        client="agy",
        event="UserPromptSubmit",
        session_id=session_id,
        agent_type="ida:sara",
        transcript_path=str(transcript_full),
        raw={
            "invocationNum": 0,
            "transcriptPath": str(transcript_full),
            "conversationId": session_id,
        },
    )

    # Idle notice must be ignored as a non-claim lifecycle event, not arming a false blockless gate
    assert pcg.premise_check_arm(ctx2) is None
    # Report 1 remains the armed claim
    state2 = pcg.get_state(session_id)
    assert state2.get("claim_id") == claim_id_1  # Report 1 remains the armed claim


def test_agy_system_message_does_not_rearm_after_verdict_disarms_on_later_invocations(
    tmp_path: Path, monkeypatch
):
    """After verdict.py disarms an agy SYSTEM_MESSAGE turn, invocationNum=1,2 stay disarmed."""
    import handlers

    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )
    monkeypatch.setattr(
        hg, "claude_code_tracer", _StubTracer(config={"endpoint": "http://x"}), raising=False
    )

    session_id = "sess-agy-verdict-no-rearm"
    report_msg = _agy_message(_AGY_PEER, "### Report\n\nCheck complete without argdown.")
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"step_index": 0, "type": "USER_INPUT", "content": "initial"})
        + "\n"
        + json.dumps({"step_index": 1, "type": "SYSTEM_MESSAGE", "content": report_msg})
        + "\n",
        encoding="utf-8",
    )

    ctx0 = dispatch.HookContext(
        client="agy",
        event="UserPromptSubmit",
        session_id=session_id,
        agent_type="ida:ida",
        hooks_dir=_HOOKS_DIR,
        transcript_path=str(transcript),
        raw={"invocationNum": 0, "transcriptPath": str(transcript), "conversationId": _AGY_CONV},
    )
    assert handlers.rule_against_hearsay(ctx0) is not None
    arm_res = hg.hearsay_arm(ctx0)
    assert arm_res is not None
    assert hg.is_armed(session_id) is True

    claim_id = hg.get_state(session_id)["claim_id"]
    pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="REVISE",
        reason="Valid: (1) fails #missing -- no argument supplied",
    )
    assert hg.is_armed(session_id) is False

    for inv in (1, 2):
        ctx_next = dispatch.HookContext(
            client="agy",
            event="UserPromptSubmit",
            session_id=session_id,
            agent_type="ida:ida",
            hooks_dir=_HOOKS_DIR,
            transcript_path=str(transcript),
            raw={
                "invocationNum": inv,
                "transcriptPath": str(transcript),
                "conversationId": _AGY_CONV,
            },
        )
        assert hg.should_arm_hearsay(ctx_next) is False
        assert handlers.rule_against_hearsay(ctx_next) is None
        assert hg.hearsay_arm(ctx_next) is None
        assert hg.is_armed(session_id) is False


def test_claude_peer_report_without_invocation_num_still_arms_after_agy_guard():
    """Claude Code UserPromptSubmit peer reports without invocationNum still arm and trigger hearsay."""
    import handlers

    session_id = "sess-claude-no-inv"
    prompt = '<cross-session-message from="twin-b">Verification done.</cross-session-message>'
    ctx = _prompt_ctx(session_id, prompt)
    assert "invocationNum" not in ctx.raw
    assert hg.should_arm_hearsay(ctx) is True
    assert handlers.rule_against_hearsay(ctx) is not None
    assert hg.hearsay_arm(ctx) is not None
    assert hg.is_armed(session_id) is True


def test_prose_report_arms_uniformly_and_accepts_pass_with_natural_language_reason(monkeypatch):
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )
    session_id = "sess-prose-report"
    prompt = '<cross-session-message from="twin-a">PR #12 is merged; CI green on main.</cross-session-message>'
    ctx = _prompt_ctx(session_id, prompt)
    claim_id = pcg._derive_claim_id(ctx)
    res = pcg.premise_check_arm(ctx)
    assert res is not None
    assert "no argument block supplied" not in res.inject_text
    assert "--verdict <PASS|REVISE|FAIL>" in res.inject_text
    assert pcg.is_armed(session_id) is True

    # The gate refuses dispatch while armed awaiting verdict
    dispatch_res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert dispatch_res is not None and dispatch_res.kind == dispatch.Kind.REFUSE

    # Recording PASS with a natural-language reason clears the gate without mechanical block checks
    result = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason="The prose report states the merge and green CI cleanly; reasoning holds.",
    )
    assert result["ok"] is True
    assert result["verdict"] == "PASS"
    assert pcg.is_armed(session_id) is False


def test_null_form_clears_gate_with_no_agent_action():
    session_id = "sess-null-form"
    prompt = (
        '<cross-session-message from="twin-a">\n'
        "```argdown\n"
        "===\n"
        "asks: none\n"
        "===\n\n"
        "[no claim]\n"
        "```\n"
        "</cross-session-message>"
    )
    ctx = _prompt_ctx(session_id, prompt)
    res = pcg.premise_check_arm(ctx)
    assert res is None
    assert pcg.is_armed(session_id) is False
    state = pcg.get_state(session_id)
    last_v = state.get("last_verdict")
    assert isinstance(last_v, dict)
    assert last_v.get("verdict") == "no-claim"
    assert last_v.get("reason") == "null form"
    assert last_v.get("no_claim") is True


def test_full_argument_with_asks_none_does_not_pass_as_null_form():
    session_id = "sess-full-arg-asks-none"
    prompt = (
        '<cross-session-message from="twin-a">\n'
        "Report.\n"
        "```argdown\n"
        "===\n"
        "asks: none\n"
        "===\n\n"
        "(1) p -- fact\n"
        "-- w --\n"
        "(2) c\n"
        "```\n"
        "</cross-session-message>"
    )
    ctx = _prompt_ctx(session_id, prompt)
    res = pcg.premise_check_arm(ctx)
    assert res is not None
    assert pcg.is_armed(session_id) is True


def test_claim_none_does_not_pass_as_null_form():
    session_id = "sess-claim-none"
    prompt = (
        '<cross-session-message from="twin-a">\n'
        "```argdown\n"
        "claim: none of the findings held\n"
        "```\n"
        "</cross-session-message>"
    )
    ctx = _prompt_ctx(session_id, prompt)
    res = pcg.premise_check_arm(ctx)
    assert res is not None
    assert pcg.is_armed(session_id) is True


def test_standalone_no_claim_auto_disarms_while_quoted_or_mixed_prose_arms():
    """Standalone canonical [no claim] auto-disarms; substantive prose quoting or ending with [no claim] still arms."""
    # 1. Standalone bare [no claim] notice auto-disarms
    sess_null = "sess-bare-no-claim"
    prompt_null = '<cross-session-message from="twin-a">\n[no claim]\n</cross-session-message>'
    assert pcg.premise_check_arm(_prompt_ctx(sess_null, prompt_null)) is None
    assert pcg.is_armed(sess_null) is False
    assert pcg.get_state(sess_null)["last_verdict"]["verdict"] == "no-claim"

    # 2. Standalone fenced argdown [no claim] without frontmatter also auto-disarms
    sess_fenced = "sess-fenced-no-claim"
    prompt_fenced = (
        '<cross-session-message from="twin-a">\n'
        "```argdown\n"
        "[no claim]\n"
        "```\n"
        "</cross-session-message>"
    )
    assert pcg.premise_check_arm(_prompt_ctx(sess_fenced, prompt_fenced)) is None
    assert pcg.is_armed(sess_fenced) is False
    assert pcg.get_state(sess_fenced)["last_verdict"]["verdict"] == "no-claim"

    # 3. Substantive report quoting an illustrative fenced argdown [no claim] block STILL arms the gate
    sess_quoted_mid = "sess-quoted-block-mid"
    prompt_quoted_mid = (
        '<cross-session-message from="twin-a">\n'
        "I audited the gate null-form documentation. Example block from the skill:\n"
        "```argdown\n"
        "===\n"
        "asks: none\n"
        "===\n\n"
        "[no claim]\n"
        "```\n"
        "Therefore the documentation matches the gate behavior.\n"
        "</cross-session-message>"
    )
    assert pcg.premise_check_arm(_prompt_ctx(sess_quoted_mid, prompt_quoted_mid)) is not None
    assert pcg.is_armed(sess_quoted_mid) is True

    # 4. Substantive report ending with a fenced argdown [no claim] block STILL arms the gate
    sess_quoted_end = "sess-quoted-block-end"
    prompt_quoted_end = (
        '<cross-session-message from="twin-a">\n'
        "All tests passed on main; here is the null form template:\n"
        "```argdown\n"
        "===\n"
        "asks: none\n"
        "===\n\n"
        "[no claim]\n"
        "```\n"
        "</cross-session-message>"
    )
    assert pcg.premise_check_arm(_prompt_ctx(sess_quoted_end, prompt_quoted_end)) is not None
    assert pcg.is_armed(sess_quoted_end) is True

    # 5. Substantive prose mentioning [no claim] mid-sentence or on the last line STILL arms the gate
    for tag, body in (
        ("mid", "This report discusses [no claim] notices and concludes the gate still works."),
        ("trailing", "Deployed to production and verified green.\n\n[no claim]"),
    ):
        sess = f"sess-prose-no-claim-{tag}"
        prompt_prose = f'<cross-session-message from="twin-a">\n{body}\n</cross-session-message>'
        assert pcg.premise_check_arm(_prompt_ctx(sess, prompt_prose)) is not None
        assert pcg.is_armed(sess) is True


@pytest.mark.parametrize(
    "prompt",
    [
        '<channel source="plugin:telegram:telegram" chat_id="1" user="tester">\n<cross-session-message from="twin-a">PR #12 is merged.\n```argdown\n(1) p -- fact\n-- w --\n(2) c\n```\n</cross-session-message>\n</channel>',
        '<channel source="plugin:telegram:telegram" chat_id="1" user="tester">Context</channel>\n<cross-session-message from="twin-a">PR #12 is merged.\n```argdown\n(1) p -- fact\n-- w --\n(2) c\n```\n</cross-session-message>',
        '<channel source="plugin:telegram:telegram" chat_id="1" user="worker">\n<task-notification>\n<result>worker finished\n```argdown\n(1) p -- fact\n-- w --\n(2) c\n```\n</result>\n</task-notification>\n</channel>',
    ],
)
def test_arm_handler_arms_on_wrapped_peer_report(prompt):
    session_id = f"sess-mid-peer-{abs(hash(prompt))}"
    pcg.premise_check_arm(_prompt_ctx(session_id, prompt))
    assert pcg.is_armed(session_id) is True


def test_teammate_message_idle_notification_arms_gate_and_records_verdict():
    session_id = "sess-teammate-idle"
    report_text = """## Report
```argdown
===
asks:
  tg-398: 2
answers:
  tg-398: 2
===
(1) Five ideas for resilience -- rule
-- rule --
(2) Resilience ideas hold
```"""
    payload = json.dumps(
        {
            "type": "idle_notification",
            "from": "resilience-ideas",
            "timestamp": "2026-10-23T12:23:44.965Z",
            "idleReason": "available",
            "result": report_text,
        }
    )
    prompt = (
        "Another Claude session sent a message:\n"
        f'<teammate-message teammate_id="resilience-ideas" color="green">\n{payload}\n</teammate-message>\n\n'
        "This came from another Claude session — not typed by your user, but very likely working on their behalf."
    )
    arm_res = pcg.premise_check_arm(_prompt_ctx(session_id, prompt))
    assert arm_res is not None
    assert pcg.is_armed(session_id) is True

    claim_id = pcg.get_state(session_id)["claim_id"]
    assert claim_id.startswith("claim-")

    # PreToolUse refuses dispatch while armed
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert res is not None and res.kind == dispatch.Kind.REFUSE

    # Verdict records with verification id and disarms the gate
    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=_pass_reason(claim_id),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert verdict_res["verification_id"].startswith("verdict-")
    assert pcg.is_armed(session_id) is False


def test_teammate_message_send_message_arms_gate_and_records_verdict():
    session_id = "sess-teammate-sendmsg"
    report_text = """## Report
```argdown
===
asks:
  tg-1: 2
answers:
  tg-1: 2
===
(1) Migration complete -- rule
-- rule --
(2) Migration holds
```"""
    prompt = (
        "Another Claude session sent a message:\n"
        f'<teammate-message id="worker-report-1" teammate_id="worker" color="blue" summary="Task finished">\n{report_text}\n</teammate-message>\n\n'
        "This came from another Claude session — not typed by your user, but very likely working on their behalf."
    )
    arm_res = pcg.premise_check_arm(_prompt_ctx(session_id, prompt))
    assert arm_res is not None
    assert pcg.is_armed(session_id) is True
    assert pcg.get_state(session_id)["claim_id"] == "worker-report-1"

    # PreToolUse refuses dispatch while armed
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert res is not None and res.kind == dispatch.Kind.REFUSE

    # Verdict records with verification id and disarms the gate
    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_id,
        claim_id="worker-report-1",
        verdict="PASS",
        reason=_pass_reason("worker-report-1"),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert verdict_res["verification_id"].startswith("verdict-")
    assert pcg.is_armed(session_id) is False


@pytest.mark.parametrize(
    "prompt",
    [
        '<channel source="plugin:telegram:telegram" chat_id="1" user="tester">do the thing</channel>',
        "can you check the release?",
        "what does <task-notification> mean?",
        "check <cross-session-message from='twin'>",
        '<channel source="plugin:telegram:telegram" chat_id="1" user="tester">what does <task-notification> mean?</channel>',
        'Preamble text\n<cross-session-message from="twin-a">PR #12 is merged.</cross-session-message>',
        'Context before <teammate-message teammate_id="worker">done</teammate-message> and trailing text',
        "",
    ],
)
def test_arm_handler_ignores_the_users_own_messages(prompt):
    session_id = f"sess-user-{abs(hash(prompt))}"
    pcg.premise_check_arm(_prompt_ctx(session_id, prompt))
    assert pcg.is_armed(session_id) is False
    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


def test_users_message_does_not_disarm_a_pending_check():
    session_id = "sess-user-pending"
    pcg.arm(session_id, claim_id="claim-11")
    pcg.premise_check_arm(_prompt_ctx(session_id, "what's the status?"))
    assert pcg.is_armed(session_id) is True


@pytest.mark.parametrize("agent_type", ["ida:sara", "sara"])
def test_sara_is_gated_like_ida(agent_type):
    session_id = f"sess-{agent_type}"
    pcg.premise_check_arm(
        _prompt_ctx(
            session_id,
            "<cross-session-message>report\n```argdown\n(1) p -- fact\n-- w --\n(2) c\n```\n</cross-session-message>",
            agent_type,
        )
    )
    assert pcg.is_armed(session_id) is True
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id, agent_type=agent_type))
    assert res is not None and res.kind == dispatch.Kind.REFUSE


# ---------------------------------------------------------------------------
# Prompt note and block message: concise 2-line pointers naming claim_id and
# the premise-check skill, with no pre-filled PASS
# ---------------------------------------------------------------------------


def test_derive_claim_id_generates_short_id_without_message_text():
    ctx1 = _prompt_ctx(
        "s1", '<cross-session-message from="twin-a">PR #12 is merged.</cross-session-message>'
    )
    claim1 = pcg._derive_claim_id(ctx1)
    # Must carry no message text, only a short id
    assert "PR #12 is merged." not in claim1
    assert "twin-a" not in claim1
    assert claim1.startswith("claim-")
    assert pcg.is_valid_id(claim1)

    ctx2 = _prompt_ctx("s2", '<teammate-message teammate_id="worker">done</teammate-message>')
    claim2 = pcg._derive_claim_id(ctx2)
    assert "done" not in claim2
    assert "worker" not in claim2
    assert claim2.startswith("claim-")
    assert pcg.is_valid_id(claim2)

    ctx3 = _prompt_ctx(
        "s3", "\n  <task-notification>\n<result>worker finished</result>\n</task-notification>"
    )
    claim3 = pcg._derive_claim_id(ctx3)
    assert "worker finished" not in claim3
    assert claim3.startswith("claim-")
    assert pcg.is_valid_id(claim3)

    # Explicit id attribute on peer envelope is respected
    ctx4 = _prompt_ctx(
        "s4",
        '<cross-session-message from="twin-a" id="rep-explicit-42">PR #12 is merged.</cross-session-message>',
    )
    claim4 = pcg._derive_claim_id(ctx4)
    assert claim4 == "rep-explicit-42"

    # Optional title on peer envelope is incorporated as slug
    ctx5 = _prompt_ctx(
        "s5",
        '<cross-session-message from="twin-a" title="Deploy Migration">Done</cross-session-message>',
    )
    claim5 = pcg._derive_claim_id(ctx5)
    assert claim5.startswith("claim-")
    assert claim5.endswith("-deploy-migration")
    assert pcg.is_valid_id(claim5)


def test_arm_handler_returns_two_line_prompt_note_and_no_message_text():
    session_id = "sess-note-1"
    prompt = (
        '<cross-session-message from="twin-a">PR #12 is merged.\n'
        "```argdown\n(1) p -- fact\n-- w --\n(2) c\n```\n"
        "</cross-session-message>"
    )
    ctx = _prompt_ctx(session_id, prompt)
    claim_id = pcg._derive_claim_id(ctx)
    res = pcg.premise_check_arm(ctx)
    assert res is not None
    assert res.kind == dispatch.Kind.ADVISE
    assert len(res.inject_text.splitlines()) <= 2
    assert res.user_text is None
    assert claim_id in res.inject_text
    assert "premise-check" in res.inject_text
    assert "PR #12 is merged." not in res.inject_text
    cmd = pcg.format_verdict_command(claim_id, ctx.hooks_dir, session_id)
    assert res.inject_text.splitlines()[1] == cmd
    assert "--verdict <PASS|REVISE|FAIL>" in res.inject_text
    assert "--verdict PASS" not in res.inject_text


def test_stop_block_message_is_two_lines_pointing_to_skill():
    session_id = "sess-stop-elements"
    claim = "claim-e5f6a7b8"
    pcg.arm(session_id, claim_id=claim)

    stop_ctx = dispatch.HookContext(
        client="claude",
        event="Stop",
        session_id=session_id,
        agent_type="ida:ida",
    )
    res = pcg.premise_check_handler(stop_ctx)
    assert res is not None
    assert res.kind == dispatch.Kind.BLOCK
    assert len(res.inject_text.splitlines()) == 2
    assert res.user_text is None
    assert claim in res.inject_text
    assert "premise-check" in res.inject_text
    cmd = pcg.format_verdict_command(claim, stop_ctx.hooks_dir, session_id)
    assert res.inject_text.splitlines()[1] == cmd
    assert "--verdict PASS" not in res.inject_text


def test_resolve_verdict_script_with_empty_or_relative_hooks_dir_resolves_absolute_existing_file():
    script_default = pcg.resolve_verdict_script(Path())
    assert script_default.is_absolute()
    assert script_default.is_file()

    script_none = pcg.resolve_verdict_script(None)
    assert script_none.is_absolute()
    assert script_none.is_file()


# ---------------------------------------------------------------------------
# Separate short IDs in shared format for claims and verifications
# ---------------------------------------------------------------------------


def test_id_format_helpers():
    # build_id produces <kind>-<hash>[-<title>]
    cid = pcg.build_id("claim", "test content")
    assert pcg.is_valid_id(cid)
    parsed = pcg.parse_id(cid)
    assert parsed["kind"] == "claim"
    assert len(parsed["hash"]) == 8
    assert parsed["title"] is None

    # build_id with title slugifies title
    cid_titled = pcg.build_id("claim", "test content", title="My Feature: Auth Gate!")
    assert pcg.is_valid_id(cid_titled)
    parsed_titled = pcg.parse_id(cid_titled)
    assert parsed_titled["kind"] == "claim"
    assert parsed_titled["title"] == "my-feature-auth-gate"

    # mint_verification_id produces verdict-<hash>[-<title>] distinct from claim id
    vid = pcg.mint_verification_id(cid, "PASS", "valid logic", title="review-ok")
    assert pcg.is_valid_id(vid)
    parsed_vid = pcg.parse_id(vid)
    assert parsed_vid["kind"] == "verdict"
    assert parsed_vid["title"] == "review-ok"
    assert vid != cid


def test_record_verdict_returns_distinct_verification_id():
    session_id = "sess-distinct-id"
    claim_id = "claim-1a2b3c4d-pr-diff"
    pcg.arm(session_id, claim_id=claim_id)
    tracer = _StubTracer(config={"endpoint": "http://x"})

    result = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=_pass_reason(claim_id),
        title="logic-pass",
        tracer_mod=tracer,
    )

    assert result["ok"] is True
    verification_id = result["verification_id"]
    assert verification_id is not None
    assert verification_id != claim_id
    assert pcg.is_valid_id(verification_id)
    parsed = pcg.parse_id(verification_id)
    assert parsed["kind"] == "verdict"
    assert parsed["title"] == "logic-pass"

    # Gate state records verification_id alongside claim_id
    last = pcg.get_state(session_id)["last_verdict"]
    assert last["verification_id"] == verification_id
    assert last["claim_id"] == claim_id
    assert last["title"] == "logic-pass"

    # Span record carries verification_id
    attrs = tracer.exported[0]["spans"][0]["attributes"]
    assert attrs["premise_check.verification_id"] == verification_id
    assert attrs["premise_check.title"] == "logic-pass"


def test_verified_outgoing_message_id_accepted_as_incoming_claim_id_upstream():
    downstream_session = "sess-downstream"
    upstream_session = "sess-upstream"

    # 1. Downstream receives a claim and records a verdict
    downstream_claim = "claim-a1b2c3d4"
    pcg.arm(downstream_session, claim_id=downstream_claim)
    downstream_result = pcv.record_verdict(
        session_id=downstream_session,
        claim_id=downstream_claim,
        verdict="PASS",
        reason=_pass_reason(downstream_claim),
        title="worker-done",
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    verification_id = downstream_result["verification_id"]
    assert verification_id.startswith("verdict-")
    assert verification_id != downstream_claim

    # 2. Downstream emits a verified outgoing message carrying that verification ID
    outgoing_msg = (
        f'<cross-session-message from="worker" id="{verification_id}">'
        f"Finished implementation and tests pass.{_SAMPLE_VALID_BLOCK}"
        "</cross-session-message>"
    )

    # 3. Upstream receives this prompt; hook extracts verification_id as incoming claim_id
    upstream_ctx = _prompt_ctx(upstream_session, outgoing_msg)
    extracted_claim_id = pcg._derive_claim_id(upstream_ctx)
    assert extracted_claim_id == verification_id

    # 4. Upstream hook arms with this claim id
    arm_res = pcg.premise_check_arm(upstream_ctx)
    assert arm_res is not None
    assert pcg.is_armed(upstream_session) is True
    assert pcg.get_state(upstream_session)["claim_id"] == verification_id

    # 5. Upstream records its own verdict referencing the incoming verification ID as claim_id
    upstream_result = pcv.record_verdict(
        session_id=upstream_session,
        claim_id=verification_id,
        verdict="PASS",
        reason=_pass_reason(verification_id),
        title="supervisor-accept",
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    assert upstream_result["ok"] is True
    assert upstream_result["claim_id"] == verification_id
    upstream_verification_id = upstream_result["verification_id"]
    assert upstream_verification_id != verification_id
    assert pcg.is_valid_id(upstream_verification_id)
    assert pcg.is_armed(upstream_session) is False


def test_format_verdict_command_prints_absolute_paths():
    cmd = pcg.format_verdict_command(
        claim_id="claim-abs-paths", hooks_dir=_HOOKS_DIR, session_id="sess-abs-paths"
    )
    tokens = shlex.split(cmd)
    script_tokens = [t for t in tokens if t.endswith("verdict.py")]
    assert script_tokens, f"no verdict.py token found in: {cmd}"
    script_path = Path(script_tokens[0])
    assert script_path.is_absolute(), f"script path must be absolute, got: {script_path}"
    assert script_path.is_file(), f"script path does not exist: {script_path}"
    if "--project" in tokens:
        proj_idx = tokens.index("--project") + 1
        proj_path = Path(tokens[proj_idx])
        assert proj_path.is_absolute(), f"project path must be absolute, got: {proj_path}"
        assert proj_path.is_dir(), f"project path does not exist: {proj_path}"


def _make_stub_tracer_dir(target_dir: Path) -> Path:
    stub_dir = target_dir / "stub_tracer"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "claude_code_tracer.py").write_text(
        '"""Stub tracer for out-of-process CLI tests."""\n'
        "def discover_config(data=None):\n"
        '    return {"endpoint": "http://test-collector:4318", "project_name": "test"}\n'
        "def _new_trace_id():\n"
        '    return "1" * 32\n'
        "def _new_span_id():\n"
        '    return "2" * 16\n'
        "def _load_state(session_id):\n"
        "    return {}\n"
        "def _truncate(value):\n"
        "    return str(value)\n"
        "def _build_tool_span_record(**kwargs):\n"
        "    return {\n"
        '        "trace_id_hex": kwargs["trace_id"],\n'
        '        "span_id_hex": "2" * 16,\n'
        '        "parent_span_id_hex": kwargs["root_span_id"],\n'
        '        "name": kwargs["tool_name"],\n'
        '        "kind": None,\n'
        '        "start_ns": kwargs["start_ns"],\n'
        '        "end_ns": kwargs["end_ns"],\n'
        '        "attributes": {\n'
        '            "openinference.span.kind": "TOOL",\n'
        '            "tool.name": kwargs["tool_name"],\n'
        "        },\n"
        '        "force_span_id": False,\n'
        "    }\n"
        "def _build_and_export_spans(**kwargs):\n"
        "    return True\n"
    )
    return stub_dir


@pytest.mark.integration
def test_printed_command_runs_from_different_cwd_under_claude_code_and_agy(tmp_path):
    import os
    import subprocess

    from build.build import build_all

    dist_root = tmp_path / "dist"
    build_all(
        _REPO_ROOT,
        dist_root,
        marketplace_path=_REPO_ROOT / "build" / "marketplace.toml",
        plugins=["ida"],
        version="0.0.0",
    )

    gate_dir = tmp_path / "gate_state"
    gate_dir.mkdir(parents=True, exist_ok=True)

    for client in ("claude", "agy"):
        build_dir = dist_root / f"ida-{client}"
        hooks_dir = build_dir / "hooks"
        session_id = f"sess-run-{client}"
        claim_id = f"claim-{client}-123"

        cmd = pcg.format_verdict_command(
            claim_id=claim_id, hooks_dir=hooks_dir, session_id=session_id
        )
        tokens = shlex.split(cmd)

        # Verify command contains absolute paths
        script_tokens = [t for t in tokens if t.endswith("verdict.py")]
        assert script_tokens, f"no verdict.py token in: {cmd}"
        script_path = Path(script_tokens[0])
        assert script_path.is_absolute(), f"script path must be absolute: {script_path}"
        assert script_path.is_file(), f"script path not found: {script_path}"

        if "--project" in tokens:
            proj_idx = tokens.index("--project") + 1
            proj_path = Path(tokens[proj_idx])
            assert proj_path.is_absolute(), f"project path must be absolute: {proj_path}"
            assert proj_path.is_dir(), f"project path not found: {proj_path}"

        # Distinct directory representing an agent running from /workspace or scratch
        outside_dir = tmp_path / f"outside-workspace-{client}"
        outside_dir.mkdir(parents=True, exist_ok=True)

        # 1. Test running help from outside cwd
        help_cmd = [*tokens[: tokens.index("--claim")], "--help"]
        res_help = subprocess.run(
            help_cmd,
            cwd=outside_dir,
            capture_output=True,
            text=True,
        )
        assert res_help.returncode == 0, (
            f"{client} failed --help from outside dir:\n{res_help.stderr}"
        )
        assert "usage: premise_check_verdict.py" in res_help.stdout

        # 2. Test running a real verdict from outside cwd
        pcg.arm(session_id, claim_id=claim_id)
        assert pcg.is_armed(session_id) is True

        stub_dir = _make_stub_tracer_dir(tmp_path)
        reason_file = tmp_path / f"reason-{client}.txt"
        reason_file.write_text(_pass_reason(claim_id), encoding="utf-8")
        run_tokens = shlex.split(
            cmd.replace("<PASS|REVISE|FAIL>", "PASS").replace(
                "<path>", shlex.quote(str(reason_file))
            )
        )
        res_verdict = subprocess.run(
            run_tokens,
            cwd=outside_dir,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "AOPS_PREMISE_GATE_DIR": str(gate_dir),
                "PYTHONPATH": f"{stub_dir}:{hooks_dir}",
            },
        )
        assert res_verdict.returncode == 0, (
            f"{client} verdict command failed from outside dir:\n{res_verdict.stderr}"
        )
        assert "PASS" in res_verdict.stdout
        assert '"ok": true' in res_verdict.stdout

        # Verify gate was disarmed
        assert pcg.is_armed(session_id) is False


@pytest.mark.integration
def test_printed_command_runs_with_relative_hooks_dir_from_plugin_cwd(tmp_path, monkeypatch):
    import os
    import subprocess

    from build.build import build_all

    dist_root = tmp_path / "dist"
    build_all(
        _REPO_ROOT,
        dist_root,
        marketplace_path=_REPO_ROOT / "build" / "marketplace.toml",
        plugins=["ida"],
        version="0.0.0",
    )

    gate_dir = tmp_path / "gate_state_rel"
    gate_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(gate_dir))

    build_dir = dist_root / "ida-claude"
    session_id = "sess-rel-hooks"
    claim_id = "claim-rel-hooks"

    # When cwd is the plugin root and hooks_dir is relative (e.g. Path("hooks"))
    monkeypatch.chdir(build_dir)
    cmd = pcg.format_verdict_command(
        claim_id=claim_id, hooks_dir=Path("hooks"), session_id=session_id
    )
    tokens = shlex.split(cmd)

    script_tokens = [t for t in tokens if t.endswith("verdict.py")]
    assert script_tokens
    script_path = Path(script_tokens[0])
    assert script_path.is_absolute(), f"script path must be absolute: {script_path}"
    assert script_path.is_file()

    # Outside cwd execution
    outside_dir = tmp_path / "outside-rel-test"
    outside_dir.mkdir(parents=True, exist_ok=True)
    pcg.arm(session_id, claim_id=claim_id)

    stub_dir = _make_stub_tracer_dir(tmp_path)
    reason_file = tmp_path / "reason-rel.txt"
    reason_file.write_text(_pass_reason(claim_id), encoding="utf-8")
    run_tokens = shlex.split(
        cmd.replace("<PASS|REVISE|FAIL>", "PASS").replace("<path>", shlex.quote(str(reason_file)))
    )
    res = subprocess.run(
        run_tokens,
        cwd=outside_dir,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "AOPS_PREMISE_GATE_DIR": str(gate_dir),
            "PYTHONPATH": f"{stub_dir}:{build_dir / 'hooks'}",
        },
    )
    assert res.returncode == 0, f"execution failed:\n{res.stderr}"
    assert "PASS" in res.stdout
    assert pcg.is_armed(session_id) is False


# ---------------------------------------------------------------------------
# agy: recorded hook payload shapes
# ---------------------------------------------------------------------------

_AGY_PAYLOADS = json.loads(
    (_REPO_ROOT / "tests" / "fixtures" / "agy_hook_payloads.json").read_text(encoding="utf-8")
)


@pytest.fixture
def agy_ida(monkeypatch):
    """The gated agent's identity, supplied the one way normalize() reads it on agy."""
    monkeypatch.delenv("CLAUDE_AGENT_NAME", raising=False)
    monkeypatch.delenv("AGY_AGENT_NAME", raising=False)
    monkeypatch.setenv("AOPS_AGENT_NAME", "ida")


def test_agy_invoke_subagent_is_a_gated_tool_on_pre_tool_use(agy_ida):
    ctx = dispatch.normalize(
        "agy", "PreToolUse", _AGY_PAYLOADS["pre_tool_invoke_subagent"], _HOOKS_DIR
    )
    assert pcg._is_blocked_tool(ctx.tool) is True


@pytest.mark.parametrize("payload", ["post_tool_invoke_subagent", "post_tool_wait"])
def test_agy_dispatch_receipt_and_wait_do_not_arm(agy_ida, payload):
    ctx = dispatch.normalize("agy", "PostToolUse", _AGY_PAYLOADS[payload], _HOOKS_DIR)
    assert ctx.agent_type == "ida"
    assert pcg.premise_check_arm(ctx) is None
    assert pcg.is_armed(ctx.session_id) is False


# ---------------------------------------------------------------------------
# Teammate messages and identity-independent arming
# ---------------------------------------------------------------------------


def _valid_report_argdown(ask_id: str = "tg-100") -> tuple[str, str]:
    report_text = f"""## Report
```argdown
===
asks:
  {ask_id}: 2
answers:
  {ask_id}: 2
===
(1) Work completed per spec -- rule
-- rule --
(2) Outcome verified
```"""
    reason = f"PASS {{claim_id}}: work completed per spec and verified for {ask_id}."
    return report_text, reason


def test_teammate_message_to_teammate_arms_gate_and_records_verdict():
    session_id = "sess-teammate-recv"
    report_text, reason_tmpl = _valid_report_argdown("tg-404")
    prompt = (
        '<teammate-message id="claim-teammate-404" teammate_id="worker">\n'
        f"{report_text}\n"
        "</teammate-message>"
    )
    # The receiving agent is a teammate, not ida or sara
    ctx = _prompt_ctx(session_id, prompt, agent_type="researcher-worker")
    arm_res = pcg.premise_check_arm(ctx)
    assert arm_res is not None
    assert pcg.is_armed(session_id) is True

    # PreToolUse refuses dispatch while armed
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id, agent_type="researcher-worker"))
    assert res is not None and res.kind == dispatch.Kind.REFUSE

    # Verdict records with verification id and disarms the gate
    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_id,
        claim_id="claim-teammate-404",
        verdict="PASS",
        reason=reason_tmpl.format(claim_id="claim-teammate-404"),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert verdict_res["verification_id"].startswith("verdict-")
    assert pcg.is_armed(session_id) is False


def test_report_to_in_session_subagent_arms_gate_and_records_verdict():
    session_id = "sess-subagent-recv"
    report_text, reason_tmpl = _valid_report_argdown("tg-406")
    prompt = (
        '<cross-session-message id="claim-subagent-406" from="peer-a">\n'
        f"{report_text}\n"
        "</cross-session-message>"
    )
    # The receiving agent is an in-session subagent
    ctx = _prompt_ctx(session_id, prompt, agent_type="general-purpose")
    arm_res = pcg.premise_check_arm(ctx)
    assert arm_res is not None
    assert pcg.is_armed(session_id) is True

    # PreToolUse refuses dispatch while armed
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id, agent_type="general-purpose"))
    assert res is not None and res.kind == dispatch.Kind.REFUSE

    # Verdict records with verification id and disarms the gate
    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_id,
        claim_id="claim-subagent-406",
        verdict="PASS",
        reason=reason_tmpl.format(claim_id="claim-subagent-406"),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert verdict_res["verification_id"].startswith("verdict-")
    assert pcg.is_armed(session_id) is False


def test_foreground_subagent_return_to_teammate_arms_gate_and_records_verdict():
    session_id = "sess-fg-subagent-return"
    report_text, reason_tmpl = _valid_report_argdown("tg-500")
    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        tool="Agent",
        session_id=session_id,
        agent_type="worker-teammate",
        raw={
            "tool_input": {"description": "audit findings"},
            "tool_response": {
                "status": "completed",
                "content": [{"type": "text", "text": report_text}],
            },
            "tool_use_id": "toolu_fg_return",
        },
    )
    arm_res = pcg.premise_check_arm(ctx)
    assert arm_res is not None
    assert pcg.is_armed(session_id) is True
    claim_id = pcg.get_state(session_id)["claim_id"]

    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=reason_tmpl.format(claim_id=claim_id),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert verdict_res["verification_id"].startswith("verdict-")
    assert pcg.is_armed(session_id) is False


def test_task_notification_return_arms_gate_and_no_result_leaves_unarmed():
    report_text, reason_tmpl = _valid_report_argdown("tg-task-1")

    # 1. Task notification with a <result> arms the gate
    session_armed = "sess-tn-result"
    prompt_armed = (
        '<task-notification id="claim-task-1">\n'
        f"<result>\n{report_text}\n</result>\n"
        "</task-notification>"
    )
    ctx_armed = _prompt_ctx(session_armed, prompt_armed, agent_type="worker")
    arm_res = pcg.premise_check_arm(ctx_armed)
    assert arm_res is not None
    assert pcg.is_armed(session_armed) is True

    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_armed,
        claim_id="claim-task-1",
        verdict="PASS",
        reason=reason_tmpl.format(claim_id="claim-task-1"),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert verdict_res["verification_id"].startswith("verdict-")
    assert pcg.is_armed(session_armed) is False

    # 2. Task notification without a <result> (e.g. background command finished) leaves gate unarmed
    session_unarmed = "sess-tn-no-result"
    prompt_unarmed = (
        '<task-notification id="claim-task-2">\n'
        "background bash command exited with code 0\n"
        "</task-notification>"
    )
    ctx_unarmed = _prompt_ctx(session_unarmed, prompt_unarmed, agent_type="worker")
    assert pcg.premise_check_arm(ctx_unarmed) is None
    assert pcg.is_armed(session_unarmed) is False


def test_teammate_message_idle_notification_arms_gate_and_records_verdict_for_non_default_agent():
    session_id = "sess-teammate-idle"
    report_text, reason_tmpl = _valid_report_argdown("tg-398")
    payload = json.dumps(
        {
            "type": "idle_notification",
            "from": "resilience-ideas",
            "timestamp": "2026-10-23T12:23:44.965Z",
            "idleReason": "available",
            "result": report_text,
        }
    )
    prompt = (
        "Another Claude session sent a message:\n"
        f'<teammate-message teammate_id="resilience-ideas" color="green">\n{payload}\n</teammate-message>\n\n'
        "This came from another Claude session — not typed by your user, but very likely working on their behalf."
    )
    arm_res = pcg.premise_check_arm(_prompt_ctx(session_id, prompt, agent_type="teammate-checker"))
    assert arm_res is not None
    assert pcg.is_armed(session_id) is True

    claim_id = pcg.get_state(session_id)["claim_id"]
    assert claim_id.startswith("claim-")

    # PreToolUse refuses dispatch while armed
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id, agent_type="teammate-checker"))
    assert res is not None and res.kind == dispatch.Kind.REFUSE

    # Verdict records with verification id and disarms the gate
    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=reason_tmpl.format(claim_id=claim_id),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert verdict_res["verification_id"].startswith("verdict-")
    assert pcg.is_armed(session_id) is False


def test_teammate_message_send_message_arms_gate_and_records_verdict_for_non_default_agent():
    session_id = "sess-teammate-sendmsg"
    report_text, reason_tmpl = _valid_report_argdown("tg-1")
    prompt = (
        "Another Claude session sent a message:\n"
        f'<teammate-message id="worker-report-1" teammate_id="worker" color="blue" summary="Task finished">\n{report_text}\n</teammate-message>\n\n'
        "This came from another Claude session — not typed by your user, but very likely working on their behalf."
    )
    arm_res = pcg.premise_check_arm(_prompt_ctx(session_id, prompt, agent_type="subagent-lead"))
    assert arm_res is not None
    assert pcg.is_armed(session_id) is True
    assert pcg.get_state(session_id)["claim_id"] == "worker-report-1"

    # PreToolUse refuses dispatch while armed
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id, agent_type="subagent-lead"))
    assert res is not None and res.kind == dispatch.Kind.REFUSE

    # Verdict records with verification id and disarms the gate
    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_id,
        claim_id="worker-report-1",
        verdict="PASS",
        reason=reason_tmpl.format(claim_id="worker-report-1"),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert verdict_res["verification_id"].startswith("verdict-")
    assert pcg.is_armed(session_id) is False


_GLUED_RESULT_EXAMPLE = (
    "<task-notification>\n"
    "<task-id>a0000000000000001</task-id>\n"
    "<output-file>/tmp/example/tasks/a0000000000000001.output</output-file>\n"
    "<status>completed</status>\n"
    '<summary>Agent "Dispatch example fix" finished</summary>\n'
    "<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>\n"
    "<result>I dispatched the fix to a worker. It is still running, so there is no PR yet.\n\n"
    '- **Task:** `task_0001`, "Example task title". It is at `queued`.\n'
    "- **Worker:** container `worker-task_0001-20260101`. The launch call returned no error.\n\n"
    "I compared the task's Goal and Acceptance with the user's message `msg-001`. Nothing is missing, and nothing was added.\n\n"
    "```argdown\n"
    "===\n"
    "asks:\n"
    "  ida/1: What was dispatched, with task id and worker or PR link.\n"
    "answers:\n"
    "  ida/1: 4\n"
    "notes:\n"
    "  a: get_task task_0001\n"
    "  b: run_container result\n"
    "===\n\n"
    "(1) The task task_0001, status queued, says what the user asked in msg-001: the requested change, PR into the release branch. -- I read the record ^a\n"
    "-- A queued task whose Goal and Acceptance say what the ask says is a faithful, ready task. Unless: the body leaves out or adds meaning; ruled out by reading it against msg-001. --\n"
    "(2) So the task is ready to dispatch.\n"
    '(3) The run_container call for container polecat-agy-task_0001-20261027 returned no error, with state "created". -- I made the call ^b\n'
    '-- A run call that returns no error launches the worker. Unless: the container never left "created"; not ruled out, since I did not read its status. --\n'
    "(4) So task_0001 was dispatched to that container; the PR link follows when it completes.\n"
    "```</result>\n"
    "<usage><subagent_tokens>50000</subagent_tokens><tool_uses>9</tool_uses><duration_ms>100000</duration_ms></usage>\n"
    "</task-notification>\n"
)


def test_issue_3181_verdict_pass_on_glued_task_notification_succeeds():
    """Issue #3181: Coordinator records PASS on a <task-notification> with glued ```</result>."""
    session_id = "sess-issue-3181"
    report_text, reason_tmpl = _valid_report_argdown("ida/1")
    glued_prompt = (
        "<task-notification>\n"
        "<task-id>task-3181</task-id>\n"
        f"<result>{report_text}</result>\n"
        "</task-notification>"
    )
    ctx = _prompt_ctx(session_id, glued_prompt)
    res = pcg.premise_check_arm(ctx)
    assert res is not None
    assert pcg.is_armed(session_id) is True
    claim_id = pcg.get_state(session_id)["claim_id"]

    tracer = _StubTracer(config={"endpoint": "http://x"})
    verdict_res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=reason_tmpl.format(claim_id=claim_id),
        tracer_mod=tracer,
    )
    assert verdict_res["ok"] is True
    assert pcg.is_armed(session_id) is False


def test_issue_3182_task_notification_unwraps_result_in_judged_text():
    """Issue #3182: Gate unwraps <result> body from <task-notification> as judged text."""
    session_id = "sess-issue-3182"
    ctx = _prompt_ctx(session_id, _GLUED_RESULT_EXAMPLE)
    res = pcg.premise_check_arm(ctx)
    assert res is not None
    claim_id = pcg.get_state(session_id)["claim_id"]
    judged_text, _ = pcg.get_judged(session_id, claim_id)
    assert judged_text is not None
    assert not judged_text.startswith("<task-notification")
    assert "<usage>" not in judged_text
    assert "<task-id>" not in judged_text
    assert judged_text.startswith("I dispatched the fix to a worker.")


def test_format_verdict_command_resolves_symlinked_skill_path_and_includes_session(
    tmp_path, monkeypatch
):
    """AC1 (#3543): hook-formatted verdict commands resolve symlinked skill paths to the real
    plugin project directory (with pyproject.toml) and include --session <session_id>."""
    # Real plugin directory where pyproject.toml and opentelemetry live
    real_plugin_dir = tmp_path / "real_plugin_ida"
    real_skills = real_plugin_dir / "skills" / "premise-check" / "scripts"
    real_skills.mkdir(parents=True)
    real_script = real_skills / "verdict.py"
    real_script.write_text("#!/usr/bin/env python3\n")
    (real_plugin_dir / "pyproject.toml").write_text('[project]\nname = "ida"\nversion = "1.0.0"\n')

    # Workspace directory with symlinked .agents/skills/premise-check
    workspace = tmp_path / "workspace"
    workspace_agents = workspace / ".agents"
    workspace_skills = workspace_agents / "skills"
    workspace_skills.mkdir(parents=True)
    symlinked_skill = workspace_skills / "premise-check"
    symlinked_skill.symlink_to(real_plugin_dir / "skills" / "premise-check")

    symlinked_script = symlinked_skill / "scripts" / "verdict.py"
    assert symlinked_script.is_file()

    # Even if AOPS_SESSION_ID is set in the hook environment,
    # the formatted command must resolve --project to real_plugin_dir and include --session <session_id>
    monkeypatch.setenv("AOPS_SESSION_ID", "env-session-id")
    cmd = pcg.format_verdict_command(
        claim_id="claim-symlink-test",
        hooks_dir=symlinked_skill,
        session_id="target-session-xyz",
    )
    tokens = shlex.split(cmd)
    assert "--project" in tokens
    proj_idx = tokens.index("--project") + 1
    assert Path(tokens[proj_idx]).resolve() == real_plugin_dir.resolve()
    assert tokens[proj_idx] != str(workspace_agents)
    assert "--session" in tokens
    sess_idx = tokens.index("--session") + 1
    assert tokens[sess_idx] == "target-session-xyz"


def test_code_fence_safe_result_extraction_preserves_trailing_argdown():
    """Extraction of <result> content ignores nested XML tags within markdown code fences."""
    raw_payload = (
        "<task-notification>\n"
        "<task-id>task-code-fence</task-id>\n"
        "<result>\n"
        "Here is the code change:\n"
        "```xml\n"
        "<result>fake nested result</result>\n"
        "</result>\n"
        "```\n"
        "And here is the conclusion:\n"
        "```argdown\n"
        "===\n"
        "asks: none\n"
        "===\n"
        "[no claim]\n"
        "```\n"
        "</result>\n"
        "</task-notification>"
    )
    extracted = hg.extract_notification_result(raw_payload)
    assert extracted is not None
    assert "[no claim]" in extracted
    assert "fake nested result" in extracted

    # And carries_report identifies it as carrying a report
    assert hg.carries_report(raw_payload) is True

    # And hearsay_gate._extract_judged_text unwraps the complete body including the argdown block
    unwrapped = hg._extract_judged_text(raw_payload)
    assert "[no claim]" in unwrapped


def test_agy_subagent_preinvocation_delivers_honesty_reminder(tmp_path, monkeypatch):
    """In agy, first PreInvocation delivers honesty.md when invoked as a subagent."""
    from handlers import agy_session_pointer

    pointer_dir = tmp_path / "pointer_dir"
    tracer_dir = tmp_path / "tracer_dir"
    monkeypatch.setenv("AOPS_SESSION_POINTER_DIR", str(pointer_dir))
    monkeypatch.setenv("AOPS_TRACER_STATE_DIR", str(tracer_dir))

    subagent_sess = "subagent-session-123"
    parent_sess = "parent-session-999"

    # Setup tracer state indicating parent session
    tracer_dir.mkdir(parents=True)
    (tracer_dir / f"{subagent_sess}.json").write_text(
        json.dumps(
            {
                "phoenix_session_id": f"{parent_sess}/{subagent_sess}",
                "parent_session_id": parent_sess,
            }
        )
    )

    ctx = dispatch.HookContext(
        client="agy",
        event="PreInvocation",
        session_id=subagent_sess,
        agent_type="james",
        hooks_dir=Path("plugins/ida/hooks"),
    )

    res = agy_session_pointer(ctx)
    assert res is not None
    # Must contain honesty reminder and premise-check pointer
    expected_honesty, _ = dispatch.load_message_pair(Path("plugins/ida/hooks"), "honesty")
    assert expected_honesty in res.inject_text
    assert "ida:premise-check" in res.inject_text
    assert f"caller_session: {parent_sess}" in res.inject_text


# ---------------------------------------------------------------------------
# Multi-agent recipient isolation, metadata filtering, batch & handback plumbing
# ---------------------------------------------------------------------------


def _agent_dispatch_ctx_for(
    session_id: str,
    agent_id: str = "",
    tool: str = "Agent",
    agent_type: str = "ida:ida",
) -> dispatch.HookContext:
    return dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool=tool,
        session_id=session_id,
        agent_id=agent_id,
        agent_type=agent_type,
        raw={"agent_id": agent_id} if agent_id else {},
    )


def _post_tool_ctx_for(
    session_id: str,
    tool_input: dict[str, Any],
    tool_response: Any,
    tool: str = "Agent",
    agent_id: str = "",
    agent_type: str = "ida:ida",
    tool_use_id: str = "toolu_test",
) -> dispatch.HookContext:
    raw: dict[str, Any] = {
        "tool_input": tool_input,
        "tool_response": tool_response,
        "tool_use_id": tool_use_id,
    }
    if agent_id:
        raw["agent_id"] = agent_id
    return dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        tool=tool,
        session_id=session_id,
        agent_id=agent_id,
        agent_type=agent_type,
        raw=raw,
    )


def test_concurrent_agent_ids_isolate_gate_slots_and_prevent_cross_blocking_or_consumption():
    """Different agent_ids sharing session_id isolate armed slots, judged files, and verdicts."""
    import handlers

    session_id = "sess-concurrent-isolation"
    report_root, reason_root = _valid_report_argdown("ask-root")
    report_sub_b, reason_sub_b = _valid_report_argdown("ask-sub-b")

    # Root receives a report -> only Root is armed and blocked
    root_prompt = _prompt_ctx(
        session_id,
        f'<agent-message from="worker-1" id="claim-root-101">{report_root}</agent-message>',
    )
    assert handlers.user_prompt_submit(root_prompt) is not None
    assert pcg.is_armed(session_id) is True
    assert pcg.is_armed(session_id, agent_id="sub-a") is False

    # Concurrent subagent sub-a is NOT blocked by Root's armed slot
    assert pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, agent_id="sub-a")) is None
    assert (
        pcg.premise_check_handler(
            _agent_dispatch_ctx_for(session_id, agent_id="sub-a", tool="SendMessage")
        )
        is None
    )
    # Root IS still blocked
    root_blk = pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, agent_id=""))
    assert root_blk is not None and root_blk.kind == dispatch.Kind.REFUSE

    # Sub-b arms an identically titled claim in parallel
    pcg.arm(
        session_id,
        claim_id="Audit module",
        judged_text=report_sub_b,
        judged_ref="toolu_b",
        agent_id="sub-b",
    )
    pcg.arm(
        session_id,
        claim_id="Audit module",
        judged_text=report_root,
        judged_ref="toolu_root",
        agent_id="",
    )
    assert pcg.is_armed(session_id, agent_id="sub-b") is True
    assert pcg.is_armed(session_id, agent_id="sub-a") is False

    tracer = _StubTracer(config={"endpoint": "http://x"})
    # Omitting --agent NEVER matches or consumes sub-b's pending slot; must only see Root
    with pytest.raises(ValueError, match="unknown or mismatched|not armed"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-only-on-sub-b",
            verdict="PASS",
            reason=reason_root.format(claim_id="claim-only-on-sub-b"),
            tracer_mod=tracer,
        )

    # Disarming sub-b's "Audit module" leaves Root's "Audit module" judged file and slot intact
    res_b = pcv.record_verdict(
        session_id=session_id,
        claim_id="Audit module",
        verdict="PASS",
        reason=reason_sub_b.format(claim_id="Audit module"),
        tracer_mod=tracer,
        agent_id="sub-b",
    )
    assert res_b["ok"] is True
    assert pcg.is_armed(session_id, agent_id="sub-b") is False
    root_judged, _ = pcg.get_judged(session_id, "Audit module")
    assert root_judged is not None and "ask-root" in root_judged
    assert pcg.is_armed(session_id) is True


def test_resolve_session_id_ignores_agent_suffix_and_parents_file(monkeypatch):
    """resolve_session_id returns the raw session_id JSON field rather than filename stems."""
    session_id = "sess-resolve-root"
    sub_id = "sub-alpha-99"
    report_text, reason_tmpl = _valid_report_argdown("ask-resolve")

    pcg.arm(
        session_id,
        claim_id="claim-sub-resolve",
        judged_text=report_text,
        judged_ref="toolu_res",
        agent_id=sub_id,
    )
    # Write a coordination sidecar too, which must be ignored
    parents_file = pcg._state_dir() / f"{session_id}.parents.json"
    parents_file.write_text(json.dumps({"subagent_parents": {sub_id: ""}}), encoding="utf-8")

    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    resolved = pcv.resolve_session_id("", "claim-sub-resolve", agent_id=sub_id)
    assert resolved == session_id


def test_block_message_identifies_this_agent_and_keeps_two_line_contract():
    """hearsay_blocked keeps <=2 lines, armed indicator prefix, and emits --agent when scoped."""
    session_id = "sess-blk-agent"
    sub_id = "sub-coord-1"
    claim_id = "claim-sub-blk"
    pcg.arm(session_id, claim_id=claim_id, judged_text="pending", agent_id=sub_id)

    ctx = _agent_dispatch_ctx_for(session_id, agent_id=sub_id)
    res = pcg.premise_check_handler(ctx)
    assert res is not None and res.kind == dispatch.Kind.REFUSE
    lines = res.inject_text.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith(_POLICY["premise_check"]["armed_indicator"])
    assert claim_id in lines[0]
    assert f"--agent {sub_id}" in lines[1]
    assert lines[1] == pcg.format_verdict_command(
        claim_id, ctx.hooks_dir, session_id, agent_id=sub_id
    )
    assert res.user_text is None
    assert (
        pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, agent_id="sub-other")) is None
    )


def test_agent_post_tool_completion_metadata_without_report_body_does_not_arm_metadata_json():
    """PostToolUse(Agent) carrying status/prompt metadata without body text does not arm metadata JSON."""
    import handlers

    session_id = "sess-meta-only"
    ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"description": "Check repo", "prompt": "inspect"},
        tool_response={"status": "completed", "prompt": "inspect", "agentId": "child-meta"},
        tool_use_id="toolu_meta_1",
    )
    res = handlers.post_tool(ctx)
    assert res is None
    assert pcg.is_armed(session_id) is False


def test_foreground_subagent_handback_plus_metadata_agent_return_bridges_notice_and_passes():
    """Child SubagentHandback + metadata-only foreground PostToolUse(Agent) arm caller and PASS."""
    import handlers

    session_id = "sess-fg-handback-bridge"
    caller_id = "sub-caller-fg"
    child_id = "child-fg-9"
    report_text, reason_tmpl = _valid_report_argdown("ask-fg")

    # 1. Foreground Agent PreToolUse fires in caller before SubagentHandback
    pre_ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Agent",
        session_id=session_id,
        agent_id=caller_id,
        agent_type="ida:ida",
        raw={
            "agent_id": caller_id,
            "tool_use_id": "toolu_fg_call",
            "tool_input": {"description": "FG check"},
        },
    )
    assert pcg.premise_check_handler(pre_ctx) is None

    # 2. Child executes SubagentHandback before caller's PostToolUse(Agent) returns
    hb_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"message": report_text},
        tool_response={"success": True, "message": "Report delivered to your caller."},
        tool="SubagentHandback",
        agent_id=child_id,
        agent_type="ida:pauli",
        tool_use_id="toolu_hb_fg",
    )
    # Must stay silent for the child itself
    assert handlers.post_tool(hb_ctx) is None

    # 3. Foreground PostToolUse(Agent) returns metadata-only completion to caller
    ret_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"description": "FG check", "prompt": "do work"},
        tool_response={"status": "completed", "agentId": child_id, "prompt": "do work"},
        tool="Agent",
        agent_id=caller_id,
        agent_type="ida:ida",
        tool_use_id="toolu_fg_call",
    )
    ret_res = handlers.post_tool(ret_ctx)
    assert ret_res is not None
    assert pcg.is_armed(session_id, agent_id=caller_id) is True

    state = pcg.get_state(session_id, agent_id=caller_id)
    claim_id = state["claim_id"]
    assert f"--agent {caller_id}" in ret_res.inject_text
    stored_text, _ = pcg.get_judged(session_id, claim_id, agent_id=caller_id)
    assert stored_text is not None and "```argdown" in stored_text
    assert '"status": "completed"' not in stored_text

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=reason_tmpl.format(claim_id=claim_id),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        agent_id=caller_id,
    )
    assert res["ok"] is True
    assert pcg.is_armed(session_id, agent_id=caller_id) is False


def test_post_tool_batch_multiple_agent_results_arms_all_claims_and_handles_same_description():
    """PostToolBatch arms every completed dispatch result (even with duplicate description) and records all PASS."""
    import handlers

    session_id = "sess-batch-3"
    rep1, tmpl1 = _valid_report_argdown("ask-b1")
    rep2, tmpl2 = _valid_report_argdown("ask-b2")
    rep3, tmpl3 = _valid_report_argdown("ask-b3")

    batch_ctx = dispatch.HookContext(
        client="claude",
        event="PostToolBatch",
        session_id=session_id,
        agent_type="ida:ida",
        hooks_dir=_HOOKS_DIR,
        tool_calls=(
            {
                "tool_name": "Agent",
                "tool_use_id": "toolu_batch_1",
                "tool_input": {"description": "Audit module"},
                "tool_response": {
                    "status": "completed",
                    "content": [{"type": "text", "text": rep1}],
                },
            },
            {
                "tool_name": "Agent",
                "tool_use_id": "toolu_batch_2",
                "tool_input": {"description": "Audit module"},
                "tool_response": {
                    "status": "completed",
                    "content": [{"type": "text", "text": rep2}],
                },
            },
            {
                "tool_name": "Agent",
                "tool_use_id": "toolu_batch_3",
                "tool_input": {"description": "Check specs"},
                "tool_response": {
                    "status": "completed",
                    "content": [{"type": "text", "text": rep3}],
                },
            },
        ),
    )
    arm_res = handlers.post_tool_batch(batch_ctx)
    assert arm_res is not None
    state = pcg.get_state(session_id)
    assert len(state["claim_ids"]) == 3
    for cid in state["claim_ids"]:
        assert cid in arm_res.inject_text
    assert arm_res.user_text is None

    tracer = _StubTracer(config={"endpoint": "http://x"})
    for cid, tmpl in zip(state["claim_ids"], (tmpl1, tmpl2, tmpl3), strict=True):
        assert pcg.is_armed(session_id) is True
        res = pcv.record_verdict(
            session_id=session_id,
            claim_id=cid,
            verdict="PASS",
            reason=tmpl.format(claim_id=cid),
            tracer_mod=tracer,
        )
        assert res["ok"] is True
    assert pcg.is_armed(session_id) is False


def test_post_tool_use_then_post_tool_batch_deduplicates_already_armed_calls(monkeypatch):
    """Firing PostToolUse then PostToolBatch for the same dispatch tool_use_id arms once without double OTel."""
    import handlers

    session_id = "sess-post-dedup"
    spans: list[tuple[str, str]] = []
    monkeypatch.setattr(
        hg, "_emit_hearsay_trace", lambda ctx, cid, ref, **_kw: spans.append((cid, str(ref or "")))
    )

    rep1, _ = _valid_report_argdown("ask-d1")
    pt_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"description": "Unique single task"},
        tool_response={"status": "completed", "content": [{"type": "text", "text": rep1}]},
        tool_use_id="toolu_dedup_1",
    )
    assert handlers.post_tool(pt_ctx) is not None

    batch_ctx = dispatch.HookContext(
        client="claude",
        event="PostToolBatch",
        session_id=session_id,
        agent_type="ida:ida",
        hooks_dir=_HOOKS_DIR,
        tool_calls=(
            {
                "tool_name": "Agent",
                "tool_use_id": "toolu_dedup_1",
                "tool_input": {"description": "Unique single task"},
                "tool_response": {
                    "status": "completed",
                    "content": [{"type": "text", "text": rep1}],
                },
            },
        ),
    )
    # Second arrival on PostToolBatch must neither double-arm nor emit a second trace
    batch_res = handlers.post_tool_batch(batch_ctx)
    assert len(pcg.get_state(session_id)["claim_ids"]) == 1
    assert len(spans) == 1
    assert batch_res is None


def test_user_prompt_submit_multiple_envelopes_arms_all_and_skips_code_fences():
    """Multiple peer envelopes in one UserPromptSubmit arm every genuine report and ignore pointers/fences."""
    session_id = "sess-multi-env"
    rep1, tmpl1 = _valid_report_argdown("ask-e1")
    rep2, tmpl2 = _valid_report_argdown("ask-e2")

    prompt = (
        "<task-notification>\n<task-id>a111</task-id>\n<status>completed</status>\n"
        '<result>The report was delivered to you as a message from "a111" (its SubagentHandback call).</result>\n'
        "</task-notification>\n"
        '<agent-message from="a111">\n'
        "First report discussing an example tag:\n"
        '```xml\n<agent-message from="fake">not a real envelope</agent-message>\n```\n'
        f"{rep1}\n"
        "</agent-message>\n"
        f'<agent-message from="a222">\n{rep2}\n</agent-message>'
    )
    arm_res = pcg.premise_check_arm(_prompt_ctx(session_id, prompt))
    assert arm_res is not None
    state = pcg.get_state(session_id)
    assert len(state["claim_ids"]) == 2
    assert state["claim_ids"][0] in arm_res.inject_text
    assert state["claim_ids"][1] in arm_res.inject_text

    tracer = _StubTracer(config={"endpoint": "http://x"})
    for cid, tmpl in zip(state["claim_ids"], (tmpl1, tmpl2), strict=True):
        res = pcv.record_verdict(
            session_id=session_id,
            claim_id=cid,
            verdict="PASS",
            reason=tmpl.format(claim_id=cid),
            tracer_mod=tracer,
        )
        assert res["ok"] is True
    assert pcg.is_armed(session_id) is False


def test_subcoordinator_async_and_sendmessage_resumed_child_handback_arms_subcoordinator():
    """Child SubagentHandback (initial & SendMessage-resumed) arms subcoordinator, wakes SubagentStart, gates SubagentHandback."""
    import handlers

    session_id = "sess-subcoord-routing"
    sub_coord = "subcoord-1"
    child_id = "child-async-1"
    rep1, tmpl1 = _valid_report_argdown("ask-c1")
    rep2, tmpl2 = _valid_report_argdown("ask-c2")

    # 1. Subcoordinator spawns async child
    spawn_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"description": "Spawn child"},
        tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
        tool="Agent",
        agent_id=sub_coord,
        tool_use_id="toolu_spawn_child",
    )
    assert handlers.post_tool(spawn_ctx) is None

    # 2. Child returns SubagentHandback -> silent for child, arms ONLY sub_coord
    hb1_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"message": rep1},
        tool_response={"success": True, "message": "Report delivered to your caller."},
        tool="SubagentHandback",
        agent_id=child_id,
        agent_type="ida:pauli",
        tool_use_id="toolu_hb1",
    )
    assert handlers.post_tool(hb1_ctx) is None
    assert pcg.is_armed(session_id) is False
    assert pcg.is_armed(session_id, agent_id=sub_coord) is True

    # 3. SubagentStart waking sub_coord includes honesty.md + --agent + armed claim_id
    wake_ctx = dispatch.HookContext(
        client="claude",
        event="SubagentStart",
        session_id=session_id,
        agent_id=sub_coord,
        agent_type="ida:ida",
        hooks_dir=_HOOKS_DIR,
        raw={"agent_id": sub_coord, "agent_type": "ida:ida"},
    )
    wake_res = handlers.subagent_start(wake_ctx)
    assert wake_res is not None
    cid1 = pcg.get_state(session_id, agent_id=sub_coord)["claim_id"]
    assert cid1 in wake_res.inject_text
    assert f"--agent {sub_coord}" in wake_res.inject_text

    # 4. PreToolUse(SubagentHandback) on armed sub_coord MUST refuse upward relay
    relay_refuse = pcg.premise_check_handler(
        _agent_dispatch_ctx_for(session_id, agent_id=sub_coord, tool="SubagentHandback")
    )
    assert relay_refuse is not None and relay_refuse.kind == dispatch.Kind.REFUSE

    # Unarmed child executing SubagentHandback proceeds freely
    assert (
        pcg.premise_check_handler(
            _agent_dispatch_ctx_for(session_id, agent_id="unrelated-leaf", tool="SubagentHandback")
        )
        is None
    )

    # 5. Subcoordinator judges rep1 PASS -> unblocked
    tracer = _StubTracer(config={"endpoint": "http://x"})
    res1 = pcv.record_verdict(
        session_id=session_id,
        claim_id=cid1,
        verdict="PASS",
        reason=tmpl1.format(claim_id=cid1),
        tracer_mod=tracer,
        agent_id=sub_coord,
    )
    assert res1["ok"] is True
    assert (
        pcg.premise_check_handler(
            _agent_dispatch_ctx_for(session_id, agent_id=sub_coord, tool="SubagentHandback")
        )
        is None
    )

    # 6. Subcoordinator resumes child via SendMessage -> subsequent SubagentHandback re-arms sub_coord even while awake
    resume_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={
            "to": child_id,
            "message": "Follow-up task\n```argdown\n===\nasks: none\n===\n\n[no claim]\n```",
        },
        tool_response={"success": True, "resumedAgentId": child_id, "revivedAgentId": child_id},
        tool="SendMessage",
        agent_id=sub_coord,
        tool_use_id="toolu_resume",
    )
    assert handlers.post_tool(resume_ctx) is None
    assert pcg.is_armed(session_id, agent_id=sub_coord) is False

    hb2_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"message": rep2},
        tool_response={"success": True, "message": "Report delivered to your caller."},
        tool="SubagentHandback",
        agent_id=child_id,
        tool_use_id="toolu_hb2",
    )
    assert handlers.post_tool(hb2_ctx) is None
    assert pcg.is_armed(session_id, agent_id=sub_coord) is True
    relay_refuse2 = pcg.premise_check_handler(
        _agent_dispatch_ctx_for(session_id, agent_id=sub_coord, tool="SubagentHandback")
    )
    assert relay_refuse2 is not None and relay_refuse2.kind == dispatch.Kind.REFUSE


def test_child_send_message_to_stopped_subcoordinator_arms_target_without_inverting_parent():
    """Child SendMessage with resumedAgentId arms stopped sub-coordinator without inverting parent DAG."""
    import handlers

    session_id = "sess-sendmsg-stopped"
    sub_coord = "sub-coord-parent"
    child_r = "child-reviewer-1"
    rep_child, tmpl_child = _valid_report_argdown("ask-sm-1")

    # Root spawns sub_coord; sub_coord spawns named child_r
    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"description": "Coordinator", "name": "coord-1"},
                tool_response={"isAsync": True, "status": "async_launched", "agentId": sub_coord},
                tool="Agent",
                agent_id="",
                tool_use_id="toolu_root_spawn",
            )
        )
        is None
    )
    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"description": "Review", "name": "reviewer-1"},
                tool_response={"isAsync": True, "status": "async_launched", "agentId": child_r},
                tool="Agent",
                agent_id=sub_coord,
                tool_use_id="toolu_sub_spawn",
            )
        )
        is None
    )

    # Child sends report via SendMessage to stopped sub_coord -> Claude returns resumedAgentId == sub_coord
    child_sm = _post_tool_ctx_for(
        session_id,
        tool_input={"to": "coord-1", "message": rep_child},
        tool_response={"success": True, "resumedAgentId": sub_coord, "revivedAgentId": sub_coord},
        tool="SendMessage",
        agent_id=child_r,
        tool_use_id="toolu_child_sm",
    )
    assert handlers.post_tool(child_sm) is None

    # sub_coord MUST be armed; Root MUST stay unarmed
    assert pcg.is_armed(session_id, agent_id=sub_coord) is True
    assert pcg.is_armed(session_id) is False

    # Parent mapping of sub_coord MUST NOT be inverted to child_r
    parents = json.loads(
        (pcg._state_dir() / f"{session_id}.parents.json").read_text(encoding="utf-8")
    )
    assert parents["subagent_parents"].get(sub_coord) == ""

    # Verify parent->child direction via SendMessage leaves child unarmed
    parent_dir = _post_tool_ctx_for(
        session_id,
        tool_input={"to": "reviewer-1", "message": "Please inspect line 10."},
        tool_response={"success": True, "resumedAgentId": child_r, "revivedAgentId": child_r},
        tool="SendMessage",
        agent_id=sub_coord,
        tool_use_id="toolu_dir_sm",
    )
    assert handlers.post_tool(parent_dir) is None
    assert pcg.is_armed(session_id, agent_id=child_r) is False

    cid = pcg.get_state(session_id, agent_id=sub_coord)["claim_id"]
    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=cid,
        verdict="PASS",
        reason=tmpl_child.format(claim_id=cid),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        agent_id=sub_coord,
    )
    assert res["ok"] is True


def test_subagent_handback_from_main_child_dedups_with_user_prompt_submit_and_warns_root(
    monkeypatch,
):
    """Child handback + immediate Root UserPromptSubmit share one claim_id without losing Root warning."""
    import handlers

    session_id = "sess-main-dedup"
    child_id = "child-of-main"
    report_text, reason_tmpl = _valid_report_argdown("ask-main-1")
    traces: list[str] = []
    monkeypatch.setattr(hg, "_emit_hearsay_trace", lambda ctx, cid, ref, **_kw: traces.append(cid))

    # Root spawns async child
    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"description": "Root child"},
            tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
            tool="Agent",
            agent_id="",
            tool_use_id="toolu_main_spawn",
        )
    )
    # Child sends SubagentHandback -> silently arms Root
    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"message": report_text},
                tool_response={"success": True, "message": "Report delivered to your caller."},
                tool="SubagentHandback",
                agent_id=child_id,
                tool_use_id="toolu_main_hb",
            )
        )
        is None
    )
    cid_after_hb = pcg.get_state(session_id)["claim_id"]

    # Root UserPromptSubmit delivers wrapped handback 4ms later -> reuses claim_id, still warns Root
    ups_ctx = _prompt_ctx(
        session_id,
        f'<agent-message from="{child_id}">\n[Subagent hand-back] Report:\n{report_text}\n</agent-message>',
    )
    ups_res = pcg.premise_check_arm(ups_ctx)
    assert ups_res is not None
    state = pcg.get_state(session_id)
    assert state["claim_ids"] == [cid_after_hb]
    assert cid_after_hb in ups_res.inject_text
    assert len(traces) == 1

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=cid_after_hb,
        verdict="PASS",
        reason=reason_tmpl.format(claim_id=cid_after_hb),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    assert res["ok"] is True
    assert pcg.is_armed(session_id) is False


def test_teammate_spawned_without_agent_id_does_not_crash():
    """PostToolUse(Agent) teammate_spawned missing agentId returns None cleanly without arming."""
    import handlers

    session_id = "sess-teammate-no-id"
    ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"description": "Teammate", "name": "tm-1"},
        tool_response={"status": "teammate_spawned", "name": "tm-1"},
        tool_use_id="toolu_tm",
    )
    assert handlers.post_tool(ctx) is None
    assert pcg.is_armed(session_id) is False


def test_foreground_subcoordinator_pre_dispatch_registers_known_subagent_for_child_sendmessage():
    """Foreground sub-coordinator calling PreToolUse(Agent) is registered so child SendMessage arms it."""
    import handlers

    session_id = "sess-fg-subcoord-sm"
    sub_coord = "fg-subcoord-1"
    child_id = "fg-child-1"
    rep, tmpl = _valid_report_argdown("ask-fg-sm")

    # Root has NOT yet received PostToolUse(Agent) for foreground sub_coord;
    # sub_coord spawns child via PreToolUse(Agent)
    pre_ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Agent",
        session_id=session_id,
        agent_id=sub_coord,
        agent_type="ida:ida",
        raw={
            "agent_id": sub_coord,
            "tool_use_id": "toolu_fg_sub_spawn",
            "tool_input": {"description": "Spawn child from fg subcoord"},
        },
    )
    assert handlers.pre_tool(pre_ctx) is None

    # Child delivers report via SendMessage(to=sub_coord) while sub_coord is still active
    sm_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"to": sub_coord, "message": rep},
        tool_response={"success": True},
        tool="SendMessage",
        agent_id=child_id,
        tool_use_id="toolu_child_to_fg",
    )
    assert handlers.post_tool(sm_ctx) is None
    assert pcg.is_armed(session_id, agent_id=sub_coord) is True
    assert pcg.is_armed(session_id) is False

    cid = pcg.get_state(session_id, agent_id=sub_coord)["claim_id"]
    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=cid,
        verdict="PASS",
        reason=tmpl.format(claim_id=cid),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        agent_id=sub_coord,
    )
    assert res["ok"] is True
    assert pcg.is_armed(session_id, agent_id=sub_coord) is False


def test_subagent_handback_lowercase_or_prefixed_tool_arms_caller():
    """SubagentHandback matching handles snake_case and MCP-prefixed tool names cleanly."""
    import handlers

    session_id = "sess-hb-toolname"
    caller_id = "sub-hb-caller"
    child_id = "child-hb-snake"
    rep, tmpl = _valid_report_argdown("ask-hb-snake")

    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"description": "Spawn child"},
            tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
            tool="Agent",
            agent_id=caller_id,
            tool_use_id="toolu_spawn_snake",
        )
    )
    hb_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"message": rep},
        tool_response={"success": True},
        tool="mcp__ida__subagent_handback",
        agent_id=child_id,
        tool_use_id="toolu_hb_snake",
    )
    assert handlers.post_tool(hb_ctx) is None
    assert pcg.is_armed(session_id, agent_id=caller_id) is True

    cid = pcg.get_state(session_id, agent_id=caller_id)["claim_id"]
    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=cid,
        verdict="PASS",
        reason=tmpl.format(claim_id=cid),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        agent_id=caller_id,
    )
    assert res["ok"] is True


def test_corrupt_parents_and_slot_files_fail_loudly():
    """Corrupt parents or state JSON fails loudly instead of silently resetting."""
    session_id = "sess-corrupt-fail-loud"
    parents_path = pcg._parents_path(session_id)
    parents_path.parent.mkdir(parents=True, exist_ok=True)
    parents_path.write_text("{corrupt json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        pcg._load_parents(session_id)

    parents_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt parents metadata"):
        pcg._load_parents(session_id)

    slot_path = pcg._state_path(session_id, agent_id="sub-bad")
    slot_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt gate state"):
        pcg.find_armed_owner(session_id, "claim-12345678")
    with pytest.raises(ValueError, match="corrupt gate state"):
        pcg.get_state(session_id, agent_id="sub-bad")


def test_corrupt_sidecar_and_missing_snapshot_fail_loudly(tmp_path: Path):
    """Existing corrupt agent-<id>.meta.json and missing .judged.txt fail loudly without silent defaults."""
    session_id = "sess-corrupt-sidecar"
    child_id = "child-bad-meta"
    transcript = tmp_path / "sess.jsonl"
    transcript.write_text("", encoding="utf-8")
    sidecar = tmp_path / f"agent-{child_id}.meta.json"
    sidecar.write_text("{corrupt json", encoding="utf-8")

    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        tool="SubagentHandback",
        session_id=session_id,
        agent_id=child_id,
        transcript_path=str(transcript),
        raw={"agent_id": child_id, "transcript_path": str(transcript)},
    )
    with pytest.raises(json.JSONDecodeError):
        pcg._lookup_sidecar_tool_use_id(ctx, child_id)

    sidecar.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt sidecar metadata"):
        pcg._lookup_sidecar_tool_use_id(ctx, child_id)

    pcg.arm(session_id, claim_id="claim-missing-snap", judged_text="stored text")
    for snap in Path(pcg._state_dir()).glob("*.judged.txt"):
        snap.unlink()
    with pytest.raises(FileNotFoundError):
        pcg.get_judged(session_id, "claim-missing-snap")


# ---------------------------------------------------------------------------
# Judged-ref capture, missing snapshot guards, task-read bypass, and overrides
# ---------------------------------------------------------------------------


def test_arm_on_subagent_result_stores_judged_text_and_tool_use_id():
    report_text = "Subagent verified tests pass across all targets."
    ctx = _prompt_ctx(
        "s-arm-sub",
        f'<task-notification id="toolu_0XYZ"><result>{report_text}</result></task-notification>',
    )
    assert pcg.premise_check_arm(ctx) is not None
    claim_id = pcg.get_state("s-arm-sub")["claim_id"]
    text, ref = pcg.get_judged("s-arm-sub", claim_id)
    assert ref == "toolu_0XYZ"
    assert text is not None and report_text in text

    tracer = _StubTracer(config={"endpoint": "http://x"})
    pcv.record_verdict(
        session_id="s-arm-sub",
        claim_id=claim_id,
        verdict="PASS",
        reason=_pass_reason(claim_id),
        tracer_mod=tracer,
    )
    assert tracer.exported[0]["spans"][0]["attributes"]["premise_check.judged_ref"] == "toolu_0XYZ"
    assert pcg.get_judged("s-arm-sub", claim_id) == (None, None)


def test_arm_on_peer_message_uses_the_envelope_id_as_judged_ref():
    report_text = "Peer checked deployment state and confirmed healthy."
    prompt = f'<cross-session-message from="twin" id="msg-42">{report_text}</cross-session-message>'
    pcg.premise_check_arm(_prompt_ctx("s-arm-peer", prompt))
    text, ref = pcg.get_judged("s-arm-peer", "msg-42")
    assert ref == "msg-42"
    assert text is not None and report_text in text


def test_get_judged_and_disarm_raise_when_stored_file_is_missing():
    pcg.arm("s-gone", claim_id="CID", judged_text="stored body")
    for path in Path(pcg._state_dir()).glob("*.judged.txt"):
        path.unlink()
    with pytest.raises(FileNotFoundError):
        pcg.get_judged("s-gone", "CID")

    pcg.arm("s-gone-2", claim_id="CID", judged_text="stored body")
    for path in Path(pcg._state_dir()).glob("*.judged.txt"):
        path.unlink()
    with pytest.raises(FileNotFoundError):
        pcg.disarm("s-gone-2", "CID", "REVISE", "r")


def _task_body(with_verdict: bool = False, with_report: bool = True) -> str:
    body = "## Goal\n\nDo the thing.\n\n"
    if with_report:
        body += "## Report\n\nCompleted the work and observed green tests.\n"
    if with_verdict:
        body += "\n## Premise-Check Verdict\n\nverdict-12345678 PASS\n"
    return body


def _task_read_ctx(tool: str, body: str, task_id: str, shape: str, agent: str = "ida:ida"):
    record = {"id": task_id, "title": "Do the thing", "status": "review", "body": body}
    if shape == "content_blocks":
        response: Any = [{"type": "text", "text": json.dumps(record)}]
    elif shape == "dict":
        response = record
    else:
        response = json.dumps(record)
    return dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        tool=tool,
        session_id=f"s-task-{shape}",
        agent_type=agent,
        raw={"tool_input": {"id": task_id}, "tool_response": response},
    )


@pytest.mark.parametrize("shape", ["content_blocks", "dict", "json_text"])
@pytest.mark.parametrize("tool", _POLICY["premise_check"]["task_read_tools"])
def test_task_read_with_unverdicted_report_does_not_arm_while_bypassed(tool, shape):
    ctx = _task_read_ctx(tool, _task_body(), "task_fixture_01", shape)
    assert pcg.premise_check_arm(ctx) is None
    assert pcg.is_armed(ctx.session_id) is False


@pytest.mark.parametrize("client", ["claude", "agy"])
def test_post_tool_entry_point_does_not_arm_on_task_read_while_bypassed(client):
    handlers = _load_plugin_module("ida_handlers_arm_task_read", _HOOKS_DIR / "handlers.py")
    record = {"id": "task_fixture_01", "body": _task_body()}
    raw = {
        "tool_name": _POLICY["premise_check"]["task_read_tools"][0],
        "session_id": f"s-entry-{client}",
        "agent_type": "ida:ida",
        "tool_input": {"id": "task_fixture_01"},
        "tool_response": [{"type": "text", "text": json.dumps(record)}],
    }
    ctx = dispatch.normalize(client, "PostToolUse", raw, _HOOKS_DIR)
    handlers.post_tool(ctx)
    assert pcg.is_armed(f"s-entry-{client}") is False


@pytest.mark.parametrize("var", _POLICY["premise_check"]["override_vars"])
def test_override_passes_an_armed_gate_with_no_span_and_no_count(monkeypatch, var):
    session_id = f"s-ovr-{var}"
    pcg.arm(session_id, claim_id="claim-ovr")
    tracer = _StubTracer(
        config={"endpoint": "http://x"}, raises=OSError("an export attempt would raise")
    )
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    monkeypatch.setenv(var, "1")

    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None
    assert tracer.exported == []
    assert "override_count" not in pcg.get_state(session_id)


def test_override_on_a_disarmed_gate_is_not_counted(monkeypatch):
    tracer = _StubTracer(config={"endpoint": "http://x"})
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    monkeypatch.setenv(_POLICY["premise_check"]["override_vars"][0], "1")
    assert pcg.premise_check_handler(_agent_dispatch_ctx("s-ovr-idle")) is None
    assert tracer.exported == []
    assert "override_count" not in pcg.get_state("s-ovr-idle")


def test_armed_direction_brief_blocks_send_message_until_no_claim_verdict_disarms(
    tmp_path: Path, monkeypatch
):
    """Armed peer/agy direction briefs refuse send_message until verdict.py --no-claim (REVISE or PASS) disarms."""
    tracer = _StubTracer(config={"endpoint": "http://x"})
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)

    # 1. Armed agy [Message] direction brief missing required inputs (even with trailing [no claim] block):
    #    gate arms -> send_message refused -> verdict.py --verdict REVISE --no-claim disarms -> send_message allowed.
    sess_revise = "sess-dir-brief-revise"
    brief_missing_inputs = (
        "Review the pending spec changes and report back.\n\n"
        "```argdown\n"
        "===\n"
        "asks: none\n"
        "===\n\n"
        "[no claim]\n"
        "```"
    )
    revise_dir = tmp_path / "revise_case"
    revise_dir.mkdir(parents=True, exist_ok=True)
    agy_ctx = _agy_turn_ctx(revise_dir, sess_revise, _agy_message(_AGY_PEER, brief_missing_inputs))
    arm_rev = pcg.premise_check_arm(agy_ctx)
    assert arm_rev is not None
    assert pcg.is_armed(sess_revise) is True
    assert "--no-claim" in arm_rev.inject_text
    claim_rev = pcg.get_state(sess_revise)["claim_id"]

    send_rev_ctx = dispatch.HookContext(
        client="agy",
        event="PreToolUse",
        tool="send_message",
        session_id=sess_revise,
        agent_type="rbg:rbg",
    )
    refused_rev = pcg.premise_check_handler(send_rev_ctx)
    assert refused_rev is not None and refused_rev.kind == dispatch.Kind.REFUSE

    reason_rev = tmp_path / "revise_brief_reason.txt"
    reason_rev.write_text(
        "Turn-1 brief intake REVISE: target artifact path omitted from direction brief.",
        encoding="utf-8",
    )
    rc_rev = pcv.main(
        [
            "--claim",
            claim_rev,
            "--verdict",
            "REVISE",
            "--no-claim",
            "--reason-file",
            str(reason_rev),
            "--session",
            sess_revise,
        ]
    )
    assert rc_rev == 0
    assert pcg.is_armed(sess_revise) is False
    state_rev = pcg.get_state(sess_revise)["last_verdict"]
    assert state_rev["verdict"] == "REVISE"
    assert state_rev["no_claim"] is True
    span_rev = tracer.exported[-1]["spans"][0]["attributes"]
    assert span_rev["premise_check.verdict"] == "REVISE"
    assert span_rev["premise_check.no_claim"] is True
    assert pcg.premise_check_handler(send_rev_ctx) is None

    # 2. Armed Claude Code peer direction brief passing Turn-1 intake:
    #    gate arms -> send_message refused -> verdict.py --verdict PASS --no-claim disarms -> send_message allowed.
    sess_pass = "sess-dir-brief-pass"
    peer_brief = (
        '<cross-session-message from="supervisor" id="brief-pass-1">\n'
        "## Ask\nReview `specs/enforcement/evidence-contract.md` on branch feat/demo.\n"
        "</cross-session-message>"
    )
    arm_pass = pcg.premise_check_arm(_prompt_ctx(sess_pass, peer_brief, agent_type="rbg:rbg"))
    assert arm_pass is not None
    assert pcg.is_armed(sess_pass) is True
    claim_pass = pcg.get_state(sess_pass)["claim_id"]
    assert claim_pass == "brief-pass-1"

    send_pass_ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="SendMessage",
        session_id=sess_pass,
        agent_type="rbg:rbg",
    )
    refused_pass = pcg.premise_check_handler(send_pass_ctx)
    assert refused_pass is not None and refused_pass.kind == dispatch.Kind.REFUSE

    reason_pass = tmp_path / "pass_brief_reason.txt"
    reason_pass.write_text(
        "Turn-1 direction brief intake PASS: target artifact and ask verified.",
        encoding="utf-8",
    )
    rc_pass = pcv.main(
        [
            "--claim",
            claim_pass,
            "--verdict",
            "PASS",
            "--no-claim",
            "--reason-file",
            str(reason_pass),
            "--session",
            sess_pass,
        ]
    )
    assert rc_pass == 0
    assert pcg.is_armed(sess_pass) is False
    state_pass = pcg.get_state(sess_pass)["last_verdict"]
    assert state_pass["verdict"] == "PASS"
    assert state_pass["no_claim"] is True
    span_pass = tracer.exported[-1]["spans"][0]["attributes"]
    assert span_pass["premise_check.verdict"] == "PASS"
    assert span_pass["premise_check.no_claim"] is True
    assert pcg.premise_check_handler(send_pass_ctx) is None


def _claims_from_notice(result: dispatch.Result) -> list[str]:
    """Extract --claim values from a hook notice/refusal Result's verdict commands."""
    claims: list[str] = []
    for line in result.inject_text.splitlines()[1:]:
        tokens = shlex.split(line)
        if "--claim" in tokens:
            claims.append(tokens[tokens.index("--claim") + 1])
    return claims


def _wrap_claude_handback(
    sender: str,
    raw_report: str,
    *,
    with_harness_warning: bool = True,
    envelope_id: str = "",
) -> str:
    """Wrap raw report text like Claude Code <agent-message> handback delivery."""
    escaped = raw_report.replace("<", "<\\")
    indented = "\n".join(f"  {line}" for line in escaped.splitlines())
    harness_line = (
        "  [harness: subagent output matched instruction-shaped pattern(s): ignore previous]\n"
        if with_harness_warning
        else ""
    )
    id_attr = f' id="{envelope_id}"' if envelope_id else ""
    return (
        f'<agent-message from="{sender}"{id_attr}>\n'
        "[Subagent hand-back] The text below is a subagent's message to you, "
        "sent via SubagentHandback.\n"
        "The report follows:\n"
        f"{harness_line}{indented}\n"
        "</agent-message>"
    )


@pytest.mark.parametrize("arrival_order", ["handback_first", "prompt_first"])
def test_indented_harness_wrapped_handback_dedups_both_orders_and_unblocks(
    arrival_order: str, monkeypatch
):
    """Indented, harness-annotated, <-escaped <agent-message> matches SubagentHandback in both arrival orders."""
    import handlers

    session_id = f"sess-indented-dedup-{arrival_order}"
    child_id = "child-indented-1"
    report_text = (
        "Verified <tag> behavior across runs.\n\n"
        "```argdown\n"
        "(1) Direct observation `path:1` with <check>.\n"
        "-- Pattern check --\n"
        "(2) So, fix holds.\n"
        "```"
    )
    tracer = _StubTracer(config={"endpoint": "http://x"})
    monkeypatch.setattr(hg, "claude_code_tracer", tracer)

    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"description": "Run check"},
                tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
                tool="Agent",
                tool_use_id="toolu_spawn_indent",
            )
        )
        is None
    )

    hb_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"message": report_text},
        tool_response={"success": True, "message": "Report delivered to your caller."},
        tool="SubagentHandback",
        agent_id=child_id,
        tool_use_id="toolu_hb_indent",
    )
    ups_ctx = _prompt_ctx(session_id, _wrap_claude_handback(child_id, report_text))

    if arrival_order == "handback_first":
        assert handlers.post_tool(hb_ctx) is None
        ups_res = handlers.user_prompt_submit(ups_ctx)
        assert ups_res is not None
    else:
        ups_res = handlers.user_prompt_submit(ups_ctx)
        assert ups_res is not None
        assert handlers.post_tool(hb_ctx) is None

    notice_claims = _claims_from_notice(ups_res)
    blk = pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage"))
    assert blk is not None and blk.kind == dispatch.Kind.REFUSE
    blocked_claims = _claims_from_notice(blk)
    assert len(notice_claims) == 1
    assert blocked_claims == notice_claims
    assert len(tracer.exported) == 1
    claim_id = notice_claims[0]

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=_pass_reason(claim_id),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    assert res["ok"] is True
    assert pcg.is_armed(session_id) is False
    assert (
        pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage")) is None
    )


def test_indented_null_claim_agent_message_auto_disarms():
    """Indented [no claim] wrapped in <agent-message> + [harness: ...] auto-disarms a matching claim."""
    import handlers

    session_id = "sess-indented-null"
    pre_arm = handlers.user_prompt_submit(
        _prompt_ctx(
            session_id,
            '<cross-session-message from="worker-1" id="claim-null-target">Preliminary status report.</cross-session-message>',
        )
    )
    assert pre_arm is not None
    assert pcg.is_armed(session_id) is True

    null_report = "```argdown\n===\nasks: none\n===\n\n[no claim]\n```"
    ups_ctx = _prompt_ctx(
        session_id,
        _wrap_claude_handback("worker-1", null_report, envelope_id="claim-null-target"),
    )
    assert handlers.user_prompt_submit(ups_ctx) is None
    assert pcg.is_armed(session_id) is False
    assert (
        pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage")) is None
    )


@pytest.mark.parametrize("first_channel", ["handback", "prompt"])
def test_delayed_twin_arrival_after_verdict_disarm_does_not_rearm_or_block(first_channel: str):
    """Judging the first-arriving handback channel prevents the slower twin channel from re-arming."""
    import handlers

    session_id = f"sess-post-verdict-twin-{first_channel}"
    child_id = "child-twin-post"
    report_text, reason_tmpl = _valid_report_argdown("ask-twin")

    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"description": "Twin test"},
            tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
            tool="Agent",
            tool_use_id="toolu_twin_spawn",
        )
    )
    hb_ctx = _post_tool_ctx_for(
        session_id,
        tool_input={"message": report_text},
        tool_response={"success": True, "message": "Report delivered to your caller."},
        tool="SubagentHandback",
        agent_id=child_id,
        tool_use_id="toolu_twin_hb",
    )
    ups_ctx = _prompt_ctx(session_id, _wrap_claude_handback(child_id, report_text))

    if first_channel == "handback":
        handlers.post_tool(hb_ctx)
        blk = pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage"))
        assert blk is not None
        claim_id = _claims_from_notice(blk)[0]
    else:
        ups_res = handlers.user_prompt_submit(ups_ctx)
        assert ups_res is not None
        claim_id = _claims_from_notice(ups_res)[0]

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=claim_id,
        verdict="PASS",
        reason=reason_tmpl.format(claim_id=claim_id),
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    assert res["ok"] is True
    assert pcg.is_armed(session_id) is False

    # Delayed twin arrival after disarm must neither notify nor re-arm
    if first_channel == "handback":
        assert handlers.user_prompt_submit(ups_ctx) is None
    else:
        assert handlers.post_tool(hb_ctx) is None

    assert pcg.is_armed(session_id) is False
    assert (
        pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage")) is None
    )


def test_resumed_subagent_identical_body_arms_distinct_claim_after_verdict():
    """Resuming a child via SendMessage allows a subsequent identical-body SubagentHandback to arm cleanly."""
    import handlers

    session_id = "sess-resume-identical"
    child_id = "child-resume-1"
    report_text, reason_tmpl = _valid_report_argdown("ask-res-1")

    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"description": "Initial"},
            tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
            tool="Agent",
            tool_use_id="toolu_res_spawn",
        )
    )
    # Turn 1 delivery + single-claim check + verdict
    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"message": report_text},
            tool_response={"success": True},
            tool="SubagentHandback",
            agent_id=child_id,
            tool_use_id="toolu_res_hb1",
        )
    )
    ups_res = handlers.user_prompt_submit(
        _prompt_ctx(session_id, _wrap_claude_handback(child_id, report_text))
    )
    assert ups_res is not None
    cids1 = _claims_from_notice(ups_res)
    assert len(cids1) == 1
    cid1 = cids1[0]
    assert (
        pcv.record_verdict(
            session_id=session_id,
            claim_id=cid1,
            verdict="PASS",
            reason=reason_tmpl.format(claim_id=cid1),
            tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        )["ok"]
        is True
    )
    assert pcg.is_armed(session_id) is False

    # Resume child cleanly via SendMessage
    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"to": child_id, "message": "[no claim]"},
            tool_response={"success": True, "resumedAgentId": child_id},
            tool="SendMessage",
            tool_use_id="toolu_res_sm",
        )
    )
    # Resumed child submits identical report text on Turn 2
    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"message": report_text},
            tool_response={"success": True},
            tool="SubagentHandback",
            agent_id=child_id,
            tool_use_id="toolu_res_hb2",
        )
    )
    assert pcg.is_armed(session_id) is True
    blk2 = pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage"))
    assert blk2 is not None
    cids2 = _claims_from_notice(blk2)
    assert len(cids2) == 1
    assert cids2[0] != cid1


def test_foreground_agent_text_dedups_silent_handback_and_notifies_once():
    """Foreground PostToolUse(Agent) carrying text promotes silent SubagentHandback notice once without twin."""
    import handlers

    session_id = "sess-fg-text-dedup"
    child_id = "child-fg-text"
    report_text, reason_tmpl = _valid_report_argdown("ask-fg-text")

    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"description": "FG task"},
                tool_response={"status": "async_launched", "agentId": child_id},
                tool="Agent",
                tool_use_id="toolu_fg_pre",
            )
        )
        is None
    )
    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"message": report_text},
                tool_response={"success": True},
                tool="SubagentHandback",
                agent_id=child_id,
                tool_use_id="toolu_fg_hb",
            )
        )
        is None
    )

    fg_res = handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"description": "FG task"},
            tool_response={
                "status": "completed",
                "agentId": child_id,
                "content": [{"type": "text", "text": report_text}],
            },
            tool="Agent",
            tool_use_id="toolu_fg_ret",
        )
    )
    assert fg_res is not None
    cids = _claims_from_notice(fg_res)
    assert len(cids) == 1
    cid = cids[0]

    # Duplicate prompt arrival for already-notified active claim does not double-emit or double-arm
    assert (
        handlers.user_prompt_submit(
            _prompt_ctx(session_id, _wrap_claude_handback(child_id, report_text))
        )
        is None
    )
    blk = pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage"))
    assert blk is not None and _claims_from_notice(blk) == [cid]

    assert (
        pcv.record_verdict(
            session_id=session_id,
            claim_id=cid,
            verdict="PASS",
            reason=reason_tmpl.format(claim_id=cid),
            tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        )["ok"]
        is True
    )
    assert pcg.is_armed(session_id) is False


def test_failed_subagent_handback_leaves_caller_unarmed_until_retry_succeeds():
    """Failed PostToolUse(SubagentHandback) leaves caller unarmed; successful retry arms cleanly."""
    import handlers

    session_id = "sess-failed-hb"
    child_id = "child-fail-1"
    report_text, _ = _valid_report_argdown("ask-fail")

    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"description": "Fail test"},
            tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
            tool="Agent",
            tool_use_id="toolu_fail_spawn",
        )
    )
    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"message": report_text},
                tool_response={"success": False, "error": "permission denied"},
                tool="SubagentHandback",
                agent_id=child_id,
                tool_use_id="toolu_fail_hb",
            )
        )
        is None
    )
    assert pcg.is_armed(session_id) is False
    assert (
        pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage")) is None
    )

    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"message": report_text},
                tool_response={"success": True, "message": "Report delivered."},
                tool="SubagentHandback",
                agent_id=child_id,
                tool_use_id="toolu_ok_hb",
            )
        )
        is None
    )
    assert pcg.is_armed(session_id) is True


def test_failed_sendmessage_does_not_arm_peer_subagent():
    """Failed peer PostToolUse(SendMessage) must not silently arm target subagent slot."""
    import handlers

    session_id = "sess-failed-peer-sm"
    sender_id = "sub-sender-fail"
    target_id = "sub-target-fail"
    report_text, _ = _valid_report_argdown("ask-sm-fail")

    for cid in (sender_id, target_id):
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"description": f"spawn {cid}"},
                tool_response={"isAsync": True, "status": "async_launched", "agentId": cid},
                tool="Agent",
                tool_use_id=f"toolu_spawn_{cid}",
            )
        )

    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"to": target_id, "message": report_text},
                tool_response={"success": False, "is_error": True},
                tool="SendMessage",
                agent_id=sender_id,
                tool_use_id="toolu_failed_peer_sm",
            )
        )
        is None
    )
    assert pcg.is_armed(session_id, agent_id=target_id) is False


def test_failed_sendmessage_does_not_supersede_prior_disarmed_claim():
    """Failed caller SendMessage must not supersede prior disarmed claim to let delayed twins re-arm."""
    import handlers

    session_id = "sess-failed-sm-supersede"
    child_id = "child-sm-sup"
    report_text, reason_tmpl = _valid_report_argdown("ask-sm-sup")

    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"description": "Worker"},
            tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
            tool="Agent",
            tool_use_id="toolu_sm_sup_spawn",
        )
    )
    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"message": report_text},
            tool_response={"success": True},
            tool="SubagentHandback",
            agent_id=child_id,
            tool_use_id="toolu_sm_sup_hb1",
        )
    )
    blk = pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage"))
    assert blk is not None
    cid1 = _claims_from_notice(blk)[0]
    assert (
        pcv.record_verdict(
            session_id=session_id,
            claim_id=cid1,
            verdict="PASS",
            reason=reason_tmpl.format(claim_id=cid1),
            tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        )["ok"]
        is True
    )

    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"to": child_id, "message": "follow-up"},
                tool_response={"success": False, "is_error": True},
                tool="SendMessage",
                tool_use_id="toolu_sm_sup_fail",
            )
        )
        is None
    )
    # Delayed twin arrival still must not re-arm when SendMessage failed
    assert (
        handlers.user_prompt_submit(
            _prompt_ctx(session_id, _wrap_claude_handback(child_id, report_text))
        )
        is None
    )
    assert pcg.is_armed(session_id) is False


def test_task_notification_waiting_pointer_leaves_gate_unarmed():
    """Interim <task-notification> waiting on SubagentHandback leaves gate unarmed."""
    import handlers

    waiting_notif = (
        "<task-notification>\n"
        "<task-id>agent-wait-1</task-id>\n"
        "<status>running</status>\n"
        "<result>This agent has not reported yet: it is waiting on its own background work "
        "and will deliver its report through SubagentHandback when that finishes.</result>\n"
        "</task-notification>"
    )
    assert handlers.user_prompt_submit(_prompt_ctx("sess-notif-wait", waiting_notif)) is None
    assert pcg.is_armed("sess-notif-wait") is False


def test_task_notification_long_sender_delivered_pointer_leaves_gate_unarmed():
    """<task-notification> delivered SubagentHandback pointer with long sender leaves gate unarmed."""
    import handlers

    long_sender = "worker-" + ("x" * 150)
    long_delivered_notif = (
        "<task-notification>\n"
        "<task-id>agent-long-1</task-id>\n"
        "<status>completed</status>\n"
        f'<result>This agent\'s report was delivered to you as a message from "{long_sender}" '
        "(its SubagentHandback call). Read it there; it is not repeated here.</result>\n"
        "</task-notification>"
    )
    assert handlers.user_prompt_submit(_prompt_ctx("sess-notif-long", long_delivered_notif)) is None
    assert pcg.is_armed("sess-notif-long") is False


def test_agent_message_quoting_pointer_prose_still_arms_gate():
    """Genuine report inside <agent-message> quoting pointer prose still arms the gate."""
    import handlers

    quoted_report = (
        "Root cause report: `<task-notification>` emitted "
        "`This agent has not reported yet: it is waiting on its own background work and will "
        "deliver its report through SubagentHandback when that finishes.` instead of a report."
    )
    quoted_msg = _wrap_claude_handback("child-reporter", quoted_report, with_harness_warning=False)
    res = handlers.user_prompt_submit(_prompt_ctx("sess-quote-pointer", quoted_msg))
    assert res is not None and len(_claims_from_notice(res)) == 1
    assert pcg.is_armed("sess-quote-pointer") is True


def test_repeated_task_notification_same_sender_suppressed_until_resume():
    """Repeated <task-notification> from same task-id does not re-arm after verdict until resumed."""
    import handlers

    session_id = "sess-notif-repeat"
    task_id = "agent-bg-repeat"
    report_text, reason_tmpl = _valid_report_argdown("ask-notif-rep")
    notif = (
        f"<task-notification>\n<task-id>{task_id}</task-id>\n<status>completed</status>\n"
        f"<result>{report_text}</result>\n</task-notification>"
    )

    first_res = handlers.user_prompt_submit(_prompt_ctx(session_id, notif))
    assert first_res is not None
    cid1 = _claims_from_notice(first_res)[0]
    assert (
        pcv.record_verdict(
            session_id=session_id,
            claim_id=cid1,
            verdict="PASS",
            reason=reason_tmpl.format(claim_id=cid1),
            tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        )["ok"]
        is True
    )

    assert handlers.user_prompt_submit(_prompt_ctx(session_id, notif)) is None
    assert pcg.is_armed(session_id) is False

    assert (
        handlers.post_tool(
            _post_tool_ctx_for(
                session_id,
                tool_input={"description": "Resume bg", "resume": task_id},
                tool_response={"isAsync": True, "status": "async_launched", "agentId": task_id},
                tool="Agent",
                tool_use_id="toolu_resume_bg",
            )
        )
        is None
    )
    second_res = handlers.user_prompt_submit(_prompt_ctx(session_id, notif))
    assert second_res is not None
    cids2 = _claims_from_notice(second_res)
    assert len(cids2) == 1 and cids2[0] != cid1
    assert pcg.is_armed(session_id) is True


def test_named_subagent_agent_message_dedups_with_handback_via_registered_name():
    """Named subagent <agent-message from='name'> matches SubagentHandback agentId via spawn registry."""
    import handlers

    session_id = "sess-named-dedup"
    child_id = "agent-named-uuid"
    child_name = "worker-alpha"
    report_text, reason_tmpl = _valid_report_argdown("ask-named")

    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"description": "Named worker", "name": child_name},
            tool_response={"isAsync": True, "status": "async_launched", "agentId": child_id},
            tool="Agent",
            tool_use_id="toolu_named_spawn",
        )
    )
    handlers.post_tool(
        _post_tool_ctx_for(
            session_id,
            tool_input={"message": report_text},
            tool_response={"success": True},
            tool="SubagentHandback",
            agent_id=child_id,
            tool_use_id="toolu_named_hb",
        )
    )

    ups_res = handlers.user_prompt_submit(
        _prompt_ctx(
            session_id, _wrap_claude_handback(child_name, report_text, with_harness_warning=False)
        )
    )
    assert ups_res is not None
    notice_cids = _claims_from_notice(ups_res)
    assert len(notice_cids) == 1
    assert (
        pcv.record_verdict(
            session_id=session_id,
            claim_id=notice_cids[0],
            verdict="PASS",
            reason=reason_tmpl.format(claim_id=notice_cids[0]),
            tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        )["ok"]
        is True
    )
    assert pcg.is_armed(session_id) is False


def test_multi_claim_block_lists_all_pending_claims_and_policy_markers():
    """Multi-claim arm and block notices use consistent count labeling and list every claim command."""
    import handlers

    session_id = "sess-multi-blk"
    batch_res = handlers.post_tool_batch(
        dispatch.HookContext(
            client="claude",
            event="PostToolBatch",
            session_id=session_id,
            agent_type="ida:ida",
            hooks_dir=_HOOKS_DIR,
            tool_calls=(
                {
                    "tool_name": "Agent",
                    "tool_use_id": "call-m1",
                    "tool_input": {"description": "Audit auth module"},
                    "tool_response": {
                        "status": "completed",
                        "content": [{"type": "text", "text": "Auth finding one."}],
                    },
                },
                {
                    "tool_name": "Agent",
                    "tool_use_id": "call-m2",
                    "tool_input": {"description": "Verify hook routing"},
                    "tool_response": {
                        "status": "completed",
                        "content": [{"type": "text", "text": "Hook finding two."}],
                    },
                },
            ),
        )
    )
    assert batch_res is not None
    expected_label = "2 claims (Audit auth module, Verify hook routing)"
    assert expected_label in batch_res.inject_text
    assert batch_res.user_text is None

    blk = pcg.premise_check_handler(_agent_dispatch_ctx_for(session_id, tool="SendMessage"))
    assert blk is not None and blk.kind == dispatch.Kind.REFUSE
    lines = blk.inject_text.splitlines()
    assert lines[0].startswith(_POLICY["premise_check"]["armed_indicator"])
    assert expected_label in lines[0]
    assert blk.user_text is None
    assert _claims_from_notice(blk) == ["Audit auth module", "Verify hook routing"]


@pytest.mark.parametrize(
    ("event", "tool", "expected_desc"),
    [
        ("Stop", "", "finishing the task or contacting the user/teammates"),
        ("PreToolUse", "Agent", "dispatching a subagent"),
        ("PreToolUse", "Task", "dispatching a subagent"),
        ("PreToolUse", "invoke_subagent", "dispatching a subagent"),
        ("PreToolUse", "SendMessage", "sending an agent message"),
        ("PreToolUse", "send_message", "sending an agent message"),
        ("PreToolUse", "mcp__services__send_message", "sending an agent message"),
        ("PreToolUse", "SubagentHandback", "delivering a subagent handback"),
        ("PreToolUse", "subagent_handback", "delivering a subagent handback"),
        ("PreToolUse", "mcp__ida__SubagentHandback", "delivering a subagent handback"),
        ("PreToolUse", "Dump", "handing over the session"),
        ("PreToolUse", "dump", "handing over the session"),
        ("PreToolUse", "AskUserQuestion", "asking the user a question"),
        ("PreToolUse", "AskQuestion", "asking the user a question"),
        ("PreToolUse", "ask_user_question", "asking the user a question"),
        ("PreToolUse", "ask_question", "asking the user a question"),
        ("PreToolUse", "ask_user", "asking the user a question"),
        ("PreToolUse", "reply", "sending a channel reply"),
        ("PreToolUse", "telegram_reply", "sending a channel reply"),
        ("PreToolUse", "telegram_send_message", "sending a channel reply"),
        ("PreToolUse", "discord_reply", "sending a channel reply"),
        ("PreToolUse", "discord_send_message", "sending a channel reply"),
    ],
)
def test_hearsay_handler_derives_action_desc_from_blocked_tool(
    event: str, tool: str, expected_desc: str
):
    """hearsay_handler describes the blocked tool action instead of hardcoding subagent dispatch."""
    session_id = f"sess-action-{event}-{tool or 'stop'}"
    claim_id = "claim-act-01"
    pcg.arm(session_id, claim_id=claim_id, judged_text="pending")

    ctx = dispatch.HookContext(
        client="claude",
        event=event,
        tool=tool,
        session_id=session_id,
        agent_type="ida:ida",
        hooks_dir=_HOOKS_DIR,
    )
    res = pcg.premise_check_handler(ctx)
    assert res is not None
    expected_kind = dispatch.Kind.BLOCK if event == "Stop" else dispatch.Kind.REFUSE
    assert res.kind is expected_kind
    assert res.user_text is None
    assert f"blocks {expected_desc};" in res.inject_text
    assert "dispatching another subagent or message" not in res.inject_text


def test_hearsay_handler_unknown_gated_tool_uses_generic_action_desc(monkeypatch):
    """Unmapped gated tools receive an explicit generic description, not subagent-dispatch text."""
    session_id = "sess-unknown-tool"
    claim_id = "claim-unk-01"
    pcg.arm(session_id, claim_id=claim_id, judged_text="pending")

    monkeypatch.setattr(hg, "_GATED_TOOLS", frozenset({*hg._GATED_TOOLS, "MysteryGatedTool"}))
    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="MysteryGatedTool",
        session_id=session_id,
        agent_type="ida:ida",
        hooks_dir=_HOOKS_DIR,
    )
    res = pcg.premise_check_handler(ctx)
    assert res is not None and res.kind is dispatch.Kind.REFUSE
    assert res.user_text is None
    assert "blocks performing this action;" in res.inject_text
    assert "dispatching another subagent or message" not in res.inject_text
    assert "dispatching a subagent" not in res.inject_text


def test_hearsay_handler_multi_claim_and_warn_mode_preserve_tool_action_desc_and_agent_only(
    monkeypatch,
):
    """Multi-claim and warn-mode blocks derive tool action_desc and emit zero user_text."""
    session_id = "sess-multi-warn"
    pcg.arm(session_id, claim_id="claim-m1", judged_text="report 1")
    pcg.arm(session_id, claim_id="claim-m2", judged_text="report 2")

    refuse_res = pcg.premise_check_handler(
        dispatch.HookContext(
            client="claude",
            event="PreToolUse",
            tool="Dump",
            session_id=session_id,
            agent_type="ida:ida",
            hooks_dir=_HOOKS_DIR,
        )
    )
    assert refuse_res is not None and refuse_res.kind is dispatch.Kind.REFUSE
    assert refuse_res.user_text is None
    assert "blocks handing over the session;" in refuse_res.inject_text
    assert "2 claims (claim-m1, claim-m2)" in refuse_res.inject_text

    monkeypatch.setenv("PREMISE_CHECK_GATE_MODE", "warn")
    warn_res = pcg.premise_check_handler(
        dispatch.HookContext(
            client="claude",
            event="PreToolUse",
            tool="AskUserQuestion",
            session_id=session_id,
            agent_type="ida:ida",
            hooks_dir=_HOOKS_DIR,
        )
    )
    assert warn_res is not None and warn_res.kind is dispatch.Kind.ADVISE
    assert warn_res.user_text is None
    assert "blocks asking the user a question;" in warn_res.inject_text


def test_subagent_start_gate_notice_is_agent_only_with_pending_claims():
    """SubagentStart gate reminder injects --agent hint and armed claims with zero user_text."""
    session_id = "sess-sub-start-agent-only"
    sub_id = "sub-agent-99"
    pcg.arm(session_id, claim_id="claim-sub-1", judged_text="pending", agent_id=sub_id)

    ctx = dispatch.HookContext(
        client="claude",
        event="SubagentStart",
        session_id=session_id,
        agent_id=sub_id,
        agent_type="ida:james",
        hooks_dir=_HOOKS_DIR,
        raw={"agent_id": sub_id},
    )
    res = hg.subagent_start_gate_notice(ctx)
    assert res is not None and res.kind is dispatch.Kind.ADVISE
    assert res.user_text is None
    assert f"--agent {sub_id}" in res.inject_text
    assert "claim-sub-1" in res.inject_text
