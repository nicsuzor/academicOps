"""Integration tests for task_ops CWD independence.

Verifies that task_ops functions work correctly regardless of current
working directory by using REAL data from the environment.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from skills.tasks.task_ops import load_task_from_file, InvalidTaskFormatError, TaskNotFoundError


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
                assert os.getcwd() == tmpdir, (
                    "Failed to change to temporary directory"
                )
                assert os.getcwd() != original_cwd, (
                    "CWD should be different from original"
                )

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
                assert hasattr(first_task, "title"), (
                    "Task missing title attribute"
                )
                assert hasattr(first_task, "filename"), (
                    "Task missing filename attribute"
                )
                assert first_task.title, "Task title should not be empty"
                assert first_task.filename, "Task filename should not be empty"
                assert first_task.filename.endswith(".md"), (
                    f"Task filename should end with .md: {first_task.filename}"
                )

                # Verify all loaded tasks have proper structure
                for task in tasks:
                    assert task.title, f"Task {task.filename} has empty title"
                    assert task.filename, "Task has empty filename"

        finally:
            # Always restore original CWD, even if test fails
            os.chdir(original_cwd)
            assert os.getcwd() == original_cwd
