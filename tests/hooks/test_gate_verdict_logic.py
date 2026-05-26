"""Gate verdict logic — parameterised across gates × modes.

Tests that the gate system produces correct block/warn/allow verdicts.
Uses fixture data for scenario-driven tests and parameterised mode overrides.
"""

import pytest

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
    def test_gate_mode_verdict(
        self, router, monkeypatch, tmp_path, gate_name, mode, expected_verdict
    ):
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
