import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add aops-core to path
AOPS_CORE = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(AOPS_CORE))

from lib.gates.custom_conditions import check_custom_condition
from lib.session_state import SessionState
from hooks.schemas import HookContext
from lib.task_model import Task

def test_uac_verified_condition():
    # Setup mock session state
    session_id = "test-session"
    state = SessionState.create(session_id)
    state.main_agent.current_task = "test-task-123"
    
    ctx = MagicMock(spec=HookContext)
    
    # Mock Task and Storage
    mock_task = MagicMock(spec=Task)
    mock_task.body = """
## Requirements
- [x] Requirement 1
- [ ] Requirement 2
"""
    
    with patch("lib.task_storage.TaskStorage") as MockStorage:
        mock_storage = MockStorage.return_value
        mock_storage.get_task.return_value = mock_task
        
        # Test 1: Incomplete items
        verified = check_custom_condition("uac_verified", ctx, state.get_gate("uac"), state)
        assert verified is False
        assert "Requirement 2" in state.get_gate("uac").metrics["incomplete_uac_list"]
        
        # Test 2: All complete
        mock_task.body = """
## Requirements
- [x] Requirement 1
- [x] Requirement 2
"""
        verified = check_custom_condition("uac_verified", ctx, state.get_gate("uac"), state)
        assert verified is True

def test_uac_verified_no_task():
    session_id = "test-session"
    state = SessionState.create(session_id)
    state.main_agent.current_task = None
    
    ctx = MagicMock(spec=HookContext)
    
    verified = check_custom_condition("uac_verified", ctx, state.get_gate("uac"), state)
    assert verified is True # vacuously true if no task
