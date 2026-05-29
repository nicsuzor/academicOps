"""Handover gate session-type behavior — parameterised across live fixture data.

Tests that the handover gate correctly differentiates between:
- Polecat/crew sessions: gate starts CLOSED, close triggers fire, UPS re-arms
- Interactive sessions: gate starts OPEN, close triggers suppressed, UPS does not re-arm
- Subagent sessions: gates skipped entirely (except Stop/SessionEnd/SubagentStop)

Fixture data extracted from real hook logs on 2026-05-27, including:
- Session 4956077c: subagent claiming task via update_task
- Session 17a70e85: nested subagent launching another Agent
- Session 790d28ab: junior session supervising agents, subagent dispatching polecat
- Session 8182f0f2: subagent Stop with gate deny
- Session 1853c8c7: Gemini polecat session
- Session 3fb9c8fc: interactive session with multiple gates
"""

import copy
import json
import os
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from tests.hooks.gate_helpers import (
    GateState,
    GateStatus,
    GateVerdict,
    HookContext,
    SessionState,
    reinit_gates_with_defaults,
)

FIXTURES_FILE = Path(__file__).parent / "fixtures" / "handover_session_type.json"


def _load_fixtures() -> dict:
    with FIXTURES_FILE.open(encoding="utf-8") as f:
        return json.load(f)


ALL_FIXTURES = _load_fixtures()


def _flatten(group: str) -> list[dict]:
    result = []
    for s in ALL_FIXTURES.get(group, []):
        s_copy = copy.deepcopy(s)
        s_copy["_group"] = group
        result.append(s_copy)
    return result


def _make_session_state(scenario: dict) -> SessionState:
    """Create a SessionState with correct session_type and gate overrides."""
    session_type = scenario.get("session_type", "interactive")

    # Temporarily set POLECAT_SESSION_TYPE so SessionState.create() picks it up
    old_val = os.environ.get("POLECAT_SESSION_TYPE")
    try:
        if session_type in ("polecat", "crew"):
            os.environ["POLECAT_SESSION_TYPE"] = session_type
        elif "POLECAT_SESSION_TYPE" in os.environ:
            del os.environ["POLECAT_SESSION_TYPE"]

        state = SessionState.create("test-handover-session-type")
    finally:
        if old_val is not None:
            os.environ["POLECAT_SESSION_TYPE"] = old_val
        elif "POLECAT_SESSION_TYPE" in os.environ:
            del os.environ["POLECAT_SESSION_TYPE"]

    # Apply gate overrides
    for gate_name, overrides in scenario.get("gate_overrides", {}).items():
        gate = state.gates.get(gate_name, GateState())
        if "status" in overrides:
            gate.status = GateStatus(overrides["status"])
        if "ops_since_open" in overrides:
            gate.ops_since_open = overrides["ops_since_open"]
        if "metrics" in overrides:
            gate.metrics.update(overrides["metrics"])
        state.gates[gate_name] = gate

    # Apply state overrides (e.g. current_task, session_did_work)
    for key, value in scenario.get("state_overrides", {}).items():
        if key == "current_task":
            state.main_agent.current_task = value
        elif hasattr(state, key) and not key.startswith("_"):
            setattr(state, key, value)  # typed fields like session_did_work
        else:
            state.state[key] = value

    return state


def _make_context(scenario: dict) -> HookContext:
    return HookContext(
        session_id="test-handover-session-type",
        hook_event=scenario["hook_event"],
        tool_name=scenario.get("tool_name"),
        tool_input=scenario.get("tool_input", {}),
        is_subagent=scenario.get("is_subagent", False),
        subagent_type=scenario.get("subagent_type"),
        raw_input=scenario.get("raw_input", {}),
    )


# --- Initial status tests ---


class TestHandoverInitialStatus:
    """Handover gate initial status depends on session type."""

    POLECAT = _flatten("handover_polecat_initial_closed")
    INTERACTIVE = _flatten("handover_interactive_stays_open")

    @pytest.mark.parametrize(
        "scenario",
        POLECAT,
        ids=[s["id"] for s in POLECAT],
    )
    def test_polecat_starts_closed(self, scenario):
        state = _make_session_state(scenario)
        assert state.gates["handover"].status == GateStatus.CLOSED, (
            f"[{scenario['id']}] Polecat/crew session should start with handover CLOSED, "
            f"got {state.gates['handover'].status}"
        )

    @pytest.mark.parametrize(
        "scenario",
        [s for s in INTERACTIVE if s["expected"].get("handover_initial_status") == "open"],
        ids=[
            s["id"] for s in INTERACTIVE if s["expected"].get("handover_initial_status") == "open"
        ],
    )
    def test_interactive_starts_open(self, scenario):
        state = _make_session_state(scenario)
        assert state.gates["handover"].status == GateStatus.OPEN, (
            f"[{scenario['id']}] Interactive session should start with handover OPEN, "
            f"got {state.gates['handover'].status}"
        )


