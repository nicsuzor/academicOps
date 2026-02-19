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
    # Mock get_session_data to avoid reading shared PID session map during xdist tests
    with patch("hooks.router.get_session_data", return_value={}):
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
        "tool_input": '{"subagent_type": "critic", "prompt": "test"}',
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
        session_id="aafdeee", hook_event="SubagentStop", subagent_type="prompt-hydrator"
    )
    gate.on_subagent_stop(ctx_stop, state)
    assert state.get_gate("hydration").status == GateStatus.OPEN

    # 2. Reset and Test PostToolUse fallback trigger
    state.get_gate("hydration").status = GateStatus.CLOSED
    ctx_post = HookContext(
        session_id="aafdeee", hook_event="PostToolUse", subagent_type="prompt-hydrator"
    )
    gate.on_tool_use(ctx_post, state)
    assert state.get_gate("hydration").status == GateStatus.OPEN


def test_regex_hook_event_matching():
    """Test that GenericGate supports regex in hook_event matching."""
    from lib.gate_types import GateCondition

    state = SessionState.create("s1")

    # Config with regex event
    cond = GateCondition(
        hook_event="^(SubagentStop|PostToolUse)$", subagent_type_pattern="prompt-hydrator"
    )

    # Mock gate
    hydration_config = next(g for g in GATE_CONFIGS if g.name == "hydration")
    gate = GenericGate(hydration_config)

    # Matches
    assert (
        gate._evaluate_condition(
            cond,
            HookContext(
                session_id="s1", hook_event="SubagentStop", subagent_type="prompt-hydrator"
            ),
            state.get_gate("hydration"),
            state,
        )
        is True
    )
    assert (
        gate._evaluate_condition(
            cond,
            HookContext(session_id="s1", hook_event="PostToolUse", subagent_type="prompt-hydrator"),
            state.get_gate("hydration"),
            state,
        )
        is True
    )

    # Does not match
    assert (
        gate._evaluate_condition(
            cond,
            HookContext(session_id="s1", hook_event="PreToolUse", subagent_type="prompt-hydrator"),
            state.get_gate("hydration"),
            state,
        )
        is False
    )
    assert (
        gate._evaluate_condition(
            cond,
            HookContext(session_id="s1", hook_event="Stop", subagent_type="prompt-hydrator"),
            state.get_gate("hydration"),
            state,
        )
        is False
    )


def test_router_normalize_skill_tool_extracts_skill_name(router):
    """normalize_input extracts skill name from Skill tool into subagent_type."""
    raw_input = {
        "hook_event_name": "PostToolUse",
        "session_id": "main-session-uuid-1234",
        "tool_name": "Skill",
        "tool_input": {"skill": "handover", "args": ""},
    }
    ctx = router.normalize_input(raw_input)
    assert ctx.subagent_type == "handover"
    assert ctx.tool_name == "Skill"


def test_router_normalize_skill_tool_not_subagent(router):
    """Main-session Skill invocations must NOT be classified as subagent sessions."""
    raw_input = {
        "hook_event_name": "PostToolUse",
        "session_id": "main-session-uuid-1234",
        "tool_name": "Skill",
        "tool_input": {"skill": "handover", "args": ""},
    }
    ctx = router.normalize_input(raw_input)
    assert ctx.is_subagent is False


def test_router_normalize_activate_skill_extracts_skill_name(router):
    """normalize_input extracts skill name from activate_skill (Gemini) into subagent_type."""
    raw_input = {
        "hook_event_name": "PostToolUse",
        "session_id": "main-session-uuid-5678",
        "tool_name": "activate_skill",
        "tool_input": {"skill": "handover"},
    }
    ctx = router.normalize_input(raw_input)
    assert ctx.subagent_type == "handover"
    assert ctx.is_subagent is False
