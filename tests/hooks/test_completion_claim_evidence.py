#!/usr/bin/env python3
"""Completion-claim evidence predicate on the handover gate (epic aops-262def9f WI2a).

The invariant: no completion claim (task → merge_ready/done) without attached
independent-verification evidence bound to final artifact state.

Wiring under test:
- hooks/router.py records completion claims on the session state at
  PostToolUse time (execute_hooks, NOT gate dispatch) so the ledger works in
  is_subagent sessions where _dispatch_gates skips tool-call events.
- An unevidenced claim force-closes the handover gate; the Stop policy
  (custom_check=handover_unevidenced_claim) then DENYs with an actionable
  evidence message.
- The handover satisfier triggers (/dump, /end_session, /continue) are
  guarded by no_unevidenced_completion_claim: an emergency /dump with NO
  claim stays evidence-free, but a claim made earlier in-session is not
  laundered by a later /dump.
"""

import sys
from pathlib import Path

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

import pytest  # noqa: E402
from hooks.router import HookRouter  # noqa: E402
from lib.gate_model import GateVerdict  # noqa: E402
from lib.gate_types import GateStatus  # noqa: E402
from lib.hook_context import HookContext  # noqa: E402
from lib.session_state import SessionState  # noqa: E402
from lib.verification_evidence import record_completion_claim  # noqa: E402

from tests.hooks.gate_helpers import (  # noqa: E402
    reinit_gates_with_defaults,
    set_gate_modes,
)

# Contract-conformant evidence trailers: independent reviewer, artifact-state
# SHA, method-named null result. Mirrors TRAILER_FORMAT_HELP.
CONFORMANT_SUMMARY = (
    "Implemented the widget frobnicator.\n\n"
    "Verified-By: marsha (subagent 9f3e3217)\n"
    "Verified-SHA: 51ed2fff\n"
    "Findings: no defects found via pytest tests/hooks + read of "
    "aops-core/lib/gates/definitions.py:294-398\n"
)

ATTESTATION_SUMMARY = "All done. Clean, verified, looks good."


@pytest.fixture
def router(monkeypatch):
    set_gate_modes(monkeypatch, handover="block", qa="off", ida="off")
    reinit_gates_with_defaults()
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


def _release_ctx(session_id: str, summary: str, *, is_subagent: bool) -> HookContext:
    return HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="mcp__plugin_aops-core_pkb__release_task",
        tool_input={"id": "task-ev1", "status": "merge_ready", "summary": summary},
        is_subagent=is_subagent,
    )


def _stop_ctx(session_id: str, *, is_subagent: bool = False) -> HookContext:
    return HookContext(
        session_id=session_id,
        hook_event="Stop",
        tool_name=None,
        tool_input={},
        is_subagent=is_subagent,
    )


def _dump_ctx(session_id: str) -> HookContext:
    return HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="Skill",
        tool_input={"skill": "dump"},
        subagent_type="dump",
    )


def _record(router: HookRouter, ctx: HookContext, state: SessionState) -> None:
    """Mirror execute_hooks() ordering: ledger first, then gate dispatch.

    The ledger step is what execute_hooks runs unconditionally; gate dispatch
    is skipped for is_subagent tool-call events (the skip under test).
    """
    record_completion_claim(ctx, state)
    router._dispatch_gates(ctx, state)


# --- Quality bar (1): is_subagent + release_task(merge_ready), no evidence ---


def test_subagent_unevidenced_release_blocks_stop(router):
    """An is_subagent session releasing merge_ready with no evidence must be
    DENIED at Stop — even though PostToolUse gate dispatch is skipped for
    that session class (the ledger rides execute_hooks, not dispatch)."""
    state = SessionState.create("ev-sub-block")

    ctx = _release_ctx("ev-sub-block", "all done!", is_subagent=True)
    # The skip under test: gate dispatch sees nothing for subagent tool calls.
    assert router._dispatch_gates(ctx, state) is None
    record_completion_claim(ctx, state)

    assert state.gates["handover"].status == GateStatus.CLOSED, (
        "unevidenced claim must force-close the handover gate (PostToolUse "
        "close triggers never run in subagent sessions)"
    )

    result = router._dispatch_gates(_stop_ctx("ev-sub-block", is_subagent=True), state)
    assert result is not None and result.verdict == GateVerdict.DENY, (
        "Stop must be blocked while an unevidenced completion claim stands"
    )
    assert "Verified-By" in (result.context_injection or ""), (
        "deny message must be actionable — it quotes the trailer format"
    )


def test_attestation_only_summary_still_blocks(router):
    """'clean/verified' with no findings or method is NOT RUN — same block."""
    state = SessionState.create("ev-sub-attest")
    _record(router, _release_ctx("ev-sub-attest", ATTESTATION_SUMMARY, is_subagent=True), state)

    result = router._dispatch_gates(_stop_ctx("ev-sub-attest", is_subagent=True), state)
    assert result is not None and result.verdict == GateVerdict.DENY


# --- Quality bar (2): same, with contract-conformant evidence bound to SHA ---


def test_subagent_release_with_conformant_evidence_passes_stop(router):
    """Evidence trailers binding an independent reviewer to a SHA satisfy the
    contract; the ledger records evidence_ok and the exit is not held."""
    state = SessionState.create("ev-sub-pass")
    _record(router, _release_ctx("ev-sub-pass", CONFORMANT_SUMMARY, is_subagent=True), state)

    claim = state.state["completion_claims"]["task-ev1"]
    assert claim["evidence_ok"] is True
    assert claim["status"] == "merge_ready"

    result = router._dispatch_gates(_stop_ctx("ev-sub-pass", is_subagent=True), state)
    verdict = result.verdict if result else None
    assert verdict != GateVerdict.DENY, f"conformant evidence must not hold the exit; got {verdict}"


