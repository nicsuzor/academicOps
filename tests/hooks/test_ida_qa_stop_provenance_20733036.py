"""Composition invariants for aops-20733036 — Stop-hook provenance + attribution.

WHAT THIS COVERS
----------------
The Ida Stop-hook message *as composed by the router* must:
  1. preserve the ``<academicOps Ida hook reminder>`` provenance wrapper
     end-to-end (it is the self-identifying boundary that lets the agent tell
     a first-party Stop-event gate from a user message);
  2. keep the IDA bullets on separate lines (no line-merge);
  3. attribute every *other* gate's advisory that is composed into the same
     Stop ``reason`` to its source gate, rather than concatenating it as a
     floating, unlabelled paragraph. Before the fix the QA gate's advisory
     (``qa-policy-context.md``) carried no boundary and was delivered adjacent
     to the IDA block with no provenance — the defect this task targets.

These are driven through the REAL router subprocess (``run_router_claude``),
so they assert on the JSON the router actually emits — i.e. "Python produces
correct JSON". They are NOT a substitute for the live channel-delivery check in
``skills/aops/workflows/11-self-test.md`` §3 ("does the wrapper actually reach
the agent's context on a real Stop"), which forbids synthetic/stdin testing and
must be run in a real session.
"""

from __future__ import annotations

import re

from lib.gate_types import GateStatus
from lib.session_state import SessionState

from tests.hooks.gate_helpers import run_router_claude

_IDA_OPEN = "<academicOps Ida hook reminder>"
_IDA_CLOSE = "</academicOps Ida hook reminder>"
_QA_OPEN = "<academicOps QA gate reminder>"
_QA_CLOSE = "</academicOps QA gate reminder>"
_QA_ADVISORY_MARK = "🧪"


def _arm_qa_and_ida(monkeypatch, state_dir, session_id: str) -> None:
    """Seed on-disk state so a Stop fires BOTH the QA and IDA Stop policies.

    QA runs in warn mode (WARN, no loop-break) ahead of IDA in block mode
    (DENY, terminal) so both gates contribute ``context_injection`` to the same
    Stop ``reason`` — the multi-source composition this task is about. Handover
    and enforcer are disabled so they neither break the chain nor add noise.
    """
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
    monkeypatch.setenv("QA_GATE_MODE", "warn")
    monkeypatch.setenv("IDA_GATE_MODE", "block")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "off")
    monkeypatch.setenv("ENFORCER_GATE_MODE", "off")

    state = SessionState.create(session_id, client_type="claude")
    state.gates["qa"].status = GateStatus.CLOSED
    # qa.policy_context renders {temp_path}; seed it so the render never KeyErrors
    # if prepare_qa_review cannot build a real audit file in the test sandbox.
    state.gates["qa"].metrics["temp_path"] = "/tmp/qa-gate-20733036.md"
    state.gates["ida"].status = GateStatus.CLOSED
    state.save()


def _stop_reason(monkeypatch, tmp_path) -> str:
    sid = "20733036-stop-provenance"
    _arm_qa_and_ida(monkeypatch, tmp_path, sid)
    output, stderr = run_router_claude({"session_id": sid, "hook_event_name": "Stop"})
    assert output.get("decision") == "block", (
        f"Stop must block so the advisory reaches the agent. "
        f"output={output!r} stderr={stderr[-400:]!r}"
    )
    reason = output.get("reason") or ""
    assert reason, f"Stop block must carry a reason. output={output!r} stderr={stderr[-400:]!r}"
    return reason


def test_ida_wrapper_preserved_end_to_end(monkeypatch, tmp_path):
    """The ``<academicOps Ida hook reminder>`` boundary survives composition.

    ``_strip_hook_markers`` removes only the ``<SYSTEM HOOK INSTRUCTION>``
    scaffold; the academicOps provenance wrapper must reach the delivered
    ``reason`` intact (both open and close tags).
    """
    reason = _stop_reason(monkeypatch, tmp_path)
    assert _IDA_OPEN in reason, f"IDA open wrapper stripped from delivered reason: {reason!r}"
    assert _IDA_CLOSE in reason, f"IDA close wrapper stripped from delivered reason: {reason!r}"


def test_ida_bullets_not_line_merged(monkeypatch, tmp_path):
    """The two trailing IDA bullets stay on separate lines (no merge)."""
    reason = _stop_reason(monkeypatch, tmp_path)
    assert "- No inferences dressed as observations." in reason, reason
    assert "- Lead with your recommendations." in reason, reason
    # The two bullets must be distinct lines, not concatenated onto one.
    assert "observations.\n- Lead with your recommendations." in reason, (
        f"IDA bullets were line-merged in the delivered reason: {reason!r}"
    )


def test_composed_qa_advisory_is_attributed(monkeypatch, tmp_path):
    """A non-IDA gate advisory composed into the same Stop must be labelled.

    The QA advisory must be wrapped in its own ``<academicOps QA gate reminder>``
    boundary — not delivered as a floating, unattributed paragraph next to the
    IDA block.
    """
    reason = _stop_reason(monkeypatch, tmp_path)
    assert _QA_OPEN in reason, f"QA advisory has no provenance wrapper: {reason!r}"
    assert _QA_CLOSE in reason, f"QA advisory wrapper not closed: {reason!r}"
    # The QA advisory text must sit INSIDE its boundary — i.e. the open tag
    # precedes the advisory mark, which precedes the close tag.
    assert _QA_ADVISORY_MARK in reason, reason
    qa_open_i = reason.index(_QA_OPEN)
    qa_mark_i = reason.index(_QA_ADVISORY_MARK)
    qa_close_i = reason.index(_QA_CLOSE)
    assert qa_open_i < qa_mark_i < qa_close_i, (
        f"QA advisory is not enclosed by its own provenance wrapper: {reason!r}"
    )


def test_every_composed_block_is_attributed(monkeypatch, tmp_path):
    """No composed gate text is delivered outside a provenance boundary.

    Dropping each matched ``<academicOps …>`` … ``</academicOps …>`` block
    should leave only whitespace and the blank-line join between them — proving
    there is no unlabelled gate text silently concatenated into the list.
    """
    reason = _stop_reason(monkeypatch, tmp_path)
    # Remove each provenance-wrapped block wholesale, then assert nothing
    # substantive remains outside a wrapper.
    cleaned = re.sub(r"<academicOps [^>]+>.*?</academicOps [^>]+>", "", reason, flags=re.DOTALL)
    leftover = cleaned.strip()
    assert leftover == "", (
        f"Unattributed gate text delivered outside any provenance wrapper: {leftover!r}\n"
        f"full reason={reason!r}"
    )
