#!/usr/bin/env python3
import sys
from pathlib import Path

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

import importlib

import pytest
from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_types import GateStatus
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
    monkeypatch.setenv("HANDOVER_GATE_MODE", "block")
    _reinit_gates_with_defaults()
    return HookRouter()


def test_handover_latch_bash_after_dump(router):
    """Verify that Bash after end_session does not re-close the gate (aops-2283a8b0)."""
    session_id = "test-latch"
    state = SessionState.create(session_id)

    # 1. Open gate with end_session
    ctx_dump = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="activate_skill",
        tool_input={"skill": "end_session"},
    )
    ctx_dump.subagent_type = "end_session"
    router._dispatch_gates(ctx_dump, state)
    assert state.gates["handover"].status == GateStatus.OPEN
    assert state.state.get("handover_skill_invoked") is True

    # 2. Run Bash
    ctx_bash = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="Bash",
        tool_input={"command": "ls"},
    )
    router._dispatch_gates(ctx_bash, state)

    # Gate should stay OPEN
    assert state.gates["handover"].status == GateStatus.OPEN
    assert state.state.get("handover_skill_invoked") is True


def test_handover_latch_edit_after_dump(router):
    """Verify that Edit after end_session DOES re-close the gate (aops-2283a8b0)."""
    session_id = "test-reclose"
    state = SessionState.create(session_id)

    # 1. Open gate with end_session
    ctx_dump = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="activate_skill",
        tool_input={"skill": "end_session"},
    )
    ctx_dump.subagent_type = "end_session"
    router._dispatch_gates(ctx_dump, state)
    assert state.gates["handover"].status == GateStatus.OPEN

    # 2. Run Edit
    ctx_edit = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="Edit",
        tool_input={"file_path": "foo.py"},
    )
    router._dispatch_gates(ctx_edit, state)

    # Gate should CLOSE
    assert state.gates["handover"].status == GateStatus.CLOSED
    assert state.state.get("handover_skill_invoked") is False


def test_bash_no_task_does_not_close_gate(router):
    """Verify that Bash without a bound task does not close the gate (aops-2283a8b0)."""
    session_id = "test-no-task"
    state = SessionState.create(session_id)
    assert state.main_agent.current_task is None
    assert state.gates["handover"].status == GateStatus.OPEN

    # Run Bash
    ctx_bash = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="Bash",
        tool_input={"command": "ls"},
    )
    router._dispatch_gates(ctx_bash, state)

    # Gate should stay OPEN
    assert state.gates["handover"].status == GateStatus.OPEN


def test_bash_with_task_closes_gate(router):
    """Verify that Bash with a bound task DOES close the gate (aops-2283a8b0)."""
    session_id = "test-with-task"
    state = SessionState.create(session_id)
    state.main_agent.current_task = "task-123"
    assert state.gates["handover"].status == GateStatus.OPEN

    # Run Bash
    ctx_bash = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="Bash",
        tool_input={"command": "ls"},
    )
    router._dispatch_gates(ctx_bash, state)

    # Gate should CLOSE
    assert state.gates["handover"].status == GateStatus.CLOSED
