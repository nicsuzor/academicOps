from unittest.mock import ANY, patch

import pytest

from hooks.gates import close_gate, on_after_agent, open_gate
from hooks.schemas import HookContext
from lib import session_state
from lib.gate_utils import create_audit_file


@pytest.fixture
def mock_session(tmp_path):
    session_id = "test_session_unification"
    with patch("lib.session_paths.get_session_status_dir", return_value=tmp_path):
        state = session_state.get_or_create_session_state(session_id)
        session_state.save_session_state(session_id, state)
        yield session_id


def test_gate_open_close_unification(mock_session):
    """Test that open_gate and close_gate update unified state and helpers work."""
    session_id = mock_session

    # Open critic gate
    open_gate(session_id, "critic")
    state = session_state.load_session_state(session_id)
    # Generic state is now a dict
    assert state["state"]["gates"]["critic"]["status"] == "open"
    # Helper should return True
    assert session_state.is_critic_invoked(session_id) is True

    # Close critic gate
    close_gate(session_id, "critic")
    state = session_state.load_session_state(session_id)
    assert state["state"]["gates"]["critic"]["status"] == "closed"
    # Helper should return False
    assert session_state.is_critic_invoked(session_id) is False


def test_critic_gate_opening_after_agent(mock_session):
    """Test that critic gate opens when APPROVED is detected in AfterAgent response."""
    session_id = mock_session

    ctx = HookContext(
        session_id=session_id,
        hook_event="AfterAgent",
        raw_input={"prompt_response": "The plan looks solid. Verdict: APPROVED"},
        tool_name=None,
        tool_input={},
        tool_output={},
    )

    # Ensure gate starts closed (or uninitialized)
    close_gate(session_id, "critic")

    # Use on_after_agent instead of update_gate_state
    result = on_after_agent(ctx)
    assert result is not None
    assert "✓ `critic` opened" in result.system_message

    state = session_state.load_session_state(session_id)
    assert state["state"]["gates"]["critic"]["status"] == "open"
    assert session_state.is_critic_invoked(session_id) is True


def test_audit_file_creation_unified(mock_session, tmp_path):
    """Test that create_audit_file uses the unified .context template."""
    session_id = mock_session

    ctx = HookContext(
        session_id=session_id,
        hook_event="PreToolUse",
        raw_input={},
        tool_name="write_file",
        tool_input={"file_path": "test.txt"},
        tool_output={},
    )

    with patch("lib.hook_utils.get_hook_temp_dir", return_value=tmp_path):
        with patch("lib.template_registry.TemplateRegistry.render") as mock_render:
            mock_render.return_value = "Audit Content"
            path = create_audit_file(session_id, "critic", ctx)

            assert path is not None
            assert path.name.startswith("audit_critic_")
            # Verify render was called with critic.context
            mock_render.assert_any_call("critic.context", ANY)


if __name__ == "__main__":
    pytest.main([__file__])
