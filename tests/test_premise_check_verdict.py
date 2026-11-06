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


def test_task_record_handback_verdict_records_with_construct_drift():
    """Defect tags #construct-drift and #method-gap are recognized and recorded in span attributes."""
    tracer = _StubTracer()
    session_id = "supervisor-session-construct-drift"
    task_id = "aops_8830b769"

    reason = (
        f"Judged: {task_id}; asks aops_8830b769/AC1\n"
        "Valid: (2) fails #construct-drift -- silent substitution of specified form\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: aops_8830b769/AC1 ← (2)\n"
        "Sufficient: (2) material; low-stakes\n"
        "Waived: block -- reviewed from task record\n"
        "Relay: none"
    )

    res = pcv.record_verdict(
        session_id=session_id,
        claim_id=task_id,
        verdict="REVISE",
        reason=reason,
        title="task record check construct drift",
        tracer_mod=tracer,
    )

    assert res["ok"] is True
    assert res["claim_id"] == task_id
    assert res["verdict"] == "REVISE"
    span = tracer.exported[0]["spans"][0]
    assert span["attributes"]["premise_check.defect_tags"] == ["#construct-drift"]
    assert span["attributes"]["premise_check.defect_tag_count"] == 1


def test_revise_recorded_when_only_failure_is_insufficient_for_stakes():
    """A sufficiency failure written on a Valid line records REVISE and its tag."""
    tracer = _StubTracer()
    task_id = "proj_0000abcd"

    reason = (
        f"Judged: {task_id}; asks {task_id}/AC1\n"
        "Valid: (3) fails #insufficient-for-stakes -- the merge it authorises rests on "
        "a worker's unchecked report that review passed\n"
        "Supported: (2) worker reported, unchecked; cannot bear a merge\n"
        f"Answered: {task_id}/AC1 ← (3)\n"
        "Sufficient: (3) material; authorises a merge; sent back\n"
        "Waived: none\n"
        "Relay: none"
    )

    res = pcv.record_verdict(
        session_id="supervisor-session-insufficient",
        claim_id=task_id,
        verdict="REVISE",
        reason=reason,
        title="sufficiency failure",
        tracer_mod=tracer,
    )

    assert res["ok"] is True
    assert res["verdict"] == "REVISE"
    attrs = tracer.exported[0]["spans"][0]["attributes"]
    assert attrs["premise_check.defect_tags"] == ["#insufficient-for-stakes"]


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


def test_pass_refused_absent_block_instructs_load_premise_check():
    """US-2 AC-2.1: Refusal on absent block instructs returning for revision and loading ida:premise-check."""
    tracer = _StubTracer()
    session_id = "s-absent-block-pass"
    claim_id = "claim-absent-1"

    hg.arm(
        session_id=session_id,
        claim_id=claim_id,
        judged_text="Result text without an argdown block.",
        judged_ref=claim_id,
        block_expected=True,
    )

    reason = (
        f"Judged: {claim_id}; asks tg-1\n"
        "Valid: (1) holds -- ok\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: tg-1 ← (1)\n"
        "Sufficient: (1) obvious\n"
        "Waived: none\n"
        "Relay: none"
    )

    with pytest.raises(ValueError) as excinfo:
        pcv.record_verdict(
            session_id=session_id,
            claim_id=claim_id,
            verdict="PASS",
            reason=reason,
            tracer_mod=tracer,
        )

    err = str(excinfo.value)
    assert "PASS refused -- no argument block in judged text" in err
    assert "Load the premise-check skill (`ida:premise-check`)" in err


def test_pass_refused_unparsable_block_instructs_load_premise_check():
    """US-2 AC-2.2: Refusal on syntax error in argdown block instructs loading ida:premise-check."""
    tracer = _StubTracer()
    session_id = "s-syntax-err-pass"
    claim_id = "claim-syntax-1"

    bad_argdown = (
        "```argdown\n===\nasks: [aops_1234]\nanswers: invalid yaml\n===\n(1) Observation.\n```"
    )

    hg.arm(
        session_id=session_id,
        claim_id=claim_id,
        judged_text=bad_argdown,
        judged_ref=claim_id,
        block_expected=True,
    )

    reason = (
        f"Judged: {claim_id}; asks aops_1234\n"
        "Valid: (1) holds -- ok\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: aops_1234 ← (1)\n"
        "Sufficient: (1) obvious\n"
        "Waived: none\n"
        "Relay: none"
    )

    with pytest.raises(ValueError) as excinfo:
        pcv.record_verdict(
            session_id=session_id,
            claim_id=claim_id,
            verdict="PASS",
            reason=reason,
            tracer_mod=tracer,
        )

    err = str(excinfo.value)
    assert f"PASS verdict refused for {claim_id}: could not parse argdown block:" in err
    assert "instruct the sender to load `ida:premise-check` before resending" in err


