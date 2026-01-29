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
            # Simulate gates.py allowing
            if script_path.name == "gates.py":
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
            if script_path.name == "gates.py":
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

            # Verify gates.py was called
            calls = [c[0][0] for c in mock_sub.call_args_list]
            script_names = [Path(c[1]).name for c in calls if isinstance(c, (list, tuple)) and len(c) > 1]
            if not script_names:
                 # Handle cases where first arg is the command list
                 script_names = [Path(c[0][1]).name for c in mock_sub.call_args_list if isinstance(c[0][0], list) and len(c[0][0]) > 1]

            assert "gates.py" in script_names


class TestSafeTempPaths:
    """Test safe temp directory allowlist for writes without task binding."""

    def test_is_safe_temp_path_claude_tmp(self):
        """Writes to ~/.claude/tmp/ should be allowed without task."""
        from hooks.gate_registry import _is_safe_temp_path

        claude_tmp = str(Path.home() / ".claude" / "tmp" / "test.txt")
        assert _is_safe_temp_path(claude_tmp), "~/.claude/tmp/ should be safe"

    def test_is_safe_temp_path_claude_projects(self):
        """Writes to ~/.claude/projects/ should be allowed without task."""
        from hooks.gate_registry import _is_safe_temp_path

        claude_projects = str(Path.home() / ".claude" / "projects" / "abc" / "state.json")
        assert _is_safe_temp_path(claude_projects), "~/.claude/projects/ should be safe"

    def test_is_safe_temp_path_gemini_tmp(self):
        """Writes to ~/.gemini/tmp/ should be allowed without task."""
        from hooks.gate_registry import _is_safe_temp_path

        gemini_tmp = str(Path.home() / ".gemini" / "tmp" / "hash" / "logs.jsonl")
        assert _is_safe_temp_path(gemini_tmp), "~/.gemini/tmp/ should be safe"

    def test_is_safe_temp_path_aops_tmp(self):
        """Writes to ~/.aops/tmp/ should be allowed without task."""
        from hooks.gate_registry import _is_safe_temp_path

        aops_tmp = str(Path.home() / ".aops" / "tmp" / "hydrator" / "ctx.md")
        assert _is_safe_temp_path(aops_tmp), "~/.aops/tmp/ should be safe"

    def test_is_safe_temp_path_user_file_blocked(self):
        """Writes to regular user files should NOT be safe (require task)."""
        from hooks.gate_registry import _is_safe_temp_path

        user_file = str(Path.home() / "src" / "project" / "main.py")
        assert not _is_safe_temp_path(user_file), "User files should not be safe"

    def test_is_safe_temp_path_claude_settings_blocked(self):
        """Writes to ~/.claude/settings.json should NOT be safe."""
        from hooks.gate_registry import _is_safe_temp_path

        settings = str(Path.home() / ".claude" / "settings.json")
        assert not _is_safe_temp_path(settings), "~/.claude/settings.json should not be safe"

    def test_should_require_task_write_to_temp_allowed(self):
        """Write to temp dir should NOT require task."""
        from hooks.gate_registry import _should_require_task

        tool_input = {"file_path": str(Path.home() / ".claude" / "tmp" / "test.md")}
        assert not _should_require_task("Write", tool_input), "Write to temp should not require task"

    def test_should_require_task_write_to_user_file_required(self):
        """Write to user file SHOULD require task."""
        from hooks.gate_registry import _should_require_task

        tool_input = {"file_path": "/home/user/src/main.py"}
        assert _should_require_task("Write", tool_input), "Write to user file should require task"


class TestGateRegistry:
    """Test the actual gate logic in gate_registry.py."""

    @pytest.fixture
    def gate_context_factory(self):
        from hooks.gate_registry import GateContext

        def _make_context(tool_name, tool_input, session_id="sess-1", event_name="PreToolUse"):
            return GateContext(
                session_id=session_id,
                event_name=event_name,
                input_data={
                    "hook_event_name": event_name,
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "session_id": session_id,
                },
            )

        return _make_context

    def test_check_task_required_gate_blocked(self, gate_context_factory):
        """Task required gate should block destructive commands when not bound."""
        from hooks.gate_registry import check_task_required_gate

        ctx = gate_context_factory("Bash", {"command": "rm -rf /"})

        with patch("lib.session_state.load_session_state", return_value={}):
            with patch("lib.session_state.check_all_gates", return_value={
                "task_bound": False,
                "plan_mode_invoked": False,
                "critic_invoked": False,
            }):
                with patch("os.environ", {"TASK_GATE_MODE": "block"}):
                    result = check_task_required_gate(ctx)

        assert result is not None
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_check_task_required_gate_allowed_when_bound(self, gate_context_factory):
        """Task required gate should allow destructive commands when bound."""
        from hooks.gate_registry import check_task_required_gate

        ctx = gate_context_factory("Bash", {"command": "rm -rf /"})

        with patch("lib.session_state.load_session_state", return_value={}):
            with patch("lib.session_state.check_all_gates", return_value={
                "task_bound": True,
                "plan_mode_invoked": True,
                "critic_invoked": True,
            }):
                result = check_task_required_gate(ctx)

        assert result is None

    def test_check_task_required_gate_warn_mode(self, gate_context_factory):
        """Task required gate should warn but allow in warn mode."""
        from hooks.gate_registry import check_task_required_gate

        ctx = gate_context_factory("Bash", {"command": "rm -rf /"})

        with patch("lib.session_state.load_session_state", return_value={}):
            with patch("lib.session_state.check_all_gates", return_value={
                "task_bound": False,
                "plan_mode_invoked": False,
                "critic_invoked": False,
            }):
                with patch("os.environ", {"TASK_GATE_MODE": "warn"}):
                    result = check_task_required_gate(ctx)

        assert result is not None
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert "warn-only" in result["hookSpecificOutput"]["additionalContext"]



