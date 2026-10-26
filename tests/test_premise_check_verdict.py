"""Tests for premise-check verdict recording on task-record handbacks and consistency checks."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugins" / "ida"
_HOOKS_DIR = _PLUGIN_ROOT / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import hearsay_gate as hg
import premise_check_verdict as pcv
import report_argument as ra

_ANY_BASIS = ra.load_vocabulary().basis[0].phrase


class _StubTracer:
    """Minimal stub for claude_code_tracer."""

    def __init__(self, config: dict[str, Any] | None = None, export_ok: bool = True):
        self._config = config or {"endpoint": "http://localhost:4317"}
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


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate_state"))
    monkeypatch.setenv("AOPS_SESSION_ID", "test-verdict-session")
    yield


def test_task_record_handback_refusal_when_unarmed_reproduction():
    """AC1: Reproduce the refusal for a verdict on a handback read from a task record when unarmed.

    When a supervisor evaluates a task-record handback without an incoming message/notification
    arming the gate, record_verdict previously refused with 'no premise check is currently armed'.
    """
    tracer = _StubTracer()
    session_id = "test-unarmed-session"
    task_id = "aops_2bc1b139"

    # Confirm gate is unarmed for this session
    assert not hg.is_armed(session_id)

    # Calling record_verdict on a task record when unarmed raises before fix
    reason = (
        f"Judged: {task_id}; asks tg-1\n"
        "Valid: (2) fails #missing -- condition not met\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: tg-1 ← (2)\n"
        "Sufficient: (2) material; low-stakes\n"
        "Waived: block -- task handback review\n"
        "Relay: none"
    )

    # This test directly exercises recording against a task ID on an unarmed session
    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason,
        tracer_mod=tracer,
    )
    assert res["ok"] is True
    assert res["claim_id"] == task_id
    assert res["verification_id"].startswith("verdict-")


def test_task_record_handback_verdict_records_with_task_id_and_verification_id():
    """AC2: A verdict on a task-record handback records with task id as claim id and a verification id."""
    tracer = _StubTracer()
    session_id = "supervisor-session-1"
    task_id = "aops_8830b768"

    reason = (
        f"Judged: {task_id}; asks aops_8830b768/AC1\n"
        "Valid: (2) fails #undercut -- defect observed in runtime trace\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: aops_8830b768/AC1 ← (2)\n"
        "Sufficient: (2) material; low-stakes\n"
        "Waived: block -- reviewed from task record\n"
        "Relay: none"
    )

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason,
        title="task record check",
        tracer_mod=tracer,
    )

    assert res["ok"] is True
    assert res["claim_id"] == task_id
    assert res["verdict"] == "REVISE"
    assert res["verification_id"].startswith("verdict-")
    assert "task-record-check" in res["verification_id"]
    assert len(tracer.exported) == 1
    span = tracer.exported[0]["spans"][0]
    assert span["attributes"]["premise_check.claim_id"] == task_id
    assert span["attributes"]["premise_check.verification_id"] == res["verification_id"]
    assert span["attributes"]["premise_check.verdict"] == "REVISE"


def test_non_task_claim_refused_when_unarmed():
    """Non-task claim ids still refuse with 'no premise check is currently armed' when unarmed."""
    tracer = _StubTracer()
    session_id = "unarmed-non-task"
    claim_id = "claim-12345678"

    with pytest.raises(ValueError, match="no premise check is currently armed"):
        pcv.record_verdict(
            session_id=session_id,
            claim_id=claim_id,
            verdict="REVISE",
            reason="some reason",
            tracer_mod=tracer,
        )


def test_revise_refused_when_valid_entries_all_hold_and_no_unanswered_ask():
    """AC5: premise_check_verdict.py refuses REVISE when Valid: is non-empty and all entries hold with no unanswered ask."""
    tracer = _StubTracer()
    session_id = "s-revise-check"
    task_id = "aops_2bc1b139"

    reason_all_hold = (
        f"Judged: {task_id}; asks tg-1\n"
        "Valid: (1) holds -- the rule yields (1)\n"
        "Valid: (2) holds -- conclusion follows\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: tg-1 ← (2)\n"
        "Sufficient: (2) material; low-stakes\n"
        "Waived: block -- reviewed\n"
        "Relay: none"
    )

    with pytest.raises(
        ValueError, match=r"REVISE refused.*requires at least one failing inference step"
    ):
        pcv.record_verdict(
            session_id=session_id,
            claim_id=task_id,
            verdict="REVISE",
            reason=reason_all_hold,
            tracer_mod=tracer,
        )


def test_fail_refused_when_valid_entries_all_hold_and_no_unanswered_ask():
    """AC5: premise_check_verdict.py refuses FAIL when Valid: is non-empty and all entries hold with no unanswered ask."""
    tracer = _StubTracer()
    session_id = "s-fail-check"
    task_id = "aops_2bc1b139"

    reason_all_hold = (
        f"Judged: {task_id}; asks tg-1\n"
        "Valid: (1) holds -- the rule yields (1)\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: tg-1 ← (1)\n"
        "Sufficient: (1) material; low-stakes\n"
        "Waived: block -- reviewed\n"
        "Relay: none"
    )

    with pytest.raises(
        ValueError, match=r"FAIL refused.*requires at least one failing inference step"
    ):
        pcv.record_verdict(
            session_id=session_id,
            claim_id=task_id,
            verdict="FAIL",
            reason=reason_all_hold,
            tracer_mod=tracer,
        )


def test_revise_allowed_when_valid_has_failing_step():
    """AC5: REVISE is accepted when at least one Valid entry fails."""
    tracer = _StubTracer()
    session_id = "s-revise-fails"
    task_id = "aops_2bc1b139"

    reason_with_failure = (
        f"Judged: {task_id}; asks tg-1\n"
        "Valid: (1) holds -- step holds\n"
        "Valid: (2) fails #missing -- condition not proven\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: tg-1 ← (2)\n"
        "Sufficient: (2) material; low-stakes\n"
        "Waived: block -- reviewed\n"
        "Relay: none"
    )

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason_with_failure,
        tracer_mod=tracer,
    )
    assert res["ok"] is True
    assert res["verdict"] == "REVISE"


def test_revise_allowed_when_ask_unanswered():
    """AC5: REVISE is accepted when Valid entries hold but an ask is unanswered."""
    tracer = _StubTracer()
    session_id = "s-revise-unans"
    task_id = "aops_2bc1b139"

    reason_unanswered_answered_key = (
        f"Judged: {task_id}; asks tg-1\n"
        "Valid: (1) holds -- step holds\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: tg-1 unanswered\n"
        "Sufficient: (1) material; low-stakes\n"
        "Waived: block -- reviewed\n"
        "Relay: none"
    )

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason_unanswered_answered_key,
        tracer_mod=tracer,
    )
    assert res["ok"] is True
    assert res["verdict"] == "REVISE"

    # Also test Ask: tg-1 -> unanswered syntax
    reason_ask_arrow = (
        f"Judged: {task_id}; asks tg-1\n"
        "Valid: (1) holds -- step holds\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Ask: tg-1 -> unanswered\n"
        "Sufficient: (1) material; low-stakes\n"
        "Waived: block -- reviewed\n"
        "Relay: none"
    )
    res2 = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason_ask_arrow,
        tracer_mod=tracer,
    )
    assert res2["ok"] is True


def test_revise_allowed_when_valid_empty():
    """AC5: REVISE is accepted when Valid is empty (e.g. absent block return)."""
    tracer = _StubTracer()
    session_id = "s-revise-no-valid"
    task_id = "aops_2bc1b139"

    reason_no_valid = "no argument supplied; please supply argument block"

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason_no_valid,
        tracer_mod=tracer,
    )
    assert res["ok"] is True
    assert res["verdict"] == "REVISE"
