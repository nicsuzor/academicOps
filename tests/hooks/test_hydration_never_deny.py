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

    def test_ask_user_question_allowed_without_hydration(self):
        """AskUserQuestion should be allowed even without hydration."""
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

        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            # Mock is_hydration_pending to return True (gate closed)
            patch("lib.session_state.is_hydration_pending", return_value=True),
        ):
            result = check_tool_gate(ctx)

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

    def test_activate_skill_allowed_without_hydration(self, mock_context):
        """activate_skill should be allowed even without hydration."""
        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            patch("lib.session_state.is_hydration_pending", return_value=True),
        ):
            result = check_tool_gate(mock_context)

            # Should allow because activate_skill is always_available
            assert result.verdict == GateVerdict.ALLOW

    def test_activate_skill_allowed_when_hydration_pending(self, mock_context):
        """activate_skill should be allowed even when hydration is pending."""
        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            patch("lib.session_state.is_hydration_pending", return_value=True),
        ):
            result = check_tool_gate(mock_context)

            assert result.verdict == GateVerdict.ALLOW


class TestHydratorActiveBypass:
    """Test that when hydrator is active, all tools are allowed."""

    def test_read_tool_allowed_when_hydrator_active(self):
        """Read tool should be allowed when hydrator is active."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        with patch("lib.session_state.is_hydrator_active", return_value=True):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW

    def test_write_tool_allowed_when_hydrator_active(self):
        """Write tool should be allowed when hydrator is active."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Write",
            tool_input={"file_path": "/some/file.py", "content": "test"},
        )

        with patch("lib.session_state.is_hydrator_active", return_value=True):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW


class TestTaskHydratorSpawn:
    """Test that Task tool with hydrator subagent is allowed and sets active."""

    def test_task_hydrator_allowed_and_sets_active(self):
        """Task with hydrator subagent should be allowed."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Task",
            tool_input={
                "subagent_type": "aops-core:prompt-hydrator",
                "prompt": "Hydrate this task",
            },
        )

        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            patch("lib.session_state.is_hydration_pending", return_value=True),
            # Note: set_hydrator_active is called in on_tool_use, not check.
            # But check calls clear_hydration_pending.
            patch("lib.session_state.clear_hydration_pending") as mock_clear,
        ):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW
            mock_clear.assert_called_once_with("test-session-123")


class TestReadToolBlockedWithoutHydration:
    """Test that read tools are blocked without hydration (when hydrator not active)."""

    def test_read_blocked_when_hydration_not_passed(self):
        """Read should be blocked when hydration gate is not passed."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            # Gate closed (pending)
            patch("lib.session_state.is_hydration_pending", return_value=True),
            patch("lib.gate_utils.create_audit_file", return_value=None),
        ):
            result = check_tool_gate(ctx)

            # Should block or warn because hydration is required for read_only
            assert result.verdict in (GateVerdict.DENY, GateVerdict.WARN)

    def test_read_allowed_when_hydration_passed(self):
        """Read should be allowed when hydration gate is passed."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            # Gate open
            patch("lib.session_state.is_hydration_pending", return_value=False),
        ):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW
