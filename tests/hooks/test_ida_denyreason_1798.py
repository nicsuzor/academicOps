"""Engine-level invariant harness for issue #1798 — IDA text as PreToolUse denyReason.

SYMPTOM (#1798): in agy (Antigravity CLI) sessions the IDA reminder text
("≡ Before you stop — be honest:") was reported surfacing as the ``denyReason``
field of a ``PreToolHookResult`` for an ordinary read tool (``grep_search``).

WHAT THIS MODULE DOES
---------------------
It drives the REAL router + gate engine (subprocess, not a mock of the unit under
test) and asserts invariants the bug report claims are violated. These invariants
are engine-level — they live in router.py / engine.py / definitions.py and MUST
hold for ALL clients. Tests are parametrized over agy and claude.

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
  * For agy: ``output_for_agy`` only emits ``denyReason`` on ``event=="PreToolUse"``
    with a block verdict (router.py:1040-1044); the PostInvocation/Stop advisory
    (IDA included) is routed to ``injectSteps`` / ``reason`` instead.
  * the router never reads any injection/advisory field FROM the input payload,
    so an agy-forwarded PostInvocation output cannot re-enter a PreToolUse
    result through our code.
"""

from __future__ import annotations

import pytest
from lib.gate_types import GateStatus
from lib.session_state import SessionState

from tests.hooks.gate_helpers import (
    run_router_agy,
    run_router_claude,
    run_router_claude_raw,
)

_IDA_MARKER = "be honest"


# --- Normalized runners (payload, event) → (output, stderr) ---
# run_router_agy takes event as a positional CLI arg.
# run_router_claude embeds event in the payload as hook_event_name.


def _run_agy(payload: dict, event: str) -> tuple[dict, str]:
    return run_router_agy(payload, event)


def _run_claude(payload: dict, event: str) -> tuple[dict, str]:
    return run_router_claude({**payload, "hook_event_name": event})


_CLIENTS = [
    pytest.param(_run_agy, "agy", id="agy"),
    pytest.param(_run_claude, "claude", id="claude"),
]


def _arm_ida(monkeypatch, state_dir, session_id: str, client_type: str = "agy") -> None:
    """Seed on-disk session state with IDA armed (CLOSED) for `session_id`.

    The subprocess router loads this state by session id. IDA armed is the
    default; we set it explicitly so the test is robust to any default change.
    AOPS_SESSION_STATE_DIR overrides path resolution for all clients, so the
    seeded state is found regardless of which client the subprocess uses.
    """
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
    monkeypatch.setenv("IDA_GATE_MODE", "warn")
    state = SessionState.create(session_id, client_type=client_type)
    state.gates["ida"].status = GateStatus.CLOSED
    state.save()


def _grep_pretool_payload(session_id: str) -> dict:
    """Payload for a grep_search PreToolUse.

    ``conversationId`` is read by the router for all clients via
    ``raw_input.get("session_id") or raw_input.get("conversationId")``.
    ``toolCall`` at the ROOT reflects the real agy wire shape (session
    6d3d5783, observed on agy 1.0.7; current at 1.0.12) after the #1800 fix.
    """
    return {
        "conversationId": session_id,
        "stepIdx": 5,
        "toolCall": {"name": "grep_search", "args": {"Query": "foo"}},
        "workspacePaths": ["/home/nic/src/overwhelm-dashboard"],
    }


@pytest.mark.parametrize("run_router,client_type", _CLIENTS)
def test_grep_pretooluse_never_emits_ida_denyreason(monkeypatch, tmp_path, run_router, client_type):
    """A grep_search PreToolUse with IDA armed must NOT deny, and must carry no IDA text.

    This is the direct #1798 invariant. If the router ever emits a
    ``denyReason`` (or any IDA text) on this read-only PreToolUse, this fails.
    """
    sid = f"1798-grep-pretool-{client_type}"
    _arm_ida(monkeypatch, tmp_path, sid, client_type)

    output, stderr = run_router(_grep_pretool_payload(sid), "PreToolUse")

    assert "denyReason" not in output, (
        f"#1798: IDA-as-denyReason on a read-only PreToolUse. "
        f"output={output!r} stderr={stderr[-400:]!r}"
    )
    assert output.get("allowTool") is not False, (
        f"#1798: grep_search PreToolUse was DENIED (allowTool=false) — a read "
        f"tool must never be blocked. output={output!r} stderr={stderr[-400:]!r}"
    )
    assert _IDA_MARKER not in str(output), (
        f"#1798: IDA reminder text leaked into a PreToolUse result. output={output!r}"
    )


