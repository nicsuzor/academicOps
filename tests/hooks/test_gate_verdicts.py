#!/usr/bin/env python3
"""Gate verdict regression tests driven by saved scenario fixtures.

Validates that the gate system produces the correct block/warn/allow verdicts
for every realistic hook call scenario. Uses JSON fixture data that replicates
actual Claude Code and Gemini CLI hook invocations.

Key invariants tested:
1. Compliance agents (hydrator, custodiet, audit, butler) are NEVER blocked
2. Read-only tools bypass custodiet gate (unlike write tools)
3. Infrastructure tools bypass ALL gates; spawn tools (Agent, Skill) do NOT
4. Custodiet blocks at ops threshold for write/spawn tools only
5. Stop event respects handover and QA gates
6. Claude Code and Gemini CLI output formats match their respective schemas
7. Gate triggers (custodiet resets counter) fire correctly
8. Gate mode env var overrides work correctly
9. Custodiet deadlock prevented: Agent(custodiet) dispatch resets counter before policy fires

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
    monkeypatch.setenv("HYDRATION_GATE_MODE", "off")
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
    def test_spawn_blocked(self, router, hydration_mode, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if hydration_mode == "off":
            assert result is None, f"[{scenario['id']}] Expected None (allow) in 'off' mode"
            return

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

        if hydration_mode == "off":
            assert result is None, f"[{scenario['id']}] Expected None (allow) in 'off' mode"
            return

        expected = GateVerdict.WARN if hydration_mode == "warn" else GateVerdict.DENY
        assert result is not None, (
            f"[{scenario['id']}] Expected {expected.value} but got None (allow) "
            f"in {hydration_mode} mode"
        )
        assert result.verdict == expected, (
            f"[{scenario['id']}] {scenario['tool_name']} should be "
            f"{expected.value} in {hydration_mode} mode, got {result.verdict.value}"
        )


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
                "subagent_type": "aops-core:hydrator",
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
            "hydrator_tool": "hydrator",
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
    because tool_name='hydrator' (not 'delegate_to_agent'), so the
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

    @pytest.mark.parametrize("hydration_mode", ["off", "warn", "block"])
    @pytest.mark.parametrize("cmd", HEREDOC_COMMANDS)
    def test_bash_heredoc_blocked_when_hydration_closed(
        self, router, hydration_mode, cmd, monkeypatch
    ):
        """Bash with file-writing commands must be denied in block mode.

        In off mode, the gate allows through (no verdict).
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

        if hydration_mode == "off":
            assert result is None, f"Bash({cmd['description']}) should be allowed in 'off' mode"
            return

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
# GATE MODE ENV VAR CASES: non-hydration gates
# ===========================================================================

_GATE_MODE_CASES = [
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
