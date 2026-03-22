from __future__ import annotations

from pathlib import Path

from lib.task_index import TaskIndex
from lib.task_model import Task, TaskStatus, TaskType
from lib.task_storage import TaskStorage


class TestReadyFilterConsolidation:
    """Test that Task.is_ready() and TaskIndexEntry.is_ready() are consistent."""

    def test_basic_ready_task(self):
        task = Task(
            id="t1", title="Task 1", type=TaskType.TASK, status=TaskStatus.ACTIVE, leaf=True
        )
        assert task.is_ready() is True

    def test_non_leaf_not_ready(self):
        task = Task(
            id="t1", title="Task 1", type=TaskType.TASK, status=TaskStatus.ACTIVE, leaf=False
        )
        assert task.is_ready() is False

    def test_non_claimable_type_not_ready(self):
        task = Task(
            id="t1", title="Task 1", type=TaskType.GOAL, status=TaskStatus.ACTIVE, leaf=True
        )
        assert task.is_ready() is False

        task = Task(
            id="t1", title="Task 1", type=TaskType.PROJECT, status=TaskStatus.ACTIVE, leaf=True
        )
        assert task.is_ready() is False

    def test_non_active_status_not_ready(self):
        task = Task(
            id="t1", title="Task 1", type=TaskType.TASK, status=TaskStatus.IN_PROGRESS, leaf=True
        )
        assert task.is_ready() is False

        task = Task(id="t1", title="Task 1", type=TaskType.TASK, status=TaskStatus.DONE, leaf=True)
        assert task.is_ready() is False

    def test_unmet_dependencies_not_ready(self):
        task = Task(
            id="t2",
            title="Task 2",
            type=TaskType.TASK,
            status=TaskStatus.ACTIVE,
            leaf=True,
            depends_on=["t1"],
        )

        # Without completed_ids, any depends_on means not ready
        assert task.is_ready() is False

        # With completed_ids not containing t1, still not ready
        assert task.is_ready(completed_ids={"t0"}) is False

        # With completed_ids containing t1, it's ready
        assert task.is_ready(completed_ids={"t1"}) is True

    def test_task_storage_list_tasks_ready(self, tmp_path: Path):
        storage = TaskStorage(data_root=tmp_path)

        # Create a goal (not claimable)
        goal = storage.create_task(title="Goal", type=TaskType.GOAL)
        storage.save_task(goal)

        # Create a ready task
        task1 = storage.create_task(title="Task 1", type=TaskType.TASK, parent=goal.id)
        storage.save_task(task1)

        # Create an in-progress task
        task2 = storage.create_task(title="Task 2", type=TaskType.TASK, parent=goal.id)
        task2.status = TaskStatus.IN_PROGRESS
        storage.save_task(task2)

        # Create a blocked task
        task3 = storage.create_task(
            title="Task 3", type=TaskType.TASK, parent=goal.id, depends_on=["non-existent"]
        )
        storage.save_task(task3)

        ready_tasks = storage.list_tasks(status="ready")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].title == "Task 1"

        blocked_tasks = storage.list_tasks(status="blocked")
        assert len(blocked_tasks) == 1
        assert blocked_tasks[0].title == "Task 3"

    def test_task_index_ready(self, tmp_path: Path):
        storage = TaskStorage(data_root=tmp_path)

        # Create a goal
        goal = storage.create_task(title="Goal", type=TaskType.GOAL)
        storage.save_task(goal)

        # Create a ready task
        task1 = storage.create_task(title="Task 1", type=TaskType.TASK, parent=goal.id)
        storage.save_task(task1)

        # Create a blocked task (unmet dep)
        task3 = storage.create_task(
            title="Task 3", type=TaskType.TASK, parent=goal.id, depends_on=["non-existent"]
        )
        storage.save_task(task3)

        index = TaskIndex(data_root=tmp_path)
        index.rebuild()

        ready_tasks = index.get_ready_tasks()
        assert len(ready_tasks) == 1
        assert ready_tasks[0].title == "Task 1"

        blocked_tasks = index.get_blocked_tasks()
        assert len(blocked_tasks) == 1
        assert blocked_tasks[0].title == "Task 3"
