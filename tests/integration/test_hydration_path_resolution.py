import datetime
import os

# Ensure we can import lib and hooks
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Tests are run from root, so we need to add aops-core to path
AOPS_CORE_DIR = Path(__file__).resolve().parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from lib.hydration.builder import build_hydration_instruction
from lib.session_state import SessionState


class TestHydrationPathResolution(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.home_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch("lib.hydration.builder.load_template")
    @patch("lib.hydration.builder.load_glossary")
    @patch("lib.hydration.builder.load_framework_paths")
    @patch("lib.hydration.builder.load_mcp_tools_context")
    @patch("lib.hydration.builder.load_environment_variables_context")
    @patch("lib.hydration.builder.load_project_paths_context")
    @patch("lib.hydration.builder.load_workflows_index")
    @patch("lib.hydration.builder.load_skills_index")
    @patch("lib.hydration.builder.load_scripts_index")
    @patch("lib.hydration.builder.load_project_rules")
    @patch("lib.hydration.builder.get_task_work_state")
    @patch("lib.hydration.builder.get_formatted_relevant_paths")
    @patch("lib.hydration.builder.load_project_context_index")
    @patch("lib.hydration.builder.extract_router_context")
    @patch("lib.session_state.SessionState.load")
    def test_build_hydration_instruction_real_path_claude(
        self,
        mock_load,
        mock_extract,
        mock_proj_idx,
        mock_rel_paths,
        mock_task_state,
        mock_rules,
        mock_scripts,
        mock_skills,
        mock_workflows,
        mock_proj_paths,
        mock_env,
        mock_mcp,
        mock_framework,
        mock_glossary,
        mock_template,
    ):
        """Verify build_hydration_instruction uses real get_gate_file_path for Claude."""
        session_id = "07328230-44d4-414b-9fec-191a6eec0948"
        prompt = "Hello"

        # Setup mocks
        mock_template.side_effect = lambda x: (
            "{temp_path}" if "instruction" in str(x) else "{prompt}"
        )
        mock_state = MagicMock(spec=SessionState)
        mock_state.global_turn_count = 0
        mock_gate = MagicMock()
        mock_gate.metrics = {}
        mock_state.get_gate.return_value = mock_gate
        mock_load.return_value = mock_state

        # Mock Path.home() to use our temp home
        with (
            patch.object(Path, "home", return_value=self.home_dir),
            patch("lib.session_paths.get_claude_project_folder", return_value="-project"),
            patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": ""}, clear=True),
        ):
            # Call build_hydration_instruction
            instruction = build_hydration_instruction(session_id, prompt)

            # Expected path
            date_compact = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
            expected_path = (
                self.home_dir
                / ".claude"
                / "projects"
                / "-project"
                / f"{date_compact}-07328230-hydration.md"
            )

            self.assertTrue(expected_path.exists(), f"Gate file should exist at {expected_path}")
            self.assertIn(str(expected_path), instruction)
            self.assertEqual(mock_gate.metrics["temp_path"], str(expected_path))

    @patch("lib.hydration.builder.load_template")
    @patch("lib.hydration.builder.load_glossary")
    @patch("lib.hydration.builder.load_framework_paths")
    @patch("lib.hydration.builder.load_mcp_tools_context")
    @patch("lib.hydration.builder.load_environment_variables_context")
    @patch("lib.hydration.builder.load_project_paths_context")
    @patch("lib.hydration.builder.load_workflows_index")
    @patch("lib.hydration.builder.load_skills_index")
    @patch("lib.hydration.builder.load_scripts_index")
    @patch("lib.hydration.builder.load_project_rules")
    @patch("lib.hydration.builder.get_task_work_state")
    @patch("lib.hydration.builder.get_formatted_relevant_paths")
    @patch("lib.hydration.builder.load_project_context_index")
    @patch("lib.hydration.builder.extract_router_context")
    @patch("lib.session_state.SessionState.load")
    def test_build_hydration_instruction_real_path_gemini(
        self,
        mock_load,
        mock_extract,
        mock_proj_idx,
        mock_rel_paths,
        mock_task_state,
        mock_rules,
        mock_scripts,
        mock_skills,
        mock_workflows,
        mock_proj_paths,
        mock_env,
        mock_mcp,
        mock_framework,
        mock_glossary,
        mock_template,
    ):
        """Verify build_hydration_instruction uses real get_gate_file_path for Gemini."""
        session_id = "07328230-44d4-414b-9fec-191a6eec0948"
        prompt = "Hello"

        state_dir = self.home_dir / ".gemini" / "tmp" / "abc"
        state_dir.mkdir(parents=True, exist_ok=True)

        # Setup mocks
        mock_template.side_effect = lambda x: (
            "{temp_path}" if "instruction" in str(x) else "{prompt}"
        )
        mock_state = MagicMock(spec=SessionState)
        mock_state.global_turn_count = 0
        mock_gate = MagicMock()
        mock_gate.metrics = {}
        mock_state.get_gate.return_value = mock_gate
        mock_load.return_value = mock_state

        with (
            patch.object(Path, "home", return_value=self.home_dir),
            patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": str(state_dir)}, clear=True),
        ):
            # Call build_hydration_instruction
            instruction = build_hydration_instruction(session_id, prompt)

            # Expected path
            date_compact = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
            expected_path = state_dir / "logs" / f"{date_compact}-07328230-hydration.md"

            self.assertTrue(expected_path.exists(), f"Gate file should exist at {expected_path}")
            self.assertIn(str(expected_path), instruction)
            self.assertEqual(mock_gate.metrics["temp_path"], str(expected_path))


if __name__ == "__main__":
    unittest.main()
