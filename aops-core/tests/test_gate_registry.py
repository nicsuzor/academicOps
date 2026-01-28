"""Unit tests for gate_registry consolidated gate functions.

Tests the helper functions and gate check functions ported from:
- task_required_gate.py
- overdue_enforcement.py
- handover_gate.py
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from hooks.gate_registry import (
    _is_safe_temp_path,
    _is_destructive_bash,
    _should_require_task,
    _is_handover_skill_invocation,
    SAFE_TEMP_PREFIXES,
    TASK_BINDING_TOOLS,
    MUTATING_TOOLS,
)


class TestIsSafeTempPath:
    """Tests for _is_safe_temp_path helper."""

    def test_none_path_returns_false(self):
        assert _is_safe_temp_path(None) is False

    def test_empty_path_returns_false(self):
        assert _is_safe_temp_path("") is False

    def test_claude_tmp_path_is_safe(self):
        path = str(Path.home() / ".claude" / "tmp" / "test.txt")
        assert _is_safe_temp_path(path) is True

    def test_claude_projects_path_is_safe(self):
        path = str(Path.home() / ".claude" / "projects" / "test" / "file.txt")
        assert _is_safe_temp_path(path) is True

    def test_gemini_tmp_path_is_safe(self):
        path = str(Path.home() / ".gemini" / "tmp" / "test.txt")
        assert _is_safe_temp_path(path) is True

    def test_aops_tmp_path_is_safe(self):
        path = str(Path.home() / ".aops" / "tmp" / "test.txt")
        assert _is_safe_temp_path(path) is True

    def test_user_project_path_is_not_safe(self):
        path = "/home/user/project/src/main.py"
        assert _is_safe_temp_path(path) is False

    def test_system_tmp_path_is_not_safe(self):
        # /tmp is NOT in safe prefixes - only framework-controlled dirs
        path = "/tmp/random_file.txt"
        assert _is_safe_temp_path(path) is False


class TestIsDestructiveBash:
    """Tests for _is_destructive_bash helper."""

    def test_rm_is_destructive(self):
        assert _is_destructive_bash("rm file.txt") is True
        assert _is_destructive_bash("rm -rf /path") is True

    def test_mv_is_destructive(self):
        assert _is_destructive_bash("mv old.txt new.txt") is True

    def test_cp_is_destructive(self):
        assert _is_destructive_bash("cp src.txt dst.txt") is True

    def test_mkdir_is_destructive(self):
        assert _is_destructive_bash("mkdir new_dir") is True

    def test_git_commit_is_destructive(self):
        assert _is_destructive_bash("git commit -m 'msg'") is True

    def test_git_push_is_destructive(self):
        assert _is_destructive_bash("git push origin main") is True

    def test_redirect_is_destructive(self):
        assert _is_destructive_bash("echo hello > file.txt") is True
        assert _is_destructive_bash("cat input >> output.txt") is True

    def test_ls_is_safe(self):
        assert _is_destructive_bash("ls -la") is False

    def test_cat_is_safe(self):
        assert _is_destructive_bash("cat file.txt") is False

    def test_git_status_is_safe(self):
        assert _is_destructive_bash("git status") is False

    def test_git_diff_is_safe(self):
        assert _is_destructive_bash("git diff HEAD") is False

    def test_git_log_is_safe(self):
        assert _is_destructive_bash("git log --oneline") is False

    def test_grep_is_safe(self):
        assert _is_destructive_bash("grep pattern file.txt") is False

    def test_find_is_safe(self):
        assert _is_destructive_bash("find . -name '*.py'") is False

    def test_pip_list_is_safe(self):
        assert _is_destructive_bash("pip list") is False

    def test_pip_install_is_destructive(self):
        assert _is_destructive_bash("pip install package") is True

    def test_npm_list_is_safe(self):
        assert _is_destructive_bash("npm list") is False

    def test_npm_install_is_destructive(self):
        assert _is_destructive_bash("npm install package") is True


class TestShouldRequireTask:
    """Tests for _should_require_task helper."""

    def test_task_binding_tools_dont_require_task(self):
        for tool in TASK_BINDING_TOOLS:
            assert _should_require_task(tool, {}) is False

    def test_write_requires_task(self):
        assert _should_require_task("Write", {"file_path": "/home/user/file.txt"}) is True

    def test_edit_requires_task(self):
        assert _should_require_task("Edit", {"file_path": "/home/user/file.txt"}) is True

    def test_write_to_safe_temp_doesnt_require_task(self):
        safe_path = str(Path.home() / ".claude" / "tmp" / "test.txt")
        assert _should_require_task("Write", {"file_path": safe_path}) is False

    def test_bash_with_safe_command_doesnt_require_task(self):
        assert _should_require_task("Bash", {"command": "ls -la"}) is False
        assert _should_require_task("Bash", {"command": "git status"}) is False

    def test_bash_with_destructive_command_requires_task(self):
        assert _should_require_task("Bash", {"command": "rm file.txt"}) is True
        assert _should_require_task("Bash", {"command": "git commit -m 'x'"}) is True

    def test_read_doesnt_require_task(self):
        assert _should_require_task("Read", {"file_path": "/any/path"}) is False

    def test_glob_doesnt_require_task(self):
        assert _should_require_task("Glob", {"pattern": "*.py"}) is False

    def test_grep_doesnt_require_task(self):
        assert _should_require_task("Grep", {"pattern": "test"}) is False

    def test_task_tool_doesnt_require_task(self):
        assert _should_require_task("Task", {"subagent_type": "explore"}) is False


class TestIsHandoverSkillInvocation:
    """Tests for _is_handover_skill_invocation helper."""

    def test_skill_tool_with_handover(self):
        assert _is_handover_skill_invocation("Skill", {"skill": "handover"}) is True
        assert _is_handover_skill_invocation("Skill", {"skill": "aops-core:handover"}) is True

    def test_skill_tool_with_other_skill(self):
        assert _is_handover_skill_invocation("Skill", {"skill": "commit"}) is False
        assert _is_handover_skill_invocation("Skill", {"skill": "pdf"}) is False

    def test_activate_skill_with_handover(self):
        assert _is_handover_skill_invocation("activate_skill", {"name": "handover"}) is True
        assert _is_handover_skill_invocation("activate_skill", {"name": "aops-core:handover"}) is True

    def test_activate_skill_with_other(self):
        assert _is_handover_skill_invocation("activate_skill", {"name": "other"}) is False

    def test_delegate_to_agent_with_handover(self):
        assert _is_handover_skill_invocation("delegate_to_agent", {"agent_name": "handover"}) is True

    def test_direct_handover_tool(self):
        assert _is_handover_skill_invocation("handover", {}) is True

    def test_unrelated_tool(self):
        assert _is_handover_skill_invocation("Read", {"file_path": "/test"}) is False
        assert _is_handover_skill_invocation("Write", {"file_path": "/test"}) is False


class TestMutatingToolsSet:
    """Tests for MUTATING_TOOLS constant."""

    def test_edit_in_mutating_tools(self):
        assert "Edit" in MUTATING_TOOLS

    def test_write_in_mutating_tools(self):
        assert "Write" in MUTATING_TOOLS

    def test_bash_in_mutating_tools(self):
        assert "Bash" in MUTATING_TOOLS

    def test_read_not_in_mutating_tools(self):
        assert "Read" not in MUTATING_TOOLS

    def test_glob_not_in_mutating_tools(self):
        assert "Glob" not in MUTATING_TOOLS
