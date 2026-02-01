#!/usr/bin/env python3
"""Unit tests for hydration gate with Gemini hook events.

Tests hydration gate behavior with real Gemini hook event formats to ensure
cross-agent compatibility between Claude and Gemini.

Test cases derived from actual Gemini hook events:
1. PostToolUse with activate_skill "prompt-hydrator" -> marks hydration complete
2. PreToolUse with run_shell_command reading hydration file -> allows (hydration attempt)
3. PreToolUse with read_file for non-hydration file -> should NOT block (safe tool)

Related:
- specs/prompt-hydration.md
- Task: Implement hydration gate for Gemini - test cases from real events
"""

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.gate_registry import (
    GateContext,
    check_hydration_gate,
    post_hydration_trigger,
    _hydration_is_hydrator_task,
    _hydration_is_gemini_hydration_attempt,
)


# ============================================================================
# Fixtures: Real Gemini Hook Events
# ============================================================================


@pytest.fixture
def gemini_post_tool_use_activate_skill_hydrator() -> dict[str, Any]:
    """PostToolUse event when Gemini invokes activate_skill for prompt-hydrator.

    This event should mark hydration as COMPLETE.
    """
    return {
        "hook_event": "PostToolUse",
        "logged_at": "2026-01-28T16:36:59+10:00",
        "exit_code": 0,
        "session_id": "42e642ba-ba31-4b47-b867-eeba04509581",
        "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session-2026-01-28T06-36-42e642ba.json",
        "cwd": "/home/nic/src/academicOps",
        "hook_event_name": "PostToolUse",
        "timestamp": "2026-01-28T06:36:59.713Z",
        "tool_name": "activate_skill",
        "tool_input": {"name": "prompt-hydrator"},
        "tool_response": {
            "llmContent": '<activated_skill name="prompt-hydrator">\n  <instructions>\n    # Prompt Hydrator Agent...'
        },
    }


@pytest.fixture
def gemini_pre_tool_use_shell_read_hydration_file() -> dict[str, Any]:
    """PreToolUse event when Gemini reads the hydration context file via shell.

    This event should BLOCK if hydration is not complete (but this IS the
    hydration attempt, so it should be allowed and clear pending).
    """
    return {
        "hook_event": "PreToolUse",
        "logged_at": "2026-01-28T10:02:29+10:00",
        "exit_code": 0,
        "session_id": "f2aa587a-68e9-48d6-8535-25ace06a3b47",
        "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session-2026-01-28T00-01-f2aa587a.json",
        "cwd": "/home/nic/src/academicOps",
        "hook_event_name": "PreToolUse",
        "timestamp": "2026-01-28T00:02:28.798Z",
        "tool_name": "run_shell_command",
        "tool_input": {
            "command": "cat /home/nic/.aops/tmp/hydrator/hydrate_96x7iqw1.md",
            "description": "Reading the hydration temporary file for workflow guidance.",
        },
    }


@pytest.fixture
def gemini_pre_tool_use_read_file_general() -> dict[str, Any]:
    """PreToolUse event when Gemini reads a general file (not hydration-related).

    This event should NOT block even if hydration is pending - read_file is
    a safe read-only tool that shouldn't require hydration completion.
    """
    return {
        "hook_event": "PreToolUse",
        "logged_at": "2026-01-28T10:02:20+10:00",
        "exit_code": 0,
        "session_id": "f2aa587a-68e9-48d6-8535-25ace06a3b47",
        "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session-2026-01-28T00-01-f2aa587a.json",
        "cwd": "/home/nic/src/academicOps",
        "hook_event_name": "PreToolUse",
        "timestamp": "2026-01-28T00:02:20.245Z",
        "tool_name": "read_file",
        "tool_input": {"file_path": "specs/prompt-hydration.md"},
    }


# ============================================================================
# Test: Hydrator Task Detection
# ============================================================================


