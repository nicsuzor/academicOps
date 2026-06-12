"""Repro / elimination harness for issue #1798 — IDA text as agy PreToolUse denyReason.

SYMPTOM (#1798): in agy (Antigravity CLI 1.0.7) sessions the IDA reminder text
("≡ Before you stop — be honest:") was reported surfacing as the ``denyReason``
field of a ``PreToolHookResult`` for an ordinary read tool (``grep_search``).

WHAT THIS MODULE DOES
---------------------
It drives the REAL router + gate engine (``--client agy`` subprocess, not a mock
of the unit under test) and asserts the invariant the bug report claims is
violated: no agy ``PreToolUse`` output for a read tool may ever carry IDA
content, and in particular IDA text must never appear as ``denyReason``.

These tests are the code-level elimination of hypotheses (b) state-leakage,
(c) event-misidentification, and (d) single-event multi-gate merge from the
#1798 trace. They are written to FAIL loudly the instant a future change makes
our router emit IDA-as-denyReason on a PreToolUse — i.e. if the defect ever
becomes ours. As of dev (this commit) they PASS, which is itself the evidence
that the mechanism is NOT in router.py / engine.py / definitions.py:

  * IDA's two policies are both ``hook_event="Stop"`` (definitions.py:476, 490),
    so ``GenericGate._evaluate_condition`` rejects them on a PreToolUse call
    (engine.py:62).
  * ``ida.reminder`` is referenced ONLY by those two Stop policies
    (definitions.py:482, 496) — no PreToolUse policy renders it.
  * ``grep_search`` is in the ``read_only`` tool category (gate_config.py:244),
    which the enforcer policy excludes (definitions.py:129) and which sentinel
    never matches — so NO PreToolUse gate can even DENY ``grep_search``.
  * ``output_for_agy`` only emits ``denyReason`` on ``event=="PreToolUse"`` with
    a block verdict (router.py:1040-1044); the PostInvocation/Stop advisory
    (IDA included) is routed to ``injectSteps`` / ``reason`` instead.
  * the router never reads any injection/advisory field FROM the input payload,
    so an agy-forwarded PostInvocation output cannot re-enter a PreToolUse
    result through our code.
"""

from __future__ import annotations

import pytest
from lib.gate_types import GateStatus
from lib.session_state import SessionState

from tests.hooks.gate_helpers import run_router_agy

_IDA_MARKER = "be honest"


def _arm_ida(monkeypatch, state_dir, session_id: str) -> None:
    """Seed on-disk session state with IDA armed (CLOSED) for `session_id`.

    The subprocess router loads this state by session id. IDA armed is the
    default; we set it explicitly so the test is robust to any default change.
    """
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
    monkeypatch.setenv("IDA_GATE_MODE", "warn")
    state = SessionState.create(session_id, client_type="agy")
    state.gates["ida"].status = GateStatus.CLOSED
    state.save()


def _grep_pretool_payload(session_id: str) -> dict:
    """The REAL agy 1.0.7 PreToolUse payload shape (copied from the live hook log,
    session 6d3d5783): ``toolCall`` sits at the ROOT of the stdin object, not
    double-nested under ``raw_input`` (#1800). ``conversationId`` carries the
    session id for state lookup.
    """
    return {
        "conversationId": session_id,
        "stepIdx": 5,
        "toolCall": {"name": "grep_search", "args": {"Query": "foo"}},
        "workspacePaths": ["/home/nic/src/overwhelm-dashboard"],
    }


def test_agy_grep_pretooluse_never_emits_ida_denyreason(monkeypatch, tmp_path):
    """A grep_search PreToolUse with IDA armed must NOT deny, and must carry no IDA text.

    This is the direct #1798 invariant. If the router ever emits a
    ``denyReason`` (or any IDA text) on this read-only PreToolUse, this fails.
    """
    sid = "agy-1798-grep-pretool"
    _arm_ida(monkeypatch, tmp_path, sid)

    output, stderr = run_router_agy(_grep_pretool_payload(sid), "PreToolUse")

    assert "denyReason" not in output, (
        f"#1798: IDA-as-denyReason on a read-only PreToolUse. "
        f"output={output!r} stderr={stderr[-400:]!r}"
    )
    assert output.get("allowTool") is not False, (
        f"#1798: grep_search PreToolUse was DENIED (allowTool=false) — a read "
        f"tool must never be blocked. output={output!r} stderr={stderr[-400:]!r}"
    )
    # No IDA advisory text may leak into ANY field of a PreToolUse result.
    assert _IDA_MARKER not in str(output), (
        f"#1798: IDA reminder text leaked into a PreToolUse result. output={output!r}"
    )


def test_agy_postinvocation_routes_ida_to_injectsteps_not_denyreason(monkeypatch, tmp_path):
    """The CORRECT IDA path: PostInvocation (→Stop) delivers IDA via injectSteps.

    Differential control for #1798. Same armed IDA, same session — only the
    event differs. IDA content belongs here (injectSteps), never on a
    PreToolUse denyReason.
    """
    sid = "agy-1798-postinvocation"
    _arm_ida(monkeypatch, tmp_path, sid)

    output, stderr = run_router_agy({"conversationId": sid}, "PostInvocation")

    assert "denyReason" not in output, f"PostInvocation must not emit denyReason: {output!r}"
    steps = output.get("injectSteps")
    assert steps, f"PostInvocation should deliver the IDA advisory via injectSteps: {output!r}"
    joined = " ".join(s.get("ephemeralMessage", "") for s in steps)
    assert _IDA_MARKER in joined, (
        f"PostInvocation injectSteps should carry the IDA reminder: {output!r}"
    )


@pytest.mark.parametrize(
    "payload_event",
    ["PostInvocation", "Stop"],
)
def test_agy_pretool_positional_governs_over_payload_event(monkeypatch, tmp_path, payload_event):
    """Cross-labeled event: positional ``PreToolUse`` must win over a payload claim.

    Eliminates hypothesis (c): even if agy were to invoke the PreToolUse-
    registered hook with a payload whose ``hook_event_name`` claims a
    Stop-family event, the positional arg governs and IDA does not fire — so no
    IDA-as-denyReason can form.
    """
    sid = f"agy-1798-crosslabel-{payload_event.lower()}"
    _arm_ida(monkeypatch, tmp_path, sid)

    payload = _grep_pretool_payload(sid)
    payload["hook_event_name"] = payload_event

    output, stderr = run_router_agy(payload, "PreToolUse")

    assert "denyReason" not in output, (
        f"Cross-labeled PreToolUse (payload claims {payload_event}) leaked a "
        f"denyReason: {output!r} stderr={stderr[-400:]!r}"
    )
    assert _IDA_MARKER not in str(output), f"Cross-labeled PreToolUse leaked IDA text: {output!r}"
