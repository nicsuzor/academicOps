import unittest
from unittest.mock import MagicMock, patch

from hooks.user_prompt_submit import (
    build_hydration_instruction,
    write_initial_hydrator_state,
    CONTEXT_TEMPLATE_FILE,
    INSTRUCTION_TEMPLATE_FILE,
)
from lib.session_state import SessionState


class TestUserPromptSubmit(unittest.TestCase):
    def setUp(self):
        self.session_id = "test-session"
        self.prompt = "Test prompt"
        self.temp_path = "/tmp/hydrate_123.md"

        # Setup mock session state
        self.mock_state = MagicMock(spec=SessionState)
        self.mock_state.gates = {}
        # We need to ensure get_gate returns a mock gate with metrics dict
        self.mock_gate = MagicMock()
        self.mock_gate.metrics = {}
        self.mock_state.get_gate.return_value = self.mock_gate

        # Legacy
        self.mock_state.state = {}

        # New global turn count
        self.mock_state.global_turn_count = 0

    @patch("hooks.user_prompt_submit.get_hook_temp_dir")
    @patch("hooks.user_prompt_submit._write_temp")
    @patch("hooks.user_prompt_submit.cleanup_old_temp_files")
    @patch("hooks.user_prompt_submit.load_framework_paths")
    @patch("hooks.user_prompt_submit.load_mcp_tools_context")
    @patch("hooks.user_prompt_submit.load_environment_variables_context")
    @patch("hooks.user_prompt_submit.load_project_paths_context")
    @patch("hooks.user_prompt_submit.load_workflows_index")
    @patch("hooks.user_prompt_submit.load_skills_index")
    @patch("hooks.user_prompt_submit.load_scripts_index")
    @patch("hooks.user_prompt_submit.load_project_rules")
    @patch("hooks.user_prompt_submit.get_task_work_state")
    @patch("hooks.user_prompt_submit.get_formatted_relevant_paths")
    @patch("hooks.user_prompt_submit.load_project_context_index")
    @patch("hooks.user_prompt_submit.load_template")
    @patch("hooks.user_prompt_submit.extract_router_context")
    @patch("lib.session_state.SessionState.load")
    def test_build_hydration_instruction(
        self,
        mock_load,
        mock_extract_context,
        mock_load_template,
        mock_load_context_index,
        mock_get_relevant_paths,
        mock_get_task_work,
        mock_load_project_rules,
        mock_load_scripts,
        mock_load_skills,
        mock_load_workflows,
        mock_load_project_paths,
        mock_load_env,
        mock_load_mcp,
        mock_load_framework,
        mock_cleanup,
        mock_write_temp,
        mock_get_hook_temp,
    ):
        # Mock setup
        mock_load.return_value = self.mock_state
        mock_write_temp.return_value = self.temp_path

        # Determine return value based on file argument
        def side_effect(filepath):
            if filepath == CONTEXT_TEMPLATE_FILE:
                return "Context for {prompt}"
            if filepath == INSTRUCTION_TEMPLATE_FILE:
                return "Instruction template: {temp_path}"
            return "Unknown template"

        mock_load_template.side_effect = side_effect

        # Call function
        result = build_hydration_instruction(self.session_id, self.prompt)

        # Verification
        self.assertIn(self.temp_path, result)

        # Verify SessionState interactions
        mock_load.assert_called_with(self.session_id)
        self.mock_state.save.assert_called_once()

        # Verify hydration state set
        self.mock_state.get_gate.assert_called_with("hydration")
        self.assertEqual(self.mock_gate.metrics["temp_path"], self.temp_path)
        self.assertEqual(self.mock_gate.metrics["original_prompt"], self.prompt)

        # Verify gate closed (pending hydration)
        self.mock_state.close_gate.assert_called_with("hydration")

    @patch("lib.session_state.SessionState.load")
    def test_write_initial_hydrator_state_pending(self, mock_load):
        # Setup
        mock_load.return_value = self.mock_state

        # Call with hydration_pending=True (default)
        write_initial_hydrator_state(self.session_id, self.prompt, hydration_pending=True)

        # Verify
        mock_load.assert_called_with(self.session_id)
        self.mock_state.close_gate.assert_called_with("hydration")
        self.assertEqual(self.mock_gate.metrics["original_prompt"], self.prompt)
        self.mock_state.save.assert_called_once()

    @patch("lib.session_state.SessionState.load")
    def test_write_initial_hydrator_state_not_pending(self, mock_load):
        # Setup
        mock_load.return_value = self.mock_state

        # Call with hydration_pending=False
        write_initial_hydrator_state(self.session_id, self.prompt, hydration_pending=False)

        # Verify
        mock_load.assert_called_with(self.session_id)
        self.mock_state.open_gate.assert_called_with("hydration")
        self.mock_state.save.assert_called_once()
