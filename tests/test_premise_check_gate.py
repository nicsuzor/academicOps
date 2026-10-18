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
import shlex
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugins" / "ida"
_HOOKS_DIR = _PLUGIN_ROOT / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import dispatch
import premise_check_gate as pcg
import premise_check_verdict as pcv


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

    def __init__(self, config: dict[str, Any] | None, export_ok: bool = True):
        self._config = config
        self._export_ok = export_ok
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

    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="claim-1",
        verdict=token,
        reason="The cited diff supports each claim; the conclusion answers the ask.",
        tracer_mod=tracer,
    )

    assert result["ok"] is True
    assert result["verdict"] == token
    assert result["disarmed"] is True
    attrs = tracer.exported[0]["spans"][0]["attributes"]
    assert attrs["premise_check.verdict"] == token
    assert "conclusion answers the ask" in attrs["premise_check.reason"]
    assert attrs["premise_check.claim_id"] == "claim-1"
    assert pcg.is_armed(session_id) is False
    last = pcg.get_state(session_id)["last_verdict"]
    assert last["verdict"] == token
    assert "conclusion answers the ask" in last["reason"]


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
    reason = "Worker says it ran git push to the branch; the PR link backs that."
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


def test_cli_accepts_inline_reason(monkeypatch):
    session_id = "sess-cli-inline"
    pcg.arm(session_id, claim_id="claim-1")
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )

    rc = pcv.main(
        [
            "--report",
            "claim-1",
            "--verdict",
            "REVISE",
            "--reason",
            "No evidence for AC2.",
            "--session",
            session_id,
        ]
    )

    assert rc == 0
    assert pcg.get_state(session_id)["last_verdict"]["reason"] == "No evidence for AC2."


def test_cli_records_verdict_with_distinct_verification_id_and_title(capsys, monkeypatch):
    import json

    session_id = "sess-cli-title"
    claim_id = "claim-3a4b5c6d"
    pcg.arm(session_id, claim_id=claim_id)
    monkeypatch.setattr(
        pcv, "_import_claude_code_tracer", lambda: _StubTracer(config={"endpoint": "http://x"})
    )

    rc = pcv.main(
        [
            "--claim",
            claim_id,
            "--verdict",
            "PASS",
            "--reason",
            "Evidence supports all claims.",
            "--title",
            "unit-tests-passed",
            "--session",
            session_id,
        ]
    )

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["claim_id"] == claim_id
    assert out["verification_id"] != claim_id
    assert out["verification_id"].startswith("verdict-")
    assert out["verification_id"].endswith("-unit-tests-passed")
    assert pcg.is_valid_id(out["verification_id"])
    assert out["verdict"] == "PASS"
    assert out["title"] == "unit-tests-passed"
    assert pcg.is_armed(session_id) is False


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


def test_record_verdict_by_id_clears_gate():
    session_id = "sess-clear-by-id"
    report_id = "report-a1b2c3d4"
    pcg.arm(session_id, claim_id=report_id)
    assert pcg.is_armed(session_id) is True

    result = pcv.record_verdict(
        session_id=session_id,
        claim_id=report_id,
        verdict="PASS",
        reason="Logic holds against the original ask.",
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    assert result["ok"] is True
    assert result["claim_id"] == report_id
    assert result["disarmed"] is True
    assert pcg.is_armed(session_id) is False


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
            session_id=session_id, claim_id="claim-3", verdict="PASS", reason="r", tracer_mod=tracer
        )

    assert tracer.exported == []
    assert pcg.is_armed(session_id) is True


def test_record_verdict_fails_and_stays_armed_on_unacknowledged_export():
    session_id = "sess-export-failed"
    pcg.arm(session_id, claim_id="claim-4")

    tracer = _StubTracer(config={"endpoint": "http://collector:4317"}, export_ok=False)

    with pytest.raises(RuntimeError, match="span export failed"):
        pcv.record_verdict(
            session_id=session_id, claim_id="claim-4", verdict="PASS", reason="r", tracer_mod=tracer
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
            "all good",
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
            "all good",
            "--session",
            session_id,
        ]
    )

    assert rc == 0
    assert pcg.is_armed(session_id) is False


