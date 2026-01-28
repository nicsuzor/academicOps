import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks import router


class TestTaskRequiredGateIntegration:
    """Test the Task Required Gate via the Router."""

    @pytest.fixture
    def mock_env(self):
        env = {
            "AOPS_SESSIONS": "/mock/sessions",
            "TASK_GATE_MODE": "block",
            "PYTHONPATH": str(AOPS_CORE_DIR),
        }
        with patch.dict(os.environ, env):
            yield

    @pytest.fixture
    def mock_hook_runner(self):
        """Mock the actual subprocess execution to avoid calling scripts."""
        with patch("hooks.router.run_hook_script") as mock_run:
            yield mock_run

    def test_safe_bash_allowed_without_task(self, mock_env, mock_hook_runner):
        """Safe Bash command (ls) should be allowed even without a task."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "session_id": "sess-1",
        }

        # Determine strict side effect for run_hook_script
        def side_effect(script_path, input_data, **kwargs):
            # Simulate task_required_gate.py allowing
            if script_path.name == "task_required_gate.py":
                return ({}, 0)
            return ({}, 0)

        mock_hook_runner.side_effect = side_effect

        output, code = router.execute_hooks("PreToolUse", input_data)

        assert code == 0
        assert (
            "hookSpecificOutput" not in output
            or output["hookSpecificOutput"].get("permissionDecision") == "allow"
        )

    def test_destructive_bash_blocked_without_task(self, mock_env, mock_hook_runner):
        """Destructive Bash command (rm) should be blocked without a task."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
            "session_id": "sess-1",
        }

        def side_effect(script_path, input_data, **kwargs):
            if script_path.name == "task_required_gate.py":
                # Gate blocks
                return (
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "additionalContext": "Task required for destructive command",
                        }
                    },
                    2,
                )
            return ({}, 0)

        mock_hook_runner.side_effect = side_effect

        output, code = router.execute_hooks("PreToolUse", input_data)

        assert code == 2
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_subprocess_invocation_check(self, mock_env):
        """Verify the router actually tries to run the script (integration check)."""
        # This test actually allows subprocess.run to be called, but we mock it
        # to ensure the path is correct

        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(stdout="{}", stderr="", returncode=0)

            input_data = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "echo check"},
                "session_id": "sess-1",
            }

            router.execute_hooks("PreToolUse", input_data)

            # Verify task_required_gate.py was called
            calls = [c[0][0] for c in mock_sub.call_args_list]
            script_names = [Path(c[1]).name for c in calls if len(c) > 1]  # cmd is list

            assert "task_required_gate.py" in script_names


class TestSafeTempPaths:
    """Test safe temp directory allowlist for writes without task binding."""

    def test_is_safe_temp_path_claude_tmp(self):
        """Writes to ~/.claude/tmp/ should be allowed without task."""
        from hooks.task_required_gate import _is_safe_temp_path

        claude_tmp = str(Path.home() / ".claude" / "tmp" / "test.txt")
        assert _is_safe_temp_path(claude_tmp), "~/.claude/tmp/ should be safe"

    def test_is_safe_temp_path_claude_projects(self):
        """Writes to ~/.claude/projects/ should be allowed without task."""
        from hooks.task_required_gate import _is_safe_temp_path

        claude_projects = str(Path.home() / ".claude" / "projects" / "abc" / "state.json")
        assert _is_safe_temp_path(claude_projects), "~/.claude/projects/ should be safe"

    def test_is_safe_temp_path_gemini_tmp(self):
        """Writes to ~/.gemini/tmp/ should be allowed without task."""
        from hooks.task_required_gate import _is_safe_temp_path

        gemini_tmp = str(Path.home() / ".gemini" / "tmp" / "hash" / "logs.jsonl")
        assert _is_safe_temp_path(gemini_tmp), "~/.gemini/tmp/ should be safe"

    def test_is_safe_temp_path_aops_tmp(self):
        """Writes to ~/.aops/tmp/ should be allowed without task."""
        from hooks.task_required_gate import _is_safe_temp_path

        aops_tmp = str(Path.home() / ".aops" / "tmp" / "hydrator" / "ctx.md")
        assert _is_safe_temp_path(aops_tmp), "~/.aops/tmp/ should be safe"

    def test_is_safe_temp_path_user_file_blocked(self):
        """Writes to regular user files should NOT be safe (require task)."""
        from hooks.task_required_gate import _is_safe_temp_path

        user_file = str(Path.home() / "src" / "project" / "main.py")
        assert not _is_safe_temp_path(user_file), "User files should not be safe"

    def test_is_safe_temp_path_claude_settings_blocked(self):
        """Writes to ~/.claude/settings.json should NOT be safe."""
        from hooks.task_required_gate import _is_safe_temp_path

        settings = str(Path.home() / ".claude" / "settings.json")
        assert not _is_safe_temp_path(settings), "~/.claude/settings.json should not be safe"

    def test_should_require_task_write_to_temp_allowed(self):
        """Write to temp dir should NOT require task."""
        from hooks.task_required_gate import should_require_task

        tool_input = {"file_path": str(Path.home() / ".claude" / "tmp" / "test.md")}
        assert not should_require_task("Write", tool_input), "Write to temp should not require task"

    def test_should_require_task_write_to_user_file_required(self):
        """Write to user file SHOULD require task."""
        from hooks.task_required_gate import should_require_task

        tool_input = {"file_path": "/home/user/src/main.py"}
        assert should_require_task("Write", tool_input), "Write to user file should require task"
