"""Unit tests for Task Storage v2.

Tests flat file storage per specs/tasks-v2.md Section 2.
"""

from pathlib import Path

import pytest

from lib.task_model import TaskStatus, TaskType
from lib.task_storage import TaskStorage


@pytest.fixture
def storage(tmp_path: Path, monkeypatch) -> TaskStorage:
    """Create TaskStorage with temp directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "tasks" / "inbox").mkdir(parents=True)
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return TaskStorage(data_dir)


class TestTaskCreation:
    """Test task creation via storage."""

    def test_create_task_generates_id(self, storage: TaskStorage):
        """Create task auto-generates ID."""
        task = storage.create_task("Test Task")

        assert task.id.endswith("-test-task")
        assert task.title == "Test Task"
        assert task.status == TaskStatus.INBOX

    def test_create_task_with_project(self, storage: TaskStorage):
        """Create task with project assignment."""
        task = storage.create_task("Project Task", project="book")

        assert task.project == "book"

    def test_create_task_with_parent(self, storage: TaskStorage):
        """Create task with parent computes depth."""
        # Create parent first
        parent = storage.create_task("Parent Task", project="book")
        parent.depth = 1
        storage.save_task(parent)

        # Create child
        child = storage.create_task("Child Task", project="book", parent=parent.id)

        assert child.parent == parent.id
        assert child.depth == 2


class TestTaskSaving:
    """Test task file operations."""

    def test_save_creates_file(self, storage: TaskStorage):
        """Save task creates markdown file."""
        task = storage.create_task("Save Test", project="test-project")
        path = storage.save_task(task)

        assert path.exists()
        assert path.suffix == ".md"
        assert "test-project/tasks" in str(path)

    def test_save_inbox_task(self, storage: TaskStorage):
        """Save task without project goes to inbox."""
        task = storage.create_task("Inbox Task")
        path = storage.save_task(task)

        assert "tasks/inbox" in str(path)

    def test_save_updates_parent_leaf(self, storage: TaskStorage):
        """Saving child updates parent's leaf status."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)
        assert parent.leaf is True

        child = storage.create_task("Child", project="test", parent=parent.id)
        storage.save_task(child)

        # Reload parent to check updated leaf status
        reloaded = storage.get_task(parent.id)
        assert reloaded is not None
        assert reloaded.leaf is False


class TestTaskLoading:
    """Test task retrieval."""

    def test_get_task_by_id(self, storage: TaskStorage):
        """Load task by ID."""
        task = storage.create_task("Load Test", project="test")
        storage.save_task(task)

        loaded = storage.get_task(task.id)

        assert loaded is not None
        assert loaded.id == task.id
        assert loaded.title == "Load Test"

    def test_get_nonexistent_returns_none(self, storage: TaskStorage):
        """Loading missing task returns None."""
        result = storage.get_task("20260112-nonexistent")
        assert result is None

    def test_get_task_finds_in_project(self, storage: TaskStorage):
        """Find task in project directory."""
        task = storage.create_task("Project Task", project="my-project")
        storage.save_task(task)

        loaded = storage.get_task(task.id)
        assert loaded is not None
        assert loaded.project == "my-project"


class TestTaskListing:
    """Test task listing and filtering."""

    def test_list_all_tasks(self, storage: TaskStorage):
        """List all tasks across projects."""
        storage.save_task(storage.create_task("Task 1", project="proj-a"))
        storage.save_task(storage.create_task("Task 2", project="proj-b"))
        storage.save_task(storage.create_task("Task 3"))  # inbox

        tasks = storage.list_tasks()

        assert len(tasks) == 3

    def test_list_by_project(self, storage: TaskStorage):
        """List tasks filtered by project."""
        storage.save_task(storage.create_task("Task A1", project="proj-a"))
        storage.save_task(storage.create_task("Task A2", project="proj-a"))
        storage.save_task(storage.create_task("Task B1", project="proj-b"))

        tasks = storage.list_tasks(project="proj-a")

        assert len(tasks) == 2
        assert all(t.project == "proj-a" for t in tasks)

    def test_list_by_status(self, storage: TaskStorage):
        """List tasks filtered by status."""
        t1 = storage.create_task("Active Task")
        t1.status = TaskStatus.ACTIVE
        storage.save_task(t1)

        t2 = storage.create_task("Done Task")
        t2.status = TaskStatus.DONE
        storage.save_task(t2)

        active = storage.list_tasks(status=TaskStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].status == TaskStatus.ACTIVE

    def test_list_by_type(self, storage: TaskStorage):
        """List tasks filtered by type."""
        storage.save_task(
            storage.create_task("Goal", type=TaskType.GOAL, project="test")
        )
        storage.save_task(
            storage.create_task("Action", type=TaskType.ACTION, project="test")
        )

        goals = storage.list_tasks(type=TaskType.GOAL)
        assert len(goals) == 1
        assert goals[0].type == TaskType.GOAL


class TestTaskDeletion:
    """Test task deletion."""

    def test_delete_removes_file(self, storage: TaskStorage):
        """Delete task removes file."""
        task = storage.create_task("Delete Me", project="test")
        path = storage.save_task(task)
        assert path.exists()

        result = storage.delete_task(task.id)

        assert result is True
        assert not path.exists()

    def test_delete_nonexistent_returns_false(self, storage: TaskStorage):
        """Delete missing task returns False."""
        result = storage.delete_task("20260112-nonexistent")
        assert result is False