def test_import_claude_code_tracer_raises_when_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "claude_code_tracer":
            raise ImportError("No module named 'claude_code_tracer'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError):
        pcv._import_claude_code_tracer()


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


def test_handler_ignores_non_gated_agent_type():
    session_id = "sess-gate-4"
    pcg.arm(session_id, claim_id="claim-7")

    ctx = _agent_dispatch_ctx(session_id, agent_type="aops:james")
    assert pcg.premise_check_handler(ctx) is None


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

_OUTGOING_CALLS = [
    ("Agent", {"description": "verify the claim"}),
    ("Agent", {"description": "verify the claim", "run_in_background": False}),
    ("Agent", {"description": "background worker", "run_in_background": True}),
    ("Task", {"description": "research X"}),
    ("invoke_subagent", {"prompt": "research X"}),
    ("SendMessage", {"to": "twin-a", "message": "status?"}),
    ("Bash", {"command": "ls"}),
]


@pytest.mark.parametrize("tool,tool_input", _OUTGOING_CALLS)
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


@pytest.mark.parametrize("tool,tool_input", _OUTGOING_CALLS)
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
# End-to-end: full claim -> refusal -> verdict -> allowed cycle
# ---------------------------------------------------------------------------


def test_end_to_end_claim_blocks_next_dispatch_until_verdicted():
    session_id = "sess-e2e"

    # A worker's report arrives at Ida.
    report_ctx = _prompt_ctx(
        session_id, '<task-notification id="researched-X">worker finished</task-notification>'
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
        reason="The report's evidence supports its conclusion.",
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
        '<cross-session-message from="twin-a">PR #12 is merged.</cross-session-message>',
        '<teammate-message teammate_id="worker">done</teammate-message>',
        "\n  <task-notification>\nworker finished\n</task-notification>",
    ],
)
def test_arm_handler_arms_on_peer_report(prompt):
    session_id = "sess-peer"
    pcg.premise_check_arm(_prompt_ctx(session_id, prompt))
    assert pcg.is_armed(session_id) is True
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert res is not None and res.kind == dispatch.Kind.REFUSE


@pytest.mark.parametrize(
    "prompt",
    [
        '<channel source="plugin:telegram:telegram" chat_id="1" user="nic">do the thing</channel>',
        "can you check the release?",
        "what does <task-notification> mean?",
        "check <cross-session-message from='twin'>",
        "",
    ],
)
def test_arm_handler_ignores_the_users_own_messages(prompt):
    session_id = "sess-user"
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
        _prompt_ctx(session_id, "<cross-session-message>report</cross-session-message>", agent_type)
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

    ctx3 = _prompt_ctx("s3", "\n  <task-notification>\nworker finished\n</task-notification>")
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
    prompt = '<cross-session-message from="twin-a">PR #12 is merged.</cross-session-message>'
    ctx = _prompt_ctx(session_id, prompt)
    claim_id = pcg._derive_claim_id(ctx)
    res = pcg.premise_check_arm(ctx)
    assert res is not None
    assert res.kind == dispatch.Kind.ADVISE
    assert len(res.inject_text.splitlines()) <= 2
    assert res.user_text is not None and len(res.user_text.splitlines()) == 1
    assert claim_id in res.inject_text
    assert "premise-check" in res.inject_text
    assert "PR #12 is merged." not in res.inject_text
    assert "PR #12 is merged." not in res.user_text
    cmd = pcg.format_verdict_command(claim_id, ctx.hooks_dir, session_id)
    assert res.inject_text.splitlines()[1] == cmd
    assert "--verdict <PASS|REVISE|FAIL>" in res.inject_text
    assert "--verdict PASS" not in res.inject_text
    assert cmd not in res.user_text


