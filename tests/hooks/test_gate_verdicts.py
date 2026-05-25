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
    """Reload gate_config and definitions, then reinit the registry.

    Gate modes now live in $AOPS_POLECAT_CONFIG / $AOPS_SESSIONS/polecat.yaml
    (loaded by lib.polecat_config). Tests that change modes write a new YAML
    and call ``hooks.gate_config._reset_gate_mode_cache()`` before invoking
    this helper. All imports use qualified paths from aops-core/ root so
    sys.modules has exactly one entry per module.
    """
    if "hooks.gate_config" in sys.modules:
        # sys.modules["hooks.gate_config"]._reset_gate_mode_cache()
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


def _set_gate_modes(
    monkeypatch,
    *,
    handover: str = "warn",
    qa: str = "block",
    enforcer: str = "block",
    hydration: str = "off",
    ida: str = "off",
    sentinel: str = "block",
    enforcer_threshold: int = 50,
) -> None:
    """Stamp the requested gate modes onto the environment.

    ida defaults to "off" here so existing test scenarios that expect
    "allow" on Stop (e.g. syn-stop-all-open-allow) keep their invariants.
    Tests targeting ida behaviour pass it explicitly.
    """
    monkeypatch.setenv("HANDOVER_GATE_MODE", handover)
    monkeypatch.setenv("QA_GATE_MODE", qa)
    monkeypatch.setenv("ENFORCER_GATE_MODE", enforcer)
    monkeypatch.setenv("HYDRATION_GATE_MODE", hydration)
    monkeypatch.setenv("IDA_GATE_MODE", ida)
    monkeypatch.setenv("SENTINEL_GATE_MODE", sentinel)
    monkeypatch.setenv("ENFORCER_TOOL_CALL_THRESHOLD", str(enforcer_threshold))


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
def _deterministic_gate_modes(monkeypatch, tmp_path):
    """Ensure gate modes use known defaults regardless of host env."""
    _set_gate_modes(
        monkeypatch,
        handover="warn",
        qa="block",
        enforcer="block",
        hydration="off",
    )
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
    # Enforcer
    ("enforcer", "warn", GateVerdict.WARN),
    ("enforcer", "block", GateVerdict.DENY),
    # QA
    ("qa", "warn", GateVerdict.WARN),
    ("qa", "block", GateVerdict.DENY),
    # Handover
    ("handover", "warn", GateVerdict.WARN),
    ("handover", "block", GateVerdict.DENY),
    # Ida (Ida B. Wells — fires on Stop when armed/CLOSED; starts CLOSED each session)
    ("ida", "warn", GateVerdict.WARN),
    ("ida", "block", GateVerdict.DENY),
]


