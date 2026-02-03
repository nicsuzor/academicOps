import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(AOPS_CORE_DIR / "aops-core"))

from hooks import gate_registry  # noqa: E402

class TestHydrationDetection(unittest.TestCase):

    def setUp(self):
        self.input_data = {
            "session_id": "test-session",
            "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session.json"
        }
        self.temp_dir = Path("/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/hydrator")

    @patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
    def test_gemini_read_file_detection(self, mock_get_temp_dir):
        # Setup mock to return the expected temp dir
        mock_get_temp_dir.return_value = self.temp_dir

        # Case 1: Matching path
        tool_input = {
            "file_path": str(self.temp_dir / "hydrate_xbq_whk1.md")
        }
        is_detected = gate_registry._hydration_is_gemini_hydration_attempt(
            "read_file", tool_input, self.input_data
        )
        self.assertTrue(is_detected, "Should detect read_file on hydration temp file")

        # Case 2: Non-matching path
        tool_input = {
            "file_path": "/some/other/path/hydrate_xbq_whk1.md"
        }
        is_detected = gate_registry._hydration_is_gemini_hydration_attempt(
            "read_file", tool_input, self.input_data
        )
        self.assertFalse(is_detected, "Should NOT detect read_file on other paths")

    @patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
    def test_gemini_run_shell_detection(self, mock_get_temp_dir):
        mock_get_temp_dir.return_value = self.temp_dir

        # Case 1: Matching command
        tool_input = {
            "command": f"cat {self.temp_dir}/hydrate_xbq_whk1.md"
        }
        is_detected = gate_registry._hydration_is_gemini_hydration_attempt(
            "run_shell_command", tool_input, self.input_data
        )
        self.assertTrue(is_detected, "Should detect run_shell_command on hydration temp file")

        # Case 2: Non-matching command
        tool_input = {
            "command": "ls -la"
        }
        is_detected = gate_registry._hydration_is_gemini_hydration_attempt(
            "run_shell_command", tool_input, self.input_data
        )
        self.assertFalse(is_detected, "Should NOT detect unrelated commands")

    @patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
    def test_exact_path_match(self, mock_get_temp_dir):
         # Verify exact path matching
        mock_get_temp_dir.return_value = self.temp_dir

        # Note: In the actual run, tool_input might be passed differently or context might differ
        # But let's check if there's any path normalization issue
        
        # Simulating exact path from the prompt
        path = "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/hydrator/hydrate_xbq_whk1.md"
        tool_input = {"file_path": path}
        
        is_detected = gate_registry._hydration_is_gemini_hydration_attempt(
            "read_file", tool_input, self.input_data
        )
        self.assertTrue(is_detected, "Exact path match should work")

    @patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
    @patch("hooks.gate_registry.session_state")
    def test_post_hydration_trigger_gemini(self, mock_session_state, mock_get_temp_dir):
        # Verify that post_hydration_trigger correctly identifies Gemini hydration
        mock_get_temp_dir.return_value = self.temp_dir

        # Simulating Gemini read_file on hydration path
        path = str(self.temp_dir / "hydrate_xbq_whk1.md")
        tool_input = {"file_path": path}

        ctx = gate_registry.GateContext(
            session_id="test-session",
            event_name="PostToolUse",
            input_data={
                **self.input_data,
                "tool_name": "read_file",
                "tool_input": tool_input
            }
        )

        result = gate_registry.post_hydration_trigger(ctx)

        # Assertions
        mock_session_state.update_hydration_metrics.assert_called_with("test-session", turns_since_hydration=0)
        mock_session_state.clear_hydration_pending.assert_called_with("test-session")
        self.assertIsNotNone(result, "Should return GateResult on hydration detection")
        self.assertEqual(result.verdict, gate_registry.GateVerdict.ALLOW)
        # Hydration complete sets system_message, not context_injection
        self.assertIn("hydration", result.system_message.lower())

    @patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
    @patch("hooks.gate_registry.session_state")
    def test_post_hydration_trigger_gemini_negative(self, mock_session_state, mock_get_temp_dir):
        # Verify that it doesn't trigger for random files
        mock_get_temp_dir.return_value = self.temp_dir
        
        tool_input = {"file_path": "/some/other/file.md"}
        
        ctx = gate_registry.GateContext(
            session_id="test-session",
            event_name="PostToolUse",
            input_data={
                **self.input_data,
                "tool_name": "read_file",
                "tool_input": tool_input
            }
        )
        
        result = gate_registry.post_hydration_trigger(ctx)
        
        # Assertions
        mock_session_state.update_hydration_metrics.assert_not_called()
        self.assertIsNone(result, "Should return None for non-hydration files")

if __name__ == "__main__":
    unittest.main()
