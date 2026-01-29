"""Test Skill Activation Bypass for Hydration."""

import pytest
from unittest.mock import MagicMock, patch
from hooks.gate_registry import (
    check_hydration_gate,
    check_skill_activation_listener,
    GateContext,
    GateVerdict,
)


@patch("hooks.gate_registry.session_state")
@patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
def test_skill_activation_bypass(mock_get_temp_dir, mock_session_state):
    """Verify skill activation bypasses hydration check and clears pending."""
    mock_session_state.is_hydration_pending.return_value = True
    mock_get_temp_dir.return_value = "/tmp/hydrator"

    # 1. Activation Check (PreToolUse)
    # Ensure activate_skill (any name) is allowed even if hydration pending
    ctx_pre = GateContext(
        session_id="s1",
        event_name="PreToolUse",
        input_data={"tool_name": "activate_skill", "tool_input": {"name": "daily"}},
    )
    result_pre = check_hydration_gate(ctx_pre)
    assert result_pre is None  # Allowed

    # 2. State Cleared (PostToolUse)
    # Ensure hydration pending is cleared after activation
    ctx_post = GateContext(
        session_id="s1",
        event_name="PostToolUse",
        input_data={"tool_name": "activate_skill", "tool_input": {"name": "daily"}},
    )
    # Mock return value of is_hydration_pending - actually irrelevant now as we force clear
    # mock_session_state.is_hydration_pending.return_value = True

    result_post = check_skill_activation_listener(ctx_post)

    # Verify Allow result and state clearing call regardless of prior check
    assert result_post is not None
    assert result_post.verdict == GateVerdict.ALLOW
    mock_session_state.clear_hydration_pending.assert_called_with("s1")
