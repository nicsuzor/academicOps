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

    # Open critic gate
    state.open_gate("critic")
    state.save()

    state = SessionState.load(session_id)
    assert state.gates["critic"].status == GateStatus.OPEN

    # Close critic gate
    state.close_gate("critic")
    state.save()

    state = SessionState.load(session_id)
    assert state.gates["critic"].status == GateStatus.CLOSED


def test_critic_gate_opening_subagent(mock_session):
    """Test that critic gate opens when Critic subagent stops."""
    session_id = mock_session

    ctx = HookContext(
        session_id=session_id,
        hook_event="SubagentStop",
        subagent_type="critic",  # Matches pattern
        raw_input={"subagent_type": "critic"},
    )

    state = SessionState.load(session_id)
    # Ensure gate starts closed (simulate metrics high)
    state.gates["critic"].ops_since_open = 100
    # Status might be open but we want to test ResetOps
    state.gates["critic"].status = GateStatus.OPEN

    # Run hook
    # Note: on_subagent_stop calls triggers
    result = on_subagent_stop(ctx, state)

    assert result is not None
    assert result.system_message is not None
    assert "Critic review complete" in result.system_message

    # Verify Ops reset
    assert state.gates["critic"].ops_since_open == 0


if __name__ == "__main__":
    pytest.main([__file__])