# --- Quality bar (3): /dump with no completion claim stays evidence-free ---


def test_dump_without_claim_opens_gate_evidence_free(router):
    """Emergency bail: a session that did work but made NO completion claim
    satisfies handover via /dump exactly as before — no evidence demanded."""
    state = SessionState.create("ev-dump-free")

    # Real work closes the gate (main session — dispatch handles PostToolUse).
    router._dispatch_gates(
        HookContext(
            session_id="ev-dump-free",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/tmp/foo.py"},
        ),
        state,
    )
    assert state.gates["handover"].status == GateStatus.CLOSED
    assert state.session_did_work is True

    router._dispatch_gates(_dump_ctx("ev-dump-free"), state)
    assert state.gates["handover"].status == GateStatus.OPEN, (
        "/dump with no completion claim in-session must open the gate evidence-free"
    )

    result = router._dispatch_gates(_stop_ctx("ev-dump-free"), state)
    verdict = result.verdict if result else None
    assert verdict != GateVerdict.DENY


# --- Constraint (iii): a later /dump must not launder an earlier claim ---


def test_dump_does_not_launder_unevidenced_claim(router):
    """A completion claim made earlier in-session suppresses the /dump
    satisfier until the claim is re-issued with conformant evidence."""
    state = SessionState.create("ev-launder")
    _record(router, _release_ctx("ev-launder", "shipped it", is_subagent=False), state)
    assert state.gates["handover"].status == GateStatus.CLOSED

    # /dump after the unevidenced claim: trigger suppressed, gate stays armed.
    router._dispatch_gates(_dump_ctx("ev-launder"), state)
    assert state.gates["handover"].status == GateStatus.CLOSED, (
        "/dump must not launder an unevidenced completion claim"
    )
    result = router._dispatch_gates(_stop_ctx("ev-launder"), state)
    assert result is not None and result.verdict == GateVerdict.DENY

    # Re-issue the release WITH evidence → the same task's claim is cleared,
    # and /dump satisfies the gate again.
    _record(router, _release_ctx("ev-launder", CONFORMANT_SUMMARY, is_subagent=False), state)
    router._dispatch_gates(_dump_ctx("ev-launder"), state)
    assert state.gates["handover"].status == GateStatus.OPEN

    result = router._dispatch_gates(_stop_ctx("ev-launder"), state)
    verdict = result.verdict if result else None
    assert verdict != GateVerdict.DENY


def test_claim_after_end_session_reblocks_sticky_gate(router):
    """Ordering hole: /end_session opens the gate (sticky), THEN the agent
    releases unevidenced. The ledger force-close must clear the sticky latch
    so the exit is still held."""
    state = SessionState.create("ev-post-skill")
    router._dispatch_gates(
        HookContext(
            session_id="ev-post-skill",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/tmp/foo.py"},
        ),
        state,
    )
    router._dispatch_gates(
        HookContext(
            session_id="ev-post-skill",
            hook_event="PostToolUse",
            tool_name="Skill",
            tool_input={"skill": "end_session"},
            subagent_type="end_session",
        ),
        state,
    )
    assert state.gates["handover"].status == GateStatus.OPEN
    assert state.gates["handover"].sticky is True

    _record(router, _release_ctx("ev-post-skill", "done, closing out", is_subagent=False), state)
    assert state.gates["handover"].status == GateStatus.CLOSED
    assert state.gates["handover"].sticky is False

    result = router._dispatch_gates(_stop_ctx("ev-post-skill"), state)
    assert result is not None and result.verdict == GateVerdict.DENY


# --- Ledger integration: execute_hooks records for subagent sessions ---


def test_execute_hooks_records_claims_in_subagent_sessions(router, monkeypatch):
    """The ledger step lives in execute_hooks (session-state bookkeeping),
    which is NOT subject to the _dispatch_gates is_subagent skip."""
    state = SessionState.create("ev-integration")
    monkeypatch.setattr(SessionState, "load", classmethod(lambda cls, *a, **k: state))
    monkeypatch.setattr(SessionState, "save", lambda self: None)

    ctx = HookContext(
        session_id="ev-integration",
        hook_event="PostToolUse",
        tool_name="mcp__pkb__release_task",
        tool_input={"id": "task-9", "status": "merge_ready", "summary": "finished"},
        is_subagent=True,
    )
    router.execute_hooks(ctx)

    claim = state.state["completion_claims"]["task-9"]
    assert claim["evidence_ok"] is False
    assert claim["status"] == "merge_ready"
    assert state.gates["handover"].status == GateStatus.CLOSED


# --- Non-claims must not arm the evidence predicate ---


def test_non_terminal_release_is_not_a_claim(router):
    """release_task(blocked/partial) is an honest non-completion — no ledger
    entry, no force-close, /dump unaffected."""
    state = SessionState.create("ev-nonclaim")
    ctx = HookContext(
        session_id="ev-nonclaim",
        hook_event="PostToolUse",
        tool_name="mcp__pkb__release_task",
        tool_input={"id": "task-ev1", "status": "blocked", "summary": "stuck on X"},
        is_subagent=True,
    )
    record_completion_claim(ctx, state)
    assert "completion_claims" not in state.state
    assert state.gates["handover"].status == GateStatus.OPEN
