"""Tests for the premise-check verdict script and its gate.

Covers:
1. A verdict is one token (PASS, REVISE, FAIL) plus a free-text reason; the
   reason may come inline, from a file, or from stdin. A malformed verdict
   never disarms the gate.
2. record_verdict() emits a TOOL span (via a stubbed claude_code_tracer)
   carrying the token and the reason, and disarms the gate.
3. record_verdict() still disarms when the tracer is unconfigured, but reports
   span_emitted=False -- telemetry and "the check ran" are separable.
4. premise_check_handler refuses the next dispatch, message or stop while
   armed, allows it once disarmed, and respects mode=warn/off and overrides.
5. premise_check_arm arms only for the gated agents (ida, sara): after a
   dispatch batch, or on an incoming peer report -- never on the user's own
   messages.
"""

from __future__ import annotations

import importlib.util
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
        tracer_mod=_StubTracer(config=None),
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
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: None)
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
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: None)
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
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: None)

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


def test_cli_rejects_free_text_as_the_verdict(monkeypatch):
    session_id = "sess-cli-bad"
    pcg.arm(session_id, claim_id="claim-1")
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: None)

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


# ---------------------------------------------------------------------------
# 4. Telemetry and "the check ran" are separable
# ---------------------------------------------------------------------------


def test_record_verdict_disarms_even_when_tracer_unconfigured():
    session_id = "sess-unconfigured"
    pcg.arm(session_id, claim_id="claim-3")

    tracer = _StubTracer(config=None)  # discover_config() -> None, silent no-op

    result = pcv.record_verdict(
        session_id=session_id, claim_id="claim-3", verdict="PASS", reason="r", tracer_mod=tracer
    )

    assert result["span_emitted"] is False
    assert result["span_error"] is None
    assert tracer.exported == []
    assert pcg.is_armed(session_id) is False  # still disarmed: the check ran locally


def test_record_verdict_reports_unacknowledged_export_as_not_emitted():
    session_id = "sess-export-failed"
    pcg.arm(session_id, claim_id="claim-4")

    tracer = _StubTracer(config={"endpoint": "http://collector:4317"}, export_ok=False)

    result = pcv.record_verdict(
        session_id=session_id, claim_id="claim-4", verdict="PASS", reason="r", tracer_mod=tracer
    )

    assert len(tracer.exported) == 1  # the export was attempted
    assert result["span_emitted"] is False
    assert pcg.is_armed(session_id) is False  # the check still ran locally


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


# ---------------------------------------------------------------------------
# 6. Arming the check on PostToolBatch
# ---------------------------------------------------------------------------


def test_arm_handler_fires_on_agent_batch_for_scoped_agent():
    session_id = "sess-open-1"
    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolBatch",
        session_id=session_id,
        agent_type="ida:ida",
        tool_calls=({"tool_name": "Agent", "tool_input": {"description": "verify the claim"}},),
    )
    assert pcg.premise_check_arm(ctx) is None
    assert pcg.is_armed(session_id) is True
    assert pcg.get_state(session_id)["claim_id"] == "verify the claim"


def test_arm_handler_ignores_non_agent_batch():
    session_id = "sess-open-2"
    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolBatch",
        session_id=session_id,
        agent_type="ida:ida",
        tool_calls=({"tool_name": "Bash"},),
    )
    pcg.premise_check_arm(ctx)
    assert pcg.is_armed(session_id) is False


def test_arm_handler_ignores_non_scoped_agent_type():
    session_id = "sess-open-3"
    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolBatch",
        session_id=session_id,
        agent_type="aops:james",
        tool_calls=({"tool_name": "Agent"},),
    )
    pcg.premise_check_arm(ctx)
    assert pcg.is_armed(session_id) is False


# ---------------------------------------------------------------------------
# End-to-end: full claim -> refusal -> verdict -> allowed cycle
# ---------------------------------------------------------------------------


def test_end_to_end_claim_blocks_next_dispatch_until_verdicted():
    session_id = "sess-e2e"

    # A subagent is called by Ida.
    batch_ctx = dispatch.HookContext(
        client="claude",
        event="PostToolBatch",
        session_id=session_id,
        agent_type="ida:ida",
        tool_calls=({"tool_name": "Agent", "tool_input": {"description": "researched X"}},),
    )
    pcg.premise_check_arm(batch_ctx)
    assert pcg.is_armed(session_id) is True

    # Dispatching another subagent before the verdict is refused.
    res = pcg.premise_check_handler(_agent_dispatch_ctx(session_id))
    assert res is not None and res.kind == dispatch.Kind.REFUSE

    # The verdict script runs and disarms the check.
    pcv.record_verdict(
        session_id=session_id,
        claim_id="researched X",
        verdict="PASS",
        reason="The report's evidence supports its conclusion.",
        tracer_mod=_StubTracer(config=None),
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


@pytest.mark.parametrize(
    "prompt",
    [
        '<channel source="plugin:telegram:telegram" chat_id="1" user="nic">do the thing</channel>',
        "can you check the release?",
        "",
    ],
)
def test_arm_handler_ignores_the_users_own_messages(prompt):
    session_id = "sess-user"
    pcg.premise_check_arm(_prompt_ctx(session_id, prompt))
    assert pcg.is_armed(session_id) is False


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
