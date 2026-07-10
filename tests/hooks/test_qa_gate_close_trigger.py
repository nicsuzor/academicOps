#!/usr/bin/env python3
"""
Regression tests for the qa gate close-on-task-claim triggers and sticky_until.

The qa gate closes when a task is claimed (update_task → in_progress), NOT on
write-tool use. Sessions without a claimed task skip the QA gate entirely.
The verifier subagent (marsha/qa/verify) reopens it with sticky_until so
writes to fix findings don't re-close it.
"""

import importlib
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter  # noqa: E402
from lib.gate_types import GateState, GateStatus, GateVerdict  # noqa: E402
from lib.gates.registry import GateRegistry  # noqa: E402
from lib.hook_context import HookContext  # noqa: E402
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
    state.main_agent.current_task = "task-stub"
    state.gates["qa"] = GateState(status=GateStatus.OPEN)
    state.gates["handover"] = GateState(status=GateStatus.OPEN)
    return state


def _state_without_task(session_id: str) -> SessionState:
    state = SessionState.create(session_id)
    state.gates["qa"] = GateState(status=GateStatus.OPEN)
    state.gates["handover"] = GateState(status=GateStatus.OPEN)
    return state


# --- Close trigger: task-claim ---


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


# --- Write tool does NOT close QA gate ---


def test_edit_does_not_close_qa_gate(router):
    """Write tools should NOT close the qa gate — only task-claim does."""
    state = _state_with_bound_task("qa-edit")

    ctx = HookContext(
        session_id="qa-edit",
        hook_event="PostToolUse",
        tool_name="Edit",
        tool_input={"file_path": "/tmp/foo.py"},
    )
    router._dispatch_gates(ctx, state)

    assert state.gates["qa"].status == GateStatus.OPEN, (
        "qa gate should NOT close on write tool — only task-claim closes it"
    )


def test_write_without_task_claim_does_not_close_qa(router):
    """Write tools without a task claim should not close the qa gate."""
    state = _state_without_task("qa-no-task")

    ctx = HookContext(
        session_id="qa-no-task",
        hook_event="PostToolUse",
        tool_name="Write",
        tool_input={"file_path": "/tmp/bar.py"},
    )
    router._dispatch_gates(ctx, state)

    assert state.gates["qa"].status == GateStatus.OPEN, (
        "qa gate must stay open when no task is claimed"
    )


# --- Task-claim → Stop (no verifier) → blocked ---