class TestHydratorTaskDetection:
    """Test detection of hydrator invocation across agent types."""

    def test_claude_task_subagent_type_detected(self):
        """Claude Task tool with subagent_type='prompt-hydrator' is detected."""
        tool_input = {"subagent_type": "prompt-hydrator"}
        assert _hydration_is_hydrator_task(tool_input)

    def test_claude_task_partial_match_detected(self):
        """Claude Task tool with 'hydrator' in subagent_type is detected."""
        tool_input = {"subagent_type": "aops-core:prompt-hydrator"}
        assert _hydration_is_hydrator_task(tool_input)

    def test_gemini_delegate_agent_name_detected(self):
        """Gemini delegate_to_agent with agent_name='prompt-hydrator' is detected."""
        tool_input = {"agent_name": "prompt-hydrator"}
        assert _hydration_is_hydrator_task(tool_input)

    def test_gemini_delegate_partial_match_detected(self):
        """Gemini delegate_to_agent with 'hydrator' in agent_name is detected."""
        tool_input = {"agent_name": "custom-hydrator-v2"}
        assert _hydration_is_hydrator_task(tool_input)

    def test_non_hydrator_task_not_detected(self):
        """Non-hydrator tasks are not falsely detected."""
        tool_input = {"subagent_type": "qa"}
        assert not _hydration_is_hydrator_task(tool_input)

        tool_input = {"agent_name": "research-agent"}
        assert not _hydration_is_hydrator_task(tool_input)

    def test_empty_input_not_detected(self):
        """Empty input returns False, not error."""
        assert not _hydration_is_hydrator_task({})
        assert not _hydration_is_hydrator_task({"other_field": "value"})


class TestGeminiActivateSkillDetection:
    """Test detection of Gemini's activate_skill tool for hydrator.

    Gemini uses activate_skill(name="prompt-hydrator") to invoke the hydrator,
    which is different from Claude's Task(subagent_type="prompt-hydrator").

    The gate should recognize this on PreToolUse and allow + clear pending.
    """

    def test_activate_skill_hydrator_detected_by_helper(self):
        """_hydration_is_hydrator_task should detect activate_skill with hydrator name."""
        # This should be detected as a hydrator invocation
        tool_input = {"name": "prompt-hydrator"}
        assert _hydration_is_hydrator_task(tool_input), \
            "activate_skill with name='prompt-hydrator' should be detected"

    def test_activate_skill_partial_match_detected(self):
        """activate_skill with 'hydrator' in name should be detected."""
        tool_input = {"name": "aops-core:prompt-hydrator"}
        assert _hydration_is_hydrator_task(tool_input), \
            "activate_skill with 'hydrator' in name should be detected"

    def test_activate_skill_other_skill_not_detected(self):
        """activate_skill with other skill names should not be detected."""
        tool_input = {"name": "commit"}
        assert not _hydration_is_hydrator_task(tool_input)

        tool_input = {"name": "handover"}
        assert not _hydration_is_hydrator_task(tool_input)

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_activate_skill_hydrator_allows_pretooluse(
        self, mock_hook_utils, mock_session_state
    ):
        """PreToolUse with activate_skill 'prompt-hydrator' should allow.

        This is the key integration test: when Gemini invokes activate_skill to
        load the prompt-hydrator skill, the gate should recognize this as the
        hydration step and allow the tool to proceed.

        Note: clear_hydration_pending is called on PostToolUse, not PreToolUse.
        """
        mock_hook_utils.is_subagent_session.return_value = False
        mock_hook_utils.get_hook_temp_dir.return_value = Path("/tmp/hydrator")
        mock_session_state.is_hydration_pending.return_value = True
        mock_session_state.is_hydrator_active.return_value = False

        event = {
            "hook_event_name": "PreToolUse",
            "session_id": "gemini-session-123",
            "tool_name": "activate_skill",
            "tool_input": {"name": "prompt-hydrator"},
        }
        ctx = GateContext(
            session_id=event["session_id"],
            event_name=event["hook_event_name"],
            input_data=event,
        )

        result = check_hydration_gate(ctx)

        # Should allow (return None) - pending is cleared on PostToolUse
        assert result is None, "activate_skill with hydrator should be allowed"


# ============================================================================
# Test: Hydration Gate Behavior
# ============================================================================


