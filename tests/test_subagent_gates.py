
from unittest.mock import patch

import pytest
from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_types import GateStatus
from lib.gates.definitions import GATE_CONFIGS
from lib.gates.engine import GenericGate
from lib.session_state import SessionState


@pytest.fixture
def router():
    return HookRouter()


def test_router_normalize_subagent_type_extraction(router):
    """Test extraction of subagent_type from tool_input in normalize_input."""
    raw_input = {
        "hook_event_name": "PreToolUse",
        "session_id": "main-session",
        "tool_name": "Task",
        "tool_input": {"subagent_type": "hydrator", "prompt": "test"},
    }

    ctx = router.normalize_input(raw_input)
    assert ctx.subagent_type == "hydrator"
    assert ctx.tool_name == "Task"


def test_router_normalize_subagent_type_from_string_input(router):
    """Test extraction of subagent_type when tool_input is a JSON string."""
    raw_input = {
        "hook_event_name": "PreToolUse",
        "session_id": "main-session",
        "tool_name": "Task",
        "tool_input": '{"subagent_type": "critic", "prompt": "test"}'
    }
    
    ctx = router.normalize_input(raw_input)
    assert ctx.subagent_type == "critic"


def test_subagent_detection_from_id(router):
    """Test that short hex session IDs are correctly identified as subagents."""
    raw_input = {
        "hook_event_name": "PreToolUse",
        "session_id": "aafdeee",  # Typical Claude subagent ID
        "tool_name": "Read",
        "tool_input": {"file_path": "test.txt"},
    }

    ctx = router.normalize_input(raw_input)
    assert ctx.is_subagent is True


def test_hydration_gate_simplified_triggers():
    """Test that simplified triggers in hydration gate work correctly."""
    state = SessionState.create("test-session")
    state.get_gate("hydration").status = GateStatus.CLOSED
    
    hydration_config = next(g for g in GATE_CONFIGS if g.name == "hydration")
    gate = GenericGate(hydration_config)
    
    # 1. Test SubagentStop trigger
    ctx_stop = HookContext(
        session_id="aafdeee",
        hook_event="SubagentStop",
        subagent_type="hydrator"
    )
    gate.on_subagent_stop(ctx_stop, state)
    assert state.get_gate("hydration").status == GateStatus.OPEN
    
    # 2. Reset and Test PostToolUse fallback trigger
    state.get_gate("hydration").status = GateStatus.CLOSED
    ctx_post = HookContext(
        session_id="aafdeee",
        hook_event="PostToolUse",
        subagent_type="hydrator"
    )
    gate.on_tool_use(ctx_post, state)
    assert state.get_gate("hydration").status == GateStatus.OPEN


def test_critic_gate_simplified_triggers():
    """Test simplified triggers for critic gate."""
    state = SessionState.create("test-session")
    # Initially Open
    assert state.get_gate("critic").status == GateStatus.OPEN

    critic_config = next(g for g in GATE_CONFIGS if g.name == "critic")
    gate = GenericGate(critic_config)

    # 1. Hydration stop should CLOSE critic gate
    ctx_hyd_stop = HookContext(session_id="s1", hook_event="SubagentStop", subagent_type="hydrator")
    gate.on_subagent_stop(ctx_hyd_stop, state)
    assert state.get_gate("critic").status == GateStatus.CLOSED

    # 2. Critic stop should OPEN critic gate
    ctx_critic_stop = HookContext(
        session_id="s1", hook_event="SubagentStop", subagent_type="critic"
    )
    gate.on_subagent_stop(ctx_critic_stop, state)
    assert state.get_gate("critic").status == GateStatus.OPEN


def test_regex_hook_event_matching():
    """Test that GenericGate supports regex in hook_event matching."""
    from lib.gate_types import GateCondition
    state = SessionState.create("s1")
    
    # Config with regex event
    cond = GateCondition(hook_event="^(SubagentStop|PostToolUse)$", subagent_type_pattern="hydrator")
    
    # Mock gate
    hydration_config = next(g for g in GATE_CONFIGS if g.name == "hydration")
    gate = GenericGate(hydration_config)
    
    # Matches
    assert gate._evaluate_condition(cond, HookContext(session_id="s1", hook_event="SubagentStop", subagent_type="hydrator"), state.get_gate("hydration"), state) is True
    assert gate._evaluate_condition(cond, HookContext(session_id="s1", hook_event="PostToolUse", subagent_type="hydrator"), state.get_gate("hydration"), state) is True
    
    # Does not match
    assert gate._evaluate_condition(cond, HookContext(session_id="s1", hook_event="PreToolUse", subagent_type="hydrator"), state.get_gate("hydration"), state) is False
    assert gate._evaluate_condition(cond, HookContext(session_id="s1", hook_event="Stop", subagent_type="hydrator"), state.get_gate("hydration"), state) is False


def test_router_bypass_for_subagents(router):
    """Test that router.execute_hooks bypasses gates for subagents (sidechains)."""
    # 1. Setup Session State (Hydration CLOSED)
    # We must mock SessionState.load because it reads from disk
    with patch("lib.session_state.SessionState.load") as mock_load, \
         patch("lib.session_state.SessionState.save"):
        state = SessionState.create("s1")
        state.get_gate("hydration").status = GateStatus.CLOSED
        mock_load.return_value = state
        
        # 2. Setup HookContext for a subagent
        ctx = HookContext(
            session_id="aafdeee", hook_event="PreToolUse", tool_name="Read", is_subagent=True
        )
        
        # 3. Execute hooks
        # We need to mock GateRegistry and special handlers if they do side effects
        with patch("lib.gates.registry.GateRegistry.initialize"), \
             patch("hooks.router.HookRouter._run_special_handlers"), \
             patch("hooks.router.log_hook_event"):
            
            result = router.execute_hooks(ctx)
            
            # The result should be ALLOW (default) because gates were skipped
            assert result.verdict == "allow"
            # And no "Hydration required" message should be present
            if result.system_message:
                assert "Hydration required" not in result.system_message
