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
        patch("lib.session_paths.get_pid_session_map_path", return_value=tmp_path / "pid_map.json"),
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
    input_data = {
        "session_id": session_id,
        "is_sidechain": True,
        "tool_name": "Read",
        "tool_input": {"file_path": "test.txt"},
    }

    router = HookRouter()
    GateRegistry.initialize()

    ctx = router.normalize_input(input_data, gemini_event="BeforeTool")

    # Currently, if is_subagent is True but subagent_type is None,
    # it won't be a compliance agent and will be blocked.

    # Let's see what happens with current _dispatch_gates logic
    result = router._dispatch_gates(ctx, state)

    # The router returns None for an ALLOW verdict with no messages,
    # which is a valid success case for a bypassed gate.
    assert result is None or result.verdict == GateVerdict.ALLOW
