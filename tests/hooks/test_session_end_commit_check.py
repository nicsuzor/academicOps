#!/usr/bin/env python3
"""Tests for session_end_commit_check.py Stop hook.

Tests the session-end enforcement hook that detects uncommitted work
after Framework Reflection or passing tests, and enforces auto-commit.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add hooks directory to path
HOOKS_DIR = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from hooks.internal_models import GitPushStatus, GitStatus
from session_end_commit_check import (
    check_uncommitted_work,
    get_git_push_status,
    get_git_status,
    has_framework_reflection,
    has_test_success,
)


class TestHasFrameworkReflection:
    """Test Framework Reflection detection."""

    def test_detects_reflection_section(self) -> None:
        """Should detect ## Framework Reflection header with proper format."""
        messages = [
            """## Framework Reflection

**Prompts**: Test prompt

**Guidance Received**: None

**Followed**: Yes

**Outcome**: Success

**Accomplishments**:
- Work completed

**Friction Points**: None

**Root Cause**: N/A

**Proposed Changes**: None

**Next Step**: Continue"""
        ]
        assert has_framework_reflection(messages) is True

    def test_detects_framework_reflection_variant(self) -> None:
        """Should detect Framework Reflection with different formatting."""
        messages = [
            """Work complete.

## Framework Reflection

**Prompts**: Task completion

**Guidance Received**: None

**Followed**: Yes

**Outcome**: Success

**Accomplishments**:
- Task done

**Friction Points**: None

**Root Cause**: N/A

**Proposed Changes**: None

**Next Step**: None"""
        ]
        assert has_framework_reflection(messages) is True

    def test_no_reflection_in_messages(self) -> None:
        """Should return False if no reflection found."""
        messages = [
            "Here is my work",
            "Task completed successfully",
            "All tests passed",
        ]
        assert has_framework_reflection(messages) is False

    def test_empty_messages(self) -> None:
        """Should handle empty message list."""
        assert has_framework_reflection([]) is False


