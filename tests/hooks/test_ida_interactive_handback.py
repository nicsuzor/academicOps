"""Ida gate interactive-handback tests — AC#2 of the Ida-elevation PR.

Four invariants verified (mirrors the AC acceptance criteria):

(a) interactive-handback-concise-revisable
    A Stop in an interactive session emits the CONCISE honesty disclosure
    (ida.interactive_reminder content), NOT the full batch manifest.
    Never silent — the floor must be present.

(b) no-re-fire
    Within a single UPS→Stop cycle the disclosure fires once; a second Stop
    in the same turn passes through without re-emitting (fire-once lifecycle
    already present in the gate, tested here as a regression guard).

(c) session-end-byte-identical
    A Stop in a batch (polecat) session renders context_key="ida.reminder"
    byte-identical to the pre-change template — the full manifest is NOT
    replaced for autonomous/polecat sessions.

(d) floor-fires-interactive
    An interactive session ALWAYS receives a honesty check on Stop; the
    interactive register is never silently suppressed. Guards the LOCKED
    "ida always fires in every register" invariant (note-36c15a69 v0.5.3).
"""

from __future__ import annotations

import sys
from pathlib import Path

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.schemas import HookContext
from lib.gate_types import GateStatus, GateVerdict
from lib.session_state import SessionState
from lib.template_registry import TemplateRegistry

from tests.hooks.gate_helpers import reinit_gates_with_defaults

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INTERACTIVE_MARKER = "Quick honesty check"  # phrase unique to interactive template
_BATCH_MARKER = "Before you stop — be honest"  # phrase from the batch manifest


def _make_interactive_state(session_id: str, monkeypatch) -> SessionState:
    """SessionState for a bare interactive (claude-code-cli) session."""
    monkeypatch.delenv("AOPS_POLECAT_CONTAINER", raising=False)
    monkeypatch.delenv("POLECAT_CREW_NAME", raising=False)
    reinit_gates_with_defaults()
    state = SessionState.create(session_id)
    assert state.session_type == "interactive", (
        f"Expected interactive session_type, got {state.session_type!r}"
    )
    return state


def _make_polecat_state(session_id: str, monkeypatch) -> SessionState:
    """SessionState for a polecat (worker) session."""
    monkeypatch.setenv("AOPS_POLECAT_CONTAINER", "1")
    monkeypatch.delenv("POLECAT_CREW_NAME", raising=False)
    reinit_gates_with_defaults()
    state = SessionState.create(session_id)
    assert state.session_type == "polecat", (
        f"Expected polecat session_type, got {state.session_type!r}"
    )
    return state


def _stop_ctx(session_id: str) -> HookContext:
    return HookContext(
        session_id=session_id,
        hook_event="Stop",
        tool_name=None,
        tool_input={},
    )


def _ups_ctx(session_id: str) -> HookContext:
    return HookContext(
        session_id=session_id,
        hook_event="UserPromptSubmit",
        tool_name=None,
        tool_input={},
    )


# ---------------------------------------------------------------------------
# (a) interactive-handback-concise-revisable
# ---------------------------------------------------------------------------


class TestInteractiveHandbackConciseRevisable:
    """Stop in an interactive session emits the CONCISE disclosure.

    Verifies:
    - The Ida gate fires (never silent) — verdict is not None / not allow
    - The context_injection contains the INTERACTIVE marker, not the batch one
    - The disclosure is surfaced via the warn+context_injection channel
      (WARN verdict = advisory, not a hard block)
    """

    def test_interactive_stop_emits_concise_disclosure(self, router, monkeypatch):
        monkeypatch.setenv("IDA_GATE_MODE", "warn")
        sid = "ida-interactive-concise-test"
        state = _make_interactive_state(sid, monkeypatch)
        # Gate starts CLOSED (armed from session start)
        assert state.gates["ida"].status == GateStatus.CLOSED

        ctx = _stop_ctx(sid)
        result = router._dispatch_gates(ctx, state)

        assert result is not None, (
            "Ida gate must fire on Stop in an interactive session (never silent)"
        )
        assert result.verdict == GateVerdict.WARN, (
            f"Interactive Ida must produce WARN (advisory), got {result.verdict!r}"
        )
        assert result.context_injection is not None, (
            "Interactive Ida must deliver context_injection (the honesty disclosure)"
        )
        assert _INTERACTIVE_MARKER in result.context_injection, (
            f"Interactive Stop must use the CONCISE template (look for {_INTERACTIVE_MARKER!r}). "
            f"Got: {result.context_injection[:300]!r}"
        )
        assert _BATCH_MARKER not in result.context_injection, (
            "Interactive Stop must NOT use the full batch manifest"
        )

    def test_interactive_stop_floor_present(self, router, monkeypatch):
        """The concise template still contains the irreducible honesty floor."""
        monkeypatch.setenv("IDA_GATE_MODE", "warn")
        sid = "ida-interactive-floor-test"
        state = _make_interactive_state(sid, monkeypatch)

        ctx = _stop_ctx(sid)
        result = router._dispatch_gates(ctx, state)

        assert result is not None
        inj = result.context_injection or ""
        # Floor: "actually asked" (not adjacent/easier version)
        assert "actually asked" in inj, (
            "Concise template must check 'delivered what was actually asked'"
        )
        # Floor: observed vs inferred
        assert "observed" in inj or "infer" in inj, (
            "Concise template must distinguish observed from inferred"
        )


