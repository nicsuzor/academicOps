import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks import router, gate_registry


class TestUniversalRouter:
    @pytest.fixture
    def mock_env(self):
        with patch.dict(
            os.environ, {"AOPS": "/mock/aops", "AOPS_SESSIONS": "/mock/sessions"}
        ):
            yield

    def test_map_gemini_to_claude_basic(self, mock_env):
        gemini_input = {"tool_name": "read_file", "tool_input": {"path": "test.txt"}}
        event = "BeforeTool"

        claude_input = router.map_gemini_to_claude(event, gemini_input)

        assert claude_input["hook_event_name"] == "PreToolUse"
        assert claude_input["tool_name"] == "read_file"
        assert "session_id" in claude_input
        assert claude_input["session_id"].startswith("gemini-fallback")

    def test_map_claude_to_gemini_permission(self):
        claude_output = {
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "additionalContext": "Access denied",
            },
            "systemMessage": "Blocked",
        }
        event = "BeforeTool"

        gemini_output = router.map_claude_to_gemini(claude_output, event)

        assert gemini_output["decision"] == "deny"
        assert gemini_output["hookSpecificOutput"]["hookEventName"] == "BeforeTool"
        # Check mapping cleaned up permissionDecision from nested dict?
        # The implementation pops it, so it should be gone from hookSpecificOutput
        assert "permissionDecision" not in gemini_output["hookSpecificOutput"]

    @patch("hooks.router.run_hook_script")
    def test_execute_hooks_dispatch(self, mock_run):
        mock_run.return_value = ({}, 0)

        input_data = {"hook_event_name": "SessionStart", "session_id": "test"}
        router.execute_hooks("SessionStart", input_data)

        # Verify calls - updated for actual REGISTRY content
        # SessionStart has 2 hooks: session_env_setup.sh, unified_logger.py
        assert mock_run.call_count == 2
        calls = [c[0][0].name for c in mock_run.call_args_list]
        assert "session_env_setup.sh" in calls
        assert "unified_logger.py" in calls

    @patch("hooks.router.run_hook_script")
    def test_block_behavior(self, mock_run):
        # Simulate a block from the first hook
        mock_run.side_effect = [
            ({"systemMessage": "Blocked"}, 2),  # Block
            ({}, 0),  # Should not run
        ]

        input_data = {"hook_event_name": "PreToolUse"}
        output, code = router.execute_hooks("PreToolUse", input_data)

        assert code == 2
        # Should verify break after first block
        assert mock_run.call_count == 1


class TestGateRegistry:
    def test_hydration_bypass_subagent(self):
        ctx = gate_registry.GateContext("sess1", "PreToolUse", {})

        with patch(
            "hooks.gate_registry._hydration_is_subagent_session", return_value=True
        ):
            result = gate_registry.check_hydration_gate(ctx)
            assert result is None  # Allowed

    def test_hydration_block(self):
        ctx = gate_registry.GateContext(
            "sess1", "PreToolUse", {"tool_name": "read_file"}
        )

        with (
            patch(
                "hooks.gate_registry._hydration_is_subagent_session", return_value=False
            ),
            patch("lib.session_state.is_hydration_pending", return_value=True),
            patch("lib.session_state.clear_hydration_pending") as mock_clear,
            patch("lib.template_loader.load_template", return_value="Please hydrate"),
            patch("lib.hook_utils.make_deny_output") as mock_make_deny,
        ):
            mock_make_deny.return_value = {"decision": "deny"}

            result = gate_registry.check_hydration_gate(ctx)

            assert result == {"decision": "deny"}
            mock_clear.assert_not_called()

    def test_hydration_allow_hydrator(self):
        input_data = {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "prompt-hydrator"},
        }
        ctx = gate_registry.GateContext("sess1", "PreToolUse", input_data)

        with (
            patch(
                "hooks.gate_registry._hydration_is_subagent_session", return_value=False
            ),
            patch("lib.session_state.is_hydration_pending", return_value=True),
            patch("lib.session_state.clear_hydration_pending") as mock_clear,
        ):
            result = gate_registry.check_hydration_gate(ctx)

            assert result is None
            mock_clear.assert_called_once_with("sess1")
