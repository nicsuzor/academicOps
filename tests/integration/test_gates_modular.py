import pytest
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator

# --- Fixtures ---

@pytest.fixture
def temp_home() -> Generator[Path, None, None]:
    """Create a temporary home directory for isolation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        home_path = Path(temp_dir)
        # Mock minimal necessary files
        (home_path / ".config" / "gemini").mkdir(parents=True, exist_ok=True)
        (home_path / ".claude").mkdir(exist_ok=True)
        (home_path / "src").mkdir(exist_ok=True)
        
        # Setup environment variables
        env = os.environ.copy()
        env["HOME"] = str(home_path)
        env["AOPS"] = str(Path(__file__).parent.parent.parent) # Root of aops-core
        
        yield home_path

@pytest.fixture
def mock_session_state(temp_home: Path) -> Generator[Path, None, None]:
    """Initialize a mock session state for testing gates."""
    # This would simulate the files created by the framework
    session_dir = temp_home / ".aops" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    yield session_dir

class CLIDriver:
    """Abstraction for driving CLI agents."""
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
    
    def run(self, instruction: str) -> str:
        """Run the agent with an instruction and return output."""
        # For now, we mock the execution or use subprocess if we want real runs
        # Real runs might be too slow for unit/integration tests without a mock
        pass

@pytest.fixture(params=["gemini", "claude"])
def cli_agent(request) -> str:
    return request.param

# --- Tests ---

@pytest.mark.parametrize("gate, instruction, expected_result", [
    ("hydration", "read file /etc/hosts", "blocked"),
    ("hydration", "list_prompts", "allowed"), # Allowed tool
    ("hydration", "activate_skill prompt-hydrator", "allowed"), # Bypass
    ("task", "write_file test.txt content='hello'", "blocked"), # Requires task
    ("task", "create_task title='Test'", "allowed"), # Task creation allowed
])
def test_gate_enforcement(cli_agent, gate, instruction, expected_result):
    """
    Test that specific gates enforce rules correctly across both agents.
    
    This is a skeleton. We need to decide:
    1. Are we running the REAL hooks? (Yes, importing `gate_registry`)
    2. Are we running the REAL CLI? (Maybe too heavy/expensive)
    
    Better approach:
    Test the `gate_registry` logic directly with mocked GateContexts that 
    simulate what Claude/Gemini WOULD send.
    """
    from hooks.gate_registry import GateContext, GATE_CHECKS, GateVerdict
    
    # Construct input_data based on agent type simulation
    input_data = _simulate_tool_call(cli_agent, instruction)
    
    ctx = GateContext(
        session_id="test-session-123",
        event_name="PreToolUse", 
        input_data=input_data
    )
    
    # Identify which check to run
    gate_key = gate
    if gate == "task": gate_key = "task_required"
    check_func = GATE_CHECKS.get(gate_key)
    if not check_func:
        raise ValueError(f"Unknown gate: {gate} (mapped to {gate_key})")
    
    # Mock session state for Hydration gate blocking
    if gate == "hydration" and expected_result == "blocked":
        # We need to mock session_state.is_hydration_pending to return True
        # Since we can't easily patch inside the function without more complex setup,
        # we'll use unittest.mock.patch
        from unittest.mock import patch, MagicMock
        with patch("lib.session_state.is_hydration_pending", return_value=True), \
             patch("lib.session_state.get_hydration_temp_path", return_value="/tmp/test"), \
             patch("lib.session_state.is_hydrator_active", return_value=False):
             result = check_func(ctx)
    elif gate == "task" or gate == "task_required":
        from unittest.mock import patch
        # Default gates state: all False (meaning gates are CLOSED/ACTIVE)
        # check_all_gates returns {gate_name: True/False} where True = PASSED/OPEN
        
        gates_state = {
            "task_bound": False, 
            "plan_mode_invoked": False, 
            "critic_invoked": False
        }
        
        if expected_result == "allowed":
             # For allowed case, we simulate task binding happened
             gates_state["task_bound"] = True

        with patch("lib.session_state.check_all_gates", return_value=gates_state), \
             patch("lib.session_state.load_session_state", return_value={}):
             result = check_func(ctx)
    else:
        result = check_func(ctx)
    
    if expected_result == "blocked":
        assert result is not None
        # WARN or DENY both count as "blocked" behavior - WARN is used in test mode
        assert result.verdict in (GateVerdict.DENY, GateVerdict.WARN), \
            f"Expected DENY or WARN, got {result.verdict}"
    elif expected_result == "allowed":
        assert result is None or result.verdict == GateVerdict.ALLOW
    elif expected_result == "warned":
        assert result is not None
        assert result.verdict == GateVerdict.WARN

def _simulate_tool_call(agent: str, instruction: str) -> Dict[str, Any]:
    """Helper to generate tool input JSON based on instruction."""
    if "read file" in instruction:
        path = instruction.split(" ")[-1]
        if agent == "gemini":
            return {"tool_name": "read_file", "tool_input": {"file_path": path}}
        else:
            return {"tool_name": "Read", "tool_input": {"file_path": path}}
            
    if "list_prompts" in instruction:
        return {"tool_name": "list_prompts", "tool_input": {}}
        
    if "activate_skill" in instruction:
        skill = instruction.split(" ")[-1]
        if agent == "gemini":
            return {"tool_name": "activate_skill", "tool_input": {"name": skill}}
        else:
            return {"tool_name": "Skill", "tool_input": {"skill": skill}}

    if "write_file" in instruction:
        # naive parsing
        return {"tool_name": "write_to_file", "tool_input": {"file_path": "test.txt"}}

    if "create_task" in instruction:
        return {"tool_name": "create_task", "tool_input": {"title": "test"}}
        
    return {}
