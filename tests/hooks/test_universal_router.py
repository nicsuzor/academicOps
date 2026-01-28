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

    @pytest.fixture
    def mock_session_file(self):
        # Mock Path for session file operations
        with patch("hooks.router.get_session_file_path") as mock_get:
            mock_path = MagicMock(spec=Path)
            mock_get.return_value = mock_path
            yield mock_path

    def test_map_gemini_to_claude_basic(self, mock_env):
        gemini_input = {"tool_name": "read_file", "tool_input": {"path": "test.txt"}}
        event = "BeforeTool"

        with patch(
            "hooks.router.get_session_data", return_value={"session_id": "gemini-test"}
        ):
            claude_input = router.map_gemini_to_claude(event, gemini_input)

        assert claude_input["hook_event_name"] == "PreToolUse"
        assert claude_input["tool_name"] == "read_file"
        assert claude_input["session_id"] == "gemini-test"

    def test_session_start_captures_temp_root(self, mock_env, mock_session_file):
        # Setup: SessionStart with transcript_path
        transcript_path = "/home/user/.gemini/tmp/hash123/chats/session-1.json"
        gemini_input = {"transcript_path": transcript_path}
        mock_session_file.exists.return_value = False

        # Action
        with patch("hooks.router.persist_session_data") as mock_persist:
            router.map_gemini_to_claude("SessionStart", gemini_input)

            # Assert
            args = mock_persist.call_args[0][0]
            assert "session_id" in args
            assert args["temp_root"] == "/home/user/.gemini/tmp/hash123"

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
        assert "permissionDecision" not in gemini_output["hookSpecificOutput"]

    @patch("hooks.router.run_hook_script")
    def test_execute_hooks_dispatch(self, mock_run):
        mock_run.return_value = ({}, 0)

        input_data = {"hook_event_name": "SessionStart", "session_id": "test"}
        router.execute_hooks("SessionStart", input_data)

        assert mock_run.call_count == 2
        calls = [c[0][0].name for c in mock_run.call_args_list]
        assert "session_env_setup.sh" in calls
        assert "unified_logger.py" in calls

    @patch("hooks.router.run_hook_script")
    def test_block_behavior(self, mock_run):
        mock_run.side_effect = [
            ({"systemMessage": "Blocked"}, 2),
            ({}, 0),
        ]

        input_data = {"hook_event_name": "PreToolUse"}
        output, code = router.execute_hooks("PreToolUse", input_data)

        assert code == 2
        assert mock_run.call_count == 1

    def test_run_hook_injects_env(self, mock_env):
        # Setup: input_data has temp_root (as passed from SessionStart)
        with (
            patch("hooks.router.validate_temp_path", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="{}", stderr="", returncode=0)

            # We call run_hook_script directly with temp_root in input_data
            script_path = Path("hooks/foo.py")
            with patch.object(Path, "exists", return_value=True):
                router.run_hook_script(script_path, {"temp_root": "/custom/temp"})

            # Assert env var injected
            call_env = mock_run.call_args[1]["env"]
            assert call_env["AOPS_SESSION_STATE_DIR"] == "/custom/temp"

    def test_gemini_acceptance_session_start(self, mock_env, capsys, tmp_path):
        """Acceptance test for Gemini SessionStart output.
        
        Verifies:
        1. Output contains hook_event and source fields.
        2. State file is created in the temp root (derived from transcript_path).
        """
        # Create directory structure for Gemini session
        session_root = tmp_path / "gemini_root_123"
        session_root.mkdir()
        chats_dir = session_root / "chats"
        chats_dir.mkdir()
        
        with patch.dict(os.environ, {}):
            gemini_input = {
                "hook_event": "SessionStart",
                "transcript_path": str(chats_dir / "session-1.json"),
                "cwd": "/home/nic/src/academicOps",
            }
            
            mock_stdin = MagicMock()
            mock_stdin.read.return_value = json.dumps(gemini_input)
            mock_stdin.isatty.return_value = False
            
            with patch("sys.stdin", mock_stdin):
                with patch("sys.argv", ["router.py", "SessionStart"]):
                    with pytest.raises(SystemExit) as exc:
                        router.main()
                    
                    assert exc.value.code == 0
                    captured = capsys.readouterr()
                    output = json.loads(captured.out.strip())
                    
                    # 1. Output Structure
                    assert output["hook_event"] == "SessionStart"
                    assert output["source"] == "startup"
                    
                    # 2. Path Verification
                    system_msg = output.get("systemMessage", "")
                    import re
                    match = re.search(r"State file: (.*)", system_msg)
                    assert match, "State file path not found in systemMessage"
                    
                    state_file_path = Path(match.group(1))
                    
                    # Crucial: The state file should be in the session_root (temp root), NOT fallback
                    # router.py logic: chats/session.json -> temp_root = parent of chats
                    assert state_file_path.parent == session_root, \
                        f"State file {state_file_path} not in session root {session_root}"
                    
                    # Verify file exists
                    assert state_file_path.exists(), "State file was not created"

    def test_claude_acceptance_session_start(self, mock_env, capsys, tmp_path):
        """Acceptance test for Claude SessionStart output."""
        cwd = "/home/nic/src/academicOps"
        # Expected path: ~/.claude/projects/-home-nic-src-academicOps/
        expected_dir = str(Path.home() / ".claude" / "projects" / "-home-nic-src-academicOps")

        with patch.dict(os.environ, {}):
            claude_input = {
                "hook_event_name": "SessionStart",
                "session_id": "test-session-claude",
                "cwd": cwd,
            }

            mock_stdin = MagicMock()
            mock_stdin.read.return_value = json.dumps(claude_input)
            mock_stdin.isatty.return_value = False

            with patch("sys.stdin", mock_stdin):
                # Claude mode: no args
                with patch("sys.argv", ["router.py"]):
                    with pytest.raises(SystemExit) as exc:
                        router.main()

                    assert exc.value.code == 0
                    captured = capsys.readouterr()
                    output = json.loads(captured.out.strip())

                    # Verify Claude output structure (NO hook_event/source top level)
                    assert "hook_event" not in output
                    assert "source" not in output

                    # Verify Path Correctness in Output
                    hso = output.get("hookSpecificOutput", {})
                    context = hso.get("additionalContext", "")

                    # Should use ~/.claude/projects/<encoded-cwd>/
                    assert expected_dir in context


class TestGateRegistry:
    def test_hydration_bypass_subagent(self):
        ctx = gate_registry.GateContext("sess1", "PreToolUse", {})

        with patch(
            "hooks.gate_registry._hydration_is_subagent_session", return_value=True
        ):
            result = gate_registry.check_hydration_gate(ctx)
            assert result is None  # Allowed

    def test_hydration_block(self):
        # Use Bash (not in safe tools list) to test blocking behavior
        # read_file is now in HYDRATION_SAFE_TOOLS and won't be blocked
        ctx = gate_registry.GateContext(
            "sess1", "PreToolUse", {"tool_name": "Bash"}
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
