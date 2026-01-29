"""Test Post-Hydration Critic injection."""

import pytest
from unittest.mock import MagicMock, patch
from hooks.gate_registry import check_agent_response_listener, GateContext
from lib.gate_model import GateResult, GateVerdict


@patch("hooks.gate_registry.session_state")
def test_post_hydration_critic_injection(mock_session_state):
    """Verify that detecting HYDRATION RESULT injects a critic reminder."""
    ctx = GateContext(
        session_id="session-123",
        event_name="AfterAgent",
        input_data={
            "prompt_response": "Here is the plan:\n\n## HYDRATION RESULT\n\nPlan details..."
        },
    )

    result = check_agent_response_listener(ctx)

    assert result is not None
    assert isinstance(result, GateResult)
    assert result.verdict == GateVerdict.ALLOW

    # Check injection content
    msg = result.context_injection
    assert "Invoke the critic" in msg or "activate_skill" in msg
    assert "critic" in msg

    # Verify state update
    mock_session_state.clear_hydration_pending.assert_called_with("session-123")


@patch("hooks.gate_registry.session_state")
def test_normal_response_no_injection(mock_session_state):
    """Verify normal responses don't trigger injection."""
    ctx = GateContext(
        session_id="session-123",
        event_name="AfterAgent",
        input_data={"prompt_response": "Just a normal response."},
    )

    result = check_agent_response_listener(ctx)
    assert result is None
