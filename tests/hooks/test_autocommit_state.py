"""Reproduction tests for bugs fixed in aops-core/hooks/autocommit_state.py.

P#82 compliance: every framework bug fix must have a failing reproduction test.
"""

import sys
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.autocommit_state import generate_commit_message, get_modified_repos, is_aca_data_repo


class TestIsAcaDataRepoTildeExpansion:
    """Regression: is_aca_data_repo must handle ACA_DATA paths with ~ (home dir)."""

    def test_tilde_in_aca_data_matches_expanded_path(self, tmp_path, monkeypatch):
        """ACA_DATA=~/brain should match a repo_path of /home/user/brain."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ACA_DATA", "~/brain")
        brain_dir = tmp_path / "brain"
        brain_dir.mkdir()
        assert is_aca_data_repo(brain_dir) is True

    def test_tilde_in_aca_data_no_false_positive(self, tmp_path, monkeypatch):
        """Non-brain dirs should not match when ACA_DATA uses tilde."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ACA_DATA", "~/brain")
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        assert is_aca_data_repo(other_dir) is False

    def test_absolute_aca_data_still_works(self, tmp_path, monkeypatch):
        """Absolute ACA_DATA path should still match correctly."""
        brain_dir = tmp_path / "brain"
        brain_dir.mkdir()
        monkeypatch.setenv("ACA_DATA", str(brain_dir))
        assert is_aca_data_repo(brain_dir) is True


class TestGenerateCommitMessageRegex:
    """Regression: tool name matching must work for non-__ prefixed tool names.

    Old code used endswith("__create_task") which missed:
    - bare tool names (e.g. "create_task" directly)
    - colon-separated MCP names (e.g. "tasks:create_task")
    """

    def test_bare_create_task(self):
        """create_task without __ prefix should match."""
        msg = generate_commit_message("create_task", {"task_title": "My task"})
        assert msg == "task: create 'My task'"

    def test_colon_separated_create_task(self):
        """tasks:create_task should match (colon-separated MCP name)."""
        msg = generate_commit_message("tasks:create_task", {"task_title": "My task"})
        assert msg == "task: create 'My task'"

    def test_double_underscore_create_task_still_works(self):
        """mcp__tasks__create_task should still match after regex change."""
        msg = generate_commit_message("mcp__tasks__create_task", {"task_title": "My task"})
        assert msg == "task: create 'My task'"

    def test_plugin_style_create_task(self):
        """mcp__plugin_aops-core_tasks__create_task should still match."""
        msg = generate_commit_message(
            "mcp__plugin_aops-core_tasks__create_task", {"task_title": "Test"}
        )
        assert msg == "task: create 'Test'"

    def test_complete_task_singular(self):
        """complete_task should match (bare name)."""
        msg = generate_commit_message("complete_task", {"id": "abc123"})
        assert msg == "task: complete abc123"

    def test_complete_tasks_plural(self):
        """complete_tasks should also match."""
        msg = generate_commit_message("complete_tasks", {"ids": ["a", "b", "c"]})
        assert msg == "task: complete 3 tasks"

    def test_no_spurious_match_on_create_task_substring(self):
        """A tool like 'my_create_task_helper' should NOT match (no separator)."""
        msg = generate_commit_message("my_create_task_helper", {})
        assert msg == "sync: auto-commit"


class TestGetModifiedReposRegex:
    """Regression: get_modified_repos must use regex for tool name matching."""

    def test_bare_create_task_triggers_data_repo(self, monkeypatch):
        """Bare create_task tool name should trigger data repo commit."""
        monkeypatch.delenv("ACA_DATA", raising=False)
        modified = get_modified_repos("create_task", {})
        assert "data" in modified

    def test_colon_append_triggers_data_repo(self, monkeypatch):
        """pkb:append should trigger data repo commit."""
        monkeypatch.delenv("ACA_DATA", raising=False)
        modified = get_modified_repos("pkb:append", {})
        assert "data" in modified

    def test_double_underscore_delete_triggers_data_repo(self, monkeypatch):
        """mcp__pkb__delete should still trigger data repo commit."""
        monkeypatch.delenv("ACA_DATA", raising=False)
        modified = get_modified_repos("mcp__pkb__delete", {})
        assert "data" in modified
