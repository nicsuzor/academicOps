#!/usr/bin/env python3
"""Gate verdict regression tests driven by saved scenario fixtures.

Validates that the gate system produces the correct block/warn/allow verdicts
for every realistic hook call scenario. Uses JSON fixture data that replicates
actual Claude Code and Gemini CLI hook invocations.

Key invariants tested:
1. Compliance agents (hydrator, custodiet, audit, butler) are NEVER blocked
2. Write tools ARE blocked/warned when hydration gate is closed
3. Read-only tools are subject to hydration gate (only infrastructure is exempt)
4. Read-only tools bypass custodiet gate (unlike write tools)
5. Infrastructure tools bypass ALL gates; spawn tools (Agent, Skill) do NOT
6. Custodiet blocks at ops threshold for write/spawn tools only
7. Stop event respects handover and QA gates
8. Claude Code and Gemini CLI output formats match their respective schemas
9. Gate triggers (hydrator opens gate, custodiet resets counter) fire correctly
10. Gate mode env var overrides work correctly
11. Custodiet deadlock prevented: Agent(custodiet) dispatch resets counter before policy fires

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

from hooks.gate_config import (
    COMPLIANCE_SUBAGENT_TYPES,
    CUSTODIET_TOOL_CALL_THRESHOLD,
    extract_subagent_type,
    get_tool_category,
)
from hooks.router import HookRouter
from hooks.schemas import (
    CanonicalHookOutput,
    ClaudeGeneralHookOutput,
    ClaudeStopHookOutput,
    GeminiHookOutput,
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
    )


@pytest.fixture(autouse=True)
def _deterministic_gate_modes(monkeypatch):
    """Ensure gate modes use known defaults regardless of env.

    This prevents test flakiness from env var leakage when tests run
    inside a live Claude Code session.
    """
    monkeypatch.setenv("HYDRATION_GATE_MODE", "warn")
    monkeypatch.setenv("CUSTODIET_GATE_MODE", "block")
    monkeypatch.setenv("QA_GATE_MODE", "block")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "warn")
    _reinit_gates_with_defaults()
    yield
    # Cleanup: reinit after test to avoid cross-test pollution
    _reinit_gates_with_defaults()


@pytest.fixture
def router(monkeypatch):
    """Create a HookRouter with mocked session data."""
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


@pytest.fixture(params=["warn", "block"], ids=["hydration=warn", "hydration=block"])
def hydration_mode(request, monkeypatch):
    """Run hydration gate tests in both warn and block modes."""
    monkeypatch.setenv("HYDRATION_GATE_MODE", request.param)
    _reinit_gates_with_defaults()
    return request.param


# ===========================================================================
# HYDRATION GATE: Write tools warned when closed
# ===========================================================================


class TestHydrationGateBlocksWriteTools:
    """Write-category tools get mode-appropriate verdict when hydration gate is closed.

    warn mode -> WARN (tool allowed, agent warned to hydrate)
    block mode -> DENY (tool blocked until hydration)
    """

    SCENARIOS = _flatten_scenarios("hydration_gate_blocks_write_tools")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_write_tool_verdict_matches_mode(self, router, hydration_mode, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        expected = GateVerdict.WARN if hydration_mode == "warn" else GateVerdict.DENY
        assert result is not None, (
            f"[{scenario['id']}] Expected {expected.value} but got None (allow) "
            f"in {hydration_mode} mode"
        )
        assert result.verdict == expected, (
            f"[{scenario['id']}] Write tool '{scenario['tool_name']}' should be "
            f"{expected.value} in {hydration_mode} mode, got {result.verdict.value}"
        )


# ===========================================================================
# HYDRATION GATE: Read-only tools are subject to hydration (only
# always_available is exempt from hydration policy)
# ===========================================================================


class TestHydrationGateReadOnlyTools:
    """Read-only tools are subject to hydration gate — only always_available is exempt.

    warn mode -> WARN (tool allowed, agent warned to hydrate)
    block mode -> DENY (tool blocked until hydration)
    """

    SCENARIOS = _flatten_scenarios("hydration_gate_warns_read_only")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_read_tool_verdict_matches_mode(self, router, hydration_mode, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        expected = GateVerdict.WARN if hydration_mode == "warn" else GateVerdict.DENY
        assert result is not None, (
            f"[{scenario['id']}] Expected {expected.value} but got None (allow) "
            f"in {hydration_mode} mode"
        )
        assert result.verdict == expected, (
            f"[{scenario['id']}] Read-only tool '{scenario['tool_name']}' should be "
            f"{expected.value} in {hydration_mode} mode, got {result.verdict.value}"
        )


class TestReadOnlyBypassesCustodiet:
    """Read-only tools bypass custodiet gate (unlike write tools).

    The custodiet gate excludes both always_available AND read_only categories.
    This allows agents to read files even when custodiet threshold is exceeded.
    """

    SCENARIOS = _flatten_scenarios("read_only_bypasses_custodiet")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_read_bypasses_custodiet(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        # Should be ALLOW (or None which means allow)
        if result is not None:
            assert result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] Read-only tool '{scenario['tool_name']}' "
                f"should bypass custodiet gate, got {result.verdict.value}"
            )


# ===========================================================================
# HYDRATION GATE: Always-available tools pass through
# ===========================================================================


class TestHydrationGateAllowsInfrastructure:
    """Infrastructure tools must bypass ALL gates."""

    SCENARIOS = _flatten_scenarios("hydration_gate_allows_always_available")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_infrastructure_allowed(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            # Note: always_available_bypass contains some Agent calls which are now BLOCKED.
            # We filter those out in the logic below.
            if get_tool_category(scenario["tool_name"]) == "infrastructure":
                assert result.verdict == GateVerdict.ALLOW, (
                    f"[{scenario['id']}] Infrastructure tool '{scenario['tool_name']}' "
                    f"should be ALLOW, got {result.verdict.value}"
                )


class TestHydrationGateBlocksSpawn:
    """Spawn tools (Agent, Task, Skill) are BLOCKED by hydration gate."""

    SCENARIOS = [
        {
            "id": "agent_blocked_when_hydration_closed",
            "description": "Agent (spawn) blocked by hydration gate",
            "hook_event": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "explorer"},
            "is_subagent": False,
            "gate_overrides": {
                "hydration": {"status": "closed", "metrics": {"temp_path": "/tmp/hydration.md"}}
            },
        },
        {
            "id": "delegate_to_agent_blocked_when_hydration_closed",
            "description": "delegate_to_agent (spawn) blocked by hydration gate",
            "hook_event": "PreToolUse",
            "tool_name": "delegate_to_agent",
            "tool_input": {"name": "explorer"},
            "is_subagent": False,
            "gate_overrides": {
                "hydration": {"status": "closed", "metrics": {"temp_path": "/tmp/hydration.md"}}
            },
        },
    ]

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_spawn_blocked(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        # Spawn tools must be BLOCKED/WARNED
        assert result is not None
        assert result.verdict != GateVerdict.ALLOW


# ===========================================================================
# HYDRATION GATE: Open gate allows all tools
# ===========================================================================


class TestHydrationGateAllowsWhenOpen:
    """When hydration gate is open, all tools should pass."""

    SCENARIOS = _flatten_scenarios("hydration_gate_allows_when_open")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_tool_allowed_when_open(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] Tool '{scenario['tool_name']}' should be ALLOW "
                f"when hydration gate is open, got {result.verdict.value}"
            )


# ===========================================================================
# COMPLIANCE AGENT BYPASS: hydrator/custodiet/audit/butler NEVER blocked
# ===========================================================================


class TestComplianceAgentBypass:
    """Compliance agents must NEVER receive DENY verdicts from gates.

    This is the critical invariant: hydrator, custodiet, audit, and butler
    subagents bypass gate POLICIES (blocking/warning) while still allowing
    triggers to fire (so gate state transitions update correctly).
    """

    SCENARIOS = _flatten_scenarios("compliance_agent_bypass")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_compliance_agent_never_denied(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                f"[{scenario['id']}] Compliance agent '{scenario['subagent_type']}' "
                f"calling '{scenario['tool_name']}' was DENIED — this must never happen. "
                f"Compliance agents bypass gate policies."
            )
            assert result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] Compliance agent '{scenario['subagent_type']}' "
                f"got {result.verdict.value}, expected ALLOW"
            )


class TestComplianceSubagentTypesComplete:
    """Verify all expected compliance types are registered."""

    EXPECTED_TYPES = {
        "hydrator",
        "prompt-hydrator",
        "aops-core:prompt-hydrator",
        "custodiet",
        "aops-core:custodiet",
        "audit",
        "aops-core:audit",
        "butler",
        "aops-core:butler",
        "qa",
        "aops-core:qa",
    }

    def test_all_expected_types_registered(self):
        for t in self.EXPECTED_TYPES:
            assert t in COMPLIANCE_SUBAGENT_TYPES, f"'{t}' missing from COMPLIANCE_SUBAGENT_TYPES"

    def test_no_unexpected_types(self):
        """Guard against accidental additions that weaken gate enforcement."""
        for t in COMPLIANCE_SUBAGENT_TYPES:
            assert t in self.EXPECTED_TYPES, (
                f"Unexpected type '{t}' in COMPLIANCE_SUBAGENT_TYPES — "
                f"adding new compliance types weakens gate enforcement"
            )


# ===========================================================================
# NON-COMPLIANCE SUBAGENTS: Still subject to gates
# ===========================================================================


class TestNonComplianceSubagentBlocked:
    """Non-compliance subagents get mode-appropriate verdict when hydration gate is closed.

    warn mode -> WARN
    block mode -> DENY
    """

    SCENARIOS = _flatten_scenarios("non_compliance_subagent_blocked")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_non_compliance_verdict_matches_mode(self, router, hydration_mode, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        expected = GateVerdict.WARN if hydration_mode == "warn" else GateVerdict.DENY
        assert result is not None, (
            f"[{scenario['id']}] Expected {expected.value} but got None (allow) "
            f"in {hydration_mode} mode"
        )
        assert result.verdict == expected, (
            f"[{scenario['id']}] Non-compliance agent '{scenario['subagent_type']}' "
            f"should be {expected.value} in {hydration_mode} mode, got {result.verdict.value}"
        )


# ===========================================================================
# CUSTODIET GATE: Block at threshold
# ===========================================================================


class TestCustodietGateBlocksAtThreshold:
    """Custodiet gate must block write tools when ops exceed threshold (default mode=block)."""

    SCENARIOS = _flatten_scenarios("custodiet_gate_blocks_at_threshold")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_custodiet_verdict(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        expected = scenario["expected"]["verdict"]
        if expected == "allow":
            if result is not None:
                assert result.verdict == GateVerdict.ALLOW, (
                    f"[{scenario['id']}] Expected ALLOW, got {result.verdict.value}"
                )
        elif expected == "deny":
            assert result is not None, f"[{scenario['id']}] Expected DENY but got None (allow)"
            assert result.verdict == GateVerdict.DENY, (
                f"[{scenario['id']}] Expected DENY, got {result.verdict.value}"
            )


# ===========================================================================
# TRIGGER TESTS: Hydrator opens gate, custodiet resets counter
# ===========================================================================


class TestHydrationTriggerOpensGate:
    """Hydrator subagent events must open the hydration gate."""

    SCENARIOS = _flatten_scenarios("hydration_trigger_opens_gate")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_hydrator_opens_gate(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        router._dispatch_gates(ctx, state)

        expected_gate_after = scenario["expected"].get("gate_after", {})
        for gate_name, expected_status in expected_gate_after.items():
            actual = state.gates[gate_name].status
            assert actual == expected_status, (
                f"[{scenario['id']}] Gate '{gate_name}' should be "
                f"'{expected_status}' after event, got '{actual}'"
            )


class TestCustodietTriggerResetsCounter:
    """Custodiet subagent events must reset the ops counter."""

    SCENARIOS = _flatten_scenarios("custodiet_trigger_resets_counter")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_custodiet_resets_ops(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        pre_ops = state.gates["custodiet"].ops_since_open

        router._dispatch_gates(ctx, state)

        post_ops = state.gates["custodiet"].ops_since_open
        if scenario["expected"].get("ops_reset"):
            assert post_ops == 0, (
                f"[{scenario['id']}] Expected ops_since_open reset to 0, "
                f"got {post_ops} (was {pre_ops})"
            )


# ===========================================================================
# STOP EVENT: Handover and QA gates
# ===========================================================================


class TestStopGateBehavior:
    """Stop event must respect handover and QA gates."""

    SCENARIOS = _flatten_scenarios("stop_gate_behavior")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_stop_verdict(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        expected = scenario["expected"]["verdict"]
        if expected == "allow":
            if result is not None:
                assert result.verdict == GateVerdict.ALLOW, (
                    f"[{scenario['id']}] Expected ALLOW, got {result.verdict.value}"
                )
        elif expected == "deny":
            assert result is not None, f"[{scenario['id']}] Expected DENY but got None"
            assert result.verdict == GateVerdict.DENY, (
                f"[{scenario['id']}] Expected DENY, got {result.verdict.value}"
            )
        elif expected == "warn":
            assert result is not None, f"[{scenario['id']}] Expected WARN but got None"
            assert result.verdict == GateVerdict.WARN, (
                f"[{scenario['id']}] Expected WARN, got {result.verdict.value}"
            )


# ===========================================================================
# CLAUDE CODE OUTPUT FORMAT
# ===========================================================================


class TestClaudeOutputFormat:
    """Verify Claude Code hook output matches its expected schema."""

    SCENARIOS = _flatten_scenarios("claude_output_format")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_claude_format(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        gate_result = router._dispatch_gates(ctx, state)
        assert gate_result is not None, f"[{scenario['id']}] Expected gate result but got None"

        canonical = router._gate_result_to_canonical(gate_result)
        output = router.output_for_claude(canonical, scenario["hook_event"])

        expected = scenario["expected"]

        if "claude_permission_decision" in expected:
            assert isinstance(output, ClaudeGeneralHookOutput), (
                f"[{scenario['id']}] Expected ClaudeGeneralHookOutput"
            )
            assert output.hookSpecificOutput is not None
            assert (
                output.hookSpecificOutput.permissionDecision
                == expected["claude_permission_decision"]
            ), (
                f"[{scenario['id']}] Claude permissionDecision: "
                f"expected {expected['claude_permission_decision']}, "
                f"got {output.hookSpecificOutput.permissionDecision}"
            )

        if "claude_stop_decision" in expected:
            assert isinstance(output, ClaudeStopHookOutput), (
                f"[{scenario['id']}] Expected ClaudeStopHookOutput"
            )
            assert output.decision == expected["claude_stop_decision"], (
                f"[{scenario['id']}] Claude stop decision: "
                f"expected {expected['claude_stop_decision']}, got {output.decision}"
            )


# ===========================================================================
# GEMINI CLI OUTPUT FORMAT
# ===========================================================================


class TestGeminiOutputFormat:
    """Verify Gemini CLI hook output matches its expected schema."""

    SCENARIOS = _flatten_scenarios("gemini_output_format")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_gemini_format(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        gate_result = router._dispatch_gates(ctx, state)

        if gate_result:
            canonical = router._gate_result_to_canonical(gate_result)
        else:
            canonical = CanonicalHookOutput()

        output = router.output_for_gemini(canonical, scenario["hook_event"])

        expected = scenario["expected"]
        assert isinstance(output, GeminiHookOutput)

        if "gemini_decision" in expected:
            assert output.decision == expected["gemini_decision"], (
                f"[{scenario['id']}] Gemini decision: "
                f"expected {expected['gemini_decision']}, got {output.decision}"
            )


# ===========================================================================
# COMBINED GATE INTERACTIONS
# ===========================================================================


class TestCombinedGateInteractions:
    """Test that multiple gates interacting produce correct merged verdicts."""

    SCENARIOS = _flatten_scenarios("combined_gate_interactions")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_combined_verdict(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        expected = scenario["expected"]

        if expected.get("not_allow"):
            assert result is not None, f"[{scenario['id']}] Expected non-allow verdict but got None"
            assert result.verdict != GateVerdict.ALLOW, (
                f"[{scenario['id']}] Expected non-allow verdict, got ALLOW"
            )

        if "verdict_in" in expected:
            assert result is not None
            assert result.verdict.value in expected["verdict_in"], (
                f"[{scenario['id']}] Expected verdict in {expected['verdict_in']}, "
                f"got {result.verdict.value}"
            )

        if "verdict" in expected:
            expected_verdict = expected["verdict"]
            if expected_verdict == "allow":
                if result is not None:
                    assert result.verdict == GateVerdict.ALLOW, (
                        f"[{scenario['id']}] Expected ALLOW, got {result.verdict.value}"
                    )
            elif expected_verdict == "deny":
                assert result is not None, f"[{scenario['id']}] Expected DENY but got None (allow)"
                assert result.verdict == GateVerdict.DENY, (
                    f"[{scenario['id']}] Expected DENY, got {result.verdict.value}"
                )
            elif expected_verdict == "warn":
                assert result is not None, f"[{scenario['id']}] Expected WARN but got None (allow)"
                assert result.verdict == GateVerdict.WARN, (
                    f"[{scenario['id']}] Expected WARN, got {result.verdict.value}"
                )


# ===========================================================================
# HYDRATION OUTPUT FORMAT: Verify Claude/Gemini output across modes (issue #710)
# ===========================================================================


class TestHydrationOutputFormat:
    """Verify Claude and Gemini output format reflects hydration gate mode.

    Parameterized across warn/block modes using JSON fixture scenarios.
    Each scenario defines expected output for both modes:
      warn_mode: verdict=warn, claude permissionDecision=allow, gemini decision=allow
      block_mode: verdict=deny, claude permissionDecision=deny, gemini decision=deny
    """

    SCENARIOS = _flatten_scenarios("hydration_output_format_synthetic")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_claude_output_matches_mode(self, router, hydration_mode, scenario):
        """Claude permissionDecision must match hydration gate mode."""
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        gate_result = router._dispatch_gates(ctx, state)
        assert gate_result is not None, (
            f"[{scenario['id']}] Expected gate result but got None (allow) in {hydration_mode} mode"
        )

        expected = scenario["expected"][f"{hydration_mode}_mode"]

        assert gate_result.verdict.value == expected["verdict"], (
            f"[{scenario['id']}] verdict: expected {expected['verdict']}, "
            f"got {gate_result.verdict.value} in {hydration_mode} mode"
        )

        canonical = router._gate_result_to_canonical(gate_result)
        output = router.output_for_claude(canonical, scenario["hook_event"])

        assert isinstance(output, ClaudeGeneralHookOutput)
        assert output.hookSpecificOutput is not None
        assert (
            output.hookSpecificOutput.permissionDecision == expected["claude_permission_decision"]
        ), (
            f"[{scenario['id']}] Claude permissionDecision: "
            f"expected {expected['claude_permission_decision']}, "
            f"got {output.hookSpecificOutput.permissionDecision} "
            f"in {hydration_mode} mode"
        )

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_gemini_output_matches_mode(self, router, hydration_mode, scenario):
        """Gemini decision must match hydration gate mode."""
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        gate_result = router._dispatch_gates(ctx, state)
        assert gate_result is not None

        expected = scenario["expected"][f"{hydration_mode}_mode"]

        canonical = router._gate_result_to_canonical(gate_result)
        output = router.output_for_gemini(canonical, scenario["hook_event"])

        assert output.decision == expected["gemini_decision"], (
            f"[{scenario['id']}] Gemini decision: "
            f"expected {expected['gemini_decision']}, "
            f"got {output.decision} in {hydration_mode} mode"
        )


# ===========================================================================
# LIVE DATA TESTS: Scenarios extracted from real hook logs with provenance
# Source: scripts/extract_fixtures.py against real session JSONL logs
# ===========================================================================


class TestLiveHydrationGateBlocks:
    """Hydration gate blocks tools when closed — from real logged events.

    Source logs:
    - Claude: 20260303-f45b1f80-hooks.jsonl, 20260303-825840e5-hooks.jsonl
    - Gemini: /tmp/g.jsonl (session a51fc272)
    """

    SCENARIOS = _flatten_scenarios(
        "claude_hydration_gate_blocks_tools",
        "gemini_hydration_gate_blocks_tools",
    )

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_hydration_blocks_tool(self, router, hydration_mode, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        expected = GateVerdict.WARN if hydration_mode == "warn" else GateVerdict.DENY
        assert result is not None, (
            f"[{scenario['id']}] Expected {expected.value} but got None (allow) "
            f"in {hydration_mode} mode"
        )
        assert result.verdict == expected, (
            f"[{scenario['id']}] {scenario['tool_name']} should be "
            f"{expected.value} in {hydration_mode} mode, got {result.verdict.value}"
        )


class TestLiveToolSearchNotBlocked:
    """ToolSearch with `select:` queries must not be blocked by the hydration gate.

    This test uses real logged events to verify that `select:` queries, which are
    pure tool-loading operations, are not blocked by a closed hydration gate.
    Blocking these creates an unresolvable loop: the agent needs ToolSearch to
    load tools, but ToolSearch is blocked until hydration, which also requires tools.

    Source log: 20260305-2bff28e1-hooks.jsonl (session 2bff28e1, aops-86528f6c)
    """
    SCENARIOS = _flatten_scenarios("claude_toolsearch_not_blocked")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_toolsearch_not_blocked(self, router, hydration_mode, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        assert result is None or result.verdict == GateVerdict.ALLOW, (
            f"[{scenario['id']}] ToolSearch with a 'select:' query must not be blocked by the hydration gate "
            f"(query={scenario['tool_input'].get('query')!r}). "
            f"Got {result.verdict.value if result else 'None'} in {hydration_mode} mode. "
            f"Fix: `get_tool_category` should classify `ToolSearch` as 'infrastructure' when the query starts with 'select:'."
        )


class TestLiveComplianceAgentAllowed:
    """Compliance agents always allowed — from real logged events.

    Verifies that real hydrator/custodiet calls from live sessions are not blocked.
    """

    SCENARIOS = _flatten_scenarios(
        "claude_compliance_agent_allowed",
        "gemini_compliance_agent_allowed",
    )

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_compliance_agent_allowed(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                f"[{scenario['id']}] Compliance agent call "
                f"'{scenario['tool_name']}' (subagent_type={scenario.get('subagent_type')}) "
                f"should not be DENY, got {result.verdict.value}"
            )


class TestLiveAlwaysAvailableBypass:
    """Always-available tools bypass gates — from real logged events."""

    SCENARIOS = _flatten_scenarios(
        "claude_always_available_bypass",
        "gemini_always_available_bypass",
    )

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_always_available_allowed(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] Always-available tool '{scenario['tool_name']}' "
                f"should be ALLOW, got {result.verdict.value}"
            )


class TestLiveCustodietThreshold:
    """Custodiet blocks at ops threshold — from real logged events.

    The test env sets CUSTODIET_GATE_MODE=block, so we expect DENY (not the
    WARN that may have been recorded in the live session with mode=warn).
    """

    SCENARIOS = _flatten_scenarios(
        "claude_custodiet_threshold",
        "gemini_custodiet_threshold",
    )

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_custodiet_threshold(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        # Some tools are exempt from custodiet threshold (infrastructure, read_only).
        # Derived dynamically from gate_config to stay in sync with production config.
        # Matches excluded_tool_categories=["infrastructure", "read_only"] in definitions.py.
        _exempt_categories = {"infrastructure", "read_only"}
        tool_cat = get_tool_category(scenario["tool_name"] or "")

        # Check if this scenario dispatches custodiet specifically.
        # The custodiet gate has a PreToolUse trigger that fires ONLY for custodiet
        # dispatches, resetting ops_since_open BEFORE the policy evaluates (deadlock
        # prevention fix). Agent(custodiet) at threshold → trigger resets → ALLOW.
        # Other compliance agents (prompt-hydrator, butler) do NOT reset the custodiet
        # counter, so they are still subject to the policy at threshold.
        tool_input = scenario.get("tool_input") or {}
        extracted_st, _ = extract_subagent_type(scenario["tool_name"] or "", tool_input)
        effective_subagent = scenario.get("subagent_type") or extracted_st
        is_custodiet_dispatch = effective_subagent in ("custodiet", "aops-core:custodiet")

        if tool_cat in _exempt_categories:
            assert result is None or result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] {scenario['tool_name']} is exempt from custodiet "
                f"but got non-allow verdict: {result.verdict if result else 'None'}"
            )
        elif is_custodiet_dispatch:
            # Agent(custodiet) resets the custodiet counter via PreToolUse trigger
            # before the policy evaluates → must be ALLOW (deadlock prevention).
            assert result is None or result.verdict == GateVerdict.ALLOW, (
                f"[{scenario['id']}] {scenario['tool_name']}({effective_subagent}) is a "
                f"custodiet dispatch; trigger resets ops_since_open=0 before policy. "
                f"Expected ALLOW but got {result.verdict if result else 'None'}"
            )
        else:
            # Non-exempt tools (like Bash, Write) MUST be blocked/warned
            assert result is not None, (
                f"[{scenario['id']}] Expected non-allow verdict for {scenario['tool_name']} "
                f"at custodiet threshold"
            )
            assert result.verdict != GateVerdict.ALLOW, (
                f"[{scenario['id']}] {scenario['tool_name']} should be blocked/warned "
                f"at custodiet threshold, got ALLOW"
            )


# ===========================================================================
# CUSTODIET DEADLOCK PREVENTION: Agent(custodiet) must never be self-blocked
# ===========================================================================


class TestCustodietDeadlockPrevention:
    """Agent(custodiet) must bypass the custodiet gate when dispatched.

    Before the PreToolUse trigger was added to the custodiet gate, there was
    a deadlock: when ops >= threshold, the gate blocked Agent(custodiet)
    itself (because Agent is in 'spawn' category, not exempt). The agent
    needed to satisfy the gate, but the gate blocked the agent dispatch.

    Fix (definitions.py): added PreToolUse to the custodiet trigger's
    hook_event pattern. The trigger fires (resets ops_since_open=0) BEFORE
    the policy evaluates, so the policy sees 0 < threshold and doesn't fire.

    This mirrors how the hydration gate opens via PreToolUse for the hydrator.
    """

    @pytest.mark.parametrize(
        "subagent_type,tool_name,tool_input",
        [
            # Claude Code: Agent tool dispatching custodiet
            (
                "custodiet",
                "Agent",
                {"subagent_type": "custodiet", "prompt": "/tmp/custodiet.md"},
            ),
            (
                "aops-core:custodiet",
                "Agent",
                {"subagent_type": "aops-core:custodiet", "prompt": "/tmp/custodiet.md"},
            ),
            # Gemini CLI: delegate_to_agent dispatching custodiet
            (
                "custodiet",
                "delegate_to_agent",
                {"name": "custodiet", "query": "/tmp/custodiet.md"},
            ),
            (
                "aops-core:custodiet",
                "delegate_to_agent",
                {"name": "aops-core:custodiet", "query": "/tmp/custodiet.md"},
            ),
        ],
        ids=[
            "claude-custodiet",
            "claude-aops-core-custodiet",
            "gemini-custodiet",
            "gemini-aops-core-custodiet",
        ],
    )
    def test_custodiet_dispatch_not_blocked_at_threshold(
        self, router, subagent_type, tool_name, tool_input
    ):
        """Dispatching custodiet agent must not be blocked when threshold is exceeded."""
        state = SessionState.create("test-deadlock")
        # Set ops well above threshold
        state.gates["custodiet"].ops_since_open = 75

        ctx = HookContext(
            session_id="test-deadlock",
            hook_event="PreToolUse",
            tool_name=tool_name,
            tool_input=tool_input,
            is_subagent=False,
            subagent_type=subagent_type,
        )

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                f"DEADLOCK REGRESSION: {tool_name}(subagent_type={subagent_type!r}) "
                f"was DENIED at custodiet threshold. This is the deadlock bug: "
                f"the agent cannot dispatch custodiet to reset the counter it needs "
                f"to satisfy. The PreToolUse trigger must fire before the policy."
            )

    def test_custodiet_dispatch_resets_ops_counter(self, router):
        """Dispatching custodiet resets the ops counter via PreToolUse trigger."""
        state = SessionState.create("test-deadlock-reset")
        state.gates["custodiet"].ops_since_open = 75

        ctx = HookContext(
            session_id="test-deadlock-reset",
            hook_event="PreToolUse",
            tool_name="Agent",
            tool_input={"subagent_type": "custodiet", "prompt": "/tmp/custodiet.md"},
            is_subagent=False,
            subagent_type="custodiet",
        )

        router._dispatch_gates(ctx, state)

        assert state.gates["custodiet"].ops_since_open == 0, (
            f"PreToolUse trigger for custodiet dispatch should reset ops_since_open to 0, "
            f"got {state.gates['custodiet'].ops_since_open}. "
            f"Without this reset, the policy still fires after the dispatch attempt."
        )


class TestLiveReadOnlyTools:
    """Read-only tools from real sessions.

    Validates that real Read/Grep/Glob/read_file calls produce the correct
    verdict. These are subject to hydration gate (warn/deny when closed)
    but exempt from custodiet.
    """

    SCENARIOS = _flatten_scenarios(
        "claude_read_only_tools",
        "gemini_read_only_tools",
    )

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_read_only_verdict(self, router, hydration_mode, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        # If gate_overrides include hydration=closed, expect mode-dependent verdict
        if scenario.get("gate_overrides", {}).get("hydration", {}).get("status") == "closed":
            expected = GateVerdict.WARN if hydration_mode == "warn" else GateVerdict.DENY
            assert result is not None, (
                f"[{scenario['id']}] Expected {expected.value} in {hydration_mode} mode"
            )
            assert result.verdict == expected, (
                f"[{scenario['id']}] {scenario['tool_name']}: expected {expected.value} "
                f"in {hydration_mode} mode, got {result.verdict.value}"
            )
        else:
            # No hydration gate override — should be allowed
            if result is not None:
                assert result.verdict == GateVerdict.ALLOW, (
                    f"[{scenario['id']}] {scenario['tool_name']}: expected ALLOW, "
                    f"got {result.verdict.value}"
                )


class TestLiveWriteTools:
    """Write tools from real sessions.

    Write tools are subject to BOTH hydration and custodiet gates.
    Expected verdict depends on which gate is active and its mode.
    """

    SCENARIOS = _flatten_scenarios(
        "claude_write_tools",
        "gemini_write_tools",
    )

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_write_tool_verdict(self, router, hydration_mode, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        overrides = scenario.get("gate_overrides", {})
        hydration_closed = overrides.get("hydration", {}).get("status") == "closed"
        # Custodiet only fires when ops_since_open >= threshold.
        # A scenario may include a custodiet override without actually being at threshold.
        custodiet_ops = overrides.get("custodiet", {}).get("ops_since_open", 0)
        custodiet_at_threshold = custodiet_ops >= CUSTODIET_TOOL_CALL_THRESHOLD

        if hydration_closed and custodiet_at_threshold:
            # Both gates fire -- engine merges: deny > warn > allow.
            # Custodiet is "block" in test env -> DENY.
            # Hydration is parameterized -> WARN or DENY.
            # Merged verdict is always DENY (custodiet forces it).
            assert result is not None
            assert result.verdict == GateVerdict.DENY, (
                f"[{scenario['id']}] {scenario['tool_name']}: both hydration+custodiet active, "
                f"expected DENY (custodiet=block), got {result.verdict.value}"
            )
        elif hydration_closed:
            expected = GateVerdict.WARN if hydration_mode == "warn" else GateVerdict.DENY
            assert result is not None
            assert result.verdict == expected, (
                f"[{scenario['id']}] {scenario['tool_name']}: expected {expected.value} "
                f"in {hydration_mode} mode (hydration closed), got {result.verdict.value}"
            )
        elif custodiet_at_threshold:
            # Custodiet mode is block in test env
            assert result is not None, (
                f"[{scenario['id']}] Expected non-allow at custodiet threshold"
            )
            assert result.verdict != GateVerdict.ALLOW, (
                f"[{scenario['id']}] {scenario['tool_name']}: should be blocked/warned "
                f"at custodiet threshold, got ALLOW"
            )
        else:
            if result is not None:
                assert result.verdict == GateVerdict.ALLOW


# ===========================================================================
# HYDRATION GATE SEQUENCE: Trigger opens gate for subsequent tools (issue #710)
# ===========================================================================


_HYDRATOR_SEQUENCE_PLATFORMS = [
    pytest.param(
        # Claude Code: from session f45b1f80, lines 90+98
        # Source: 20260303-f45b1f80-hooks.jsonl
        {
            "platform": "claude",
            "read_tool": "Read",
            "read_input": {
                "file_path": "/opt/nic/.aops/crew/jewelle_96/aops/aops-core/hooks/gate_config.py"
            },
            "hydrator_tool": "Agent",
            "hydrator_input": {
                "description": "Hydrate prompt",
                "prompt": "/home/debian/.claude/projects/-opt-nic-_aops-crew-jewelle_96-aops/20260303-f45b1f80-hydration.md",
                "subagent_type": "aops-core:prompt-hydrator",
                "run_in_background": True,
            },
        },
        id="claude",
    ),
    pytest.param(
        # Gemini CLI: from session a51fc272, lines 2+3
        # Source: /tmp/g.jsonl
        # Real Gemini logs: tool_name IS the agent name, subagent_type=None
        {
            "platform": "gemini",
            "read_tool": "read_file",
            "read_input": {
                "file_path": "/Users/suzor/.gemini/tmp/brain/logs/20260303-a51fc272-hydration.md"
            },
            "hydrator_tool": "prompt-hydrator",
            "hydrator_input": {
                "query": "/Users/suzor/.gemini/tmp/brain/logs/20260303-a51fc272-hydration.md"
            },
        },
        id="gemini",
    ),
]


class TestHydrationGateSequence:
    """Three-step sequence: read denied -> hydrator allowed -> read allowed.

    Reproduces issue #710: in Gemini, the hydrator call doesn't open the gate
    because tool_name='prompt-hydrator' (not 'delegate_to_agent'), so the
    router never extracts the subagent_type, the trigger never fires, and
    subsequent reads remain denied.

    This test must pass for BOTH platforms. It currently fails for Gemini.
    """

    @pytest.fixture
    def block_mode(self, monkeypatch):
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")
        _reinit_gates_with_defaults()

    @pytest.mark.parametrize("platform", _HYDRATOR_SEQUENCE_PLATFORMS)
    def test_read_then_hydrator_then_read(self, router, block_mode, platform):
        """After hydrator call, subsequent reads must be allowed."""
        # Shared state across the three steps
        state = SessionState.create("test-sequence")
        state.gates["hydration"].status = GateStatus.CLOSED
        state.gates["hydration"].metrics["temp_path"] = "/tmp/hydration.md"

        # --- Step 1: read_file/Read before hydration -> DENY ---
        ctx1 = HookContext(
            session_id="test-sequence",
            hook_event="PreToolUse",
            tool_name=platform["read_tool"],
            tool_input=platform["read_input"],
        )
        result1 = router._dispatch_gates(ctx1, state)
        assert result1 is not None and result1.verdict == GateVerdict.DENY, (
            f"[{platform['platform']}] Step 1: {platform['read_tool']} should be DENY "
            f"before hydration, got {result1.verdict.value if result1 else 'None (allow)'}"
        )

        # --- Step 2: hydrator call -> ALLOW (and trigger opens gate) ---
        ctx2 = HookContext(
            session_id="test-sequence",
            hook_event="PreToolUse",
            tool_name=platform["hydrator_tool"],
            tool_input=platform["hydrator_input"],
        )
        result2 = router._dispatch_gates(ctx2, state)
        # Hydrator must not be denied
        if result2 is not None:
            assert result2.verdict != GateVerdict.DENY, (
                f"[{platform['platform']}] Step 2: hydrator call should not be DENY, "
                f"got {result2.verdict.value}"
            )

        # --- Step 3: read_file/Read after hydration -> ALLOW ---
        # The hydrator trigger should have opened the gate
        assert state.gates["hydration"].status == GateStatus.OPEN, (
            f"[{platform['platform']}] Gate should be OPEN after hydrator call, "
            f"got {state.gates['hydration'].status}"
        )

        ctx3 = HookContext(
            session_id="test-sequence",
            hook_event="PreToolUse",
            tool_name=platform["read_tool"],
            tool_input=platform["read_input"],
        )
        result3 = router._dispatch_gates(ctx3, state)
        if result3 is not None:
            assert result3.verdict == GateVerdict.ALLOW, (
                f"[{platform['platform']}] Step 3: {platform['read_tool']} should be ALLOW "
                f"after hydration, got {result3.verdict.value}"
            )


# ===========================================================================
# HEREDOC BYPASS: Agent uses Bash with heredoc to write files (issue #710)
# ===========================================================================


class TestBashHeredocBypass:
    """Bash heredoc file-write must be blocked by hydration gate.

    Attack vector: an agent calls Bash(command="cat <<'EOF' > file.py\n...")
    to write file contents, bypassing the Edit/Write tool permission system.
    The hydration gate is the defense layer — it blocks ALL non-always_available
    tools (including Bash) when hydration is pending.

    In warn mode: Bash is allowed through (the original bug #710).
    In block mode: Bash is denied, preventing the heredoc bypass.
    """

    HEREDOC_COMMANDS = [
        pytest.param(
            {
                "command": "cat <<'EOF' > /tmp/exploit.py\nimport os\nos.system('rm -rf /')\nEOF",
                "description": "heredoc file write",
            },
            id="cat-heredoc-write",
        ),
        pytest.param(
            {
                "command": "python3 -c \"\nwith open('output.py', 'w') as f:\n    f.write('malicious')\n\"",
                "description": "python inline file write",
            },
            id="python-inline-write",
        ),
        pytest.param(
            {
                "command": "echo 'payload' | tee /tmp/config.json",
                "description": "tee pipe write",
            },
            id="echo-tee-write",
        ),
        pytest.param(
            {
                "command": "printf '%s\n' 'line1' 'line2' > /tmp/out.txt",
                "description": "printf redirect write",
            },
            id="printf-redirect-write",
        ),
    ]

    @pytest.mark.parametrize("hydration_mode", ["warn", "block"])
    @pytest.mark.parametrize("cmd", HEREDOC_COMMANDS)
    def test_bash_heredoc_blocked_when_hydration_closed(
        self, router, hydration_mode, cmd, monkeypatch
    ):
        """Bash with file-writing commands must be denied in block mode.

        In warn mode, the gate only warns (the agent can still proceed).
        In block mode, the gate denies (the agent cannot proceed).
        This is the key difference that issue #710 exposed.
        """
        monkeypatch.setenv("HYDRATION_GATE_MODE", hydration_mode)
        _reinit_gates_with_defaults()

        state = SessionState.create("test-heredoc")
        state.gates["hydration"].status = GateStatus.CLOSED
        state.gates["hydration"].metrics["temp_path"] = "/tmp/hydration.md"

        ctx = HookContext(
            session_id="test-heredoc",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": cmd["command"], "description": cmd["description"]},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, (
            f"Bash({cmd['description']}) should not be allowed when hydration is closed"
        )

        if hydration_mode == "block":
            assert result.verdict == GateVerdict.DENY, (
                f"BLOCK mode: Bash({cmd['description']}) should be DENY, "
                f"got {result.verdict.value}. "
                f"This is the exact bug from issue #710 — the agent can bypass "
                f"Edit/Write permissions by using Bash heredocs."
            )
        else:
            assert result.verdict == GateVerdict.WARN, (
                f"WARN mode: Bash({cmd['description']}) should be WARN, got {result.verdict.value}"
            )

    def test_bash_heredoc_allowed_after_hydration(self, router, monkeypatch):
        """After hydration completes, Bash heredoc should be allowed."""
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")
        _reinit_gates_with_defaults()

        state = SessionState.create("test-heredoc-ok")
        state.gates["hydration"].status = GateStatus.OPEN  # Hydration done

        ctx = HookContext(
            session_id="test-heredoc-ok",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={
                "command": "cat <<'EOF' > /tmp/legit.py\nprint('hello')\nEOF",
                "description": "heredoc file write after hydration",
            },
        )

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                f"Bash should be allowed after hydration, got {result.verdict.value}"
            )


# ===========================================================================
# EXHAUSTIVE COMPLIANCE BYPASS: Every compliance type x every write tool
# ===========================================================================


class TestExhaustiveComplianceBypass:
    """Cross-product: every COMPLIANCE_SUBAGENT_TYPE x every write tool.

    This is the nuclear option — ensures no combination can ever produce DENY.
    If a new compliance type or write tool is added, this test will catch
    any missing bypass.
    """

    WRITE_TOOLS = [
        ("Edit", {"file_path": "/f.py", "old_string": "a", "new_string": "b"}),
        ("Write", {"file_path": "/f.py", "content": "x"}),
        ("Bash", {"command": "echo hi"}),
        ("NotebookEdit", {"notebook_path": "/n.ipynb", "new_source": "x=1"}),
        ("MultiEdit", {"edits": []}),
        ("write_file", {"path": "/f.py", "content": "x"}),
        ("replace", {"path": "/f.py", "old": "a", "new": "b"}),
        ("run_shell_command", {"command": "ls"}),
        ("execute_code", {"code": "print(1)"}),
        ("save_memory", {"content": "note"}),
    ]

    @pytest.fixture
    def hostile_state(self):
        """Create state where ALL gates would block a normal agent."""
        state = SessionState.create("test-exhaustive")
        state.gates["hydration"].status = GateStatus.CLOSED
        state.gates["hydration"].metrics["temp_path"] = "/tmp/h.md"
        state.gates["custodiet"].ops_since_open = 100
        return state

    @pytest.mark.parametrize("subagent_type", sorted(COMPLIANCE_SUBAGENT_TYPES))
    @pytest.mark.parametrize(
        "tool_name,tool_input",
        WRITE_TOOLS,
        ids=[t[0] for t in WRITE_TOOLS],
    )
    def test_compliance_type_x_write_tool_never_denied(
        self, router, hostile_state, subagent_type, tool_name, tool_input
    ):
        ctx = HookContext(
            session_id="test-exhaustive",
            hook_event="PreToolUse",
            tool_name=tool_name,
            tool_input=tool_input,
            is_subagent=True,
            subagent_type=subagent_type,
        )

        result = router._dispatch_gates(ctx, hostile_state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                f"CRITICAL: Compliance agent '{subagent_type}' calling "
                f"'{tool_name}' was DENIED. This breaks the compliance bypass."
            )
            assert result.verdict == GateVerdict.ALLOW, (
                f"Compliance agent '{subagent_type}' calling '{tool_name}' "
                f"got {result.verdict.value}, expected ALLOW"
            )


# ===========================================================================
# GATE MODE ENV VAR OVERRIDES (parameterized across all gates and modes)
# ===========================================================================


def _make_gate_trigger_state(gate_name: str) -> SessionState:
    """Create session state that will trigger the named gate's policy."""
    state = SessionState.create("test-gate-mode")
    # Ensure all four gates exist (SessionState.create only populates 3)
    for g in ("hydration", "custodiet", "qa", "handover"):
        if g not in state.gates:
            state.gates[g] = GateState(status=GateStatus.OPEN)
    # Start with all gates open to isolate the gate under test
    for g in state.gates:
        state.gates[g].status = GateStatus.OPEN
        state.gates[g].ops_since_open = 0

    if gate_name == "hydration":
        state.gates["hydration"].status = GateStatus.CLOSED
        state.gates["hydration"].metrics["temp_path"] = "/tmp/h.md"
    elif gate_name == "custodiet":
        # Use threshold+5 to guarantee firing regardless of CUSTODIET_TOOL_CALL_THRESHOLD env var
        _threshold = sys.modules["hooks.gate_config"].CUSTODIET_TOOL_CALL_THRESHOLD
        state.gates["custodiet"].ops_since_open = _threshold + 5
    elif gate_name == "qa":
        state.gates["qa"].status = GateStatus.CLOSED
        state.gates["qa"].metrics["temp_path"] = "/tmp/qa-review.md"
    elif gate_name == "handover":
        state.gates["handover"].status = GateStatus.CLOSED

    return state


def _make_gate_trigger_context(gate_name: str) -> HookContext:
    """Create hook context that fires the named gate's policy."""
    if gate_name in ("hydration", "custodiet"):
        return HookContext(
            session_id="test-gate-mode",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/f.py", "old_string": "a", "new_string": "b"},
        )
    else:  # qa, handover -- block on Stop
        return HookContext(
            session_id="test-gate-mode",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        )


# Parameterized scenarios: (gate_name, env_var, mode, expected_verdict)
# "block" and "deny" both map to GateVerdict.DENY in the engine (engine.py:334)
_GATE_MODE_CASES = [
    # Hydration: default=warn
    ("hydration", "HYDRATION_GATE_MODE", "warn", GateVerdict.WARN),
    ("hydration", "HYDRATION_GATE_MODE", "block", GateVerdict.DENY),
    ("hydration", "HYDRATION_GATE_MODE", "deny", GateVerdict.DENY),
    # Custodiet: default=block
    ("custodiet", "CUSTODIET_GATE_MODE", "warn", GateVerdict.WARN),
    ("custodiet", "CUSTODIET_GATE_MODE", "block", GateVerdict.DENY),
    ("custodiet", "CUSTODIET_GATE_MODE", "deny", GateVerdict.DENY),
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

        assert result is not None, (
            f"{gate_name} gate with {env_var}={mode} should produce a verdict, got None (allow)"
        )
        assert result.verdict == expected_verdict, (
            f"{gate_name} gate with {env_var}={mode}: "
            f"expected {expected_verdict.value}, got {result.verdict.value}"
        )