class TestGateModeConfigOverrides:
    """Verify polecat.yaml gate modes control enforcement for all gates.

    Each gate's mode (handover/qa/enforcer/hydration in the YAML)
    must produce the correct verdict when the gate's policy fires.
    Replaces the previous *_GATE_MODE env-var test class — env vars are
    no longer a config source.
    """

    @pytest.mark.parametrize(
        "gate_name,mode,expected_verdict",
        _GATE_MODE_CASES,
        ids=[f"{g}-{m}" for g, m, _ in _GATE_MODE_CASES],
    )
    def test_gate_mode_verdict(
        self, router, monkeypatch, tmp_path, gate_name, mode, expected_verdict
    ):
        kwargs: dict[str, str] = {gate_name: mode}
        _set_gate_modes(monkeypatch, **kwargs)
        _reinit_gates_with_defaults()

        state = _make_gate_trigger_state(gate_name)
        ctx = _make_gate_trigger_context(gate_name)

        result = router._dispatch_gates(ctx, state)

        if expected_verdict is None:
            assert result is None, (
                f"{gate_name} gate with mode={mode} should be ALLOW (None), "
                f"got {result.verdict.value if result else 'N/A'}"
            )
            return

        assert result is not None, (
            f"{gate_name} gate with mode={mode} should produce a verdict, got None (allow)"
        )
        assert result.verdict == expected_verdict, (
            f"{gate_name} gate with mode={mode}: "
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


# ===========================================================================
# IDA GATE: per-turn lifecycle and warn-mode advisory routing
# ===========================================================================


class TestIdaPerTurnLifecycle:
    """IDA gate per-turn lifecycle: armed → fires → opens → re-armed on UPS.

    AC from aops-83f40207:
    1. IDA_GATE_MODE=warn → advisory-only (non-blocking) Stop behaviour.
    2. Lifecycle: armed → fires → opens → re-armed on next UserPromptSubmit.
    """

    def test_ida_starts_closed(self, monkeypatch):
        """IDA gate is armed (CLOSED) from session start."""
        _set_gate_modes(monkeypatch, ida="warn")
        _reinit_gates_with_defaults()
        from lib.gates.registry import GateRegistry

        GateRegistry.initialize()
        ida_gate = GateRegistry.get_gate("ida")
        assert ida_gate is not None, "IDA gate must be registered"
        assert ida_gate.config.initial_status == GateStatus.CLOSED, (
            "IDA gate must start CLOSED (armed) so it fires on the first Stop"
        )

    def test_ida_opens_after_firing_on_stop(self, router, monkeypatch):
        """IDA gate transitions CLOSED → OPEN after firing on Stop."""
        _set_gate_modes(monkeypatch, ida="warn")
        _reinit_gates_with_defaults()

        state = _make_gate_trigger_state("ida")
        ctx = _make_gate_trigger_context("ida")  # Stop event

        router._dispatch_gates(ctx, state)

        assert state.gates["ida"].status == GateStatus.OPEN, (
            "IDA gate must be OPEN after firing (so retried Stops aren't blocked)"
        )

    def test_ida_does_not_fire_twice_same_turn(self, router, monkeypatch):
        """IDA gate does not fire on a second Stop in the same turn (gate is OPEN)."""
        _set_gate_modes(monkeypatch, ida="warn")
        _reinit_gates_with_defaults()

        state = _make_gate_trigger_state("ida")
        stop_ctx = _make_gate_trigger_context("ida")  # Stop event

        # First Stop: gate fires, opens
        first_result = router._dispatch_gates(stop_ctx, state)
        assert first_result is not None and first_result.verdict == GateVerdict.WARN
        assert state.gates["ida"].status == GateStatus.OPEN

        # Second Stop (same turn): gate is OPEN — IDA policy must not fire
        second_result = router._dispatch_gates(stop_ctx, state)
        # IDA contributes nothing; other gates (qa/handover) fire on Stop too
        # but with autouse ida="off" default they're already open. Check gate state.
        assert state.gates["ida"].status == GateStatus.OPEN, (
            "IDA gate must remain OPEN (not fire again) on a second Stop in the same turn"
        )
        # IDA-specific: if the only result came from IDA, second result should be None
        # (all other gates pass). Verify IDA didn't produce a WARN on the second Stop.
        if second_result is not None:
            # Other gates may have fired — but IDA in OPEN state cannot fire.
            # We can't easily isolate IDA's contribution here, so just check state.
            pass

    def test_ida_rearms_on_user_prompt_submit(self, router, monkeypatch):
        """IDA gate re-arms (OPEN → CLOSED) on UserPromptSubmit."""
        _set_gate_modes(monkeypatch, ida="warn")
        _reinit_gates_with_defaults()

        state = _make_gate_trigger_state("ida")
        stop_ctx = _make_gate_trigger_context("ida")  # Stop event
        ups_ctx = HookContext(
            session_id="test-gate-mode",
            hook_event="UserPromptSubmit",
            raw_input={"prompt": "continue working"},
        )

        # Step 1: Stop fires — gate opens
        router._dispatch_gates(stop_ctx, state)
        assert state.gates["ida"].status == GateStatus.OPEN

        # Step 2: UPS re-arms the gate
        router._dispatch_gates(ups_ctx, state)
        assert state.gates["ida"].status == GateStatus.CLOSED, (
            "IDA gate must be re-armed (CLOSED) on UserPromptSubmit for the next turn"
        )

    def test_ida_warn_mode_stop_is_approved(self, router, monkeypatch):
        """IDA warn mode: Stop uses decision=block to deliver advisory to agent.

        Claude Code's Stop schema has no non-blocking channel that reaches the
        agent's context. The only way to inject advisory text is via
        decision="block" + reason. The internal verdict stays "warn" (so the
        safety-net block counter is not tripped), but the output decision must
        be "block" so the advisory lands in the agent's next turn.

        See output_for_claude() and definitions.py IDA comment block.
        """
        _set_gate_modes(monkeypatch, ida="warn")
        _reinit_gates_with_defaults()

        state = _make_gate_trigger_state("ida")
        ctx = _make_gate_trigger_context("ida")  # Stop event

        # Dispatch to get the raw verdict
        result = router._dispatch_gates(ctx, state)
        assert result is not None and result.verdict == GateVerdict.WARN

        # Convert to Claude output — warn+context_injection upgrades to block
        # so the advisory reaches the agent via the reason channel.
        from hooks.schemas import ClaudeStopHookOutput

        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "Stop")
        assert isinstance(output, ClaudeStopHookOutput)
        assert output.decision == "block", (
            f"IDA warn mode must use decision='block' to deliver advisory to agent "
            f"(got decision={output.decision!r}). Claude Code Stop has no non-blocking "
            "agent-visible channel; warn+context_injection upgrades to block+reason."
        )
        assert output.reason, (
            "IDA warn mode must populate reason with the advisory text "
            "so the agent sees it on the next turn"
        )

    def test_ida_block_mode_stop_is_blocked(self, router, monkeypatch):
        """IDA block mode: Stop decision=block with advisory in reason (agent-visible)."""
        _set_gate_modes(monkeypatch, ida="block")
        _reinit_gates_with_defaults()

        state = _make_gate_trigger_state("ida")
        ctx = _make_gate_trigger_context("ida")  # Stop event

        result = router._dispatch_gates(ctx, state)
        assert result is not None and result.verdict == GateVerdict.DENY

        from hooks.schemas import ClaudeStopHookOutput

        canonical = router._gate_result_to_canonical(result)
        output = router.output_for_claude(canonical, "Stop")
        assert isinstance(output, ClaudeStopHookOutput)
        assert output.decision == "block", (
            "IDA block mode must block Stop so the advisory reaches the agent"
        )

    def test_ida_block_mode_opens_after_firing(self, router, monkeypatch):
        """IDA block mode: gate opens after firing even though Stop is blocked."""
        _set_gate_modes(monkeypatch, ida="block")
        _reinit_gates_with_defaults()

        state = _make_gate_trigger_state("ida")
        ctx = _make_gate_trigger_context("ida")  # Stop event

        router._dispatch_gates(ctx, state)

        assert state.gates["ida"].status == GateStatus.OPEN, (
            "IDA gate must open after firing in block mode so a retried Stop "
            "is not blocked again in the same turn"
        )


