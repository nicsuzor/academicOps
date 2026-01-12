"""
Tests for hydration gate PreToolUse hook.

Tests the mechanical trigger that blocks all tools until prompt-hydrator is invoked.
"""

import json
import subprocess
import uuid
from pathlib import Path

import pytest

from lib.session_state import (
    clear_hydration_pending,
    is_hydration_pending,
    save_hydrator_state,
)


def make_session_id() -> str:
    """Generate a test session ID."""
    return str(uuid.uuid4())


@pytest.fixture
def temp_state_dir(monkeypatch, tmp_path):
    """Use temp directory for session state."""
    state_dir = tmp_path / "claude-session"
    state_dir.mkdir()
    monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
    return state_dir


@pytest.fixture
def test_session_id():
    """Provide a test session_id for state file keying."""
    return make_session_id()


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

    def test_is_hydration_pending_no_state(self, temp_state_dir, test_session_id):
        """No state file means not pending."""
        assert is_hydration_pending(test_session_id) is False

    def test_is_hydration_pending_true(self, temp_state_dir, test_session_id):
        """hydration_pending=True in state means pending."""
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(test_session_id, state)
        assert is_hydration_pending(test_session_id) is True

    def test_is_hydration_pending_false(self, temp_state_dir, test_session_id):
        """hydration_pending=False in state means not pending."""
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": False,
        }
        save_hydrator_state(test_session_id, state)
        assert is_hydration_pending(test_session_id) is False

    def test_clear_hydration_pending(self, temp_state_dir, test_session_id):
        """clear_hydration_pending sets flag to False."""
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(test_session_id, state)
        assert is_hydration_pending(test_session_id) is True

        clear_hydration_pending(test_session_id)
        assert is_hydration_pending(test_session_id) is False


class TestHydrationGateHook:
    """Test the PreToolUse hook behavior."""

    def test_allow_when_not_pending(self, temp_state_dir, test_session_id):
        """Allow all tools when hydration is not pending."""
        # No state file = not pending
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file"},
            "session_id": test_session_id,
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 0
        assert stderr == ""

    def test_block_when_pending(self, temp_state_dir, test_session_id):
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
        save_hydrator_state(test_session_id, state)

        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file"},
            "session_id": test_session_id,
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 2
        assert "HYDRATION GATE" in stderr
        assert "prompt-hydrator" in stderr

    def test_allow_hydrator_task_and_clear(self, temp_state_dir, test_session_id):
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
        save_hydrator_state(test_session_id, state)

        input_data = {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "prompt-hydrator",
                "description": "Hydrate: test task",
                "prompt": "Read /tmp/claude-hydrator/test.md",
            },
            "session_id": test_session_id,
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 0
        assert stderr == ""

        # Verify flag was cleared
        assert is_hydration_pending(test_session_id) is False

    def test_block_non_hydrator_task(self, temp_state_dir, test_session_id):
        """Block Task with different subagent_type when pending."""
        state = {
            "last_hydration_ts": 0,
            "declared_workflow": {},
            "active_skill": "",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(test_session_id, state)

        input_data = {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "Explore",
                "description": "Explore codebase",
                "prompt": "Find files",
            },
            "session_id": test_session_id,
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

    def test_fail_open_on_missing_session_id(self, temp_state_dir):
        """Fail open when session_id is missing."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file"},
            # No session_id
            "_state_dir": str(temp_state_dir),
        }
        stdout, stderr, code = run_hook(input_data)
        assert code == 0  # Fail open
