"""Reproduction tests for bugs fixed in aops-core/hooks/autocommit_state.py.

P#82 compliance: every framework bug fix must have a failing reproduction test.
"""

import subprocess
import sys
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.autocommit_state import (
    commit_and_push_repo,
    generate_commit_message,
    get_modified_repos,
    is_aca_data_repo,
)


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

    def test_create_task_with_title_param(self):
        """create_task with 'title' instead of 'task_title' should match."""
        msg = generate_commit_message("create_task", {"title": "My task"})
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

    def test_update_task_with_title_param(self):
        """update_task with 'title' instead of 'task_title' should match."""
        msg = generate_commit_message("update_task", {"id": "abc123", "title": "New Title"})
        assert msg == "task: update 'New Title'"

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


class TestCommitAndPushRepo:
    """Regression: commit_and_push_repo must commit before rebase.

    Bug: the function tried to rebase BEFORE committing local changes,
    causing 'cannot pull with rebase: You have unstaged changes' when
    the repo was behind remote and had local modifications.
    """

    def _make_repo_pair(self, tmp_path):
        """Create a local repo with a remote, both with one initial commit."""
        origin = tmp_path / "origin"
        origin.mkdir()
        subprocess.run(["git", "init", "--bare"], cwd=origin, capture_output=True, check=True)

        local = tmp_path / "local"
        subprocess.run(["git", "clone", str(origin), str(local)], capture_output=True, check=True)
        # Initial commit so we have a branch
        (local / "init.txt").write_text("init")
        subprocess.run(["git", "add", "."], cwd=local, capture_output=True, check=True)
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@test", "commit", "-m", "init"],
            cwd=local,
            capture_output=True,
            check=True,
        )
        subprocess.run(["git", "push"], cwd=local, capture_output=True, check=True)

        return local, origin

    def _push_remote_change(self, origin, tmp_path):
        """Push a change to origin from a separate clone."""
        other = tmp_path / "other"
        subprocess.run(["git", "clone", str(origin), str(other)], capture_output=True, check=True)
        (other / "remote.txt").write_text("remote change")
        subprocess.run(["git", "add", "."], cwd=other, capture_output=True, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=test",
                "-c",
                "user.email=test@test",
                "commit",
                "-m",
                "remote change",
            ],
            cwd=other,
            capture_output=True,
            check=True,
        )
        subprocess.run(["git", "push"], cwd=other, capture_output=True, check=True)

    def test_dirty_repo_behind_remote_succeeds(self, tmp_path, monkeypatch):
        """Repo with local changes AND behind remote should commit+sync successfully.

        This is the exact scenario that caused the SYNC CONFLICT error.
        """
        local, origin = self._make_repo_pair(tmp_path)
        self._push_remote_change(origin, tmp_path)

        # Create local dirty state (tracked file modified + new untracked file)
        (local / "init.txt").write_text("local edit")
        (local / "new-task.md").write_text("new task from PKB")

        monkeypatch.setenv("ACA_DATA", str(local))
        monkeypatch.setenv("GIT_AUTHOR_NAME", "test")
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@test")
        monkeypatch.setenv("GIT_COMMITTER_NAME", "test")
        monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@test")

        ok, msg = commit_and_push_repo(local, commit_message="test: auto-commit")

        assert ok, f"commit_and_push_repo failed: {msg}"
        assert "SYNC CONFLICT" not in msg

        # Verify both local and remote changes are present
        assert (local / "remote.txt").exists(), "Remote change not pulled"
        assert (local / "new-task.md").exists(), "Local new file lost"
        assert "local edit" in (local / "init.txt").read_text(), "Local edit lost"

    def test_clean_repo_behind_remote_syncs(self, tmp_path, monkeypatch):
        """Clean repo behind remote should sync without issues."""
        local, origin = self._make_repo_pair(tmp_path)
        self._push_remote_change(origin, tmp_path)

        monkeypatch.setenv("ACA_DATA", str(local))

        # No local changes — commit should fail (nothing to commit), but
        # that's expected. The test verifies no crash.
        ok, msg = commit_and_push_repo(local, commit_message="test: auto-commit")

        # git commit fails with "nothing to commit" — CalledProcessError
        assert not ok  # Expected: commit fails because nothing to commit
