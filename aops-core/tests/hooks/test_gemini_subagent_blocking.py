import uuid
from unittest.mock import patch

import pytest
from hooks.router import HookRouter
from lib.gate_model import GateVerdict
from lib.gate_types import GateStatus
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState


@pytest.fixture
def mock_session(tmp_path):
    session_id = f"gemini-test-{uuid.uuid4().hex[:8]}"
    with (
        patch("lib.session_paths.get_session_status_dir", return_value=tmp_path),
        patch("lib.session_state.get_session_status_dir", return_value=tmp_path),
    ):
        state = SessionState.create(session_id)
        # Ensure hydration is closed
        state.gates["hydration"].status = GateStatus.CLOSED
        state.save()
        yield session_id, state


def test_gemini_subagent_bypasses_hydration_even_if_not_compliance(mock_session):
    """
    Verify that a subagent (detected via is_sidechain) bypasses the hydration gate
    even if its subagent_type is unknown or not in the compliance list.
    """
    session_id, state = mock_session

    # Simulate a Gemini subagent tool call where we only have is_sidechain
    raw_input = {
        "is_sidechain": True,
        "tool_name": "Read",
        "tool_input": {"file_path": "test.txt"}
    }

    router = HookRouter()
    GateRegistry.initialize()

    ctx = router.normalize_input(raw_input, gemini_event="BeforeTool")

    # Currently, if is_subagent is True but subagent_type is None,
    # it won't be a compliance agent and will be blocked.

    # Let's see what happens with current _dispatch_gates logic
    result = router._dispatch_gates(ctx, state)

    # If the fix works, result should be None or verdict ALLOW
    if result:
        assert result.verdict == GateVerdict.ALLOW
    else:
        assert result is None
