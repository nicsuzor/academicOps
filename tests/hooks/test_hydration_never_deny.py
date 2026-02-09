#!/usr/bin/env python3
"""Tests for hydration gate never blocking itself."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))


from hooks.gate_config import TOOL_CATEGORIES, get_tool_category
from hooks.gates import check_tool_gate
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.session_state import SessionState


# Helper to mock session state loading
@pytest.fixture
def mock_session_state():
    with patch("lib.session_state.SessionState.load") as mock_load:
        # Create a real Pydantic object
        state = SessionState.create("test-session-123")
        mock_load.return_value = state
        yield state, mock_load


class TestActivateSkillAlwaysAvailable:
    """Test that activate_skill is in always_available category."""

    def test_activate_skill_in_always_available(self):
        """activate_skill should be in the always_available category."""
        assert "activate_skill" in TOOL_CATEGORIES["always_available"]

    def test_activate_skill_category(self):
        """get_tool_category should return always_available for activate_skill."""
        assert get_tool_category("activate_skill") == "always_available"

    def test_skill_tool_in_always_available(self):
        """Skill tool should also be in always_available."""
        assert "Skill" in TOOL_CATEGORIES["always_available"]

    def test_task_tool_in_always_available(self):
        """Task tool should also be in always_available."""
        assert "Task" in TOOL_CATEGORIES["always_available"]


class TestAskUserQuestionAlwaysAvailable:
    """Test that AskUserQuestion is never blocked by the hydration gate."""

    def test_ask_user_question_in_always_available(self):
        """AskUserQuestion should be in the always_available category."""
        assert "AskUserQuestion" in TOOL_CATEGORIES["always_available"]

    def test_ask_user_question_category(self):
        """get_tool_category should return always_available for AskUserQuestion."""
        assert get_tool_category("AskUserQuestion") == "always_available"

    def test_ask_user_question_allowed_without_hydration(self, mock_session_state):
        """AskUserQuestion should be allowed even without hydration."""
        state, _ = mock_session_state
        # Ensure hydration is closed
        state.gates["hydration"].status = "closed"
        state.state["hydration_pending"] = True

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="AskUserQuestion",
            tool_input={
                "questions": [
                    {
                        "question": "Test?",
                        "header": "Test",
                        "options": [],
                        "multiSelect": False,
                    }
                ]
            },
        )

        # check_tool_gate no longer takes state argument when called via import?
        # Wait, check_tool_gate in hooks/gates.py takes (ctx, state) or just ctx?
        # In my refactor: `def check_tool_gate(ctx: HookContext) -> GateResult:`
        # It calls `session_state.load_session_state(ctx.session_id)`.
        # BUT I changed it to `def check_tool_gate(ctx: HookContext) -> GateResult:` in the *legacy* dispatcher signature?
        # NO, I changed it to `def check_tool_gate(ctx: HookContext, state: SessionState) -> GateResult:` in the *new* dispatcher.
        # But wait, `router.py` calls it with `(ctx, state)`.

        # However, `gate_registry.py` imports it.
        # If I import it directly from `hooks.gates`, I need to pass state.

        result = check_tool_gate(ctx, state)

        # Should allow because AskUserQuestion is always_available
        assert result.verdict == GateVerdict.ALLOW


class TestActivateSkillNeverBlocked:
    """Test that activate_skill is never blocked by check_tool_gate."""

    @pytest.fixture
    def mock_context(self):
        """Create a PreToolUse context for activate_skill."""
        return HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="activate_skill",
            tool_input={"name": "prompt-hydrator"},
        )

    def test_activate_skill_allowed_without_hydration(self, mock_context, mock_session_state):
        """activate_skill should be allowed even without hydration."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "closed"
        state.state["hydration_pending"] = True

        result = check_tool_gate(mock_context, state)

        # Should allow because activate_skill is always_available
        assert result.verdict == GateVerdict.ALLOW

    def test_activate_skill_allowed_when_hydration_pending(self, mock_context, mock_session_state):
        """activate_skill should be allowed even when hydration is pending."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "closed"
        state.state["hydration_pending"] = True

        result = check_tool_gate(mock_context, state)

        assert result.verdict == GateVerdict.ALLOW


class TestHydratorActiveBypass:
    """Test that when hydrator is active, all tools are allowed."""

    def test_read_tool_allowed_when_hydrator_active(self, mock_session_state):
        """Read tool should be allowed when hydrator is active."""
        state, _ = mock_session_state
        state.state["hydrator_active"] = True

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        result = check_tool_gate(ctx, state)

        assert result.verdict == GateVerdict.ALLOW

    def test_write_tool_allowed_when_hydrator_active(self, mock_session_state):
        """Write tool should be allowed when hydrator is active."""
        state, _ = mock_session_state
        state.state["hydrator_active"] = True

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Write",
            tool_input={"file_path": "/some/file.py", "content": "test"},
        )

        result = check_tool_gate(ctx, state)

        assert result.verdict == GateVerdict.ALLOW


class TestTaskHydratorSpawn:
    """Test that Task tool with hydrator subagent is allowed and sets active."""

    def test_task_hydrator_allowed_and_sets_active(self, mock_session_state):
        """Task with hydrator subagent should be allowed."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "closed"

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Task",
            tool_input={
                "subagent_type": "aops-core:prompt-hydrator",
                "prompt": "Hydrate this task",
            },
        )

        result = check_tool_gate(ctx, state)

        assert result.verdict == GateVerdict.ALLOW
        # Note: Hydrator active flag is set in on_tool_use, not check.
        # But gate should be opened (cleared) if spawning.
        assert state.gates["hydration"].status == "open"


class TestReadToolBlockedWithoutHydration:
    """Test that read tools are blocked without hydration (when hydrator not active)."""

    def test_read_blocked_when_hydration_not_passed(self, mock_session_state):
        """Read should be blocked when hydration gate is not passed."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "closed"
        state.state["hydrator_active"] = False
        state.state["hydration_pending"] = True

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        # Mock audit file creation to avoid IO error
        with patch("lib.gates.hydration.HydrationGate._create_block_result") as mock_block:
            from lib.gate_model import GateResult
            mock_block.return_value = GateResult.deny("Blocked")

            result = check_tool_gate(ctx, state)

            # Should block or warn because hydration is required for read_only
            assert result.verdict in (GateVerdict.DENY, GateVerdict.WARN)

    def test_read_allowed_when_hydration_passed(self, mock_session_state):
        """Read should be allowed when hydration gate is passed."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "open"
        state.state["hydrator_active"] = False
        state.state["hydration_pending"] = False

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        result = check_tool_gate(ctx, state)

        assert result.verdict == GateVerdict.ALLOW