class TestHydrationGateBehavior:
    """Test the hydration gate's permit/deny decisions."""

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_gate_allows_when_hydration_not_pending(
        self, mock_hook_utils, mock_session_state, gemini_pre_tool_use_read_file_general
    ):
        """When hydration is NOT pending, all tools are allowed."""
        mock_hook_utils.is_subagent_session.return_value = False
        mock_session_state.is_hydration_pending.return_value = False

        event = gemini_pre_tool_use_read_file_general
        ctx = GateContext(
            session_id=event["session_id"],
            event_name=event["hook_event_name"],
            input_data=event,
        )

        result = check_hydration_gate(ctx)
        assert result is None, "Gate should allow when hydration not pending"

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_gate_allows_subagent_sessions(
        self, mock_hook_utils, mock_session_state, gemini_pre_tool_use_read_file_general
    ):
        """Subagent sessions bypass the hydration gate entirely."""
        mock_hook_utils.is_subagent_session.return_value = True
        # Even if pending is True, subagents should pass
        mock_session_state.is_hydration_pending.return_value = True

        event = gemini_pre_tool_use_read_file_general
        ctx = GateContext(
            session_id=event["session_id"],
            event_name=event["hook_event_name"],
            input_data=event,
        )

        result = check_hydration_gate(ctx)
        assert result is None, "Gate should allow subagent sessions"

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    @patch("hooks.gate_registry.load_template")
    def test_gate_blocks_general_tool_when_hydration_pending(
        self,
        mock_load_template,
        mock_hook_utils,
        mock_session_state,
    ):
        """General tools should be blocked when hydration is pending.

        Note: This tests current behavior. The test for read_file specifically
        tests whether we WANT to allow safe read tools.
        """
        mock_hook_utils.is_subagent_session.return_value = False
        mock_session_state.is_hydration_pending.return_value = True
        mock_session_state.is_hydrator_active.return_value = False
        mock_session_state.get_hydration_temp_path.return_value = "/tmp/hydrator/context.md"
        mock_hook_utils.get_hook_temp_dir.side_effect = RuntimeError("no temp dir")
        mock_load_template.return_value = "Hydration gate blocked"

        # A general Bash command (not reading hydration file)
        event = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }
        ctx = GateContext(
            session_id=event["session_id"],
            event_name=event["hook_event_name"],
            input_data=event,
        )

        result = check_hydration_gate(ctx)
        assert result is not None, "Gate should block Bash when hydration pending"
        # GateResult has verdict attribute (not permissionDecision)
        from hooks.gate_registry import GateVerdict
        assert result.verdict == GateVerdict.DENY


class TestGeminiHydrationFileRead:
    """Test detection of Gemini reading the hydration context file."""

    @patch("hooks.gate_registry.hook_utils")
    def test_run_shell_command_reading_hydration_file_detected(
        self, mock_hook_utils, gemini_pre_tool_use_shell_read_hydration_file
    ):
        """run_shell_command with cat of hydration file should be detected."""
        # Mock the temp dir to match what's in the command
        mock_hook_utils.get_hook_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")

        event = gemini_pre_tool_use_shell_read_hydration_file
        result = _hydration_is_gemini_hydration_attempt(
            event["tool_name"],
            event["tool_input"],
            event,
        )

        assert result, "run_shell_command reading hydration file should be detected"

    @patch("hooks.gate_registry.hook_utils")
    def test_run_shell_command_other_command_not_detected(self, mock_hook_utils):
        """run_shell_command with unrelated command should not be detected."""
        mock_hook_utils.get_hook_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")

        result = _hydration_is_gemini_hydration_attempt(
            "run_shell_command",
            {"command": "ls -la /home/nic/src"},
            {},
        )

        assert not result, "Unrelated shell command should not be detected"

    @patch("hooks.gate_registry.hook_utils")
    def test_read_file_hydration_temp_detected(self, mock_hook_utils):
        """read_file targeting hydration temp dir should be detected."""
        mock_hook_utils.get_hook_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")

        result = _hydration_is_gemini_hydration_attempt(
            "read_file",
            {"file_path": "/home/nic/.aops/tmp/hydrator/hydrate_abc123.md"},
            {},
        )

        assert result, "read_file targeting hydration temp should be detected"

    @patch("hooks.gate_registry.hook_utils")
    def test_read_file_general_file_not_detected(
        self, mock_hook_utils, gemini_pre_tool_use_read_file_general
    ):
        """read_file for general files should NOT be detected as hydration attempt."""
        mock_hook_utils.get_hook_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")

        event = gemini_pre_tool_use_read_file_general
        result = _hydration_is_gemini_hydration_attempt(
            event["tool_name"],
            event["tool_input"],
            event,
        )

        assert not result, "read_file for specs/ should not be detected as hydration"


