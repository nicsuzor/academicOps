"""Gate verdict logic — parameterised across gates × modes.

Tests that the gate system produces correct block/warn/allow verdicts.
Uses fixture data for scenario-driven tests and parameterised mode overrides.
"""

import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from tests.hooks.gate_helpers import (
    GateVerdict,
    flatten_scenarios,
    make_context,
    make_gate_trigger_context,
    make_gate_trigger_state,
    make_session_state,
    reinit_gates_with_defaults,
    set_gate_modes,
)

# --- Gate mode override parameterisation ---

_GATE_MODE_CASES = [
    ("enforcer", "warn", GateVerdict.WARN),
    ("enforcer", "block", GateVerdict.DENY),
    ("qa", "warn", GateVerdict.WARN),
    ("qa", "block", GateVerdict.DENY),
    ("handover", "warn", GateVerdict.WARN),
    ("handover", "block", GateVerdict.DENY),
    ("ida", "warn", GateVerdict.WARN),
    ("ida", "block", GateVerdict.DENY),
]


class TestGateModeConfigOverrides:
    """Gate modes control enforcement for all gates."""

    @pytest.mark.parametrize(
        "gate_name,mode,expected_verdict",
        _GATE_MODE_CASES,
        ids=[f"{g}-{m}" for g, m, _ in _GATE_MODE_CASES],
    )
    def test_gate_mode_verdict(self, router, monkeypatch, gate_name, mode, expected_verdict):
        kwargs: dict[str, str] = {gate_name: mode}
        set_gate_modes(monkeypatch, **kwargs)
        reinit_gates_with_defaults()

        state = make_gate_trigger_state(gate_name)
        ctx = make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)

        if expected_verdict is None:
            assert result is None, (
                f"{gate_name} gate with mode={mode} should be ALLOW (None), "
                f"got {result.verdict.value if result else 'N/A'}"
            )
            return

        assert result is not None, (
            f"{gate_name} gate with mode={mode} should produce a verdict, got None"
        )
        assert result.verdict == expected_verdict, (
            f"{gate_name} gate with mode={mode}: "
            f"expected {expected_verdict.value}, got {result.verdict.value}"
        )


# --- Read-only bypass ---


class TestReadOnlyBypassesEnforcer:
    """Read-only tools bypass enforcer gate (unlike write tools)."""

    SCENARIOS = flatten_scenarios("read_only_bypasses_enforcer")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_read_bypasses_enforcer(self, router, scenario):
        state = make_session_state(scenario)
        ctx = make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] Read-only tool '{scenario['tool_name']}' "
                f"should bypass enforcer gate, got {result.verdict.value}"
            )


# --- Re-audit instruction content ---


class TestEnforcerReAuditInstructionContent:
    """Enforcer instruction template must contain re-audit judgment rules (R5).

    These tests guard against the re-audit noise regression: the enforcer fires
    on whole-session history, so without explicit re-audit rules RBG re-litigates
    already-noted violations on every pass. The instruction must tell RBG to
    distinguish RESOLVED / UNRESOLVED PRIOR / NEW ACTIVITY findings.
    """

    @pytest.fixture(autouse=True)
    def _registry(self):
        from lib.template_registry import TemplateRegistry

        self._reg = TemplateRegistry.instance()

    def _render(self) -> str:
        return self._reg.render("enforcer.instruction", {"temp_path": "/tmp/audit-test.md"})

    def test_instruction_has_resolved_rule(self):
        """RBG must be told not to re-raise findings already resolved in-session."""
        content = self._render()
        assert "RESOLVED" in content, (
            "enforcer.instruction must contain RESOLVED re-audit rule — "
            "RBG must know not to re-raise already-remediated findings."
        )
        assert "do NOT re-raise" in content, (
            "enforcer.instruction must explicitly say 'do NOT re-raise' for resolved findings."
        )

    def test_instruction_has_escalate_rule(self):
        """RBG must escalate unresolved prior findings, not merely restate them."""
        content = self._render()
        assert "ESCALATE" in content, (
            "enforcer.instruction must contain ESCALATE rule — "
            "unresolved prior findings must be escalated, not restated."
        )

    def test_instruction_has_new_activity_rule(self):
        """RBG must judge genuinely new violations (post-last-enforcer) as REVISE."""
        content = self._render()
        assert "NEW ACTIVITY" in content, (
            "enforcer.instruction must contain NEW ACTIVITY rule — "
            "violations after the last enforcer pass should be judged fresh."
        )
