from hooks.gate_registry import (
    GateContext,
    check_hydration_gate,
    run_accountant,
)
from hooks.unified_logger import handle_subagent_stop
from lib import session_state


class TestHydratorStateClearing:
    """Test that hydrator state is correctly set and cleared."""

    def test_activate_skill_clears_state(self):
        """Test activate_skill sets and then clears hydrator_active via accountant."""
        session_id = "test-session-activate"

        # 1. PreToolUse: activate_skill
        ctx_pre = GateContext(
            session_id=session_id,
            event_name="PreToolUse",
            input_data={
                "tool_name": "activate_skill",
                "tool_input": {"name": "prompt-hydrator"},
            },
        )

        session_state.get_or_create_session_state(session_id)

        result = check_hydration_gate(ctx_pre)
        assert result is None
        assert session_state.is_hydrator_active(session_id) is True

        # 2. PostToolUse: activate_skill
        ctx_post = GateContext(
            session_id=session_id,
            event_name="PostToolUse",
            input_data={
                "tool_name": "activate_skill",
                "tool_input": {"name": "prompt-hydrator"},
            },
        )

        run_accountant(ctx_post)
        assert session_state.is_hydrator_active(session_id) is False

    def test_subagent_stop_clears_state(self):
        """Test unified_logger.handle_subagent_stop clears hydrator_active."""
        session_id = "test-session-subagent-stop"

        # Setup: set hydrator active manually
        session_state.get_or_create_session_state(session_id)
        session_state.set_hydrator_active(session_id)
        assert session_state.is_hydrator_active(session_id) is True

        # Simulate SubagentStop event for prompt-hydrator
        input_data = {
            "subagent_type": "prompt-hydrator",
            "subagent_result": "## HYDRATION RESULT\nPlan...",
        }

        handle_subagent_stop(session_id, input_data)

        # Verify cleared
        assert session_state.is_hydrator_active(session_id) is False, (
            "unified_logger should clear active flag"
        )

    def test_subagent_stop_clears_state_even_on_failure(self):
        """Test unified_logger clears state even without valid hydration result."""
        session_id = "test-session-subagent-fail"

        session_state.get_or_create_session_state(session_id)
        session_state.set_hydrator_active(session_id)

        # Simulate SubagentStop event with FAILURE/No Result
        input_data = {
            "subagent_type": "prompt-hydrator",
            "subagent_result": "Failed to hydrate",
        }

        handle_subagent_stop(session_id, input_data)

        # Verify cleared (flag should be cleared even if hydration pending isn't)
        assert session_state.is_hydrator_active(session_id) is False

        # Hydration pending might still be true (if it was true), but active flag is gone
        # (We didn't set pending in setup, but logic check is about active flag)
