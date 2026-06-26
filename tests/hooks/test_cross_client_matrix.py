"""Cross-client router conformance matrix — Test Layer A of specs/hooks/CLIENT-TRANSLATION.md.

The fast, deterministic, CI counterpart of the live conformance harnesses (the
headless ``test_live_conformance.py`` = Test Layer B was deleted 2026-06-26;
user-visibility is now measured by the PTY harness ``scripts/pty_hook_probe.py``
= Test Layer C). This is the SINGLE parametrized
``(client × event × scenario)`` matrix the spec calls for (CLIENT-TRANSLATION.md
§"Test layer A"), replacing the scattered per-client test bodies with ONE
``run_router`` fixture + per-client **interpreters**.

ARCHITECTURE
------------
- ``run_router(client, event, canonical)`` renders a synthetic ``CanonicalHookOutput``
  through the client's real renderer (``HookRouter.output_for_{claude,gemini,agy}``)
  and returns the wire dict.
- ``interpret(client, event, wire) -> Delivered`` mirrors how each REAL client
  consumes that wire dict — the agy interpreter IS the agy protojson
  accept-contract (``agy_accept_contract.is_accepted_by_agy``); the claude/gemini
  interpreters mirror their documented field semantics. ``Delivered`` carries
  ``agent_sees`` / ``user_sees`` / ``blocked`` / ``accepted``.

The matrix asserts the four core invariants (CLIENT-TRANSLATION.md §"Core invariants"):
  * **A. accepted** — output validates against the client's accept-contract.
  * **B. injection reaches agent** — ``context_injection`` present ⇒ ``agent_sees``
    it, OR (no agent channel) ⇒ blocked-to-deliver / raised. *The property that
    keeps regressing.*
  * **C. verdict fidelity** — deny ⇒ blocked; allow/warn ⇒ not blocked
    (agy: allow ≠ ``{}``).
  * **D. no leak** — ``system_message`` only on user channels; advisory never on a
    user-only field.

P4-RESOLVED CELLS encoded here (do NOT re-flip — see epic aops-aa512c33 P4):
  * (a) Claude Stop WARN delivers via additionalContext WITHOUT a block
        (``channel_spec("claude","Stop").agent_context_without_block`` True,
        mem-4ab6cc0b live-verified 2026-06-25).
  * (b) PreToolUse decision-vs-allowTool: agy emits the enforcing
        ``{allowTool:true}`` / ``{allowTool:false,denyReason}``; NO flip.
  * (d) ``--dangerously-skip-permissions`` × PreToolUse: agy still fires the hook
        (live-verified) — a runtime/wire fact owned by the live harness, not
        re-asserted here.

DEFERRED CELL (c): agy PostInvocation ``terminationBehavior:force_continue``
RUNTIME re-entry is UNVERIFIED on the live-build host (the probe timed out;
isolated runtime re-entry is unobservable where agy runs only the globally
installed plugin). It is encoded as a single ``xfail`` below — wire-shape
acceptance is asserted, runtime re-entry is NOT claimed.

This file is the cross-client SSoT for router-vs-table conformance; the frozen
per-client literal anchors (``test_output_for_agy.py``,
``test_output_channel_routing.py``, ``test_universal_router.py``) remain as the
byte-exact wire-shape guards the matrix's semantic interpreters sit on top of.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).resolve().parents[2] / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks import client_spec  # noqa: E402
from hooks.router import HookRouter, _strip_hook_markers  # noqa: E402
from hooks.schemas import CanonicalHookOutput  # noqa: E402

from tests.hooks.agy_accept_contract import is_accepted_by_agy  # noqa: E402

# The advisory the gate layer injects (agent-only), with the framework trust
# markers. Reused from gate_helpers' shape so the matrix exercises a real
# marked advisory, not a toy string.
ADVISORY = "<SYSTEM HOOK INSTRUCTION>provide evidence for EACH claim.</SYSTEM HOOK INSTRUCTION>"
ADVISORY_BODY = _strip_hook_markers(ADVISORY)
USER_MSG = "Handover required before stop"


# ---------------------------------------------------------------------------
# Per-client INTERPRETERS — how the REAL client consumes the wire dict.
# ---------------------------------------------------------------------------
@dataclass
class Delivered:
    """What a client actually does with a rendered hook output.

    accepted  — the client's accept-contract did not reject the payload.
    agent_sees — text the MODEL receives this/next turn (agent-only or via block).
    user_sees  — text rendered to the USER (notices, summaries).
    blocked    — the tool/stop was actually blocked (None = N/A for the event).
    """

    accepted: bool
    agent_sees: str
    user_sees: str
    blocked: bool | None


def _interpret_claude(event: str, wire) -> Delivered:
    """Mirror Claude Code's documented consumption of a hook result.

    Stop/SessionEnd: agent reads ``reason`` (on block) or
    ``hookSpecificOutput.additionalContext`` (no block); user sees
    ``stopReason``/``systemMessage``. General HSO events: agent reads
    ``hookSpecificOutput.additionalContext``; user sees ``systemMessage``.
    """
    payload = wire.model_dump(exclude_none=True)
    hso = payload.get("hookSpecificOutput") or {}
    agent = ""
    user = ""
    blocked = None
    if event in ("Stop", "SessionEnd"):
        decision = payload.get("decision")
        blocked = decision == "block"
        # On a block, `reason` reaches the agent (and is also user-visible).
        agent = payload.get("reason") or hso.get("additionalContext") or ""
        user = payload.get("stopReason") or payload.get("systemMessage") or ""
    else:
        agent = hso.get("additionalContext") or ""
        user = payload.get("systemMessage") or ""
        decision = hso.get("permissionDecision")
        if event == "PreToolUse":
            blocked = decision in ("deny", "ask")
    # Claude's accept-contract: an HSO on a non-HSO event would be rejected, but
    # the renderer raises before emitting that, so any payload we get here is
    # accepted by construction.
    return Delivered(accepted=True, agent_sees=agent, user_sees=user, blocked=blocked)


def _interpret_gemini(event: str, wire) -> Delivered:
    """Mirror Gemini CLI consumption: decision=deny blocks; additionalContext to agent."""
    payload = wire.model_dump(exclude_none=True)
    hso = payload.get("hookSpecificOutput") or {}
    agent = hso.get("additionalContext") or ""
    user = payload.get("systemMessage") or ""
    decision = payload.get("decision")
    blocked = decision == "deny" if event in ("PreToolUse", "Stop", "SessionEnd") else None
    return Delivered(accepted=True, agent_sees=agent, user_sees=user, blocked=blocked)


def _interpret_agy(event: str, wire: dict) -> Delivered:
    """The agy interpreter IS the agy protojson accept-contract.

    agy parses each result as ``exa.hooks_pb.*Result`` and rejects on the first
    unknown field — so ``accepted`` is exactly ``is_accepted_by_agy``. agy has NO
    hidden agent-only channel (CLIENT-TRANSLATION.md): injectSteps are
    user-visible AND agent-visible (model echo), so they count as both
    ``agent_sees`` and ``user_sees``. PreToolUse deny = ``allowTool:false``;
    ``{}``/omitted allowTool = DENY on the wire (invariant #2).
    """
    accepted, _offending = is_accepted_by_agy(wire, event)
    agent = ""
    user = ""
    blocked = None
    if event == "PreToolUse":
        # Omitted/false allowTool = DENY (protojson omitted-bool default = false).
        blocked = wire.get("allowTool") is not True
        user = wire.get("denyReason") or ""
        # PreToolUse has no agent inject channel; denyReason is user-facing.
    elif event in ("PreInvocation", "PostInvocation"):
        joined = " ".join(
            s.get("ephemeralMessage") or s.get("userMessage") or ""
            for s in wire.get("injectSteps", [])
        )
        # agy injectSteps are user-visible AND reach the model (no hidden channel).
        agent = joined
        user = joined
    elif event == "Stop":
        user = wire.get("reason") or ""
        agent = wire.get("reason") or ""
    return Delivered(accepted=accepted, agent_sees=agent, user_sees=user, blocked=blocked)


_INTERPRET = {
    "claude": _interpret_claude,
    "gemini": _interpret_gemini,
    "agy": _interpret_agy,
}


# ---------------------------------------------------------------------------
# Unified runner.
# ---------------------------------------------------------------------------
def run_router(client: str, event: str, canonical: CanonicalHookOutput):
    """Render a canonical verdict through the client's renderer and interpret it.

    Returns (wire, Delivered). The agy renderer takes the ORIGINAL agy wire event
    name (PreInvocation/PostInvocation/Stop); the cross-client scenarios below use
    each client's own wire event name so the renderer selects the right shape.
    """
    router = HookRouter()
    if client == "claude":
        wire = router.output_for_claude(canonical, event)
    elif client == "gemini":
        wire = router.output_for_gemini(canonical, event)
    elif client == "agy":
        wire = router.output_for_agy(canonical, event)
    else:  # pragma: no cover - guard
        raise ValueError(f"unknown client {client!r}")
    delivered = _INTERPRET[client](event, wire)
    return wire, delivered


# ---------------------------------------------------------------------------
# SCENARIO MATRIX. Each row: (client, event, canonical-kwargs, expectations).
# Per-client event names so each renderer selects its native *Result shape.
# ---------------------------------------------------------------------------
def _c(verdict, *, context=None, system=None):
    return CanonicalHookOutput(verdict=verdict, context_injection=context, system_message=system)


# (id, client, event, canonical, expect: dict of invariant assertions)
_MATRIX = [
    # ===================== Claude =====================
    # Cell (a): WARN Stop delivers advisory via additionalContext, NO block.
    (
        "claude-stop-warn-advisory-noblock",
        "claude",
        "Stop",
        _c("warn", context=ADVISORY),
        {"blocked": False, "agent_has": ADVISORY, "user_clean": True},
    ),
    # ENFORCEMENT: deny Stop blocks; advisory reaches agent via reason (stripped).
    (
        "claude-stop-deny-blocks",
        "claude",
        "Stop",
        _c("deny", context=ADVISORY, system=USER_MSG),
        {"blocked": True, "agent_has": ADVISORY_BODY, "user_has": USER_MSG, "user_clean": True},
    ),
    # General HSO: PreToolUse warn delivers advisory to agent, allow (not blocked).
    (
        "claude-pretool-warn-advisory",
        "claude",
        "PreToolUse",
        _c("warn", context=ADVISORY, system="short note"),
        {"blocked": False, "agent_has": ADVISORY, "user_clean": True},
    ),
    # PreToolUse deny blocks; reason user-visible, no advisory leak.
    (
        "claude-pretool-deny-blocks",
        "claude",
        "PreToolUse",
        _c("deny", context=ADVISORY, system="Tool denied"),
        {"blocked": True, "agent_has": ADVISORY, "user_has": "Tool denied", "user_clean": True},
    ),
    # UserPromptSubmit warn advisory to agent.
    (
        "claude-ups-warn-advisory",
        "claude",
        "UserPromptSubmit",
        _c("warn", context=ADVISORY),
        {"blocked": None, "agent_has": ADVISORY, "user_clean": True},
    ),
    # ===================== Gemini =====================
    (
        "gemini-pretool-deny-blocks",
        "gemini",
        "PreToolUse",
        _c("deny", context=ADVISORY, system="denied"),
        {"blocked": True, "agent_has": ADVISORY, "user_has": "denied", "user_clean": True},
    ),
    (
        "gemini-pretool-allow-advisory",
        "gemini",
        "PreToolUse",
        _c("allow", context=ADVISORY),
        {"blocked": False, "agent_has": ADVISORY, "user_clean": True},
    ),
    (
        "gemini-ups-allow-advisory",
        "gemini",
        "UserPromptSubmit",
        _c("warn", context=ADVISORY),
        {"blocked": None, "agent_has": ADVISORY, "user_clean": True},
    ),
    # ===================== agy =====================
    # Cell (b): PreToolUse allow = explicit {allowTool:true} (NEVER {} = deny).
    (
        "agy-pretool-allow-explicit-true",
        "agy",
        "PreToolUse",
        _c("allow"),
        {"blocked": False, "accepted": True},
    ),
    (
        "agy-pretool-warn-explicit-true",
        "agy",
        "PreToolUse",
        _c("warn"),
        {"blocked": False, "accepted": True},
    ),
    # Cell (b): PreToolUse deny = {allowTool:false,denyReason}; reason user-facing.
    (
        "agy-pretool-deny-blocks",
        "agy",
        "PreToolUse",
        _c("deny", system="compliance overdue"),
        {"blocked": True, "user_has": "compliance overdue", "accepted": True},
    ),
    # ask cannot prompt headless → enforcing interpretation is block.
    (
        "agy-pretool-ask-blocks",
        "agy",
        "PreToolUse",
        _c("ask", system="needs confirmation"),
        {"blocked": True, "accepted": True},
    ),
    # PreInvocation injectSteps deliver advisory to model (verified by echo).
    (
        "agy-preinvocation-advisory",
        "agy",
        "PreInvocation",
        _c("allow", context="search the PKB first"),
        {"blocked": None, "agent_has": "search the PKB first", "accepted": True},
    ),
    # PostInvocation deny delivers advisory via injectSteps (NOT a denyReason).
    (
        "agy-postinvocation-advisory",
        "agy",
        "PostInvocation",
        _c("deny", context="finish the handover"),
        {"blocked": None, "agent_has": "finish the handover", "accepted": True},
    ),
    # PostToolUse is always {} and accepted.
    (
        "agy-posttool-empty",
        "agy",
        "PostToolUse",
        _c("allow"),
        {"blocked": None, "accepted": True},
    ),
    # Stop deny surfaces reason (no guessed decision enum).
    (
        "agy-stop-deny-reason",
        "agy",
        "Stop",
        _c("deny", system="short reason"),
        {"blocked": None, "user_has": "short reason", "accepted": True},
    ),
]


@pytest.mark.parametrize(
    "client,event,canonical,expect",
    [pytest.param(c, e, can, ex, id=i) for (i, c, e, can, ex) in _MATRIX],
)
def test_cross_client_matrix(client, event, canonical, expect):
    """One row per (client × event × scenario): invariants A–D + P4-resolved cells."""
    wire, d = run_router(client, event, canonical)

    # --- A. accepted ---
    if "accepted" in expect:
        assert d.accepted == expect["accepted"], (
            f"{client}/{event}: accept-contract mismatch — wire={wire!r}"
        )

    # --- C. verdict fidelity ---
    if expect.get("blocked") is not None:
        assert d.blocked == expect["blocked"], (
            f"{client}/{event}: verdict-fidelity — expected blocked={expect['blocked']}, "
            f"got {d.blocked} (wire={wire!r})"
        )

    # --- B. injection reaches agent ---
    if "agent_has" in expect:
        assert expect["agent_has"] in d.agent_sees, (
            f"{client}/{event}: invariant B — context_injection did not reach the "
            f"agent. agent_sees={d.agent_sees!r} wire={wire!r}"
        )

    # --- D. no leak: system_message only on user channels; advisory clean ---
    if "user_has" in expect:
        assert expect["user_has"] in d.user_sees, (
            f"{client}/{event}: user message missing from user channel. "
            f"user_sees={d.user_sees!r} wire={wire!r}"
        )
    if expect.get("user_clean"):
        # The advisory's framework marker must NEVER appear in a user-visible field.
        assert "SYSTEM HOOK INSTRUCTION" not in d.user_sees, (
            f"{client}/{event}: invariant D — advisory leaked into a user channel: "
            f"user_sees={d.user_sees!r}"
        )


# ---------------------------------------------------------------------------
# Re-anchor the SSoT cells the matrix's resolved expectations depend on.
# ---------------------------------------------------------------------------
def test_cell_a_claude_stop_agent_context_without_block_is_true():
    """Cell (a) anchor: the SSoT cell the no-block WARN delivery depends on.

    If this flips False, the matrix's ``claude-stop-warn-advisory-noblock`` row
    would (correctly) start failing — this names the single table cell that
    governs it (mem-4ab6cc0b, live-verified 2026-06-25).
    """
    spec = client_spec.channel_spec("claude", "Stop")
    assert spec is not None
    assert spec.agent_context_without_block is True


def test_cell_b_agy_pretool_can_block_and_no_free_agent_channel():
    """Cell (b) anchor: agy PreToolUse can block and has no free agent-inject channel."""
    spec = client_spec.channel_spec("agy", "PreToolUse")
    assert spec is not None
    assert spec.can_block is True
    assert spec.agent_context_without_block is False


# ---------------------------------------------------------------------------
# Cell (c): DEFERRED — agy PostInvocation terminationBehavior runtime re-entry.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    reason="agy terminationBehavior runtime re-entry unverified on live-build host "
    "— wire-shape accepted only; see epic aops-aa512c33 P4. The renderer delivers "
    "the PostInvocation advisory via injectSteps but does NOT yet emit the "
    "force_continue enum (aops-939b6c3a), so a Stop-block does not actually "
    "re-enter the agent loop. This asserts the not-yet-true RUNTIME end state.",
    strict=False,
)
def test_cell_c_agy_postinvocation_force_continue_reentry_deferred():
    """Forcing function: a Stop/PostInvocation DENY must eventually force-continue.

    Wire-shape acceptance of the PostInvocation advisory is already proven by the
    ``agy-postinvocation-advisory`` matrix row. What is UNVERIFIED — and therefore
    xfailed — is the RUNTIME re-entry: the ``terminationBehavior:force_continue``
    enum that makes agy re-enter its loop after a hard stop-block. The enum is not
    emitted (not live-verified), so this end-state assertion fails today.
    """
    wire, _ = run_router("agy", "PostInvocation", _c("deny", context="keep going"))
    assert "terminationBehavior" in wire, (
        "agy PostInvocation hard stop-block must emit terminationBehavior to "
        "actually re-enter the loop — deferred until the enum is live-verified."
    )
