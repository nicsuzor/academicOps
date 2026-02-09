import pytest
import os
import tempfile
from pathlib import Path
from hooks.schemas import HookContext
from hooks.gate_registry import run_accountant
from hooks.gates import update_gate_state
from lib import session_state

@pytest.fixture
def session_id():
    return "test-session-custodiet"

@pytest.fixture
def mock_session(session_id, tmp_path):
    # Set AOPS_SESSION_STATE_DIR to tmp_path
    os.environ["AOPS_SESSION_STATE_DIR"] = str(tmp_path)
    state = session_state.create_session_state(session_id)
    # Ensure custodiet is open initially
    state.setdefault("state", {}).setdefault("gates", {})["custodiet"] = "open"
    state["state"]["tool_calls_since_compliance"] = 0
    session_state.save_session_state(session_id, state)
    yield state
    if "AOPS_SESSION_STATE_DIR" in os.environ:
        del os.environ["AOPS_SESSION_STATE_DIR"]

def test_custodiet_double_increment(session_id, mock_session):
    """Reproduction: custodiet counter increments twice for write tools."""
    ctx = HookContext(
        session_id=session_id,
        hook_event="PostToolUse",
        tool_name="write_file",
        tool_input={"file_path": "test.txt", "content": "hello"},
        tool_output={"success": True}
    )

    # 1. Run accountant
    run_accountant(ctx)
    state = session_state.load_session_state(session_id)
    assert state["state"]["tool_calls_since_compliance"] == 1

    # 2. Run gate_update
    update_gate_state(ctx)
    state = session_state.load_session_state(session_id)
    
    # IT SHOULD BE 1, but it will probably be 2 due to the bug
    print(f"Count after both: {state['state']['tool_calls_since_compliance']}")
    assert state["state"]["tool_calls_since_compliance"] == 2, "Bug confirmed: Double increment"

def test_custodiet_threshold_mismatch(session_id, mock_session):
    """Reproduction: custodiet threshold doesn't respect env var in gates.py."""
    # Set threshold to 11
    os.environ["CUSTODIET_TOOL_CALL_THRESHOLD"] = "11"
    
    # Trigger 8 write calls. 
    # Since gate_config.py has hardcoded 7, it will close at 8 (or earlier if double incrementing)
    for i in range(8):
        ctx = HookContext(
            session_id=session_id,
            hook_event="PostToolUse",
            tool_name="write_file",
            tool_input={"file_path": f"test_{i}.txt", "content": "hello"},
            tool_output={"success": True}
        )
        update_gate_state(ctx)

    state = session_state.load_session_state(session_id)
    # If it respected 11, it should still be open.
    # But it will likely be closed because hardcoded 7 < 8.
    gates = state.get("state", {}).get("gates", {})
    print(f"Gates state after 8 calls: {gates}")
    # Note: _close_gate is broken for custodiet, so it might NOT even show as closed in 'gates' dict
    # but the counter will be high.
    
def test_custodiet_close_gate_broken(session_id, mock_session):
    """Reproduction: _close_gate does nothing for custodiet."""
    from hooks.gates import _close_gate
    
    _close_gate(session_id, "custodiet")
    state = session_state.load_session_state(session_id)
    gates = state.get("state", {}).get("gates", {})
    
    # It should be 'closed', but it won't be because _close_gate is missing the logic
    assert gates.get("custodiet") != "closed", "Bug confirmed: _close_gate doesn't handle custodiet"