# ---------------------------------------------------------------------------
# (b) no-re-fire
# ---------------------------------------------------------------------------


class TestNoRefire:
    """Within a single UPS→Stop cycle the disclosure fires once, not twice.

    The gate opens (fire-once) on the first Stop so a second Stop in the
    same turn passes without re-blocking. Re-arms on the next UPS.
    """

    def test_second_stop_in_same_turn_passes(self, router, monkeypatch):
        monkeypatch.setenv("IDA_GATE_MODE", "warn")
        sid = "ida-no-refire-test"
        state = _make_interactive_state(sid, monkeypatch)
        # Open the qa gate so it doesn't interfere
        state.gates["qa"].status = GateStatus.OPEN

        ctx = _stop_ctx(sid)

        # First Stop: Ida fires (WARN)
        result1 = router._dispatch_gates(ctx, state)
        assert result1 is not None, "First Stop should produce a result"

        # Gate should now be OPEN (fire-once trigger fired)
        assert state.gates["ida"].status == GateStatus.OPEN, (
            "Ida gate should open after first Stop (fire-once lifecycle)"
        )

        # Second Stop in same turn: Ida must NOT fire again
        # (gate is OPEN — the CLOSED condition fails)
        result2 = router._dispatch_gates(ctx, state)
        # result2 may be None (allow) or from a different gate — but Ida
        # specifically must not be producing a WARN with its context_injection
        if result2 is not None and result2.context_injection:
            assert _INTERACTIVE_MARKER not in result2.context_injection, (
                "Ida must not re-fire the interactive disclosure on a second Stop in the same turn"
            )
            assert _BATCH_MARKER not in result2.context_injection, (
                "Ida must not re-fire any manifest on a second Stop in the same turn"
            )

    def test_rearms_on_next_ups(self, router, monkeypatch):
        """After UPS the gate re-arms, so the NEXT turn's Stop fires again."""
        monkeypatch.setenv("IDA_GATE_MODE", "warn")
        sid = "ida-rearm-test"
        state = _make_interactive_state(sid, monkeypatch)
        state.gates["qa"].status = GateStatus.OPEN

        # Turn 1: Stop fires, gate opens
        result1 = router._dispatch_gates(_stop_ctx(sid), state)
        assert result1 is not None
        assert state.gates["ida"].status == GateStatus.OPEN

        # UPS: re-arm
        router._dispatch_gates(_ups_ctx(sid), state)
        assert state.gates["ida"].status == GateStatus.CLOSED, (
            "Ida gate must re-arm (CLOSED) after UserPromptSubmit"
        )

        # Turn 2: Stop fires again (re-armed)
        result2 = router._dispatch_gates(_stop_ctx(sid), state)
        assert result2 is not None, "Ida must fire again after UPS re-arm"


# ---------------------------------------------------------------------------
# (c) session-end-byte-identical
# ---------------------------------------------------------------------------