def test_task_claim_then_stop_without_verifier_blocks(router, monkeypatch):
    """After task claim, Stop without verifier should be blocked."""
    monkeypatch.setenv("QA_GATE_MODE", "block")
    _reinit_gates_with_defaults()

    state = _state_with_bound_task("qa-block-stop")
    state.gates["qa"].metrics["temp_path"] = "/tmp/qa-gate.md"

    router._dispatch_gates(
        HookContext(
            session_id="qa-block-stop",
            hook_event="PostToolUse",
            tool_name="update_task",
            tool_input={"id": "task-abc", "status": "in_progress"},
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.CLOSED

    result = router._dispatch_gates(
        HookContext(
            session_id="qa-block-stop",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        ),
        state,
    )
    assert result is not None, "Stop should be blocked when qa gate is CLOSED"


# --- Verifier reopens ---


def test_verifier_subagent_reopens_qa_gate(router):
    """marsha completion should reopen the qa gate after a close."""
    state = _state_with_bound_task("qa-reopen")

    # Close the gate via task claim.
    router._dispatch_gates(
        HookContext(
            session_id="qa-reopen",
            hook_event="PostToolUse",
            tool_name="update_task",
            tool_input={"id": "task-abc", "status": "in_progress"},
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


# --- After verifier, Stop should allow ---


def test_stop_allowed_after_verifier(router, monkeypatch):
    """After verifier runs, Stop should be allowed (qa isolated: ida/handover off
    so this asserts the qa gate specifically — ida now hard-blocks once on every
    Stop by default, D1)."""
    monkeypatch.setenv("IDA_GATE_MODE", "off")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "off")
    _reinit_gates_with_defaults()
    state = _state_with_bound_task("qa-allow-stop")

    # Close via task claim.
    router._dispatch_gates(
        HookContext(
            session_id="qa-allow-stop",
            hook_event="PostToolUse",
            tool_name="update_task",
            tool_input={"id": "task-abc", "status": "in_progress"},
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.CLOSED

    # Verifier runs.
    router._dispatch_gates(
        HookContext(
            session_id="qa-allow-stop",
            hook_event="SubagentStop",
            tool_name=None,
            tool_input={},
            subagent_type="aops-core:marsha",
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.OPEN

    # Stop should pass.
    result = router._dispatch_gates(
        HookContext(
            session_id="qa-allow-stop",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
        ),
        state,
    )
    has_deny = (
        result is not None
        and hasattr(result, "verdict")
        and str(result.verdict) in ("deny", "GateVerdict.DENY")
    )
    assert not has_deny, "Stop should be allowed after verifier runs"


def test_release_task_does_not_close_qa_gate(router):
    """Infrastructure mcp tools must not close the qa gate."""
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


# --- Sticky lifecycle ---


def test_write_after_marsha_does_not_reclose_qa(router):
    """Writes after marsha verification must not re-close the QA gate.
    sticky_until keeps the gate open until UserPromptSubmit."""
    state = _state_with_bound_task("qa-loop")

    # 1. Close the gate via task claim.
    router._dispatch_gates(
        HookContext(
            session_id="qa-loop",
            hook_event="PostToolUse",
            tool_name="update_task",
            tool_input={"id": "task-abc", "status": "in_progress"},
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


# --- UPS re-arm gated on task ---


def test_ups_does_not_rearm_qa_without_task(router):
    """UserPromptSubmit should NOT re-arm (close) the QA gate when no task
    is bound. Sessions without a claimed task skip the QA gate entirely."""
    state = _state_without_task("qa-no-rearm")

    router._dispatch_gates(
        HookContext(
            session_id="qa-no-rearm",
            hook_event="UserPromptSubmit",
            tool_name=None,
            tool_input={},
        ),
        state,
    )
    assert state.gates["qa"].status == GateStatus.OPEN, (
        "qa gate must stay OPEN on UPS when no task is bound"
    )


def test_stop_hook_active_is_ignored_no_special_bypass(router, monkeypatch):
    """The old global stop_hook_active bypass was REMOVED (client-agnostic
    redesign). A Stop carrying stop_hook_active=True is treated like any other
    Stop — the flag no longer short-circuits gate evaluation. Uses handover block
    (no PKB dependency) and isolates other gates so this asserts the bypass is
    gone, not some other gate."""
    monkeypatch.setenv("IDA_GATE_MODE", "off")
    monkeypatch.setenv("QA_GATE_MODE", "off")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "block")
    _reinit_gates_with_defaults()
    state = _state_with_bound_task("hv-stop-active")
    state.turn_did_work = True
    state.gates["handover"] = GateState(status=GateStatus.CLOSED)  # armed → would block

    result = router._dispatch_gates(
        HookContext(
            session_id="hv-stop-active",
            hook_event="Stop",
            tool_name=None,
            tool_input={},
            raw_input={"stop_hook_active": True},
        ),
        state,
    )
    assert result is not None and result.verdict == GateVerdict.DENY, (
        "stop_hook_active must NOT bypass gates any more — handover block still fires"
    )


def test_block_gate_retry_loop_is_bounded_by_deny_counter(router, monkeypatch):
    """Client-agnostic loop safety WITHOUT the stop_hook_active bypass: a block
    gate that is never satisfied re-DENYs each Stop-continuation within a turn,
    but the per-gate stop_deny_count escape hatch downgrades it to WARN-and-allow
    at the threshold (engine default 3) so the retry loop terminates. This is the
    replacement guarantee for the deleted router bypass. Uses handover block (no
    PKB dependency)."""
    monkeypatch.setenv("IDA_GATE_MODE", "off")
    monkeypatch.setenv("QA_GATE_MODE", "off")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "block")
    _reinit_gates_with_defaults()
    state = _state_with_bound_task("hv-loop")
    state.turn_did_work = True
    state.gates["handover"] = GateState(status=GateStatus.CLOSED)  # armed, never satisfied

    stop = HookContext(session_id="hv-loop", hook_event="Stop", tool_name=None, tool_input={})

    # Simulate the runtime forcing continuation after each block (no UPS between —
    # this is the within-turn retry loop the old bypass used to short-circuit).
    r1 = router._dispatch_gates(stop, state)
    assert r1 is not None and r1.verdict == GateVerdict.DENY
    r2 = router._dispatch_gates(stop, state)
    assert r2 is not None and r2.verdict == GateVerdict.DENY
    r3 = router._dispatch_gates(stop, state)
    assert r3 is not None and r3.verdict == GateVerdict.WARN, (
        "3rd consecutive unsatisfied Stop must downgrade to WARN-and-allow so the "
        f"loop terminates; got {r3.verdict.value if r3 else None}"
    )