class TestSafeToolsAllowlist:
    """Test that safe read-only tools should NOT be blocked by hydration gate.

    Safe read-only tools are allowed regardless of hydration state, similar to
    how custodiet has a skip_tools allowlist. This prevents the gate from
    blocking context-gathering operations.
    """

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_read_file_should_not_block_when_hydration_pending(
        self, mock_hook_utils, mock_session_state, gemini_pre_tool_use_read_file_general
    ):
        """read_file for general files should NOT be blocked by hydration gate.

        Rationale: Reading files is a safe, read-only operation that doesn't
        modify state. Blocking it prevents the agent from gathering context
        needed to understand what to do - counterproductive.
        """
        mock_hook_utils.is_subagent_session.return_value = False
        mock_session_state.is_hydration_pending.return_value = True
        mock_hook_utils.get_hook_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")

        event = gemini_pre_tool_use_read_file_general
        ctx = GateContext(
            session_id=event["session_id"],
            event_name=event["hook_event_name"],
            input_data=event,
        )

        result = check_hydration_gate(ctx)
        assert result is None, "read_file should not be blocked when hydration pending"

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_view_file_should_not_block_when_hydration_pending(
        self, mock_hook_utils, mock_session_state
    ):
        """Gemini's view_file should not be blocked by hydration gate."""
        mock_hook_utils.is_subagent_session.return_value = False
        mock_session_state.is_hydration_pending.return_value = True
        mock_hook_utils.get_hook_temp_dir.side_effect = RuntimeError("no temp dir")

        event = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "view_file",
            "tool_input": {"file_path": "README.md"},
        }
        ctx = GateContext(
            session_id=event["session_id"],
            event_name=event["hook_event_name"],
            input_data=event,
        )

        result = check_hydration_gate(ctx)
        assert result is None, "view_file should not be blocked when hydration pending"

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_claude_read_tool_should_not_block(self, mock_hook_utils, mock_session_state):
        """Claude's Read tool should not be blocked by hydration gate."""
        mock_hook_utils.is_subagent_session.return_value = False
        mock_session_state.is_hydration_pending.return_value = True
        mock_hook_utils.get_hook_temp_dir.side_effect = RuntimeError("no temp dir")

        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Read",
                "tool_input": {"file_path": "/some/file.py"},
            },
        )

        result = check_hydration_gate(ctx)
        assert result is None, "Read should not be blocked when hydration pending"

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_claude_glob_tool_should_not_block(self, mock_hook_utils, mock_session_state):
        """Claude's Glob tool should not be blocked by hydration gate."""
        mock_hook_utils.is_subagent_session.return_value = False
        mock_session_state.is_hydration_pending.return_value = True
        mock_hook_utils.get_hook_temp_dir.side_effect = RuntimeError("no temp dir")

        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Glob",
                "tool_input": {"pattern": "**/*.py"},
            },
        )

        result = check_hydration_gate(ctx)
        assert result is None, "Glob should not be blocked when hydration pending"