class TestGraphQueries:
    """Test graph relationship queries."""

    def test_get_children(self, storage: TaskStorage):
        """Get direct children of a task."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        c1 = storage.create_task("Child 1", project="test", parent=parent.id)
        c1.order = 1
        storage.save_task(c1)

        c2 = storage.create_task("Child 2", project="test", parent=parent.id)
        c2.order = 0
        storage.save_task(c2)

        children = storage.get_children(parent.id)

        assert len(children) == 2
        # Should be sorted by order
        assert children[0].order == 0
        assert children[1].order == 1

    def test_get_descendants(self, storage: TaskStorage):
        """Get all descendants recursively."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        grandchild = storage.create_task("Grandchild", project="test", parent=child.id)
        storage.save_task(grandchild)

        descendants = storage.get_descendants(root.id)

        assert len(descendants) == 2
        ids = {d.id for d in descendants}
        assert child.id in ids
        assert grandchild.id in ids

    def test_get_ancestors(self, storage: TaskStorage):
        """Get path to root."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        grandchild = storage.create_task("Grandchild", project="test", parent=child.id)
        storage.save_task(grandchild)

        ancestors = storage.get_ancestors(grandchild.id)

        assert len(ancestors) == 2
        assert ancestors[0].id == child.id
        assert ancestors[1].id == root.id

    def test_get_root(self, storage: TaskStorage):
        """Get root goal for nested task."""
        root = storage.create_task("Root", project="test", type=TaskType.GOAL)
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        result = storage.get_root(child.id)

        assert result is not None
        assert result.id == root.id


class TestReadyBlockedQueries:
    """Test ready/blocked task queries."""

    def test_get_ready_tasks(self, storage: TaskStorage):
        """Get tasks ready to work on."""
        # Ready: leaf, no deps, active
        ready = storage.create_task("Ready Task", project="test")
        ready.status = TaskStatus.ACTIVE
        storage.save_task(ready)

        # Not ready: has children (not leaf)
        parent = storage.create_task("Parent", project="test")
        parent.status = TaskStatus.ACTIVE
        storage.save_task(parent)
        child = storage.create_task("Child", project="test", parent=parent.id)
        storage.save_task(child)

        ready_tasks = storage.get_ready_tasks()

        # Only the ready task and child should be ready
        ready_ids = {t.id for t in ready_tasks}
        assert ready.id in ready_ids
        assert parent.id not in ready_ids  # Has children

    def test_get_ready_respects_dependencies(self, storage: TaskStorage):
        """Ready excludes tasks with unmet dependencies."""
        dep = storage.create_task("Dependency", project="test")
        dep.status = TaskStatus.ACTIVE
        storage.save_task(dep)

        blocked = storage.create_task("Blocked", project="test", depends_on=[dep.id])
        blocked.status = TaskStatus.ACTIVE
        storage.save_task(blocked)

        ready_tasks = storage.get_ready_tasks()

        ready_ids = {t.id for t in ready_tasks}
        assert dep.id in ready_ids
        assert blocked.id not in ready_ids

    def test_get_ready_completed_deps_unblock(self, storage: TaskStorage):
        """Completed dependencies unblock tasks."""
        dep = storage.create_task("Dependency", project="test")
        dep.status = TaskStatus.DONE
        storage.save_task(dep)

        unblocked = storage.create_task(
            "Unblocked", project="test", depends_on=[dep.id]
        )
        unblocked.status = TaskStatus.ACTIVE
        storage.save_task(unblocked)

        ready_tasks = storage.get_ready_tasks()

        ready_ids = {t.id for t in ready_tasks}
        assert unblocked.id in ready_ids

    def test_get_blocked_tasks(self, storage: TaskStorage):
        """Get tasks blocked by dependencies."""
        dep = storage.create_task("Dependency", project="test")
        storage.save_task(dep)

        blocked = storage.create_task("Blocked", project="test", depends_on=[dep.id])
        storage.save_task(blocked)

        blocked_tasks = storage.get_blocked_tasks()

        assert any(t.id == blocked.id for t in blocked_tasks)


class TestDecomposition:
    """Test task decomposition."""

    def test_decompose_creates_children(self, storage: TaskStorage):
        """Decompose task creates child tasks."""
        parent = storage.create_task("Chapter 1", project="book", type=TaskType.PROJECT)
        storage.save_task(parent)

        children = storage.decompose_task(
            parent.id,
            [
                {"title": "Outline chapter", "type": "action", "order": 0},
                {"title": "Write draft", "type": "action", "order": 1},
                {"title": "Revise", "type": "action", "order": 2},
            ],
        )

        assert len(children) == 3
        assert all(c.parent == parent.id for c in children)
        assert children[0].title == "Outline chapter"
        assert children[1].title == "Write draft"

    def test_decompose_sets_dependencies(self, storage: TaskStorage):
        """Decompose with dependencies between children."""
        parent = storage.create_task("Chapter 1", project="book")
        storage.save_task(parent)

        children = storage.decompose_task(
            parent.id,
            [
                {"title": "Outline", "type": "action"},
            ],
        )

        outline_id = children[0].id

        # Add dependent task
        more_children = storage.decompose_task(
            parent.id,
            [
                {"title": "Draft", "type": "action", "depends_on": [outline_id]},
            ],
        )

        assert outline_id in more_children[0].depends_on

    def test_decompose_nonexistent_raises(self, storage: TaskStorage):
        """Decompose missing task raises error."""
        with pytest.raises(ValueError, match="not found"):
            storage.decompose_task("20260112-nonexistent", [{"title": "Child"}])
