#!/usr/bin/env python3
"""Tests for task_required_gate.py PreToolUse hook.

Tests the task-gated permissions model per specs/permission-model-v1.md.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add hooks directory to path
HOOKS_DIR = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from task_required_gate import (
    is_destructive_bash,
    should_require_task,
    TASK_BINDING_TOOLS,
)


class TestIsDestructiveBash:
    """Test Bash command classification."""

    @pytest.mark.parametrize(
        "command",
        [
            "rm file.txt",
            "rm -rf /tmp/test",
            "mv old.txt new.txt",
            "cp source.txt dest.txt",
            "mkdir new_dir",
            "touch newfile.txt",
            "chmod 755 script.sh",
            "git commit -m 'test'",
            "git push origin main",
            "npm install lodash",
            "pip install requests",
            "uv add pytest",
            "sed -i 's/old/new/g' file.txt",
            "echo 'data' > file.txt",
            "cat file.txt >> output.txt",
        ],
    )
    def test_destructive_commands_detected(self, command: str) -> None:
        """Destructive commands should require task binding."""
        assert is_destructive_bash(command), f"Expected '{command}' to be destructive"

    @pytest.mark.parametrize(
        "command",
        [
            "cat file.txt",
            "head -n 10 file.txt",
            "tail -f logfile.log",
            "ls -la",
            "find . -name '*.py'",
            "grep 'pattern' file.txt",
            "rg 'pattern' .",
            "echo 'hello'",  # No redirect
            "pwd",
            "which python",
            "git status",
            "git diff HEAD",
            "git log --oneline",
            "git show HEAD",
            "git branch -a",
            "npm list",
            "pip list",
        ],
    )
    def test_readonly_commands_allowed(self, command: str) -> None:
        """Read-only commands should not require task binding."""
        assert not is_destructive_bash(command), f"Expected '{command}' to be read-only"


class TestShouldRequireTask:
    """Test tool classification for task requirement."""

    @pytest.mark.parametrize(
        "tool_name,tool_input",
        [
            ("Write", {"file_path": "/tmp/test.txt", "content": "hello"}),
            ("Edit", {"file_path": "/tmp/test.txt", "old_string": "a", "new_string": "b"}),
            ("NotebookEdit", {"notebook_path": "/tmp/test.ipynb", "new_source": "code"}),
            ("Bash", {"command": "rm file.txt"}),
            ("Bash", {"command": "git commit -m 'test'"}),
        ],
    )
    def test_destructive_tools_require_task(self, tool_name: str, tool_input: dict) -> None:
        """Destructive tools should require task binding."""
        assert should_require_task(tool_name, tool_input), f"{tool_name} should require task"

    @pytest.mark.parametrize(
        "tool_name,tool_input",
        [
            ("Read", {"file_path": "/tmp/test.txt"}),
            ("Glob", {"pattern": "**/*.py"}),
            ("Grep", {"pattern": "test", "path": "."}),
            ("Task", {"subagent_type": "Explore", "prompt": "find files"}),
            ("WebFetch", {"url": "https://example.com", "prompt": "summarize"}),
            ("Bash", {"command": "git status"}),
            ("Bash", {"command": "ls -la"}),
        ],
    )
    def test_readonly_tools_dont_require_task(self, tool_name: str, tool_input: dict) -> None:
        """Read-only tools should not require task binding."""
        assert not should_require_task(tool_name, tool_input), f"{tool_name} should not require task"

    @pytest.mark.parametrize("tool_name", sorted(TASK_BINDING_TOOLS))
    def test_task_binding_tools_always_allowed(self, tool_name: str) -> None:
        """Task binding tools should never require task (they establish binding)."""
        assert not should_require_task(tool_name, {}), f"{tool_name} should be allowed (establishes binding)"


class TestHookIntegration:
    """Integration tests for the hook script."""

    @pytest.fixture
    def hook_script(self) -> Path:
        return HOOKS_DIR / "task_required_gate.py"

    def run_hook(
        self,
        hook_script: Path,
        tool_name: str,
        tool_input: dict,
        session_id: str = "test-session",
        env_overrides: dict | None = None,
    ) -> tuple[dict, int]:
        """Run the hook script and return output and exit code."""
        input_data = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "session_id": session_id,
        }

        env = {
            **os.environ,
            "PYTHONPATH": str(HOOKS_DIR.parent),
            "CLAUDE_SESSION_ID": session_id,
            "TASK_GATE_MODE": "block",  # Force block mode for testing
        }
        if env_overrides:
            env.update(env_overrides)

        result = subprocess.run(
            ["python", str(hook_script)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
            cwd=str(HOOKS_DIR),
        )

        output = {}
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass

        return output, result.returncode

    def test_write_without_task_blocked_in_block_mode(self, hook_script: Path) -> None:
        """Write tool should be blocked when no task is bound (block mode)."""
        # Clear any existing session state by using unique session ID
        output, exit_code = self.run_hook(
            hook_script,
            "Write",
            {"file_path": "/tmp/test.txt", "content": "hello"},
            session_id="test-no-task-session",
        )

        assert exit_code == 2, f"Expected exit code 2 (block), got {exit_code}"

    def test_read_without_task_allowed(self, hook_script: Path) -> None:
        """Read tool should be allowed even without task."""
        output, exit_code = self.run_hook(
            hook_script,
            "Read",
            {"file_path": "/tmp/test.txt"},
            session_id="test-read-session",
        )

        assert exit_code == 0, f"Expected exit code 0, got {exit_code}"

    def test_subagent_session_bypasses_gate(self, hook_script: Path) -> None:
        """Subagent sessions should bypass the gate."""
        output, exit_code = self.run_hook(
            hook_script,
            "Write",
            {"file_path": "/tmp/test.txt", "content": "hello"},
            session_id="test-subagent-session",
            env_overrides={"CLAUDE_AGENT_TYPE": "worker"},
        )

        assert exit_code == 0, f"Subagent should bypass, got exit code {exit_code}"

    def test_warn_mode_allows_but_warns(self, hook_script: Path) -> None:
        """Warn mode should allow but output warning."""
        output, exit_code = self.run_hook(
            hook_script,
            "Write",
            {"file_path": "/tmp/test.txt", "content": "hello"},
            session_id="test-warn-session",
            env_overrides={"TASK_GATE_MODE": "warn"},
        )

        assert exit_code == 0, f"Warn mode should allow, got exit code {exit_code}"

    def test_task_binding_tools_always_allowed(self, hook_script: Path) -> None:
        """Task binding tools should always be allowed."""
        output, exit_code = self.run_hook(
            hook_script,
            "mcp__plugin_aops-core_tasks__create_task",
            {"title": "Test task"},
            session_id="test-create-task-session",
        )

        assert exit_code == 0, f"create_task should be allowed, got exit code {exit_code}"
