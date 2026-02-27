"""Tests for task_storage.py focusing on path consistency."""

from __future__ import annotations

from pathlib import Path

from lib.task_model import TaskStatus, TaskType
from lib.task_storage import TaskStorage


class TestSaveTaskPathConsistency:
    """Test that save_task writes to the same location get_task reads from."""

    def test_save_updates_existing_file_location(self, tmp_path: Path) -> None:
        """When a task file exists, save_task should update it in place.

        Regression test for silent write failures caused by path mismatch:
        - _find_task_path() searches global dir first (for reads)
        - _get_task_path() computes project-specific path (for writes)
        - If task exists in global but has project set, writes go to wrong location
        """
        # Setup: Create directory structure
        global_tasks = tmp_path / "tasks"
        global_tasks.mkdir(parents=True)

        project_tasks = tmp_path / "myproject" / "tasks"
        project_tasks.mkdir(parents=True)

        storage = TaskStorage(data_root=tmp_path)

        # Create a task file in the GLOBAL location (simulating migration/legacy)
        task_id = "test-12345678"
        task_content = f"""---
id: {task_id}
title: Test Task
type: task
status: active
priority: 2
order: 0
project: myproject
parent: null
depends_on: []
depth: 0
leaf: true
created: 2026-01-26T00:00:00+00:00
modified: 2026-01-26T00:00:00+00:00
---

Original body content.
"""
        global_task_file = global_tasks / f"{task_id}-test-task.md"
        global_task_file.write_text(task_content)

        # Verify: get_task finds the global file
        loaded_task = storage.get_task(task_id)
        assert loaded_task is not None
        assert loaded_task.id == task_id
        assert "Original body content" in loaded_task.body

        # Modify the task
        loaded_task.body = "Updated body content."
        loaded_task.status = TaskStatus.IN_PROGRESS

        # Save the task - THIS IS THE BUG: should update global file, not create project file
        storage.save_task(loaded_task)

        # Verify: the ORIGINAL file was updated (not a new file created elsewhere)
        # Read raw file content to verify disk state
        raw_content = global_task_file.read_text()
        assert "Updated body content" in raw_content, (
            f"Expected updates in {global_task_file}, but found: {raw_content[:200]}..."
        )
        assert "in_progress" in raw_content, f"Expected status update in {global_task_file}"

        # Verify: no duplicate file was created in project location
        project_task_file = project_tasks / f"{task_id}-test-task.md"
        assert not project_task_file.exists(), (
            f"Bug: save_task created duplicate file at {project_task_file}"
        )

    def test_new_task_uses_project_path(self, tmp_path: Path) -> None:
        """New tasks should be created in the project-specific location."""
        project_tasks = tmp_path / "myproject" / "tasks"
        project_tasks.mkdir(parents=True)

        storage = TaskStorage(data_root=tmp_path)

        # Create and save a new task
        task = storage.create_task(
            title="New Task",
            project="myproject",
            type=TaskType.GOAL,
        )
        returned_path = storage.save_task(task)

        # Verify: task was created in project location
        assert returned_path.parent == project_tasks
        assert returned_path.exists()
        assert "New Task" in returned_path.read_text()


class TestCreateTaskParentValidation:
    """Test that create_task enforces parent requirement for non-root task types."""

    def test_task_type_without_parent_raises_value_error(self, tmp_path: Path) -> None:
        """create_task(type=TaskType.TASK) without parent must raise ValueError."""
        storage = TaskStorage(data_root=tmp_path)

        import pytest

        with pytest.raises(ValueError, match="require a parent"):
            storage.create_task(title="Orphan Task", type=TaskType.TASK, project=None)

    def test_goal_type_without_parent_succeeds(self, tmp_path: Path) -> None:
        """create_task(type=TaskType.GOAL) without parent must not raise."""
        storage = TaskStorage(data_root=tmp_path)

        task = storage.create_task(title="My Goal", type=TaskType.GOAL, project=None)
        assert task.title == "My Goal"

    def test_error_message_suggests_candidates_when_project_set(self, tmp_path: Path) -> None:
        """When project is provided, error message should list candidate parents."""
        project_tasks = tmp_path / "myproject" / "tasks"
        project_tasks.mkdir(parents=True)
        storage = TaskStorage(data_root=tmp_path)

        # Create a GOAL task in the project so it shows up as a candidate
        goal = storage.create_task(title="Parent Goal", type=TaskType.GOAL, project="myproject")
        storage.save_task(goal)

        import pytest

        with pytest.raises(ValueError) as exc_info:
            storage.create_task(title="Child Task", type=TaskType.TASK, project="myproject")

        error_text = str(exc_info.value)
        assert "require a parent" in error_text
        assert "myproject" in error_text
        assert "Parent Goal" in error_text


class TestAtomicWriteVerification:
    """Test that _atomic_write verifies the write succeeded."""

    def test_atomic_write_creates_file(self, tmp_path: Path) -> None:
        """Basic test that atomic write creates the file."""
        storage = TaskStorage(data_root=tmp_path)

        task = storage.create_task(title="Test", project=None, type=TaskType.GOAL)
        path = tmp_path / "tasks" / "inbox" / f"{task.id}-test.md"

        storage._atomic_write(path, task)

        assert path.exists()
        content = path.read_text()
        assert task.id in content
