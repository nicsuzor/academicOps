#!/usr/bin/env python3
import sys
from pathlib import Path

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

import importlib

from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_types import GateState, GateStatus
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState


def _reinit_gates_with_defaults():
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


@pytest.fixture
def router(monkeypatch):
    _reinit_gates_with_defaults()
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


def test_release_task_does_not_close_handover_gate(router):
    """
    Verify that release_task (infrastructure) does not re-trip the handover gate.

    REPRO:
    1. Gate is OPEN.
    2. PKB release_task is called (PostToolUse).
    3. Gate should remain OPEN.
    """
    state = SessionState.create("test-session")
    state.gates["handover"] = GateState(status=GateStatus.OPEN)

    # Simulate mcp__pkb__release_task call
    ctx = HookContext(
        session_id="test-session",
        hook_event="PostToolUse",
        tool_name="mcp__pkb__release_task",
        tool_input={"id": "task-123", "status": "done"},
    )

    router._dispatch_gates(ctx, state)

    assert state.gates["handover"].status == GateStatus.OPEN, (
        "release_task should not close the handover gate"
    )


def test_complete_task_does_not_close_handover_gate(router):
    """Verify that complete_task (infrastructure) does not re-trip the handover gate."""
    state = SessionState.create("test-session")
    state.gates["handover"] = GateState(status=GateStatus.OPEN)

    ctx = HookContext(
        session_id="test-session",
        hook_event="PostToolUse",
        tool_name="complete_task",
        tool_input={"id": "task-123"},
    )

    router._dispatch_gates(ctx, state)

    assert state.gates["handover"].status == GateStatus.OPEN, (
        "complete_task should not close the handover gate"
    )


def test_handover_skill_invoked_state_transitions(router):
    """
    Verify handover_skill_invoked state transitions:
    1. Initially False.
    2. Becomes True when handover skill completes.
    3. Becomes False when a write tool is used.
    4. Remains True when an infrastructure tool is used.
    """
    state = SessionState.create("test-session-state")
    assert state.state.get("handover_skill_invoked") is not True

    # 1. Complete handover skill
    ctx = HookContext(
        session_id="test-session-state",
        hook_event="PostToolUse",
        tool_name="activate_skill",
        tool_input={"skill": "dump"},
    )
    # router._dispatch_gates sets subagent_type from tool_input
    router._dispatch_gates(ctx, state)
    assert state.state.get("handover_skill_invoked") is True
    assert state.gates["handover"].status == GateStatus.OPEN

    # 2. Use infrastructure tool (release_task)
    ctx_infra = HookContext(
        session_id="test-session-state",
        hook_event="PostToolUse",
        tool_name="release_task",
        tool_input={"id": "task-1", "status": "done"},
    )
    router._dispatch_gates(ctx_infra, state)
    assert state.state.get("handover_skill_invoked") is True, (
        "Infrastructure should not reset handover_skill_invoked"
    )
    assert state.gates["handover"].status == GateStatus.OPEN

    # 3. Use light write tool (Bash) - latch should keep it True
    ctx_bash = HookContext(
        session_id="test-session-state",
        hook_event="PostToolUse",
        tool_name="Bash",
        tool_input={"command": "echo 'checking state'"},
    )
    router._dispatch_gates(ctx_bash, state)
    assert state.state.get("handover_skill_invoked") is True, (
        "Light Bash should not reset handover_skill_invoked due to latch"
    )
    assert state.gates["handover"].status == GateStatus.OPEN

    # 4. Use heavy write tool (Edit) - should reset
    ctx_edit = HookContext(
        session_id="test-session-state",
        hook_event="PostToolUse",
        tool_name="Edit",
        tool_input={"file_path": "foo.py"},
    )
    router._dispatch_gates(ctx_edit, state)
    assert state.state.get("handover_skill_invoked") is False, (
        "Heavy write tool should reset handover_skill_invoked"
    )
    assert state.gates["handover"].status == GateStatus.CLOSED