class TestSessionEndByteIdentical:
    """A polecat Stop renders context_key='ida.reminder' — the full batch manifest.

    Verifies that the batch reminder template is byte-identical to the
    template on disk (guards against the interactive policies accidentally
    routing polecat sessions to the concise template).
    """

    def test_polecat_stop_uses_full_manifest(self, router, monkeypatch):
        monkeypatch.setenv("IDA_GATE_MODE", "warn")
        sid = "ida-polecat-byte-identical-test"
        state = _make_polecat_state(sid, monkeypatch)
        state.gates["qa"].status = GateStatus.OPEN
        state.gates["handover"].status = GateStatus.OPEN

        ctx = _stop_ctx(sid)
        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Ida must fire in a polecat session"
        assert result.context_injection is not None

        assert _BATCH_MARKER in result.context_injection, (
            "Polecat Stop must render the FULL batch manifest (ida.reminder), "
            f"not the interactive concise version. Got: {result.context_injection[:300]!r}"
        )
        assert _INTERACTIVE_MARKER not in result.context_injection, (
            "Polecat Stop must NOT render the interactive concise template"
        )

    def test_polecat_manifest_matches_template_on_disk(self, router, monkeypatch):
        """The polecat ida.reminder context_injection contains the template file content.

        The gate engine wraps context_injection in <SYSTEM HOOK INSTRUCTION> tags;
        we strip those before comparing against the raw template content.
        """
        monkeypatch.setenv("IDA_GATE_MODE", "warn")
        sid = "ida-polecat-disk-match-test"
        state = _make_polecat_state(sid, monkeypatch)
        state.gates["qa"].status = GateStatus.OPEN
        state.gates["handover"].status = GateStatus.OPEN

        ctx = _stop_ctx(sid)
        result = router._dispatch_gates(ctx, state)
        assert result is not None and result.context_injection is not None

        # Strip the <SYSTEM HOOK INSTRUCTION> wrapper the engine adds
        inj = result.context_injection
        inj = inj.replace("<SYSTEM HOOK INSTRUCTION>", "").replace("</SYSTEM HOOK INSTRUCTION>", "")

        # Load the template directly from the registry
        registry = TemplateRegistry.instance()
        expected = registry.render("ida.reminder")

        assert inj.strip() == expected.strip(), (
            "Polecat Ida context_injection must be byte-identical to the "
            "ida.reminder template on disk (AC#2: session-end-byte-identical)"
        )


# ---------------------------------------------------------------------------
# (d) floor-fires-interactive
# ---------------------------------------------------------------------------


class TestFloorFiresInteractive:
    """Interactive sessions ALWAYS receive a honesty check — never suppressed.

    Guards the LOCKED "ida fires in every register" invariant from
    note-36c15a69 v0.5.3.
    """

    def test_interactive_stop_never_silent(self, router, monkeypatch):
        monkeypatch.setenv("IDA_GATE_MODE", "warn")
        sid = "ida-floor-fires-test"
        state = _make_interactive_state(sid, monkeypatch)
        # Open QA and handover so their verdicts don't mask Ida
        state.gates["qa"].status = GateStatus.OPEN
        state.gates["handover"].status = GateStatus.OPEN

        ctx = _stop_ctx(sid)
        result = router._dispatch_gates(ctx, state)

        assert result is not None, (
            "Ida MUST fire on Stop in an interactive session — never silent. "
            "The 'ida always on every register' invariant (note-36c15a69 v0.5.3) is violated."
        )
        inj = result.context_injection or ""
        assert inj.strip(), "Ida context_injection must be non-empty in an interactive session"

    def test_interactive_honesty_check_uses_correct_template(self, router, monkeypatch):
        """Interactive sessions get ida.interactive_reminder (concise), not ida.reminder (batch).

        The gate engine wraps context_injection in <SYSTEM HOOK INSTRUCTION> tags;
        we strip those before comparing against the raw template content.
        """
        monkeypatch.setenv("IDA_GATE_MODE", "warn")
        sid = "ida-template-correct-test"
        state = _make_interactive_state(sid, monkeypatch)
        state.gates["qa"].status = GateStatus.OPEN
        state.gates["handover"].status = GateStatus.OPEN

        ctx = _stop_ctx(sid)
        result = router._dispatch_gates(ctx, state)

        assert result is not None
        raw_inj = result.context_injection or ""

        # Strip the <SYSTEM HOOK INSTRUCTION> wrapper the engine adds
        inj = raw_inj.replace("<SYSTEM HOOK INSTRUCTION>", "").replace(
            "</SYSTEM HOOK INSTRUCTION>", ""
        )

        registry = TemplateRegistry.instance()
        interactive_template = registry.render("ida.interactive_reminder")
        batch_template = registry.render("ida.reminder")

        assert inj.strip() == interactive_template.strip(), (
            "Interactive Stop must render ida.interactive_reminder exactly. "
            f"Got (first 200 chars): {inj[:200]!r}"
        )
        assert inj.strip() != batch_template.strip(), (
            "Interactive Stop must NOT render the batch ida.reminder"
        )
