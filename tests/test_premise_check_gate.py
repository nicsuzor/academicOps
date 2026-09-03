"""Tests for the forced per-claim logic-check verdict script and its gate
(task_db1da567, epic aops_premise_check_gate).

Covers:
1. The logic-check sequence is parsed live from hearsay.md -- six questions,
   in order -- so "same number of questions, same order" holds by construction.
2. record_verdict() rejects a mismatched answer count and never closes the
   gate on a malformed verdict.
3. record_verdict() emits a TOOL span (via a stubbed claude_code_tracer) with
   one attribute per logic-check question, and closes the gate.
4. record_verdict() still closes the gate (verdict-ran-locally) when the
   tracer is unconfigured, but reports span_emitted=False -- telemetry and
   "the check ran" are separable.
5. The forcing mechanism: premise_check_gate_handler refuses the next
   Agent/Task dispatch while the gate is open, allows it once closed, and
   respects mode=warn/off and the override env vars.
6. premise_check_open_gate opens the gate only for the scoped agent types,
   and only when an Agent call is present in the batch.
7. Both handlers are wired into handlers.py's HANDLERS mapping.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugins" / "aops"
_HOOKS_DIR = _PLUGIN_ROOT / "hooks"
_LIB_HOOKS_DIR = _REPO_ROOT / "lib" / "hooks"

for p in (_LIB_HOOKS_DIR, _HOOKS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

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

    def __init__(self, config: dict[str, Any] | None):
        self._config = config
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


# ---------------------------------------------------------------------------
# 1. Question parsing
# ---------------------------------------------------------------------------


def test_load_logic_check_questions():
    questions = pcv.load_logic_check_questions()
    assert len(questions) == 6
    assert questions[0].startswith("What is the subject of this claim")
    assert questions[1].startswith("Does the evidence admit more than one explanation")
    assert questions[5].startswith("What does the conclusion depend on")


# ---------------------------------------------------------------------------
# 2. Answer-count validation
# ---------------------------------------------------------------------------


def test_record_verdict_rejects_wrong_answer_count():
    session_id = "sess-mismatch"
    pcg.arm(session_id, claim_id="claim-1")

    with pytest.raises(ValueError, match="expected 6 answers"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id="claim-1",
            answers=["only", "two"],
            tracer_mod=_StubTracer(config={"endpoint": "http://x"}),
        )

    # Malformed verdict must not disarm.
    assert pcg.is_armed(session_id) is True


# ---------------------------------------------------------------------------
# 3. Span emission — one attribute per question
# ---------------------------------------------------------------------------


def test_record_verdict_emits_one_attribute_per_question_and_disarms():
    session_id = "sess-emit"
    pcg.arm(session_id, claim_id="claim-2")

    answers = [f"answer {i}" for i in range(6)]
    tracer = _StubTracer(
        config={"endpoint": "http://collector:4317", "project_name": "academicOps"}
    )

    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="claim-2",
        answers=answers,
        tracer_mod=tracer,
    )

    assert result["ok"] is True
    assert result["span_emitted"] is True
    assert result["question_count"] == 6

    assert len(tracer.exported) == 1
    spans = tracer.exported[0]["spans"]
    assert len(spans) == 1
    attrs = spans[0]["attributes"]
    for i in range(1, 7):
        assert attrs[f"premise_check.q{i}.answer"] == answers[i - 1]
        assert f"premise_check.q{i}.question" in attrs
    assert attrs["premise_check.claim_id"] == "claim-2"
    assert attrs["premise_check.question_count"] == 6

    # Disarmed.
    assert pcg.is_armed(session_id) is False
    state = pcg.get_state(session_id)
    assert state["last_verdict"]["claim_id"] == "claim-2"
    assert state["last_verdict"]["answers"] == answers


# ---------------------------------------------------------------------------
# 4. Telemetry and "the check ran" are separable
# ---------------------------------------------------------------------------


def test_record_verdict_disarms_even_when_tracer_unconfigured():
    session_id = "sess-unconfigured"
    pcg.arm(session_id, claim_id="claim-3")

    answers = [f"answer {i}" for i in range(6)]
    tracer = _StubTracer(config=None)  # discover_config() -> None, silent no-op

    result = pcv.record_verdict(
        session_id=session_id,
        claim_id="claim-3",
        answers=answers,
        tracer_mod=tracer,
    )

    assert result["span_emitted"] is False
    assert result["span_error"] is None
    assert tracer.exported == []
    assert pcg.is_armed(session_id) is False  # still disarmed: the check ran locally


# ---------------------------------------------------------------------------
# 5. The forcing mechanism
# ---------------------------------------------------------------------------


def _agent_dispatch_ctx(session_id: str, agent_type: str = "aops:ida") -> dispatch.HookContext:
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
    pcg.disarm(session_id, "claim-5", ["q"] * 6, ["a"] * 6)

    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None


def test_handler_ignores_non_gated_tool():
    session_id = "sess-gate-3"
    pcg.arm(session_id, claim_id="claim-6")

    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        session_id=session_id,
        agent_type="aops:ida",
    )
    assert pcg.premise_check_handler(ctx) is None


def test_handler_ignores_non_gated_agent_type():
    session_id = "sess-gate-4"
    pcg.arm(session_id, claim_id="claim-7")

    ctx = _agent_dispatch_ctx(session_id, agent_type="orchestrate:james")
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
        agent_type="aops:ida",
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
        agent_type="aops:ida",
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
        agent_type="orchestrate:james",
        tool_calls=({"tool_name": "Agent"},),
    )
    pcg.premise_check_arm(ctx)
    assert pcg.is_armed(session_id) is False


# ---------------------------------------------------------------------------
# 7. Wiring
# ---------------------------------------------------------------------------


def test_handlers_registered_in_handlers_py():
    handlers = _load_plugin_module("aops_handlers_premise_test", _HOOKS_DIR / "handlers.py")
    assert handlers.premise_check_handler in handlers.HANDLERS["PreToolUse"]
    assert handlers.premise_check_arm in handlers.HANDLERS["PostToolBatch"]


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
        agent_type="aops:ida",
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
        answers=[f"a{i}" for i in range(6)],
        tracer_mod=_StubTracer(config=None),
    )

    # Now the dispatch is permitted.
    assert pcg.is_armed(session_id) is False
    assert pcg.premise_check_handler(_agent_dispatch_ctx(session_id)) is None
