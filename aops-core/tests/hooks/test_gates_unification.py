import uuid
from unittest.mock import patch

import pytest
from hooks.schemas import HookContext
from lib.gate_types import GateStatus
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState


def on_subagent_stop(ctx: HookContext, state: SessionState):
    """Dispatch SubagentStop to all gates.

    Replacement for hooks.gates.on_subagent_stop after refactoring.
    """
    GateRegistry.initialize()

    messages = []
    context_injections = []

    for gate in GateRegistry.get_all_gates():
        result = gate.on_subagent_stop(ctx, state)
        if result:
            if result.system_message:
                messages.append(result.system_message)
            if result.context_injection:
                context_injections.append(result.context_injection)

    if messages or context_injections:
        from lib.gate_model import GateResult

        return GateResult.allow(
            system_message="\n".join(messages) if messages else None,
            context_injection="\n\n".join(context_injections) if context_injections else None,
        )
    return None


@pytest.fixture
def mock_session(tmp_path):
    session_id = f"test_session_unification_{uuid.uuid4().hex}"
    # Patch both locations to ensure consistent path resolution
    with (
        patch("lib.session_paths.get_session_status_dir", return_value=tmp_path),
        patch("lib.session_state.get_session_status_dir", return_value=tmp_path),
    ):
        state = SessionState.create(session_id)
        state.save()
        yield session_id


def test_gate_open_close_unification(mock_session):
    """Test that open_gate and close_gate update unified state."""
    session_id = mock_session
    state = SessionState.load(session_id)

    # Open handover gate
    state.open_gate("handover")
    state.save()

    state = SessionState.load(session_id)
    assert state.gates["handover"].status == GateStatus.OPEN

    # Close handover gate
    state.close_gate("handover")
    state.save()

    state = SessionState.load(session_id)
    assert state.gates["handover"].status == GateStatus.CLOSED


def test_handover_gate_opening_skill(mock_session):
    """Test that handover gate opens when handover skill stops."""
    session_id = mock_session

    ctx = HookContext(
        session_id=session_id,
        trace_id=None,
        hook_event="PostToolUse",
        tool_name="Skill",
        subagent_type="handover",  # Matches pattern
        raw_input={"tool_name": "Skill", "tool_input": {"skill": "handover"}},
    )

    state = SessionState.load(session_id)
    # Ensure gate starts closed
    state.gates["handover"].status = GateStatus.CLOSED
    state.save()

    # Need a router to run triggers
    from hooks.router import HookRouter

    router = HookRouter.__new__(HookRouter)
    router.session_data = {}

    # Run hooks
    with patch("hooks.router.SessionState.load", return_value=state):
        result = router.execute_hooks(ctx)

    assert result is not None
    assert result.system_message is not None
    assert "Handover complete" in result.system_message

    # Verify status
    assert state.gates["handover"].status == GateStatus.OPEN


if __name__ == "__main__":
    pytest.main([__file__])
