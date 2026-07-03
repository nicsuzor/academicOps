#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

import importlib

import pytest
from hooks.router import HookRouter
from lib.gate_types import GateStatus
from lib.gates.registry import GateRegistry
from lib.hook_context import HookContext
from lib.session_state import SessionState


def _reinit_gates_with_defaults():
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


def _make_polecat_state(session_id: str) -> SessionState:
    """Create a polecat SessionState (handover starts CLOSED)."""
    old = os.environ.get("AOPS_POLECAT_CONTAINER")
    os.environ["AOPS_POLECAT_CONTAINER"] = "1"
    try:
        return SessionState.create(session_id)
    finally:
        if old is not None:
            os.environ["AOPS_POLECAT_CONTAINER"] = old
        else:
            os.environ.pop("AOPS_POLECAT_CONTAINER", None)


@pytest.fixture
def router():
    _reinit_gates_with_defaults()
    return HookRouter()


def test_handover_latch_bash_after_dump(router):
    """Verify that Bash after end_session does not re-close the gate (sticky_until)."""
    session_id = "test-latch"
    state = _make_polecat_state(session_id)

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
    assert state.gates["handover"].sticky is True

    # 2. Run Bash
    ctx_bash = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="Bash",
        tool_input={"command": "ls"},
    )
    router._dispatch_gates(ctx_bash, state)

    # Gate should stay OPEN (sticky suppresses close)
    assert state.gates["handover"].status == GateStatus.OPEN
    assert state.gates["handover"].sticky is True


def test_handover_latch_edit_after_dump(router):
    """Verify that Edit after end_session does NOT re-close the gate (sticky_until).

    With sticky_until, the gate stays open until UserPromptSubmit regardless
    of what tools are used — the next UPS re-arms the gate for the new turn.
    """
    session_id = "test-reclose"
    state = _make_polecat_state(session_id)

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

    # 2. Run Edit — sticky suppresses close
    ctx_edit = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="Edit",
        tool_input={"file_path": "foo.py"},
    )
    router._dispatch_gates(ctx_edit, state)

    # Gate stays OPEN while sticky
    assert state.gates["handover"].status == GateStatus.OPEN
    assert state.gates["handover"].sticky is True


def test_handover_unsticks_on_user_prompt(router):
    """Verify that UserPromptSubmit unsticks and re-arms the handover gate (polecat)."""
    session_id = "test-unstick"
    state = _make_polecat_state(session_id)

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
    assert state.gates["handover"].sticky is True

    # 2. UserPromptSubmit unsticks and re-arms
    router._dispatch_gates(
        HookContext(
            session_id=session_id,
            hook_event="UserPromptSubmit",
            tool_name=None,
            tool_input={},
        ),
        state,
    )
    assert state.gates["handover"].sticky is False
    assert state.gates["handover"].status == GateStatus.CLOSED


def test_bash_no_task_does_not_close_gate(router, monkeypatch):
    """Verify that Bash without a bound task does not close the gate (aops-2283a8b0)."""
    monkeypatch.delenv("AOPS_POLECAT_CONTAINER", raising=False)
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
    """Verify that Bash with a bound task DOES close the gate in polecat sessions."""
    session_id = "test-with-task"
    state = _make_polecat_state(session_id)
    state.main_agent.current_task = "task-123"
    # Polecat starts CLOSED; set to OPEN to test the close trigger
    state.gates["handover"].status = GateStatus.OPEN

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


def test_interactive_edit_tool_closes_gate(router):
    """An interactive session that edits a file closes handover (all-session trigger)."""
    session_id = "test-interactive-edit"
    state = SessionState.create(session_id)
    # Interactive sessions start OPEN.
    assert state.gates["handover"].status == GateStatus.OPEN

    ctx_edit = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="Edit",
        tool_input={"file_path": "x.py", "old_string": "a", "new_string": "b"},
    )
    router._dispatch_gates(ctx_edit, state)

    # Gate should CLOSE and the session is marked as having done work.
    assert state.gates["handover"].status == GateStatus.CLOSED
    assert state.session_did_work is True


def test_interactive_claim_task_closes_gate(router):
    """An interactive session that claims a pkb task closes handover (all-session trigger)."""
    session_id = "test-interactive-claim"
    state = SessionState.create(session_id)
    assert state.gates["handover"].status == GateStatus.OPEN

    ctx_claim = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="mcp__plugin_aops-core_pkb__claim_task",
        tool_input={"id": "task-123"},
    )
    router._dispatch_gates(ctx_claim, state)

    assert state.gates["handover"].status == GateStatus.CLOSED
    assert state.session_did_work is True
