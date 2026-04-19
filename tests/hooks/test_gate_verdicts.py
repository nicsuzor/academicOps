#!/usr/bin/env python3
"""Gate verdict regression tests driven by saved scenario fixtures.

Validates that the gate system produces the correct block/warn/allow verdicts
for every realistic hook call scenario. Uses JSON fixture data that replicates
actual Claude Code and Gemini CLI hook invocations.

Key invariants tested:
1. Compliance agents (hydrator, enforcer, audit, butler) are NEVER blocked
2. Read-only tools bypass enforcer gate (unlike write tools)
3. Infrastructure tools bypass ALL gates; spawn tools (Agent, Skill) do NOT
4. Enforcer blocks at ops threshold for write/spawn tools only
5. Stop event respects handover and QA gates
6. Claude Code and Gemini CLI output formats match their respective schemas
7. Gate triggers (enforcer resets counter) fire correctly
8. Gate mode env var overrides work correctly
9. Enforcer deadlock prevented: Agent(enforcer) dispatch resets counter before policy fires

Run with:
    uv run pytest tests/hooks/test_gate_verdicts.py -v
"""

import importlib
import json
import sys
from pathlib import Path

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter
from hooks.schemas import (
    HookContext,
)
from lib.gate_model import GateVerdict
from lib.gate_types import GateState, GateStatus
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState

# --- Fixture loading ---

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCENARIOS_FILE = FIXTURES_DIR / "gate_scenarios.json"
LIVE_SCENARIOS_FILE = FIXTURES_DIR / "gate_scenarios_live.json"


def _load_scenarios() -> dict:
    """Load scenarios from both fixture files.

    Legacy fixtures (gate_scenarios.json) provide scenarios for test invariants
    like gate_overrides, compliance bypass, etc. Live fixtures (gate_scenarios_live.json)
    are extracted from real hook logs with provenance metadata — these are the
    source of truth for platform-specific behavior.
    """
    with SCENARIOS_FILE.open() as f:
        scenarios = json.load(f)
    if LIVE_SCENARIOS_FILE.exists():
        with LIVE_SCENARIOS_FILE.open() as f:
            live = json.load(f)
        scenarios.update(live)
    return scenarios


ALL_SCENARIOS = _load_scenarios()


def _flatten_scenarios(*groups: str) -> list[dict]:
    """Flatten named scenario groups into a list of scenario dicts."""
    result = []
    for group in groups:
        scenarios = ALL_SCENARIOS.get(group, [])
        for s in scenarios:
            s["_group"] = group
            result.append(s)
    return result


# --- Test helpers ---


def _reinit_gates_with_defaults():
    """Reload gate_config and definitions with current env vars, reinit registry.

    All imports use qualified paths from aops-core/ root (e.g. hooks.gate_config,
    not bare gate_config), so there is exactly one sys.modules entry per module.
    """
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


def _make_session_state(scenario: dict) -> SessionState:
    """Create a SessionState with gate overrides from the scenario."""
    state = SessionState.create("test-session-verdict")

    # Apply gate overrides
    for gate_name, overrides in scenario.get("gate_overrides", {}).items():
        gate = state.gates.get(gate_name, GateState())
        if "status" in overrides:
            gate.status = GateStatus(overrides["status"])
        if "ops_since_open" in overrides:
            gate.ops_since_open = overrides["ops_since_open"]
        if "ops_since_close" in overrides:
            gate.ops_since_close = overrides["ops_since_close"]
        if "metrics" in overrides:
            gate.metrics.update(overrides["metrics"])
        state.gates[gate_name] = gate

    # Apply state dict overrides (e.g. hydrator_active)
    for key, value in scenario.get("state_overrides", {}).items():
        state.state[key] = value

    return state


def _make_context(scenario: dict) -> HookContext:
    """Create a HookContext from scenario data."""
    return HookContext(
        session_id="test-session-verdict",
        hook_event=scenario["hook_event"],
        tool_name=scenario.get("tool_name"),
        tool_input=scenario.get("tool_input", {}),
        is_subagent=scenario.get("is_subagent", False),
        subagent_type=scenario.get("subagent_type"),
        raw_input=scenario.get("raw_input", {}),
    )


def _make_gate_trigger_state(gate_name: str) -> SessionState:
    """Create a SessionState that will cause the named gate's policy to fire.

    - enforcer: ops_since_open at threshold so policy condition is met
    - qa / handover: gate CLOSED so Stop-event policy fires
    """
    state = SessionState.create("test-gate-mode")
    if gate_name == "enforcer":
        from hooks.gate_config import ENFORCER_TOOL_CALL_THRESHOLD

        state.gates["enforcer"].ops_since_open = ENFORCER_TOOL_CALL_THRESHOLD
    elif gate_name in ("qa", "handover"):
        # Ensure gate state exists (qa may not be in default_gates)
        if gate_name not in state.gates:
            state.gates[gate_name] = GateState(status=GateStatus.CLOSED)
        else:
            state.gates[gate_name].status = GateStatus.CLOSED
        # QA template requires temp_path metric
        if gate_name == "qa":
            state.gates[gate_name].metrics["temp_path"] = "/tmp/qa-gate.md"
    return state