# --- Interactive session: triggers suppressed ---


class TestHandoverInteractiveNoClose:
    """Interactive sessions: close triggers and UPS re-arm are suppressed."""

    SCENARIOS = _flatten("handover_interactive_stays_open")

    @pytest.mark.parametrize(
        "scenario",
        [s for s in SCENARIOS if s["expected"].get("handover_status_after") == "open"],
        ids=[s["id"] for s in SCENARIOS if s["expected"].get("handover_status_after") == "open"],
    )
    def test_interactive_gate_stays_open(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        router._dispatch_gates(ctx, state)

        assert state.gates["handover"].status == GateStatus.OPEN, (
            f"[{scenario['id']}] Handover gate should stay OPEN in interactive session after "
            f"{scenario['hook_event']} on {scenario.get('tool_name', 'N/A')}, "
            f"got {state.gates['handover'].status}"
        )


# --- Polecat session: triggers fire ---


class TestHandoverPolecatCloses:
    """Polecat sessions: close triggers fire and UPS re-arms."""

    SCENARIOS = _flatten("handover_polecat_close_triggers")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_polecat_close_triggers(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        router._dispatch_gates(ctx, state)

        expected_status = GateStatus(scenario["expected"]["handover_status_after"])
        assert state.gates["handover"].status == expected_status, (
            f"[{scenario['id']}] Polecat handover gate should be {expected_status.value} "
            f"after {scenario['hook_event']} on {scenario.get('tool_name', 'N/A')}, "
            f"got {state.gates['handover'].status}"
        )


# --- Subagent bypass ---


class TestHandoverSubagentBypass:
    """Subagent sessions: gates skipped for tool events, not for Stop/SubagentStop."""

    SCENARIOS = _flatten("handover_subagent_bypass")

    @pytest.mark.parametrize(
        "scenario",
        [s for s in SCENARIOS if s["expected"].get("gates_skipped")],
        ids=[s["id"] for s in SCENARIOS if s["expected"].get("gates_skipped")],
    )
    def test_subagent_gates_skipped(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        assert result is None, (
            f"[{scenario['id']}] Gates should be skipped for subagent "
            f"{scenario['hook_event']} on {scenario.get('tool_name', 'N/A')}, "
            f"but got verdict={result.verdict.value if result else 'N/A'}"
        )

    @pytest.mark.parametrize(
        "scenario",
        [s for s in SCENARIOS if not s["expected"].get("gates_skipped")],
        ids=[s["id"] for s in SCENARIOS if not s["expected"].get("gates_skipped")],
    )
    def test_subagent_stop_not_skipped(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if "verdict" in scenario["expected"]:
            expected_verdict = GateVerdict(scenario["expected"]["verdict"])
            assert result is not None, (
                f"[{scenario['id']}] Subagent {scenario['hook_event']} should NOT be skipped"
            )
            assert result.verdict == expected_verdict, (
                f"[{scenario['id']}] Expected {expected_verdict.value}, got {result.verdict.value}"
            )
        else:
            # Just verify it wasn't skipped (result can be None for allow)
            pass


# --- Stop verdict by session type ---


class TestHandoverStopBySessionType:
    """Stop event verdicts vary by session type."""

    SCENARIOS = _flatten("handover_stop_by_session_type")

    @pytest.mark.parametrize(
        "scenario",
        SCENARIOS,
        ids=[s["id"] for s in SCENARIOS],
    )
    def test_stop_verdict(self, router, scenario):
        state = _make_session_state(scenario)
        ctx = _make_context(scenario)

        result = router._dispatch_gates(ctx, state)

        if "verdict" in scenario["expected"]:
            expected_verdict = GateVerdict(scenario["expected"]["verdict"])
            assert result is not None, (
                f"[{scenario['id']}] Expected verdict={expected_verdict.value}, got None"
            )
            assert result.verdict == expected_verdict, (
                f"[{scenario['id']}] Expected {expected_verdict.value}, got {result.verdict.value}"
            )

        if "handover_status_after" in scenario["expected"]:
            expected_status = GateStatus(scenario["expected"]["handover_status_after"])
            assert state.gates["handover"].status == expected_status, (
                f"[{scenario['id']}] Handover gate should be {expected_status.value} "
                f"after Stop, got {state.gates['handover'].status}"
            )


# --- Full lifecycle: polecat session from creation through handover ---


class TestHandoverPolecatLifecycle:
    """End-to-end lifecycle test for polecat session handover gate."""

    def test_polecat_full_lifecycle(self, router, monkeypatch):
        """Polecat session: CLOSED → work → handover skill → OPEN (sticky) → UPS re-arms."""
        monkeypatch.setenv("POLECAT_SESSION_TYPE", "polecat")
        reinit_gates_with_defaults()

        state = SessionState.create("test-polecat-lifecycle")
        assert state.session_type == "polecat"
        assert state.gates["handover"].status == GateStatus.CLOSED

        # 1. Task claim (PostToolUse update_task) — stays CLOSED (already closed)
        ctx_claim = HookContext(
            session_id="test-polecat-lifecycle",
            hook_event="PostToolUse",
            tool_name="mcp__plugin_aops-core_pkb__update_task",
            tool_input={"id": "task-123", "updates": {"status": "in_progress"}},
        )
        router._dispatch_gates(ctx_claim, state)
        assert state.gates["handover"].status == GateStatus.CLOSED

        # 2. Write tool (Edit) — stays CLOSED
        ctx_edit = HookContext(
            session_id="test-polecat-lifecycle",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "foo.py"},
        )
        router._dispatch_gates(ctx_edit, state)
        assert state.gates["handover"].status == GateStatus.CLOSED

        # 3. Stop while handover CLOSED — should WARN (at minimum)
        # Open QA gate so its DENY doesn't mask the handover WARN
        state.gates["qa"].status = GateStatus.OPEN
        ctx_stop = HookContext(
            session_id="test-polecat-lifecycle",
            hook_event="Stop",
        )
        result = router._dispatch_gates(ctx_stop, state)
        assert result is not None
        assert result.verdict == GateVerdict.WARN

        # 4. Gate opens on fire-once Stop trigger
        assert state.gates["handover"].status == GateStatus.OPEN

        # 5. Handover skill completes — OPEN (sticky)
        ctx_skill = HookContext(
            session_id="test-polecat-lifecycle",
            hook_event="PostToolUse",
            tool_name="Skill",
            tool_input={"skill": "end_session"},
        )
        ctx_skill.subagent_type = "end_session"
        router._dispatch_gates(ctx_skill, state)
        assert state.gates["handover"].status == GateStatus.OPEN
        assert state.gates["handover"].sticky is True

        # 6. Write tool while sticky — stays OPEN (sticky suppresses)
        router._dispatch_gates(ctx_edit, state)
        assert state.gates["handover"].status == GateStatus.OPEN
        assert state.gates["handover"].sticky is True

        # 7. UPS unsticks and re-arms to CLOSED
        ctx_ups = HookContext(
            session_id="test-polecat-lifecycle",
            hook_event="UserPromptSubmit",
            tool_name=None,
            tool_input={},
        )
        router._dispatch_gates(ctx_ups, state)
        assert state.gates["handover"].sticky is False
        assert state.gates["handover"].status == GateStatus.CLOSED

    def test_interactive_full_lifecycle(self, router, monkeypatch):
        """Interactive session: OPEN throughout — no close triggers, no re-arm."""
        # Ensure no POLECAT_SESSION_TYPE
        monkeypatch.delenv("POLECAT_SESSION_TYPE", raising=False)
        reinit_gates_with_defaults()

        state = SessionState.create("test-interactive-lifecycle")
        assert state.session_type == "interactive"
        assert state.gates["handover"].status == GateStatus.OPEN

        # 1. Task claim — gate stays OPEN (trigger suppressed for interactive)
        ctx_claim = HookContext(
            session_id="test-interactive-lifecycle",
            hook_event="PostToolUse",
            tool_name="mcp__plugin_aops-core_pkb__update_task",
            tool_input={"id": "task-123", "updates": {"status": "in_progress"}},
        )
        router._dispatch_gates(ctx_claim, state)
        assert state.gates["handover"].status == GateStatus.OPEN

        # 2. Write tool — gate stays OPEN
        ctx_edit = HookContext(
            session_id="test-interactive-lifecycle",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "foo.py"},
        )
        router._dispatch_gates(ctx_edit, state)
        assert state.gates["handover"].status == GateStatus.OPEN

        # 3. UPS — gate stays OPEN (no re-arm in interactive)
        ctx_ups = HookContext(
            session_id="test-interactive-lifecycle",
            hook_event="UserPromptSubmit",
            tool_name=None,
            tool_input={},
        )
        router._dispatch_gates(ctx_ups, state)
        assert state.gates["handover"].status == GateStatus.OPEN

        # 4. Stop — no handover warning (gate is OPEN)
        ctx_stop = HookContext(
            session_id="test-interactive-lifecycle",
            hook_event="Stop",
        )
        router._dispatch_gates(ctx_stop, state)
        # IDA gate may still fire (warn), but handover should not
        assert state.gates["handover"].status == GateStatus.OPEN

        # 5. Bash, Agent, etc — gate stays OPEN throughout
        state.main_agent.current_task = "task-456"
        ctx_bash = HookContext(
            session_id="test-interactive-lifecycle",
            hook_event="PostToolUse",
            tool_name="Bash",
            tool_input={"command": "ls"},
        )
        router._dispatch_gates(ctx_bash, state)
        assert state.gates["handover"].status == GateStatus.OPEN
