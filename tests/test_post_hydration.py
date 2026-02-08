"""Test Post-Hydration logic."""

from unittest.mock import patch

from hooks.gate_registry import check_agent_response_listener
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict


@patch("hooks.gate_registry.session_state")
def test_post_hydration_critic_injection(mock_session_state):
    """Verify that detecting HYDRATION RESULT injects a critic reminder."""
    ctx = HookContext(
        session_id="session-123",
        hook_event="AfterAgent",
        raw_input={
            "prompt_response": "Here is the plan:\n\n## HYDRATION RESULT\n\nPlan details..."
        },
    )

    # Mock workflow ID extraction
    mock_session_state.get_or_create_session_state.return_value = {"state": {}}

    result = check_agent_response_listener(ctx)

    assert result is not None
    assert result.verdict == GateVerdict.ALLOW
    assert "Next step: Invoke the critic" in result.context_injection
    assert "activate_skill(name='critic'" in result.context_injection

    # Verify hydration_pending was cleared
    mock_session_state.clear_hydration_pending.assert_called_once_with("session-123")


@patch("hooks.gate_registry.session_state")
def test_normal_response_no_injection(mock_session_state):
    """Verify normal responses don't trigger injection."""
    ctx = HookContext(
        session_id="session-123",
        hook_event="AfterAgent",
        raw_input={"prompt_response": "Just a normal response."},
    )

    result = check_agent_response_listener(ctx)

    assert result is None
    mock_session_state.clear_hydration_pending.assert_not_called()


@patch("hooks.gate_registry.session_state")
def test_hydration_result_loose_matching(mock_session_state):
    """Verify loose matching for HYDRATION RESULT (e.g. bold or plain)."""
    # Case 1: Bold
    ctx = HookContext(
        session_id="s1",
        hook_event="AfterAgent",
        raw_input={"prompt_response": "**HYDRATION RESULT**\nIntent: foo"},
    )
    result = check_agent_response_listener(ctx)
    assert result is not None
    mock_session_state.clear_hydration_pending.assert_called_with("s1")

    # Case 2: Plain text with leading newline
    ctx2 = HookContext(
        session_id="s2",
        hook_event="AfterAgent",
        raw_input={"prompt_response": "\nHYDRATION RESULT\nIntent: bar"},
    )

    check_agent_response_listener(ctx2)
    mock_session_state.clear_hydration_pending.assert_called_with("s2")