@pytest.mark.parametrize("run_router,client_type", _CLIENTS)
def test_postinvocation_routes_ida_to_advisory_not_denyreason(
    monkeypatch, tmp_path, run_router, client_type
):
    """The CORRECT IDA path: PostInvocation (→Stop) delivers IDA via the advisory channel.

    Differential control for #1798. Same armed IDA, same session — only the
    event differs. IDA content belongs in the advisory channel, never in a
    PreToolUse denyReason. The advisory channel is client-specific: agy uses
    ``injectSteps`` (JSON); claude uses the asyncRewake quiet-split — the full
    ida-reminder body on stdout with EXIT 2 (no JSON), so the body reaches the
    agent as a <system-reminder> while the user sees only the one-line summary
    (ENFORCEMENT-MAP §1.1 `ida·reminder`).
    """
    sid = f"1798-postinvocation-{client_type}"
    _arm_ida(monkeypatch, tmp_path, sid, client_type)

    if client_type == "claude":
        # claude Stop, ida-solo warn → asyncRewake exit-2 plain-body channel.
        stdout, returncode, stderr = run_router_claude_raw(
            {"conversationId": sid, "hook_event_name": "Stop"}
        )
        assert returncode == 2, (
            f"claude ida·reminder must take the asyncRewake exit-2 path: "
            f"rc={returncode} stdout={stdout!r} stderr={stderr[-400:]!r}"
        )
        assert _IDA_MARKER in stdout, (
            f"claude asyncRewake body must carry the IDA reminder: {stdout!r}"
        )
        assert "denyReason" not in stdout, f"asyncRewake body must not be a denyReason: {stdout!r}"
        return

    # The Stop-family event is client-specific on the wire: agy fires
    # ``PostInvocation`` (→Stop). The router resolves it through client_spec's
    # per-client inbound map.
    stop_event = "PostInvocation"
    output, stderr = run_router({"conversationId": sid}, stop_event)

    assert "denyReason" not in output, f"PostInvocation must not emit denyReason: {output!r}"
    assert _IDA_MARKER in str(output), (
        f"PostInvocation must deliver the IDA advisory in the output: {output!r}"
    )
    if client_type == "agy":
        steps = output.get("injectSteps")
        assert steps, f"agy PostInvocation: IDA must go to injectSteps: {output!r}"
        # injectSteps scalar channels (invariant #5): ephemeralMessage is preferred
        # (transient), userMessage is the persistent variant. The renderer emits
        # ephemeralMessage; legacy systemMessage kept for back-compat with older shapes.
        joined = " ".join(
            s.get("ephemeralMessage", "")
            or s.get("userMessage", "")
            or s.get("systemMessage", {}).get("systemMessage", "")
            for s in steps
        )
        assert _IDA_MARKER in joined, (
            f"agy PostInvocation injectSteps must carry the IDA reminder: {output!r}"
        )


@pytest.mark.parametrize("run_router,client_type", _CLIENTS)
@pytest.mark.parametrize(
    "payload_event",
    ["PostInvocation", "Stop"],
)
def test_pretool_positional_governs_over_payload_event(
    monkeypatch, tmp_path, run_router, client_type, payload_event
):
    """PreToolUse routing governs even when the payload claims a Stop-family event.

    For agy: eliminates hypothesis (c) — the positional CLI arg "PreToolUse"
    beats a payload ``hook_event_name`` claiming PostInvocation/Stop, so IDA
    (Stop-only) never fires on a PreToolUse.

    For claude: the caller-supplied event governs (passed via hook_event_name
    by _run_claude); IDA must not fire regardless of what the payload originally
    claimed.
    """
    sid = f"1798-crosslabel-{payload_event.lower()}-{client_type}"
    _arm_ida(monkeypatch, tmp_path, sid, client_type)

    payload = _grep_pretool_payload(sid)
    payload["hook_event_name"] = payload_event

    output, stderr = run_router(payload, "PreToolUse")

    assert "denyReason" not in output, (
        f"Cross-labeled PreToolUse (payload claims {payload_event}) leaked a "
        f"denyReason: {output!r} stderr={stderr[-400:]!r}"
    )
    assert _IDA_MARKER not in str(output), f"Cross-labeled PreToolUse leaked IDA text: {output!r}"