def test_pass_refused_zero_inference_lines_instructs_load_premise_check():
    """US-2 AC-2.3: Refusal on 0 inference lines instructs loading ida:premise-check."""
    tracer = _StubTracer()
    session_id = "s-zero-inf-pass"
    claim_id = "claim-zero-inf"

    zero_inf_block = (
        "```argdown\n"
        "===\n"
        "asks:\n"
        "  q1: test\n"
        "answers:\n"
        "  q1: 1\n"
        "===\n"
        f"(1) Bare observation without inference. -- {_ANY_BASIS}\n"
        "```"
    )

    hg.arm(
        session_id=session_id,
        claim_id=claim_id,
        judged_text=zero_inf_block,
        judged_ref=claim_id,
        block_expected=True,
    )

    reason = (
        f"Judged: {claim_id}; asks q1\n"
        "Valid: (1) holds -- ok\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: q1 ← (1)\n"
        "Sufficient: (1) obvious\n"
        "Waived: none\n"
        "Relay: none"
    )

    with pytest.raises(ValueError) as excinfo:
        pcv.record_verdict(
            session_id=session_id,
            claim_id=claim_id,
            verdict="PASS",
            reason=reason,
            tracer_mod=tracer,
        )

    err = str(excinfo.value)
    assert "0 inference lines" in err
    assert "instruct the author to load `ida:premise-check` before rewriting" in err


def test_pass_refused_missing_keyed_lines_instructs_load_premise_check():
    """US-2 AC-2.4: Refusal on missing reason keys instructs loading ida:premise-check."""
    tracer = _StubTracer()
    session_id = "s-missing-keys-pass"
    claim_id = "claim-missing-keys"

    valid_block = (
        "```argdown\n"
        "===\n"
        "asks:\n"
        "  q1: test\n"
        "answers:\n"
        "  q1: 2\n"
        "===\n"
        f"(1) Fact. -- {_ANY_BASIS}\n"
        "-- rule. Unless: def; not tried. --\n"
        "(2) So, conclusion.\n"
        "```"
    )

    hg.arm(
        session_id=session_id,
        claim_id=claim_id,
        judged_text=valid_block,
        judged_ref=claim_id,
        block_expected=True,
    )

    # Incomplete reason: omits Supported, Answered, Sufficient, Waived, Relay
    incomplete_reason = f"Judged: {claim_id}; asks q1\nValid: (2) holds -- ok\n"

    with pytest.raises(ValueError) as excinfo:
        pcv.record_verdict(
            session_id=session_id,
            claim_id=claim_id,
            verdict="PASS",
            reason=incomplete_reason,
            tracer_mod=tracer,
        )

    err = str(excinfo.value)
    assert "missing keyed lines" in err
    assert (
        "Load the skill (`ida:premise-check`) to inspect the required format before resubmitting."
        in err
    )


def test_revise_and_fail_refused_all_valid_instructs_load_premise_check():
    """US-2 AC-2.5: Inconsistent REVISE/FAIL refusal instructs loading ida:premise-check."""
    tracer = _StubTracer()
    session_id = "s-inconsistent-revise"
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

    for verdict in ("REVISE", "FAIL"):
        with pytest.raises(ValueError) as excinfo:
            pcv.record_verdict(
                session_id=session_id,
                claim_id=task_id,
                verdict=verdict,
                reason=reason_all_hold,
                tracer_mod=tracer,
            )
        err = str(excinfo.value)
        assert f"{verdict} refused -- reason has Valid entries that all hold" in err
        assert (
            "Load the premise-check skill (`ida:premise-check`) to inspect the required format before resubmitting."
            in err
        )


def test_verdict_resolves_session_from_gate_state_when_unspecified(tmp_path, monkeypatch):
    """AC2 (#3543, #2798): verdict.py resolves session ID across subshell invocations from gate state."""
    gate_dir = tmp_path / "subshell_gate"
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(gate_dir))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("SESSION_ID", raising=False)

    session_id = "subshell-session-abc"
    claim_id = "claim-subshell-123"

    hg.arm(
        session_id=session_id,
        claim_id=claim_id,
        judged_text="Result text",
        judged_ref=claim_id,
    )
    assert hg.is_armed(session_id) is True

    # When --session is not passed, resolve_session_id should find session_id from state
    resolved = pcv.resolve_session_id("", claim_id)
    assert resolved == session_id

    # And main() should resolve the session and record the verdict
    tracer = _StubTracer()
    monkeypatch.setattr(pcv, "_import_claude_code_tracer", lambda: tracer)
    reason_file = tmp_path / "reason.txt"
    reason_file.write_text("no argument supplied; please supply argument block", encoding="utf-8")

    code = pcv.main(
        [
            "--claim",
            claim_id,
            "--verdict",
            "REVISE",
            "--reason-file",
            str(reason_file),
        ]
    )
    assert code == 0
    assert hg.is_armed(session_id) is False
    assert hg.get_state(session_id)["last_verdict"]["verdict"] == "REVISE"


def test_verdict_reports_clear_diagnostic_when_no_session_or_state(tmp_path, monkeypatch, capsys):
    """AC2 (#3543, #2798): verdict.py reports a clear diagnostic when neither --session nor session state is available."""
    gate_dir = tmp_path / "empty_gate"
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(gate_dir))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("SESSION_ID", raising=False)

    code = pcv.main(
        [
            "--claim",
            "claim-no-state",
            "--verdict",
            "REVISE",
            "--reason",
            "no argument supplied",
        ]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "no session id" in err
    assert "no session state available" in err
