import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add aops-core to path
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
sys.path.insert(0, str(AOPS_CORE))

from hooks.schemas import HookContext
from lib.gate_types import GateStatus
from lib.gates.custom_actions import execute_custom_action
from lib.session_state import SessionState


def test_hydrate_prompt_no_attribute_error():
    """Regression test for 'GateState' object has no attribute 'state'."""
    ctx = MagicMock(spec=HookContext)
    ctx.session_id = "test-session"
    ctx.raw_input = {"prompt": "test prompt"}
    ctx.transcript_path = None

    session_state = SessionState.create("test-session")
    # In engine.py, the 'state' passed to execute_custom_action is session_state.gates[name]
    gate_state = session_state.get_gate("hydration")

    # Mock build_hydration_instruction to avoid I/O
    with MagicMock() as mock_build:
        import hooks.user_prompt_submit

        original_build = hooks.user_prompt_submit.build_hydration_instruction
        hooks.user_prompt_submit.build_hydration_instruction = mock_build
        mock_build.return_value = "mock instruction"

        try:
            result = execute_custom_action("hydrate_prompt", ctx, gate_state, session_state)
            assert result is not None
            assert "Hydration ready" in result.system_message
        finally:
            hooks.user_prompt_submit.build_hydration_instruction = original_build


def test_user_prompt_submit_no_attribute_error(tmp_path):
    """Regression test for UserPromptSubmit hook logic."""
    from hooks.user_prompt_submit import build_hydration_instruction, write_initial_hydrator_state

    session_id = "test-session"
    session_state = SessionState.create(session_id)

    # Mock session_state.load and session_state.save
    with MagicMock() as mock_load, patch.object(SessionState, "save"):
        original_load = SessionState.load
        SessionState.load = mock_load
        mock_load.return_value = session_state

        try:
            # This should not raise AttributeError
            write_initial_hydrator_state(session_id, "test prompt", hydration_pending=True)
            assert session_state.get_gate("hydration").status == GateStatus.CLOSED

            # Reset and test build_hydration_instruction (partially mocked)
            with MagicMock() as mock_write_temp:
                import hooks.user_prompt_submit

                original_write = hooks.user_prompt_submit.write_temp_file
                hooks.user_prompt_submit.write_temp_file = mock_write_temp
                mock_write_temp.return_value = Path("/tmp/mock_hydrate.md")

                # Redirect gate file writes to tmp_path to keep the test hermetic
                gate_file = tmp_path / "hydration-gate.md"
                env_patch = patch.dict(os.environ, {"AOPS_GATE_FILE_HYDRATION": str(gate_file)})

                with env_patch:
                    try:
                        # This should not raise AttributeError
                        instruction = build_hydration_instruction(
                            session_id, "test prompt", state=session_state
                        )
                        assert "User prompt hydration required" in instruction
                    finally:
                        hooks.user_prompt_submit.write_temp_file = original_write

        finally:
            SessionState.load = original_load