class TestHasTestSuccess:
    """Test test success pattern detection."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "all tests passed",
            "All tests passing",
            "tests passed successfully",
            "PASSED",
            "test run successful",
            "100% success",
            "passed all tests",
        ],
    )
    def test_detects_test_success_patterns(self, pattern: str) -> None:
        """Should detect various test success patterns."""
        messages = [f"Test results: {pattern}"]
        assert has_test_success(messages) is True

    def test_case_insensitive_detection(self) -> None:
        """Should detect patterns case-insensitively."""
        messages = ["ALL TESTS PASSED"]
        assert has_test_success(messages) is True

    def test_no_test_success_patterns(self) -> None:
        """Should return False if no success patterns found."""
        messages = [
            "Testing in progress",
            "test file not found",
            "ERROR in tests",
        ]
        assert has_test_success(messages) is False

    def test_empty_messages(self) -> None:
        """Should handle empty message list."""
        assert has_test_success([]) is False


class TestGetGitStatus:
    """Test git status checking."""

    def test_no_changes(self) -> None:
        """Should detect clean working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo
            subprocess.run(
                ["git", "init"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Create and commit a file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            subprocess.run(
                ["git", "add", "."],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "initial"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            status = get_git_status(tmpdir)
            assert status.has_changes is False
            assert status.staged_changes is False
            assert status.unstaged_changes is False

    def test_staged_changes(self) -> None:
        """Should detect staged changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup git repo
            subprocess.run(
                ["git", "init"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Create and commit initial file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("initial")
            subprocess.run(
                ["git", "add", "."],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "initial"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Modify and stage the file
            test_file.write_text("modified")
            subprocess.run(
                ["git", "add", "."],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            status = get_git_status(tmpdir)
            assert status.has_changes is True
            assert status.staged_changes is True

    def test_unstaged_changes(self) -> None:
        """Should detect unstaged changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup git repo
            subprocess.run(
                ["git", "init"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Create and commit initial file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("initial")
            subprocess.run(
                ["git", "add", "."],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "initial"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Modify but don't stage
            test_file.write_text("modified")

            status = get_git_status(tmpdir)
            assert status.has_changes is True
            assert status.unstaged_changes is True

    def test_untracked_files(self) -> None:
        """Should detect untracked files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup git repo
            subprocess.run(
                ["git", "init"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Create untracked file
            test_file = Path(tmpdir) / "new_file.txt"
            test_file.write_text("content")

            status = get_git_status(tmpdir)
            assert status.has_changes is True
            assert status.untracked_files is True

    def test_not_a_git_repo(self) -> None:
        """Should handle non-git directories gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            status = get_git_status(tmpdir)
            assert status.has_changes is False
            assert status.staged_changes is False


class TestGetGitPushStatus:
    """Test git push status checking."""

    def test_no_tracking_branch(self) -> None:
        """Should handle case when branch has no tracking branch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo
            subprocess.run(
                ["git", "init"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Create and commit a file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            subprocess.run(
                ["git", "add", "."],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "initial"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # No remote tracking branch configured yet
            status = get_git_push_status(tmpdir)
            assert status.branch_ahead is False
            assert status.commits_ahead == 0
            assert status.current_branch  # Should have current branch name

    def test_commits_ahead_of_remote(self) -> None:
        """Should detect commits ahead of remote tracking branch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a local repo
            subprocess.run(
                ["git", "init"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Create and commit initial file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("initial")
            subprocess.run(
                ["git", "add", "."],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "initial"],
                cwd=tmpdir,
                capture_output=True,
                check=True,
            )

            # Create a "remote" repo to test against
            with tempfile.TemporaryDirectory() as remote_dir:
                subprocess.run(
                    ["git", "init", "--bare"],
                    cwd=remote_dir,
                    capture_output=True,
                    check=True,
                )

                # Add remote and push initial commit
                subprocess.run(
                    ["git", "remote", "add", "origin", remote_dir],
                    cwd=tmpdir,
                    capture_output=True,
                    check=True,
                )
                # Get current branch name (might be master or main)
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                current_branch = result.stdout.strip()
                subprocess.run(
                    ["git", "push", "-u", "origin", current_branch],
                    cwd=tmpdir,
                    capture_output=True,
                    check=True,
                )

                # Make a new local commit
                test_file.write_text("updated")
                subprocess.run(
                    ["git", "add", "."],
                    cwd=tmpdir,
                    capture_output=True,
                    check=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", "new commit"],
                    cwd=tmpdir,
                    capture_output=True,
                    check=True,
                )

                # Check push status - should show 1 commit ahead
                status = get_git_push_status(tmpdir)
                assert status.branch_ahead is True
                assert status.commits_ahead == 1


class TestCheckUncommittedWork:
    """Test uncommitted work detection logic."""

    @patch("session_end_commit_check.extract_recent_messages")
    @patch("session_end_commit_check.has_framework_reflection")
    @patch("session_end_commit_check.has_test_success")
    @patch("session_end_commit_check.get_git_status")
    def test_reflection_with_uncommitted_changes(
        self,
        mock_git_status,
        mock_test_success,
        mock_reflection,
        mock_extract,
    ) -> None:
        """Should block if reflection found and uncommitted changes exist."""
        mock_extract.return_value = ["message"]
        mock_reflection.return_value = True
        mock_test_success.return_value = False
        mock_git_status.return_value = GitStatus(
            has_changes=True,
            staged_changes=False,
            unstaged_changes=True,
            untracked_files=False,
            status_output="M file.txt",
        )

        result = check_uncommitted_work("session123", "/tmp/transcript.jsonl")
        assert result.should_block is True
        assert result.has_reflection is True
        assert "uncommitted changes" in result.message.lower()

    @patch("session_end_commit_check.extract_recent_messages")
    @patch("session_end_commit_check.has_framework_reflection")
    @patch("session_end_commit_check.has_test_success")
    @patch("session_end_commit_check.get_git_status")
    def test_test_success_with_uncommitted_changes(
        self,
        mock_git_status,
        mock_test_success,
        mock_reflection,
        mock_extract,
    ) -> None:
        """Should block if tests passed and uncommitted changes exist."""
        mock_extract.return_value = ["message"]
        mock_reflection.return_value = False
        mock_test_success.return_value = True
        mock_git_status.return_value = GitStatus(
            has_changes=True,
            staged_changes=False,
            unstaged_changes=True,
            untracked_files=False,
            status_output="M lib.py",
        )

        result = check_uncommitted_work("session123", "/tmp/transcript.jsonl")
        assert result.should_block is True
        assert result.has_test_success is True

    @patch("session_end_commit_check.extract_recent_messages")
    @patch("session_end_commit_check.has_framework_reflection")
    @patch("session_end_commit_check.has_test_success")
    @patch("session_end_commit_check.get_git_status")
    def test_clean_working_directory(
        self,
        mock_git_status,
        mock_test_success,
        mock_reflection,
        mock_extract,
    ) -> None:
        """Should not block if working directory is clean."""
        mock_extract.return_value = ["message"]
        mock_reflection.return_value = True
        mock_test_success.return_value = True
        mock_git_status.return_value = GitStatus(
            has_changes=False,
            staged_changes=False,
            unstaged_changes=False,
            untracked_files=False,
            status_output="",
        )

        result = check_uncommitted_work("session123", "/tmp/transcript.jsonl")
        assert result.should_block is False

    @patch("session_end_commit_check.extract_recent_messages")
    @patch("session_end_commit_check.has_framework_reflection")
    @patch("session_end_commit_check.has_test_success")
    @patch("session_end_commit_check.has_qa_invocation")
    @patch("session_end_commit_check.get_git_status")
    def test_no_reflection_or_tests_but_tracked_changes(
        self,
        mock_git_status,
        mock_qa_invocation,
        mock_test_success,
        mock_reflection,
        mock_extract,
    ) -> None:
        """Should block if tracked changes exist, even without reflection/tests.

        Fix for aops-579dcaeb: sessions that modify code but lack reflection/tests
        should still be blocked to prevent uncommitted work loss.
        """
        mock_extract.return_value = ["message"]
        mock_reflection.return_value = False
        mock_test_success.return_value = False
        mock_qa_invocation.return_value = False
        mock_git_status.return_value = GitStatus(
            has_changes=True,
            staged_changes=False,
            unstaged_changes=True,  # Tracked file modified
            untracked_files=False,
            status_output="M file.txt",
        )

        result = check_uncommitted_work("session123", "/tmp/transcript.jsonl")
        # Now blocks because has_tracked_changes triggers blocking (fix for aops-579dcaeb)
        assert result.should_block is True
        assert "Uncommitted changes detected" in result.message

    @patch("session_end_commit_check.extract_recent_messages")
    @patch("session_end_commit_check.has_framework_reflection")
    @patch("session_end_commit_check.has_test_success")
    @patch("session_end_commit_check.has_qa_invocation")
    @patch("session_end_commit_check.get_git_status")
    def test_untracked_only_no_block(
        self,
        mock_git_status,
        mock_qa_invocation,
        mock_test_success,
        mock_reflection,
        mock_extract,
    ) -> None:
        """Should NOT block if only untracked files exist without reflection/tests.

        Untracked files alone don't indicate the session did work - they could be
        pre-existing or unrelated to the session.
        """
        mock_extract.return_value = ["message"]
        mock_reflection.return_value = False
        mock_test_success.return_value = False
        mock_qa_invocation.return_value = False
        mock_git_status.return_value = GitStatus(
            has_changes=True,
            staged_changes=False,
            unstaged_changes=False,  # No tracked changes
            untracked_files=True,  # Only untracked
            status_output="?? newfile.txt",
        )

        result = check_uncommitted_work("session123", "/tmp/transcript.jsonl")
        # Should NOT block - only untracked files, no tracked changes
        assert result.should_block is False

    @patch("session_end_commit_check.extract_recent_messages")
    @patch("session_end_commit_check.has_framework_reflection")
    @patch("session_end_commit_check.has_test_success")
    @patch("session_end_commit_check.get_git_status")
    @patch("session_end_commit_check.attempt_auto_commit")
    def test_staged_changes_with_reflection(
        self,
        mock_auto_commit,
        mock_git_status,
        mock_test_success,
        mock_reflection,
        mock_extract,
    ) -> None:
        """Should detect staged changes (requires auto-commit attempt)."""
        mock_extract.return_value = ["message"]
        mock_reflection.return_value = True
        mock_test_success.return_value = False
        mock_git_status.return_value = GitStatus(
            has_changes=True,
            staged_changes=True,
            unstaged_changes=False,
            untracked_files=False,
            status_output="M file.txt",
        )
        mock_auto_commit.return_value = False

        result = check_uncommitted_work("session123", "/tmp/transcript.jsonl")
        assert result.should_block is True
        assert "staged" in result.message.lower()

    @patch("session_end_commit_check.extract_recent_messages")
    @patch("session_end_commit_check.has_framework_reflection")
    @patch("session_end_commit_check.has_test_success")
    @patch("session_end_commit_check.get_git_status")
    @patch("session_end_commit_check.get_git_push_status")
    def test_unpushed_commits_reminder(
        self,
        mock_push_status,
        mock_git_status,
        mock_test_success,
        mock_reflection,
        mock_extract,
    ) -> None:
        """Should show reminder for unpushed commits even without blocking."""
        mock_extract.return_value = ["message"]
        mock_reflection.return_value = False
        mock_test_success.return_value = False
        mock_git_status.return_value = GitStatus(
            has_changes=False,
            staged_changes=False,
            unstaged_changes=False,
            untracked_files=False,
            status_output="",
        )
        mock_push_status.return_value = GitPushStatus(
            branch_ahead=True,
            commits_ahead=2,
            current_branch="main",
            tracking_branch="origin/main",
        )

        result = check_uncommitted_work("session123", "/tmp/transcript.jsonl")
        assert result.should_block is False
        assert result.reminder_needed is True
        assert "unpushed" in result.message.lower()
        assert "2" in result.message


class TestHookIntegration:
    """Test hook behavior end-to-end."""

    def test_hook_input_output_format(self) -> None:
        """Test hook input/output JSON format."""
        input_data = {
            "session_id": "test-session",
            "transcript_path": "/tmp/fake/transcript.jsonl",
            "hook_event_name": "Stop",
        }

        # Verify input structure
        assert input_data["session_id"]
        assert input_data["hook_event_name"] == "Stop"

    def test_no_transcript_path(self) -> None:
        """Should handle missing transcript path gracefully."""
        with tempfile.TemporaryDirectory():
            result = check_uncommitted_work("session123", None)
            assert result.should_block is False
            assert result.has_reflection is False

    def test_nonexistent_transcript_file(self) -> None:
        """Should handle nonexistent transcript file."""
        result = check_uncommitted_work("session123", "/tmp/nonexistent.jsonl")
        assert result.should_block is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
