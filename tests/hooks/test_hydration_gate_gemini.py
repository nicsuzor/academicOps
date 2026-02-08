"""Tests for Gemini-specific hydration gate detection helpers.

Tests the helper functions that detect hydrator invocation across agent types.
These are unit tests for detection logic, not full gate behavior.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.gate_registry import (
    _hydration_is_hydrator_task,
    _hydration_is_gemini_hydration_attempt,
)


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

    def test_empty_input_not_detected(self):
        """Empty input is not falsely detected."""
        assert not _hydration_is_hydrator_task({})

    def test_none_values_handled(self):
        """None values in tool_input are handled safely."""
        tool_input = {"subagent_type": None, "agent_name": None}
        assert not _hydration_is_hydrator_task(tool_input)


class TestGeminiActivateSkillDetection:
    """Test detection of Gemini's activate_skill tool for hydrator.

    Gemini uses activate_skill(name="prompt-hydrator") to invoke the hydrator,
    which is different from Claude's Task(subagent_type="prompt-hydrator").
    """

    def test_activate_skill_hydrator_detected_by_helper(self):
        """_hydration_is_hydrator_task should detect activate_skill with hydrator name."""
        tool_input = {"name": "prompt-hydrator"}
        assert _hydration_is_hydrator_task(tool_input), (
            "activate_skill with name='prompt-hydrator' should be detected"
        )

    def test_activate_skill_partial_match_detected(self):
        """activate_skill with 'hydrator' in name should be detected."""
        tool_input = {"name": "aops-core:prompt-hydrator"}
        assert _hydration_is_hydrator_task(tool_input), (
            "activate_skill with 'hydrator' in name should be detected"
        )

    def test_activate_skill_other_skill_not_detected(self):
        """activate_skill with other skill names should not be detected."""
        tool_input = {"name": "commit"}
        assert not _hydration_is_hydrator_task(tool_input)

        tool_input = {"name": "handover"}
        assert not _hydration_is_hydrator_task(tool_input)


class TestGeminiHydrationAttemptDetection:
    """Test detection of Gemini-specific hydration patterns."""

    @patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
    def test_gemini_read_hydration_file_detected(self, mock_temp_dir):
        """Gemini reading hydration file should be detected."""
        mock_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")
        tool_name = "read_file"
        tool_input = {"file_path": "/home/nic/.aops/tmp/hydrator/hydrate_abc123.md"}
        raw_input = {"tool_name": tool_name, "tool_input": tool_input}

        assert _hydration_is_gemini_hydration_attempt(tool_name, tool_input, raw_input)

    @patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
    def test_gemini_shell_cat_hydration_file_detected(self, mock_temp_dir):
        """Gemini shell cat of hydration file should be detected."""
        mock_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")
        tool_name = "run_shell_command"
        tool_input = {"command": "cat /home/nic/.aops/tmp/hydrator/hydrate_xyz789.md"}
        raw_input = {"tool_name": tool_name, "tool_input": tool_input}

        assert _hydration_is_gemini_hydration_attempt(tool_name, tool_input, raw_input)

    @patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
    def test_non_hydration_file_not_detected(self, mock_temp_dir):
        """Reading non-hydration files should not be detected."""
        mock_temp_dir.return_value = Path("/home/nic/.aops/tmp/hydrator")
        tool_name = "read_file"
        tool_input = {"file_path": "/home/nic/src/project/README.md"}
        raw_input = {"tool_name": tool_name, "tool_input": tool_input}

        assert not _hydration_is_gemini_hydration_attempt(tool_name, tool_input, raw_input)

    def test_empty_inputs_handled(self):
        """Empty inputs should be handled safely."""
        assert not _hydration_is_gemini_hydration_attempt("", {}, {})
        assert not _hydration_is_gemini_hydration_attempt(None, {}, {})
