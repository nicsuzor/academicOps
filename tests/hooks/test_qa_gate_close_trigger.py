#!/usr/bin/env python3
"""
Regression tests for the qa gate close-on-work-begin triggers and sticky_until.

Before the close-trigger fix (PR for aops-fd1b83e0) GATE_CONFIGS[1] had no
transition that targeted GateStatus.CLOSED, so the Stop policy's
`current_status=CLOSED` condition was never satisfied and the gate was dead
code. These tests pin the close triggers: update_task→in_progress and any
write tool → CLOSED, mirroring the handover gate's pattern.

The sticky_until mechanism (replacing the qa_verified latch) keeps the QA
gate OPEN after verification until UserPromptSubmit, preventing the
marsha→fix→Stop-blocked endless loop.
"""

import importlib
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter  # noqa: E402
from hooks.schemas import HookContext  # noqa: E402
from lib.gate_types import GateState, GateStatus  # noqa: E402
from lib.gates.registry import GateRegistry  # noqa: E402
from lib.session_state import SessionState  # noqa: E402


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


def _state_with_bound_task(session_id: str) -> SessionState:
    state = SessionState.create(session_id)
    # Mark a task as bound so is_write_tool's no-task carve-out doesn't apply.
    state.main_agent.current_task = "task-stub"
    state.gates["qa"] = GateState(status=GateStatus.OPEN)
    state.gates["handover"] = GateState(status=GateStatus.OPEN)
    return state


def test_update_task_in_progress_closes_qa_gate(router):
    """update_task setting a task to in_progress should close the qa gate."""
    state = _state_with_bound_task("qa-update-task")

    ctx = HookContext(
        session_id="qa-update-task",
        hook_event="PostToolUse",
        tool_name="update_task",
        tool_input={"id": "task-abc", "status": "in_progress"},
    )
    router._dispatch_gates(ctx, state)

    assert state.gates["qa"].status == GateStatus.CLOSED, (
        "qa gate should close when a task is bound in_progress"
    )


def test_edit_closes_qa_gate(router):
    """Any write tool (Edit) should close the qa gate."""
    state = _state_with_bound_task("qa-edit")

    ctx = HookContext(
        session_id="qa-edit",
        hook_event="PostToolUse",
        tool_name="Edit",
        tool_input={"file_path": "/tmp/foo.py"},
    )
    router._dispatch_gates(ctx, state)

    assert state.gates["qa"].status == GateStatus.CLOSED, (
        "qa gate should close on PostToolUse(Edit) with a bound task"
    )


