"""Shared helpers and constants for gate hook tests.

All gate test modules import from here. Adding a new gate to the system
requires adding one entry to STOP_GATES (for stop-event gates) or the
relevant data structure.
"""

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
AOPS_CORE = REPO_ROOT / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter  # noqa: F401
from hooks.schemas import HookContext  # noqa: F401
from lib.gate_model import GateVerdict  # noqa: F401
from lib.gate_types import GateState, GateStatus  # noqa: F401
from lib.gates.registry import GateRegistry  # noqa: F401
from lib.session_state import SessionState

# --- Constants ---

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCENARIOS_FILE = FIXTURES_DIR / "gate_scenarios.json"
LIVE_SCENARIOS_FILE = FIXTURES_DIR / "gate_scenarios_live.json"

ROUTER_PATH = AOPS_CORE / "hooks" / "router.py"

STOP_GATES = ["handover", "qa", "ida"]

ALL_HOOK_EVENTS = [
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SessionEnd",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "Notification",
]

CLAUDE_ACCEPTED_HOOK_EVENT_NAMES = {
    "PreToolUse",
    "UserPromptSubmit",
    "PostToolUse",
    "PostToolBatch",
}

ADVISORY = (
    "<SYSTEM HOOK INSTRUCTION>Watch out, you aren't finished until you: "
    "provide evidence and an indicator of your level of certainty for "
    "EACH of your major claims.</SYSTEM HOOK INSTRUCTION>"
)


# --- Fixture data ---


def load_scenarios() -> dict:
    with SCENARIOS_FILE.open() as f:
        scenarios = json.load(f)
    if LIVE_SCENARIOS_FILE.exists():
        with LIVE_SCENARIOS_FILE.open() as f:
            live = json.load(f)
        scenarios.update(live)
    return scenarios


ALL_SCENARIOS = load_scenarios()


def flatten_scenarios(*groups: str) -> list[dict]:
    result = []
    for group in groups:
        scenarios = ALL_SCENARIOS.get(group, [])
        for s in scenarios:
            s["_group"] = group
            result.append(s)
    return result


# --- Gate helpers ---


def reinit_gates_with_defaults():
    """Reload gate_config and definitions, then reinit the registry."""
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


def set_gate_modes(
    monkeypatch,
    *,
    handover: str = "warn",
    qa: str = "block",
    enforcer: str = "block",
    hydration: str = "off",
    ida: str = "off",
    enforcer_threshold: int = 50,
) -> None:
    """Stamp the requested gate modes onto the environment.

    ida defaults to "off" so existing test scenarios that expect "allow" on Stop
    keep their invariants. Tests targeting ida behaviour pass it explicitly.
    """
    monkeypatch.setenv("HANDOVER_GATE_MODE", handover)
    monkeypatch.setenv("QA_GATE_MODE", qa)
    monkeypatch.setenv("ENFORCER_GATE_MODE", enforcer)
    monkeypatch.setenv("HYDRATION_GATE_MODE", hydration)
    monkeypatch.setenv("IDA_GATE_MODE", ida)
    monkeypatch.setenv("ENFORCER_TOOL_CALL_THRESHOLD", str(enforcer_threshold))


def make_session_state(scenario: dict) -> SessionState:
    """Create a SessionState with gate overrides from the scenario."""
    state = SessionState.create("test-session-verdict")
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
    for key, value in scenario.get("state_overrides", {}).items():
        state.state[key] = value
    return state


def make_context(scenario: dict) -> HookContext:
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


def make_gate_trigger_state(gate_name: str) -> SessionState:
    """Create a SessionState that causes the named gate's policy to fire.

    - enforcer: ops_since_open at threshold
    - qa / handover / ida: gate CLOSED so Stop-event policy fires
    """
    state = SessionState.create("test-gate-mode")
    if gate_name == "enforcer":
        from hooks.gate_config import ENFORCER_TOOL_CALL_THRESHOLD

        state.gates["enforcer"].ops_since_open = ENFORCER_TOOL_CALL_THRESHOLD
    elif gate_name in ("qa", "handover", "ida"):
        if gate_name not in state.gates:
            state.gates[gate_name] = GateState(status=GateStatus.CLOSED)
        else:
            state.gates[gate_name].status = GateStatus.CLOSED
        if gate_name == "qa":
            state.gates[gate_name].metrics["temp_path"] = "/tmp/qa-gate.md"
    return state


def make_gate_trigger_context(gate_name: str) -> HookContext:
    """Create a HookContext that triggers the named gate's policy.

    - enforcer: PreToolUse on Agent (spawn tool, not excluded)
    - qa / handover / ida: Stop event
    """
    if gate_name == "enforcer":
        return HookContext(
            session_id="test-gate-mode",
            hook_event="PreToolUse",
            tool_name="Agent",
            tool_input={"prompt": "test"},
        )
    return HookContext(
        session_id="test-gate-mode",
        hook_event="Stop",
    )


# --- Subprocess helpers ---


def run_router_claude(input_data: dict, timeout: int = 30) -> tuple[dict, str]:
    """Run router in Claude Code mode."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AOPS_CORE)
    result = subprocess.run(
        [sys.executable, str(ROUTER_PATH), "--client", "claude"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(AOPS_CORE),
    )
    output = {}
    if result.stdout.strip():
        output = json.loads(result.stdout)
    return output, result.stderr


def run_router_gemini(input_data: dict, event: str, timeout: int = 30) -> tuple[dict, str]:
    """Run router in Gemini CLI mode."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AOPS_CORE)
    result = subprocess.run(
        [sys.executable, str(ROUTER_PATH), "--client", "gemini", event],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(AOPS_CORE),
    )
    output = {}
    if result.stdout.strip():
        output = json.loads(result.stdout)
    return output, result.stderr
