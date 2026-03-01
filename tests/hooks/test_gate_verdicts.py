#!/usr/bin/env python3
"""Gate verdict regression tests driven by saved scenario fixtures.

Validates that the gate system produces the correct block/warn/allow verdicts
for every realistic hook call scenario. Uses JSON fixture data that replicates
actual Claude Code and Gemini CLI hook invocations.

Key invariants tested:
1. Compliance agents (hydrator, custodiet, audit, butler) are NEVER blocked
2. Write tools ARE blocked/warned when hydration gate is closed
3. Read-only tools are subject to hydration gate (only always_available is exempt)
4. Read-only tools bypass custodiet gate (unlike write tools)
5. Always-available tools bypass ALL gates
6. Custodiet blocks at ops threshold for write tools only
7. Stop event respects handover and QA gates
8. Claude Code and Gemini CLI output formats match their respective schemas
9. Gate triggers (hydrator opens gate, custodiet resets counter) fire correctly
10. Gate mode env var overrides work correctly

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

from hooks.gate_config import COMPLIANCE_SUBAGENT_TYPES
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


def _load_scenarios() -> dict:
    """Load all scenarios from the JSON fixture file."""
    with SCENARIOS_FILE.open() as f:
        return json.load(f)


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

    IMPORTANT: definitions.py imports from bare 'gate_config' (not 'hooks.gate_config').
    Because aops-core/hooks is on sys.path, Python creates TWO separate module objects
    for the same file: sys.modules['gate_config'] and sys.modules['hooks.gate_config'].
    We must reload BOTH so definitions.py picks up current env var values.
    """
    # Reload both module entries for the same file
    if "gate_config" in sys.modules:
        importlib.reload(sys.modules["gate_config"])
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    # Now reload definitions (which imports from bare 'gate_config')
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


# ===========================================================================
# HYDRATION GATE: Write tools warned when closed
# ===========================================================================


class TestHydrationGateBlocksWriteTools:
    """Write-category tools must be warned when hydration gate is closed (default mode=warn)."""

    SCENARIOS = _flatten_scenarios("hydration_gate_blocks_write_tools")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_write_tool_warned(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        assert result is not None, (
            f"[{scenario['id']}] Expected non-allow verdict but got None (allow)"
        )
        assert result.verdict != GateVerdict.ALLOW, (
            f"[{scenario['id']}] Write tool '{scenario['tool_name']}' should not be "
            f"ALLOW when hydration gate is closed"
        )


# ===========================================================================
# HYDRATION GATE: Read-only tools are subject to hydration (only
# always_available is exempt from hydration policy)
# ===========================================================================


class TestHydrationGateWarnsReadOnly:
    """Read-only tools are subject to hydration gate — only always_available is exempt.

    The hydration gate policy excludes only always_available tools. Read-only
    tools like Read, Glob, Grep get the hydration warning (not block) when
    the gate is closed. This is intentional: the warning tells the agent to
    hydrate, but doesn't prevent tool use (warn != deny).
    """

    SCENARIOS = _flatten_scenarios("hydration_gate_warns_read_only")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_read_tool_warned(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        # Read-only tools get WARN from hydration gate (not exempt)
        assert result is not None, (
            f"[{scenario['id']}] Read-only tool '{scenario['tool_name']}' should get "
            f"WARN from hydration gate, got None (allow)"
        )
        assert result.verdict == GateVerdict.WARN, (
            f"[{scenario['id']}] Read-only tool '{scenario['tool_name']}' "
            f"should be WARN (not {result.verdict.value}) when hydration closed"
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


class TestHydrationGateAllowsAlwaysAvailable:
    """Always-available tools must bypass ALL gates."""

    SCENARIOS = _flatten_scenarios("hydration_gate_allows_always_available")

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
    """Non-compliance subagents must still be subject to gate policies."""

    SCENARIOS = _flatten_scenarios("non_compliance_subagent_blocked")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_non_compliance_subagent_blocked(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        # Non-compliance agents should NOT be ALLOW when gates are closed
        assert result is not None, f"[{scenario['id']}] Expected non-allow verdict but got None"
        assert result.verdict != GateVerdict.ALLOW, (
            f"[{scenario['id']}] Non-compliance agent '{scenario['subagent_type']}' "
            f"should not be ALLOW when gate is closed"
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
# GATE MODE ENV VAR OVERRIDES
# ===========================================================================


class TestCustodietGateModeOverride:
    """Verify CUSTODIET_GATE_MODE env var controls enforcement level."""

    def test_custodiet_warn_mode(self, router, monkeypatch):
        """When CUSTODIET_GATE_MODE=warn, should warn instead of block."""
        monkeypatch.setenv("CUSTODIET_GATE_MODE", "warn")
        _reinit_gates_with_defaults()

        state = SessionState.create("test-custodiet-mode")
        state.gates["hydration"].status = GateStatus.OPEN
        state.gates["custodiet"].ops_since_open = 55

        ctx = HookContext(
            session_id="test-custodiet-mode",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/f.py", "old_string": "a", "new_string": "b"},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None
        assert result.verdict == GateVerdict.WARN, (
            f"Expected WARN in warn mode, got {result.verdict.value}"
        )


class TestHydrationGateModeOverride:
    """Verify HYDRATION_GATE_MODE env var controls enforcement level."""

    def test_hydration_deny_mode(self, router, monkeypatch):
        """When HYDRATION_GATE_MODE=deny, should deny instead of warn."""
        monkeypatch.setenv("HYDRATION_GATE_MODE", "deny")
        _reinit_gates_with_defaults()

        state = SessionState.create("test-hydration-mode")
        state.gates["hydration"].status = GateStatus.CLOSED
        state.gates["hydration"].metrics["temp_path"] = "/tmp/h.md"

        ctx = HookContext(
            session_id="test-hydration-mode",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/f.py", "old_string": "a", "new_string": "b"},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None
        assert result.verdict == GateVerdict.DENY, (
            f"Expected DENY in deny mode, got {result.verdict.value}"
        )
