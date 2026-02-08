#!/usr/bin/env python3
"""Tests for hydration gate never blocking itself.

Verifies that:
1. activate_skill(name='prompt-hydrator') is never blocked by the hydration gate
   because it's in the 'always_available' tool category.
2. When session_state.is_hydrator_active() returns True, all tools are allowed
   by the hydration gate (the hydrator's own tool calls bypass the gate).
3. Task tool with hydrator subagent_type is allowed and sets hydrator_active.

Related:
- Task aops-393209bd: Ensure hydration gate never blocks itself
- Task aops-cc52dafb: Complete hydration gate test and verification
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))


from hooks.gate_config import TOOL_CATEGORIES, get_required_gates, get_tool_category
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

    def test_activate_skill_requires_no_gates(self):
        """activate_skill should require no gates."""
        gates = get_required_gates("activate_skill")
        assert gates == []

    def test_skill_tool_in_always_available(self):
        """Skill tool should also be in always_available."""
        assert "Skill" in TOOL_CATEGORIES["always_available"]

    def test_task_tool_in_always_available(self):
        """Task tool should also be in always_available."""
        assert "Task" in TOOL_CATEGORIES["always_available"]


class TestAskUserQuestionAlwaysAvailable:
    """Test that AskUserQuestion is never blocked by the hydration gate.

    AskUserQuestion is essential for agent-user communication and should
    be available at all times, including before hydration completes.

    Related: Task aops-ffee2d2a
    """

    def test_ask_user_question_in_always_available(self):
        """AskUserQuestion should be in the always_available category."""
        assert "AskUserQuestion" in TOOL_CATEGORIES["always_available"]

    def test_ask_user_question_category(self):
        """get_tool_category should return always_available for AskUserQuestion."""
        assert get_tool_category("AskUserQuestion") == "always_available"

    def test_ask_user_question_requires_no_gates(self):
        """AskUserQuestion should require no gates."""
        gates = get_required_gates("AskUserQuestion")
        assert gates == []

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
            patch("lib.session_state.get_passed_gates", return_value=set()),
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
            patch("lib.session_state.get_passed_gates", return_value=set()),
        ):
            result = check_tool_gate(mock_context)

            # Should allow because activate_skill is always_available
            assert result.verdict == GateVerdict.ALLOW

    def test_activate_skill_allowed_when_hydration_pending(self, mock_context):
        """activate_skill should be allowed even when hydration is pending."""
        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            patch("lib.session_state.get_passed_gates", return_value=set()),
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

    def test_edit_tool_allowed_when_hydrator_active(self):
        """Edit tool should be allowed when hydrator is active."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={
                "file_path": "/some/file.py",
                "old_string": "a",
                "new_string": "b",
            },
        )

        with patch("lib.session_state.is_hydrator_active", return_value=True):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW

    def test_bash_tool_allowed_when_hydrator_active(self):
        """Bash tool should be allowed when hydrator is active."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "ls -la"},
        )

        with patch("lib.session_state.is_hydrator_active", return_value=True):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW

    def test_todo_write_allowed_when_hydrator_active(self):
        """TodoWrite (meta tool) should be allowed when hydrator is active."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="TodoWrite",
            tool_input={"todos": []},
        )

        with patch("lib.session_state.is_hydrator_active", return_value=True):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW


class TestTaskHydratorSpawn:
    """Test that Task tool with hydrator subagent is allowed and sets active."""

    def test_task_hydrator_allowed_and_sets_active(self):
        """Task with hydrator subagent should be allowed and set hydrator_active."""
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
            patch("lib.session_state.get_passed_gates", return_value=set()),
            patch("lib.session_state.set_hydrator_active") as mock_set,
        ):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW
            # Should have called set_hydrator_active
            mock_set.assert_called_once_with("test-session-123")

    def test_task_hydrator_case_insensitive(self):
        """Task with hydrator subagent should match case-insensitively."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Task",
            tool_input={
                "subagent_type": "aops-core:Prompt-Hydrator",  # Mixed case
                "prompt": "Hydrate this task",
            },
        )

        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            patch("lib.session_state.get_passed_gates", return_value=set()),
            patch("lib.session_state.set_hydrator_active") as mock_set,
        ):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW
            mock_set.assert_called_once()

    def test_task_non_hydrator_still_allowed(self):
        """Task tool is in always_available, so any subagent is allowed."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Task",
            tool_input={
                "subagent_type": "aops-core:critic",
                "prompt": "Review this plan",
            },
        )

        with (
            patch("lib.session_state.is_hydrator_active", return_value=False),
            patch("lib.session_state.get_passed_gates", return_value=set()),
            patch("lib.session_state.set_hydrator_active") as mock_set,
        ):
            result = check_tool_gate(ctx)

            # Task is always_available, so it's allowed
            assert result.verdict == GateVerdict.ALLOW
            # Should NOT set hydrator_active for non-hydrator subagent
            mock_set.assert_not_called()


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
            patch("lib.session_state.get_passed_gates", return_value=set()),
            patch("hooks.gates._create_audit_file", return_value=None),
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
            patch("lib.session_state.get_passed_gates", return_value={"hydration"}),
        ):
            result = check_tool_gate(ctx)

            assert result.verdict == GateVerdict.ALLOW


class TestNonPreToolUseEvents:
    """Test that non-PreToolUse events are always allowed."""

    def test_post_tool_use_always_allowed(self):
        """PostToolUse events should always be allowed by check_tool_gate."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PostToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        result = check_tool_gate(ctx)

        assert result.verdict == GateVerdict.ALLOW

    def test_session_start_always_allowed(self):
        """SessionStart events should always be allowed by check_tool_gate."""
        ctx = HookContext(
            session_id="test-session-123",
            hook_event="SessionStart",
        )

        result = check_tool_gate(ctx)

        assert result.verdict == GateVerdict.ALLOW
