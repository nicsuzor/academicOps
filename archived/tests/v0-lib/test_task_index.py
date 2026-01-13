"""Unit tests for Task Index v2.

Tests index schema and graph queries per specs/tasks-v2.md Section 6.
"""

from pathlib import Path

import pytest

from lib.task_index import TaskIndex, TaskIndexEntry
from lib.task_model import TaskStatus, TaskType
from lib.task_storage import TaskStorage


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create temp data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "tasks" / "inbox").mkdir(parents=True)
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


@pytest.fixture
def storage(data_dir: Path) -> TaskStorage:
    """Create TaskStorage with temp directory."""
    return TaskStorage(data_dir)


@pytest.fixture
def index(data_dir: Path) -> TaskIndex:
    """Create TaskIndex with temp directory."""
    return TaskIndex(data_dir)


class TestIndexRebuild:
    """Test index rebuild from files."""

    def test_rebuild_empty(self, index: TaskIndex):
        """Rebuild with no tasks creates empty index."""
        index.rebuild()

        assert index.index_path.exists()
        stats = index.stats()
        assert stats["total"] == 0

    def test_rebuild_creates_index_file(self, index: TaskIndex, storage: TaskStorage):
        """Rebuild creates index.json file."""
        storage.save_task(storage.create_task("Task 1", project="test"))
        storage.save_task(storage.create_task("Task 2", project="test"))

        index.rebuild()

        assert index.index_path.exists()
        stats = index.stats()
        assert stats["total"] == 2

    def test_rebuild_computes_children(self, index: TaskIndex, storage: TaskStorage):
        """Rebuild computes children from parent references."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        child1 = storage.create_task("Child 1", project="test", parent=parent.id)
        storage.save_task(child1)

        child2 = storage.create_task("Child 2", project="test", parent=parent.id)
        storage.save_task(child2)

        index.rebuild()

        entry = index.get_task(parent.id)
        assert entry is not None
        assert len(entry.children) == 2
        assert child1.id in entry.children
        assert child2.id in entry.children

    def test_rebuild_computes_blocks(self, index: TaskIndex, storage: TaskStorage):
        """Rebuild computes blocks from depends_on."""
        dep = storage.create_task("Dependency", project="test")
        storage.save_task(dep)

        dependent = storage.create_task(
            "Dependent", project="test", depends_on=[dep.id]
        )
        storage.save_task(dependent)

        index.rebuild()

        dep_entry = index.get_task(dep.id)
        assert dep_entry is not None
        assert dependent.id in dep_entry.blocks

    def test_rebuild_identifies_roots(self, index: TaskIndex, storage: TaskStorage):
        """Rebuild identifies root tasks (no parent)."""
        root1 = storage.create_task("Root 1", project="test")
        storage.save_task(root1)

        root2 = storage.create_task("Root 2", project="test")
        storage.save_task(root2)

        child = storage.create_task("Child", project="test", parent=root1.id)
        storage.save_task(child)

        index.rebuild()

        roots = index.get_roots()
        root_ids = {r.id for r in roots}
        assert root1.id in root_ids
        assert root2.id in root_ids
        assert child.id not in root_ids

    def test_rebuild_computes_ready(self, index: TaskIndex, storage: TaskStorage):
        """Rebuild computes ready tasks."""
        ready = storage.create_task("Ready", project="test")
        ready.status = TaskStatus.ACTIVE
        storage.save_task(ready)

        blocked = storage.create_task("Blocked", project="test", depends_on=[ready.id])
        blocked.status = TaskStatus.ACTIVE
        storage.save_task(blocked)

        index.rebuild()

        ready_tasks = index.get_ready_tasks()
        ready_ids = {t.id for t in ready_tasks}
        assert ready.id in ready_ids
        assert blocked.id not in ready_ids

    def test_rebuild_computes_blocked(self, index: TaskIndex, storage: TaskStorage):
        """Rebuild computes blocked tasks."""
        dep = storage.create_task("Dependency", project="test")
        storage.save_task(dep)

        blocked = storage.create_task("Blocked", project="test", depends_on=[dep.id])
        storage.save_task(blocked)

        index.rebuild()

        blocked_tasks = index.get_blocked_tasks()
        assert any(t.id == blocked.id for t in blocked_tasks)


class TestIndexLoadSave:
    """Test index persistence."""

    def test_save_and_load(self, index: TaskIndex, storage: TaskStorage):
        """Index survives save/load cycle."""
        storage.save_task(storage.create_task("Task 1", project="test"))
        storage.save_task(storage.create_task("Task 2", project="test"))
        index.rebuild()

        # Create new index instance and load
        index2 = TaskIndex(index.data_root)
        result = index2.load()

        assert result is True
        assert index2.stats()["total"] == 2

    def test_load_nonexistent_returns_false(self, index: TaskIndex):
        """Load missing index returns False."""
        result = index.load()
        assert result is False

    def test_load_wrong_version_returns_false(self, index: TaskIndex):
        """Load incompatible version returns False."""
        import json

        index.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index.index_path, "w") as f:
            json.dump({"version": 999, "tasks": {}}, f)

        result = index.load()
        assert result is False


class TestGraphQueries:
    """Test index graph queries."""

    def test_get_children(self, index: TaskIndex, storage: TaskStorage):
        """Get children returns sorted entries."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        c1 = storage.create_task("Child 1", project="test", parent=parent.id)
        c1.order = 2
        storage.save_task(c1)

        c2 = storage.create_task("Child 2", project="test", parent=parent.id)
        c2.order = 1
        storage.save_task(c2)

        index.rebuild()

        children = index.get_children(parent.id)
        assert len(children) == 2
        assert children[0].order == 1
        assert children[1].order == 2

    def test_get_descendants(self, index: TaskIndex, storage: TaskStorage):
        """Get all descendants recursively."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        grandchild = storage.create_task("Grandchild", project="test", parent=child.id)
        storage.save_task(grandchild)

        index.rebuild()

        descendants = index.get_descendants(root.id)
        ids = {d.id for d in descendants}
        assert child.id in ids
        assert grandchild.id in ids

    def test_get_ancestors(self, index: TaskIndex, storage: TaskStorage):
        """Get path to root."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        grandchild = storage.create_task("Grandchild", project="test", parent=child.id)
        storage.save_task(grandchild)

        index.rebuild()

        ancestors = index.get_ancestors(grandchild.id)
        assert len(ancestors) == 2
        assert ancestors[0].id == child.id
        assert ancestors[1].id == root.id

    def test_get_root(self, index: TaskIndex, storage: TaskStorage):
        """Get root goal for nested task."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        index.rebuild()

        result = index.get_root(child.id)
        assert result is not None
        assert result.id == root.id

    def test_get_dependencies(self, index: TaskIndex, storage: TaskStorage):
        """Get tasks this task depends on."""
        dep1 = storage.create_task("Dep 1", project="test")
        storage.save_task(dep1)

        dep2 = storage.create_task("Dep 2", project="test")
        storage.save_task(dep2)

        task = storage.create_task(
            "Task", project="test", depends_on=[dep1.id, dep2.id]
        )
        storage.save_task(task)

        index.rebuild()

        deps = index.get_dependencies(task.id)
        dep_ids = {d.id for d in deps}
        assert dep1.id in dep_ids
        assert dep2.id in dep_ids

    def test_get_dependents(self, index: TaskIndex, storage: TaskStorage):
        """Get tasks that depend on this task."""
        task = storage.create_task("Task", project="test")
        storage.save_task(task)

        dependent1 = storage.create_task(
            "Dependent 1", project="test", depends_on=[task.id]
        )
        storage.save_task(dependent1)

        dependent2 = storage.create_task(
            "Dependent 2", project="test", depends_on=[task.id]
        )
        storage.save_task(dependent2)

        index.rebuild()

        dependents = index.get_dependents(task.id)
        dep_ids = {d.id for d in dependents}
        assert dependent1.id in dep_ids
        assert dependent2.id in dep_ids

    def test_get_next_actions(self, index: TaskIndex, storage: TaskStorage):
        """Get ready leaf tasks under a goal."""
        goal = storage.create_task("Goal", project="test", type=TaskType.GOAL)
        goal.status = TaskStatus.ACTIVE
        storage.save_task(goal)

        project = storage.create_task(
            "Project", project="test", type=TaskType.PROJECT, parent=goal.id
        )
        project.status = TaskStatus.ACTIVE
        storage.save_task(project)

        action1 = storage.create_task(
            "Action 1", project="test", type=TaskType.ACTION, parent=project.id
        )
        action1.status = TaskStatus.ACTIVE
        storage.save_task(action1)

        action2 = storage.create_task(
            "Action 2",
            project="test",
            type=TaskType.ACTION,
            parent=project.id,
            depends_on=[action1.id],
        )
        action2.status = TaskStatus.ACTIVE
        storage.save_task(action2)

        index.rebuild()

        actions = index.get_next_actions(goal.id)
        action_ids = {a.id for a in actions}
        assert action1.id in action_ids
        assert action2.id not in action_ids  # Blocked by action1


class TestProjectGrouping:
    """Test project-based grouping."""

    def test_get_by_project(self, index: TaskIndex, storage: TaskStorage):
        """Get all tasks in a project."""
        storage.save_task(storage.create_task("Task A1", project="proj-a"))
        storage.save_task(storage.create_task("Task A2", project="proj-a"))
        storage.save_task(storage.create_task("Task B1", project="proj-b"))

        index.rebuild()

        proj_a = index.get_by_project("proj-a")
        assert len(proj_a) == 2
        assert all(t.project == "proj-a" for t in proj_a)

    def test_stats_includes_projects(self, index: TaskIndex, storage: TaskStorage):
        """Stats includes project count."""
        storage.save_task(storage.create_task("Task 1", project="proj-a"))
        storage.save_task(storage.create_task("Task 2", project="proj-b"))
        storage.save_task(storage.create_task("Task 3"))  # inbox

        index.rebuild()

        stats = index.stats()
        assert stats["projects"] == 3  # proj-a, proj-b, inbox


class TestTaskIndexEntry:
    """Test TaskIndexEntry dataclass."""

    def test_to_dict(self):
        """Convert entry to dictionary."""
        entry = TaskIndexEntry(
            id="20260112-test",
            title="Test",
            type="task",
            status="active",
            priority=1,
            order=0,
            parent=None,
            children=["20260112-child"],
            depends_on=[],
            blocks=[],
            depth=0,
            leaf=False,
            project="test",
            path="test/tasks/20260112-test.md",
        )

        d = entry.to_dict()
        assert d["id"] == "20260112-test"
        assert d["children"] == ["20260112-child"]
        assert d["leaf"] is False

    def test_from_dict(self):
        """Create entry from dictionary."""
        d = {
            "id": "20260112-test",
            "title": "Test",
            "type": "task",
            "status": "active",
            "priority": 1,
            "order": 0,
            "parent": None,
            "children": [],
            "depends_on": [],
            "blocks": [],
            "depth": 0,
            "leaf": True,
            "project": "test",
            "path": "test/tasks/20260112-test.md",
        }

        entry = TaskIndexEntry.from_dict(d)
        assert entry.id == "20260112-test"
        assert entry.leaf is True

    def test_roundtrip(self):
        """Entry survives to_dict/from_dict cycle."""
        original = TaskIndexEntry(
            id="20260112-test",
            title="Test Task",
            type="action",
            status="inbox",
            priority=2,
            order=5,
            parent="20260112-parent",
            children=[],
            depends_on=["20260112-dep"],
            blocks=["20260112-blocked"],
            depth=2,
            leaf=True,
            project="test",
            path="test/tasks/20260112-test.md",
            due="2026-12-31T00:00:00+00:00",
            tags=["important", "urgent"],
        )

        restored = TaskIndexEntry.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.parent == original.parent
        assert restored.depends_on == original.depends_on
        assert restored.blocks == original.blocks
        assert restored.due == original.due
        assert restored.tags == original.tags