def _make_gate_trigger_context(gate_name: str) -> HookContext:
    """Create a HookContext that will trigger the named gate's policy.

    - enforcer: PreToolUse on a spawn tool (Agent) that isn't excluded
    - qa / handover: Stop event
    """
    if gate_name == "enforcer":
        return HookContext(
            session_id="test-gate-mode",
            hook_event="PreToolUse",
            tool_name="Agent",
            tool_input={"prompt": "test"},
        )
    else:
        # qa and handover both fire on Stop
        return HookContext(
            session_id="test-gate-mode",
            hook_event="Stop",
        )


@pytest.fixture(autouse=True)
def _deterministic_gate_modes(monkeypatch):
    """Ensure gate modes use known defaults regardless of env.

    This prevents test flakiness from env var leakage when tests run
    inside a live Claude Code session.
    """
    monkeypatch.setenv("HYDRATION_GATE_MODE", "off")
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.setenv("QA_GATE_MODE", "block")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "warn")
    _reinit_gates_with_defaults()


@pytest.fixture
def router(monkeypatch):
    """Create a HookRouter with mocked session data."""
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


class TestReadOnlyBypassesEnforcer:
    """Read-only tools bypass enforcer gate (unlike write tools).

    The enforcer gate excludes both always_available AND read_only categories.
    This allows agents to read files even when enforcer threshold is exceeded.
    """

    SCENARIOS = _flatten_scenarios("read_only_bypasses_enforcer")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_read_bypasses_enforcer(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        # Should be ALLOW (or None which means allow)
        if result is not None:
            assert result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] Read-only tool '{scenario['tool_name']}' "
                f"should bypass enforcer gate, got {result.verdict.value}"
            )


# ===========================================================================
# GATE MODE ENV VAR CASES: non-hydration gates
# ===========================================================================

_GATE_MODE_CASES = [
    # Enforcer: default=block
    ("enforcer", "ENFORCER_GATE_MODE", "warn", GateVerdict.WARN),
    ("enforcer", "ENFORCER_GATE_MODE", "block", GateVerdict.DENY),
    ("enforcer", "ENFORCER_GATE_MODE", "deny", GateVerdict.DENY),
    # QA: default=block
    ("qa", "QA_GATE_MODE", "warn", GateVerdict.WARN),
    ("qa", "QA_GATE_MODE", "block", GateVerdict.DENY),
    ("qa", "QA_GATE_MODE", "deny", GateVerdict.DENY),
    # Handover: default=warn
    ("handover", "HANDOVER_GATE_MODE", "warn", GateVerdict.WARN),
    ("handover", "HANDOVER_GATE_MODE", "block", GateVerdict.DENY),
    ("handover", "HANDOVER_GATE_MODE", "deny", GateVerdict.DENY),
]


class TestGateModeEnvVarOverrides:
    """Verify *_GATE_MODE env vars control enforcement for all gates.

    Each gate's mode env var (e.g. HANDOVER_GATE_MODE=block) must produce
    the correct verdict when the gate's policy fires. Tests every gate x
    every valid mode value (warn, block, deny).
    """

    @pytest.mark.parametrize(
        "gate_name,env_var,mode,expected_verdict",
        _GATE_MODE_CASES,
        ids=[f"{g}-{m}" for g, _, m, _ in _GATE_MODE_CASES],
    )
    def test_gate_mode_verdict(
        self, router, monkeypatch, gate_name, env_var, mode, expected_verdict
    ):
        monkeypatch.setenv(env_var, mode)
        _reinit_gates_with_defaults()

        state = _make_gate_trigger_state(gate_name)
        ctx = _make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)

        if expected_verdict is None:
            assert result is None, (
                f"{gate_name} gate with {env_var}={mode} should be ALLOW (None), "
                f"got {result.verdict.value if result else 'N/A'}"
            )
            return

        assert result is not None, (
            f"{gate_name} gate with {env_var}={mode} should produce a verdict, got None (allow)"
        )
        assert result.verdict == expected_verdict, (
            f"{gate_name} gate with {env_var}={mode}: "
            f"expected {expected_verdict.value}, got {result.verdict.value}"
        )


class TestHandoverGateOpens:
    SCENARIOS = _flatten_scenarios("handover_gate_opens")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_handover_gate_opens_on_event(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        router._dispatch_gates(ctx, state)

        # The handover gate should now be OPEN
        assert state.gates["handover"].status == GateStatus.OPEN, (
            f"[{scenario['id']}] Handover gate should be OPEN in response, "
            f"but got {state.gates['handover'].status}"
        )
