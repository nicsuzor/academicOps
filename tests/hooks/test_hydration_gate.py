"""
Tests for hydration gate PreToolUse hook.

Tests the mechanical trigger that blocks all tools until prompt-hydrator is invoked.
"""

import json
import subprocess
from pathlib import Path

import pytest

from lib.session_state import (
    clear_hydration_pending,
    is_hydration_pending,
    save_hydrator_state,
)


@pytest.fixture
def temp_state_dir(monkeypatch, tmp_path):
    """Use temp directory for session state."""
    state_dir = tmp_path / "claude-session"
    state_dir.mkdir()
    monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
    return state_dir


@pytest.fixture
def test_cwd(tmp_path):
    """Provide a test cwd for state file keying."""
    return str(tmp_path / "test-project")


def run_hook(input_data: dict) -> tuple[str, str, int]:
    """Run hydration_gate.py hook and return stdout, stderr, exit code."""
    hook_path = Path(__file__).parent.parent.parent / "hooks" / "hydration_gate.py"
    result = subprocess.run(
        ["python", str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        cwd=hook_path.parent,
        env={
            "PYTHONPATH": str(hook_path.parent.parent),
            "CLAUDE_SESSION_STATE_DIR": input_data.get(
                "_state_dir", "/tmp/claude-session"
            ),
        },
    )
    return result.stdout, result.stderr, result.returncode


class TestHydrationPendingFlag:
    """Test hydration_pending flag management."""

    def test_is_hydration_pending_no_state(self, temp_state_dir, test_cwd):
        """No state file means not pending."""
        assert is_hydration_pending(test_cwd) is False

    def test_is_hydration_pending_true(self, temp_state_dir, test_cwd):
        """hydration_pending=True in state means pending."""
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(test_cwd, state)
        assert is_hydration_pending(test_cwd) is True

    def test_is_hydration_pending_false(self, temp_state_dir, test_cwd):
        """hydration_pending=False in state means not pending."""
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": False,
        }
        save_hydrator_state(test_cwd, state)
        assert is_hydration_pending(test_cwd) is False

    def test_clear_hydration_pending(self, temp_state_dir, test_cwd):
        """clear_hydration_pending sets flag to False."""
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(test_cwd, state)
        assert is_hydration_pending(test_cwd) is True

        clear_hydration_pending(test_cwd)
        assert is_hydration_pending(test_cwd) is False


class TestHydrationGateHook:
    """Test the PreToolUse hook behavior."""

    def test_allow_when_not_pending(self, temp_state_dir, test_cwd):
        """Allow all tools when hydration is not pending."""
        # No state file = not pending
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file"},
            "cwd": test_cwd,
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 0
        assert stderr == ""

    def test_block_when_pending(self, temp_state_dir, test_cwd):
        """Block tools when hydration is pending."""
        # Set hydration_pending=True
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(test_cwd, state)

        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file"},
            "cwd": test_cwd,
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 2
        assert "HYDRATION GATE" in stderr
        assert "prompt-hydrator" in stderr

    def test_allow_hydrator_task_and_clear(self, temp_state_dir, test_cwd):
        """Allow Task(prompt-hydrator) and clear the pending flag."""
        # Set hydration_pending=True
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(test_cwd, state)

        input_data = {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "prompt-hydrator",
                "description": "Hydrate: test task",
                "prompt": "Read /tmp/claude-hydrator/test.md",
            },
            "cwd": test_cwd,
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 0
        assert stderr == ""

        # Verify flag was cleared
        assert is_hydration_pending(test_cwd) is False

    def test_block_non_hydrator_task(self, temp_state_dir, test_cwd):
        """Block Task with different subagent_type when pending."""
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(test_cwd, state)

        input_data = {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "Explore",
                "description": "Explore codebase",
                "prompt": "Find files",
            },
            "cwd": test_cwd,
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 2
        assert "HYDRATION GATE" in stderr

    def test_fail_open_on_parse_error(self, temp_state_dir):
        """Fail open (allow) on JSON parse error."""
        hook_path = Path(__file__).parent.parent.parent / "hooks" / "hydration_gate.py"
        result = subprocess.run(
            ["python", str(hook_path)],
            input="not valid json",
            capture_output=True,
            text=True,
            cwd=hook_path.parent,
            env={
                "PYTHONPATH": str(hook_path.parent.parent),
                "CLAUDE_SESSION_STATE_DIR": str(temp_state_dir),
            },
        )
        assert result.returncode == 0  # Fail open

    def test_fail_open_on_missing_cwd(self, temp_state_dir):
        """Fail open when cwd is missing."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file"},
            # No cwd
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 0  # Fail open