class TestPostToolUseHydrationCompletion:
    """Test that PostToolUse events can mark hydration complete.

    For Gemini, the hydrator is invoked via activate_skill, and the completion
    event is PostToolUse. The gate must handle this to clear hydration_pending.
    """

    def test_hydration_gates_registered_for_pre_and_post_events(self):
        """Verify hydration and post_hydration gates cover both events."""
        from hooks.gates import ACTIVE_GATES

        # Hydration gate handles PreToolUse (blocking)
        hydration_gate = next(g for g in ACTIVE_GATES if g["name"] == "hydration")
        assert "PreToolUse" in hydration_gate["events"]

        # Post-hydration gate handles PostToolUse (clearing pending)
        post_hydration_gate = next(g for g in ACTIVE_GATES if g["name"] == "post_hydration")
        assert "PostToolUse" in post_hydration_gate["events"]

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_posttooluse_activate_skill_clears_hydration(
        self, mock_hook_utils, mock_session_state
    ):
        """PostToolUse with activate_skill 'prompt-hydrator' should clear pending.

        This is the REAL Gemini event format - the hydrator completion fires
        on PostToolUse, not PreToolUse. Uses post_hydration_trigger gate.
        """
        mock_hook_utils.is_subagent_session.return_value = False
        mock_hook_utils.get_hook_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")

        # Real Gemini PostToolUse event for hydrator completion
        event = {
            "hook_event": "PostToolUse",
            "exit_code": 0,
            "session_id": "6a416d2b-8864-4a05-ac5e-85e3ebeef207",
            "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session-2026-01-28T08-02-6a416d2b.json",
            "cwd": "/home/nic/src/academicOps",
            "hook_event_name": "PostToolUse",
            "timestamp": "2026-01-28T08:03:53.288Z",
            "tool_name": "activate_skill",
            "tool_input": {"name": "prompt-hydrator"},
            "tool_response": {"llmContent": "<activated_skill>..."},
        }

        ctx = GateContext(
            session_id=event["session_id"],
            event_name=event["hook_event_name"],
            input_data=event,
        )

        # Use post_hydration_trigger for PostToolUse events
        result = post_hydration_trigger(ctx)

        # Should return ALLOW result and clear pending
        assert result is not None, "PostToolUse activate_skill hydrator should return result"
        mock_session_state.clear_hydration_pending.assert_called_once_with(
            "6a416d2b-8864-4a05-ac5e-85e3ebeef207"
        )

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_posttooluse_other_tool_does_not_clear_hydration(
        self, mock_hook_utils, mock_session_state
    ):
        """PostToolUse with non-hydrator tool should NOT clear pending."""
        mock_hook_utils.is_subagent_session.return_value = False
        mock_session_state.is_hydration_pending.return_value = True

        event = {
            "hook_event_name": "PostToolUse",
            "session_id": "test-session",
            "tool_name": "activate_skill",
            "tool_input": {"name": "commit"},  # Not hydrator
        }

        ctx = GateContext(
            session_id=event["session_id"],
            event_name=event["hook_event_name"],
            input_data=event,
        )

        result = check_hydration_gate(ctx)

        # Should allow but NOT clear pending (it's not the hydrator)
        assert result is None  # PostToolUse doesn't block
        mock_session_state.clear_hydration_pending.assert_not_called()


# ============================================================================
# Integration Tests
# ============================================================================


class TestCrossAgentCompatibility:
    """Test that hydration gate behaves identically for Claude and Gemini."""

    @patch("hooks.gate_registry.session_state")
    @patch("hooks.gate_registry.hook_utils")
    def test_claude_task_and_gemini_delegate_both_detected(
        self, mock_hook_utils, mock_session_state
    ):
        """Both Claude Task and Gemini delegate_to_agent are detected as hydrator."""
        mock_hook_utils.is_subagent_session.return_value = False
        mock_session_state.is_hydration_pending.return_value = True

        # Claude style
        claude_ctx = GateContext(
            session_id="claude-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Task",
                "tool_input": {"subagent_type": "prompt-hydrator"},
            },
        )

        # Gemini style
        gemini_ctx = GateContext(
            session_id="gemini-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "delegate_to_agent",
                "tool_input": {"agent_name": "prompt-hydrator"},
            },
        )

        # Both should be detected as hydrator invocations
        assert _hydration_is_hydrator_task(claude_ctx.tool_input)
        assert _hydration_is_hydrator_task(gemini_ctx.tool_input)