def test_handler_block_message_is_two_lines_pointing_to_skill():
    session_id = "sess-block-elements"
    claim = "claim-a1b2c3d4"
    pcg.arm(session_id, claim_id=claim)

    ctx = _agent_dispatch_ctx(session_id)
    res = pcg.premise_check_handler(ctx)
    assert res is not None
    assert res.kind == dispatch.Kind.REFUSE
    assert len(res.inject_text.splitlines()) == 2
    assert res.user_text is not None and len(res.user_text.splitlines()) == 1
    assert claim in res.inject_text
    assert "premise-check" in res.inject_text
    cmd = pcg.format_verdict_command(claim, ctx.hooks_dir, session_id)
    assert res.inject_text.splitlines()[1] == cmd
    assert "--verdict <PASS|REVISE|FAIL>" in res.inject_text
    assert "--verdict PASS" not in res.inject_text
    assert cmd not in res.user_text


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
    assert res.user_text is not None and len(res.user_text.splitlines()) == 1
    assert claim in res.inject_text
    assert "premise-check" in res.inject_text
    cmd = pcg.format_verdict_command(claim, stop_ctx.hooks_dir, session_id)
    assert res.inject_text.splitlines()[1] == cmd
    assert "--verdict PASS" not in res.inject_text


def test_format_verdict_command_resolves_runnable_script():
    cmd = pcg.format_verdict_command(claim_id="my claim with spaces")
    parts = shlex.split(cmd)
    assert parts[:3] == ["uv", "run", "--project"]
    assert parts[4] == "python3"
    assert Path(parts[3]).is_dir()
    assert (
        "--claim 'my claim with spaces'" in cmd
        or '--claim "my claim with spaces"' in cmd
        or "--report 'my claim with spaces'" in cmd
        or '--report "my claim with spaces"' in cmd
    )
    assert "--verdict <PASS|REVISE|FAIL>" in cmd
    assert "--verdict PASS" not in cmd
    assert '--reason "<why>"' in cmd
    # The script path in the command must exist on disk
    script_path = Path(parts[5])
    assert script_path.is_file(), f"script path does not exist: {script_path}"


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
        reason="Logic holds against stated premises.",
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
        reason="Downstream worker verified test suite.",
        title="worker-done",
        tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
    )
    verification_id = downstream_result["verification_id"]
    assert verification_id.startswith("verdict-")
    assert verification_id != downstream_claim

    # 2. Downstream emits a verified outgoing message carrying that verification ID
    outgoing_msg = (
        f'<cross-session-message from="worker" id="{verification_id}">'
        "Finished implementation and tests pass."
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
        reason="Supervisor verified downstream report.",
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
        run_tokens = shlex.split(
            cmd.replace("<PASS|REVISE|FAIL>", "PASS").replace(
                "<why>", f"Verified under {client} from outside cwd"
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
    run_tokens = shlex.split(
        cmd.replace("<PASS|REVISE|FAIL>", "PASS").replace(
            "<why>", "Verified relative hooks_dir resolution"
        )
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


def test_printed_command_independent_of_env_vars(monkeypatch, tmp_path):
    # Set misleading environment variables
    fake_claude = tmp_path / "fake-claude-root"
    fake_agy = tmp_path / "fake-agy-root"
    fake_plugin = tmp_path / "fake-plugin-root"
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(fake_claude))
    monkeypatch.setenv("AGY_PLUGIN_ROOT", str(fake_agy))
    monkeypatch.setenv("PLUGIN_ROOT", str(fake_plugin))

    cmd = pcg.format_verdict_command(
        claim_id="env-test-claim", hooks_dir=_HOOKS_DIR, session_id="sess-env-test"
    )
    assert str(fake_claude) not in cmd
    assert str(fake_agy) not in cmd
    assert str(fake_plugin) not in cmd

    tokens = shlex.split(cmd)
    script_tokens = [t for t in tokens if t.endswith("verdict.py")]
    assert script_tokens
    script_path = Path(script_tokens[0])
    assert script_path.is_absolute()
    assert script_path.is_file()