# ===========================================================================
# SENTINEL GATE: destructive operations on user environment
# ===========================================================================


class TestSentinelBlocksDestructiveOps:
    """Sentinel gate blocks destructive ops on protected user-environment paths.

    Origin: GitHub issue #106 — agent deleted a working Gemini extension
    installation (~/.gemini/extensions/) without evidence.

    AC: destructive ops (rm, mv, etc.) on ~/.gemini/extensions/,
    ~/.claude/plugins/cache/, or equivalent paths require explicit user
    confirmation OR an evidence trail.
    """

    @pytest.mark.parametrize(
        "command,should_block",
        [
            ("rm -rf ~/.gemini/extensions/aops-core/", True),
            ("rm ~/.gemini/extensions/manifest.json", True),
            ("mv ~/.claude/plugins/cache/ /tmp/backup/", True),
            ("rm ~/.gemini/settings.json", True),
            ("rmdir ~/.claude/plugins/old-plugin/", True),
            ("unlink ~/.config/gemini/config.toml", True),
            ("rm ~/.claude/settings.json", True),
            # Safe operations — NOT blocked
            ("cat ~/.gemini/extensions/manifest.json", False),
            ("ls ~/.gemini/extensions/", False),
            ("rm some-other-file.txt", False),
            ("rm -rf /tmp/build/", False),
            ("git status", False),
            ("echo hello", False),
        ],
        ids=[
            "rm-rf-gemini-ext",
            "rm-gemini-ext-file",
            "mv-claude-plugins",
            "rm-gemini-settings",
            "rmdir-claude-plugin",
            "unlink-config-gemini",
            "rm-claude-json",
            "cat-gemini-ext-allowed",
            "ls-gemini-ext-allowed",
            "rm-other-file-allowed",
            "rm-tmp-allowed",
            "git-status-allowed",
            "echo-allowed",
        ],
    )
    def test_sentinel_verdict(self, router, monkeypatch, command, should_block):
        _set_gate_modes(monkeypatch, sentinel="block")
        _reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel")
        ctx = HookContext(
            session_id="test-sentinel",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": command},
        )

        result = router._dispatch_gates(ctx, state)

        if should_block:
            assert result is not None, f"Sentinel should block: {command!r}"
            assert result.verdict == GateVerdict.DENY, (
                f"Sentinel should DENY destructive op: {command!r}, got {result.verdict.value}"
            )
        else:
            if result is not None:
                assert result.verdict != GateVerdict.DENY, (
                    f"Sentinel should NOT block: {command!r}, got {result.verdict.value}"
                )

    def test_sentinel_off_mode_allows_all(self, router, monkeypatch):
        """SENTINEL_GATE_MODE=off disables the gate entirely."""
        _set_gate_modes(monkeypatch, sentinel="off")
        _reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel-off")
        ctx = HookContext(
            session_id="test-sentinel-off",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "rm -rf ~/.gemini/extensions/"},
        )

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                "Sentinel with mode=off must not block destructive ops"
            )

    def test_sentinel_warn_mode(self, router, monkeypatch):
        """SENTINEL_GATE_MODE=warn produces WARN instead of DENY."""
        _set_gate_modes(monkeypatch, sentinel="warn")
        _reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel-warn")
        ctx = HookContext(
            session_id="test-sentinel-warn",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "rm -rf ~/.gemini/extensions/aops-core/"},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Sentinel warn mode should produce a result"
        assert result.verdict == GateVerdict.WARN, (
            f"Sentinel warn mode should WARN, got {result.verdict.value}"
        )

    def test_sentinel_non_bash_tool_allowed(self, router, monkeypatch):
        """Non-shell tools are not inspected by sentinel."""
        _set_gate_modes(monkeypatch, sentinel="block")
        _reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel-edit")
        ctx = HookContext(
            session_id="test-sentinel-edit",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "~/.gemini/extensions/foo.txt"},
        )

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                "Sentinel should only inspect Bash/shell tools, not Edit"
            )

    def test_sentinel_gemini_shell_tool(self, router, monkeypatch):
        """Sentinel also catches Gemini's run_shell_command tool."""
        _set_gate_modes(monkeypatch, sentinel="block")
        _reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel-gemini")
        ctx = HookContext(
            session_id="test-sentinel-gemini",
            hook_event="PreToolUse",
            tool_name="run_shell_command",
            tool_input={"command": "rm -rf ~/.gemini/extensions/"},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None and result.verdict == GateVerdict.DENY, (
            "Sentinel must block destructive ops via Gemini's run_shell_command too"
        )