def test_verifier_subagent_reopens_qa_gate(router):
    """marsha completion should reopen the qa gate after a close."""
    state = _state_with_bound_task("qa-reopen")

    # Close the gate via a write.
    router._dispatch_gates(
        HookContext(
            session_id="qa-reopen",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/tmp/foo.py"},
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.CLOSED

    # Verifier runs.
    router._dispatch_gates(
        HookContext(
            session_id="qa-reopen",
            hook_event="SubagentStop",
            tool_name=None,
            tool_input={},
            subagent_type="aops-core:marsha",
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.OPEN, (
        "qa gate should reopen after a verifier subagent (marsha) runs"
    )
    assert state.gates["qa"].sticky is True, "qa gate should be sticky after verification"


def test_release_task_does_not_close_qa_gate(router):
    """Infrastructure mcp tools must not close the qa gate.

    `is_write_tool` defers to `get_tool_category`, which classifies
    mcp__pkb__release_task as infrastructure. This pins the contract.
    """
    state = _state_with_bound_task("qa-infra")

    ctx = HookContext(
        session_id="qa-infra",
        hook_event="PostToolUse",
        tool_name="mcp__pkb__release_task",
        tool_input={"id": "task-1", "status": "done"},
    )
    router._dispatch_gates(ctx, state)

    assert state.gates["qa"].status == GateStatus.OPEN, (
        "release_task is infrastructure and must not close qa"
    )


def test_bash_after_handover_does_not_close_qa(router):
    """Bash treated as read when handover gate is sticky (post-skill)
    should keep qa OPEN, matching the is_write_tool carve-out."""
    state = _state_with_bound_task("qa-post-handover")
    # Set handover gate as sticky (simulating post-/end-session state)
    state.gates["handover"] = GateState(
        status=GateStatus.OPEN, sticky=True, sticky_until_events=["UserPromptSubmit"]
    )

    ctx = HookContext(
        session_id="qa-post-handover",
        hook_event="PostToolUse",
        tool_name="Bash",
        tool_input={"command": "git status"},
    )
    router._dispatch_gates(ctx, state)

    assert state.gates["qa"].status == GateStatus.OPEN, (
        "Post-handover bash should not re-close the qa gate"
    )


def test_write_after_marsha_does_not_reclose_qa(router):
    """Regression: writes after marsha verification must not re-close the QA
    gate. sticky_until keeps the gate open until UserPromptSubmit, preventing
    the endless marsha → fix → Stop-blocked loop."""
    state = _state_with_bound_task("qa-loop")

    # 1. Close the gate via a write (work begins).
    router._dispatch_gates(
        HookContext(
            session_id="qa-loop",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/tmp/foo.py"},
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.CLOSED

    # 2. Marsha runs — gate opens with sticky.
    router._dispatch_gates(
        HookContext(
            session_id="qa-loop",
            hook_event="SubagentStop",
            tool_name=None,
            tool_input={},
            subagent_type="aops-core:marsha",
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.OPEN
    assert state.gates["qa"].sticky is True

    # 3. Agent writes code to fix marsha's findings — gate must stay OPEN.
    router._dispatch_gates(
        HookContext(
            session_id="qa-loop",
            hook_event="PostToolUse",
            tool_name="Edit",
            tool_input={"file_path": "/tmp/foo.py"},
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.OPEN, (
        "Write after marsha must not re-close the qa gate"
    )


def test_qa_sticky_clears_on_user_prompt(router):
    """QA sticky flag clears on UserPromptSubmit so the gate re-arms."""
    state = _state_with_bound_task("qa-reset")
    state.gates["qa"] = GateState(
        status=GateStatus.OPEN, sticky=True, sticky_until_events=["UserPromptSubmit"]
    )

    router._dispatch_gates(
        HookContext(
            session_id="qa-reset",
            hook_event="UserPromptSubmit",
            tool_name=None,
            tool_input={},
        ),
        state,
    )
    assert state.gates["qa"].sticky is False, "qa sticky must clear on new user prompt"
    assert state.gates["qa"].status == GateStatus.CLOSED, (
        "qa gate must re-arm (CLOSED) after UPS unsticks it"
    )


def test_qa_sticky_clears_then_new_task_closes(router):
    """After UPS unsticks QA, a new task binding closes the gate normally."""
    state = _state_with_bound_task("qa-newtask")
    state.gates["qa"] = GateState(
        status=GateStatus.OPEN, sticky=True, sticky_until_events=["UserPromptSubmit"]
    )

    # UPS unsticks and re-arms
    router._dispatch_gates(
        HookContext(
            session_id="qa-newtask",
            hook_event="UserPromptSubmit",
            tool_name=None,
            tool_input={},
        ),
        state,
    )
    assert state.gates["qa"].sticky is False
    assert state.gates["qa"].status == GateStatus.CLOSED

    # New task binding closes the gate (already closed, but verifies the path)
    router._dispatch_gates(
        HookContext(
            session_id="qa-newtask",
            hook_event="PostToolUse",
            tool_name="update_task",
            tool_input={"id": "task-new", "status": "in_progress"},
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.CLOSED


def test_stop_hook_active_bypasses_all_gates(router):
    """When stop_hook_active=True, gates must not block — prevents
    infinite retry loops in both Claude Code and Gemini CLI."""
    state = _state_with_bound_task("qa-stop-active")
    # Close all gates so they would normally block.
    state.gates["qa"] = GateState(status=GateStatus.CLOSED)
    state.gates["handover"] = GateState(status=GateStatus.CLOSED)

    result = router._dispatch_gates(
        HookContext(
            session_id="qa-stop-active",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
            raw_input={"stop_hook_active": True},
        ),
        state,
    )
    assert result is None, "stop_hook_active=True must bypass all gate evaluation"
