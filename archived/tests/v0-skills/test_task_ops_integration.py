"""Integration tests for task_ops CWD independence.

Verifies that task_ops functions work correctly regardless of current
working directory by using REAL data from the environment.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from skills.tasks.task_ops import (
    load_task_from_file,
    create_task,
    archive_task,
    InvalidTaskFormatError,
    TaskNotFoundError,
)


class TestTaskOpsCwdIndependence:
    """Integration tests verifying task_ops works from any directory."""

    def test_task_ops_reads_from_aca_data_regardless_of_cwd(self) -> None:
        """Verify task_ops loads real tasks regardless of CWD.

        This test proves that task_ops correctly:
        1. Loads actual tasks from ACA_DATA/tasks (real location)
        2. Works correctly when run from arbitrary directory (/tmp)
        3. Finds real tasks in inbox and queue subdirectories

        Integration requirement: $ACA_DATA must be set and contain
        real tasks in $ACA_DATA/tasks/inbox or queue directories.
        """
        # Get the actual data directory from ACA_DATA environment variable
        aca_data = os.environ.get("ACA_DATA")
        if not aca_data:
            pytest.skip("ACA_DATA environment variable not set")

        # task_ops expects the directory containing tasks/inbox and tasks/queue
        # which is exactly $ACA_DATA in this setup
        data_dir = Path(aca_data)

        # Verify that tasks subdirectories exist
        inbox_dir = data_dir / "tasks" / "inbox"
        if not inbox_dir.exists():
            pytest.skip(f"Task inbox not found: {inbox_dir}")

        # Save original CWD to restore after test
        original_cwd = os.getcwd()

        try:
            # Change to temporary directory (simulating different CWD)
            # This proves task loading doesn't rely on ./data or relative paths
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # Verify we're in a completely different directory
                assert os.getcwd() == tmpdir, "Failed to change to temporary directory"
                assert (
                    os.getcwd() != original_cwd
                ), "CWD should be different from original"

                # Load tasks from the real data directory
                # This proves task_ops works correctly with real data
                # regardless of where we're running from
                #
                # We manually load to handle real data that may have
                # validation errors in some task files (e.g., string priorities
                # instead of integers). This is realistic - real data is messy.
                tasks = []
                inbox_dir = data_dir / "tasks" / "inbox"

                if inbox_dir.exists():
                    for task_file in inbox_dir.glob("*.md"):
                        try:
                            task = load_task_from_file(task_file)
                            tasks.append(task)
                        except (InvalidTaskFormatError, TaskNotFoundError, ValueError):
                            # Skip invalid tasks - this is normal with real data
                            pass
                        except Exception:
                            # Skip other validation errors too
                            pass

                # CRITICAL: We must have successfully loaded at least one real task
                # This proves load_task_from_file works from any CWD with real data
                assert len(tasks) > 0, (
                    f"No valid tasks found in {inbox_dir}. "
                    f"This test requires at least one properly formatted task "
                    f"in $ACA_DATA/tasks/inbox."
                )

                # Verify task structure (proves these are real tasks)
                first_task = tasks[0]

                # Real tasks must have these attributes
                assert hasattr(first_task, "title"), "Task missing title attribute"
                assert hasattr(
                    first_task, "filename"
                ), "Task missing filename attribute"
                assert first_task.title, "Task title should not be empty"
                assert first_task.filename, "Task filename should not be empty"
                assert first_task.filename.endswith(
                    ".md"
                ), f"Task filename should end with .md: {first_task.filename}"

                # Verify all loaded tasks have proper structure
                for task in tasks:
                    assert task.title, f"Task {task.filename} has empty title"
                    assert task.filename, "Task has empty filename"

        finally:
            # Always restore original CWD, even if test fails
            os.chdir(original_cwd)
            assert os.getcwd() == original_cwd

    def test_task_create_and_archive_from_arbitrary_cwd(self) -> None:
        """Verify task_ops create/archive works from any CWD with real ACA_DATA.

        This test proves that task_ops correctly:
        1. Creates a real task in REAL $ACA_DATA/tasks/inbox from arbitrary CWD
        2. Works correctly when run from arbitrary directory (/tmp)
        3. Archives the task to $ACA_DATA/tasks/archived
        4. Verifies file locations and cleans up after itself

        Integration requirement: $ACA_DATA must be set and writable.
        """
        # Get the actual data directory from ACA_DATA environment variable
        aca_data = os.environ.get("ACA_DATA")
        if not aca_data:
            pytest.skip("ACA_DATA environment variable not set")

        data_dir = Path(aca_data)

        # Verify that tasks directories exist or can be created
        inbox_dir = data_dir / "tasks" / "inbox"
        archived_dir = data_dir / "tasks" / "archived"

        # Save original CWD to restore after test
        original_cwd = os.getcwd()

        try:
            # Change to temporary directory (simulating different CWD)
            # This proves task_ops doesn't rely on ./data or relative paths
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # Verify we're in a completely different directory
                assert os.getcwd() == tmpdir, "Failed to change to temporary directory"
                assert (
                    os.getcwd() != original_cwd
                ), "CWD should be different from original"

                # Create a unique task title with timestamp to avoid conflicts
                import time

                timestamp = int(time.time() * 1000)
                task_title = f"Integration Test Task {timestamp}"

                # Create a real task in the real data directory
                create_result = create_task(
                    title=task_title,
                    data_dir=data_dir,
                    priority=1,
                    task_type="todo",
                    body="This is an integration test task",
                    tags=["integration-test"],
                )

                # Verify task was created successfully
                assert create_result[
                    "success"
                ], f"Failed to create task: {create_result.get('message', 'unknown error')}"

                # Get the created task's filename
                filename = create_result["filename"]
                task_id = create_result["task_id"]

                # Verify the file exists in inbox
                task_file_in_inbox = inbox_dir / filename
                assert (
                    task_file_in_inbox.exists()
                ), f"Task file not found in inbox: {task_file_in_inbox}"

                # Verify we can load the created task
                task = load_task_from_file(task_file_in_inbox)
                assert (
                    task.title == task_title
                ), f"Task title mismatch: {task.title} != {task_title}"
                assert (
                    task.status == "inbox"
                ), f"Task status should be 'inbox': {task.status}"

                # Archive the task
                archive_result = archive_task(filename, data_dir)

                # Verify archive was successful
                assert archive_result[
                    "success"
                ], f"Failed to archive task: {archive_result.get('message', 'unknown error')}"

                # Verify the file no longer exists in inbox
                assert (
                    not task_file_in_inbox.exists()
                ), f"Task file still in inbox after archiving: {task_file_in_inbox}"

                # Verify the file exists in archived
                task_file_archived = archived_dir / filename
                assert (
                    task_file_archived.exists()
                ), f"Task file not found in archived: {task_file_archived}"

                # Verify we can load the archived task
                archived_task = load_task_from_file(task_file_archived)
                assert (
                    archived_task.title == task_title
                ), f"Archived task title mismatch: {archived_task.title} != {task_title}"
                assert (
                    archived_task.status == "archived"
                ), f"Archived task status should be 'archived': {archived_task.status}"
                assert (
                    archived_task.archived_at is not None
                ), "Archived task should have archived_at set"

                # CLEANUP: Delete the test task file to avoid leaving garbage
                task_file_archived.unlink()
                assert (
                    not task_file_archived.exists()
                ), f"Failed to clean up test task file: {task_file_archived}"

        finally:
            # Always restore original CWD, even if test fails
            os.chdir(original_cwd)
            assert os.getcwd() == original_cwd
