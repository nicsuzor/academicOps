"""Unit tests for Task Graph v2.

Tests graph traversal and tree display per specs/tasks-v2.md Section 3.2 and 5.2.
"""

from pathlib import Path

import pytest

from lib.task_graph import TaskGraph, TreeDisplayOptions
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
def graph(data_dir: Path) -> TaskGraph:
    """Create TaskGraph with temp directory."""
    return TaskGraph(data_dir)


class TestDecompositionTree:
    """Test decomposition tree traversal (Section 3.2)."""

    def test_get_children_returns_tasks(self, graph: TaskGraph, storage: TaskStorage):
        """get_children returns Task objects, not index entries."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        child1 = storage.create_task("Child 1", project="test", parent=parent.id)
        child1.order = 1
        storage.save_task(child1)

        child2 = storage.create_task("Child 2", project="test", parent=parent.id)
        child2.order = 0
        storage.save_task(child2)

        graph.rebuild()

        children = graph.get_children(parent.id)

        assert len(children) == 2
        # Verify they are Task objects, not TaskIndexEntry
        from lib.task_model import Task

        assert all(isinstance(c, Task) for c in children)
        # Sorted by order
        assert children[0].order == 0
        assert children[1].order == 1

    def test_get_children_nonexistent_returns_empty(self, graph: TaskGraph):
        """get_children for missing task returns empty list."""
        graph.rebuild()
        children = graph.get_children("20260112-nonexistent")
        assert children == []

    def test_get_descendants_recursive(self, graph: TaskGraph, storage: TaskStorage):
        """get_descendants returns all nested children."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        grandchild = storage.create_task("Grandchild", project="test", parent=child.id)
        storage.save_task(grandchild)

        graph.rebuild()

        descendants = graph.get_descendants(root.id)

        ids = {d.id for d in descendants}
        assert child.id in ids
        assert grandchild.id in ids
        assert len(descendants) == 2

    def test_get_ancestors_path_to_root(self, graph: TaskGraph, storage: TaskStorage):
        """get_ancestors returns path from parent to root."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        grandchild = storage.create_task("Grandchild", project="test", parent=child.id)
        storage.save_task(grandchild)

        graph.rebuild()

        ancestors = graph.get_ancestors(grandchild.id)

        assert len(ancestors) == 2
        assert ancestors[0].id == child.id  # Immediate parent first
        assert ancestors[1].id == root.id  # Root last

    def test_get_root_finds_root_goal(self, graph: TaskGraph, storage: TaskStorage):
        """get_root returns the furthest ancestor."""
        root = storage.create_task("Root Goal", project="test", type=TaskType.GOAL)
        storage.save_task(root)

        project = storage.create_task(
            "Project", project="test", type=TaskType.PROJECT, parent=root.id
        )
        storage.save_task(project)

        action = storage.create_task(
            "Action", project="test", type=TaskType.ACTION, parent=project.id
        )
        storage.save_task(action)

        graph.rebuild()

        result = graph.get_root(action.id)

        assert result is not None
        assert result.id == root.id
        assert result.type == TaskType.GOAL

    def test_get_root_self_if_already_root(self, graph: TaskGraph, storage: TaskStorage):
        """get_root returns task itself if it has no parent."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        graph.rebuild()

        result = graph.get_root(root.id)

        assert result is not None
        assert result.id == root.id


class TestDependencyGraph:
    """Test dependency graph queries (Section 3.2)."""

    def test_get_dependencies(self, graph: TaskGraph, storage: TaskStorage):
        """get_dependencies returns tasks this task depends on."""
        dep1 = storage.create_task("Dependency 1", project="test")
        storage.save_task(dep1)

        dep2 = storage.create_task("Dependency 2", project="test")
        storage.save_task(dep2)

        task = storage.create_task(
            "Dependent Task", project="test", depends_on=[dep1.id, dep2.id]
        )
        storage.save_task(task)

        graph.rebuild()

        deps = graph.get_dependencies(task.id)

        dep_ids = {d.id for d in deps}
        assert dep1.id in dep_ids
        assert dep2.id in dep_ids

    def test_get_dependents_blocks(self, graph: TaskGraph, storage: TaskStorage):
        """get_dependents returns tasks blocked by this task."""
        blocker = storage.create_task("Blocker", project="test")
        storage.save_task(blocker)

        dependent1 = storage.create_task(
            "Dependent 1", project="test", depends_on=[blocker.id]
        )
        storage.save_task(dependent1)

        dependent2 = storage.create_task(
            "Dependent 2", project="test", depends_on=[blocker.id]
        )
        storage.save_task(dependent2)

        graph.rebuild()

        dependents = graph.get_dependents(blocker.id)

        dep_ids = {d.id for d in dependents}
        assert dependent1.id in dep_ids
        assert dependent2.id in dep_ids


class TestActionabilityQueries:
    """Test actionability queries (Section 3.2)."""

    def test_get_ready_returns_actionable_tasks(
        self, graph: TaskGraph, storage: TaskStorage
    ):
        """get_ready returns leaf tasks with no unmet dependencies."""
        ready = storage.create_task("Ready Task", project="test")
        ready.status = TaskStatus.ACTIVE
        storage.save_task(ready)

        blocked = storage.create_task(
            "Blocked Task", project="test", depends_on=[ready.id]
        )
        blocked.status = TaskStatus.ACTIVE
        storage.save_task(blocked)

        graph.rebuild()

        ready_tasks = graph.get_ready()

        ready_ids = {t.id for t in ready_tasks}
        assert ready.id in ready_ids
        assert blocked.id not in ready_ids

    def test_get_ready_filters_by_project(
        self, graph: TaskGraph, storage: TaskStorage
    ):
        """get_ready can filter by project."""
        task_a = storage.create_task("Task A", project="proj-a")
        task_a.status = TaskStatus.ACTIVE
        storage.save_task(task_a)

        task_b = storage.create_task("Task B", project="proj-b")
        task_b.status = TaskStatus.ACTIVE
        storage.save_task(task_b)

        graph.rebuild()

        proj_a_ready = graph.get_ready(project="proj-a")

        assert len(proj_a_ready) == 1
        assert proj_a_ready[0].project == "proj-a"

    def test_get_blocked_returns_blocked_tasks(
        self, graph: TaskGraph, storage: TaskStorage
    ):
        """get_blocked returns tasks with unmet dependencies."""
        dep = storage.create_task("Dependency", project="test")
        storage.save_task(dep)

        blocked = storage.create_task("Blocked", project="test", depends_on=[dep.id])
        storage.save_task(blocked)

        graph.rebuild()

        blocked_tasks = graph.get_blocked()

        assert any(t.id == blocked.id for t in blocked_tasks)

    def test_get_next_actions_under_goal(
        self, graph: TaskGraph, storage: TaskStorage
    ):
        """get_next_actions returns ready leaves under a goal."""
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
        action1.order = 0
        storage.save_task(action1)

        action2 = storage.create_task(
            "Action 2",
            project="test",
            type=TaskType.ACTION,
            parent=project.id,
            depends_on=[action1.id],
        )
        action2.status = TaskStatus.ACTIVE
        action2.order = 1
        storage.save_task(action2)

        graph.rebuild()

        next_actions = graph.get_next_actions(goal.id)

        action_ids = {a.id for a in next_actions}
        assert action1.id in action_ids
        assert action2.id not in action_ids  # Blocked


class TestTreeDisplay:
    """Test tree display formatting (Section 5.2)."""

    def test_format_tree_basic(self, graph: TaskGraph, storage: TaskStorage):
        """format_tree produces expected output structure."""
        parent = storage.create_task(
            "Write Chapter 1", project="book", type=TaskType.PROJECT
        )
        parent.status = TaskStatus.ACTIVE
        storage.save_task(parent)

        outline = storage.create_task(
            "Outline chapter 1",
            project="book",
            type=TaskType.ACTION,
            parent=parent.id,
        )
        outline.order = 0
        outline.status = TaskStatus.ACTIVE
        storage.save_task(outline)

        draft = storage.create_task(
            "Write first draft",
            project="book",
            type=TaskType.ACTION,
            parent=parent.id,
            depends_on=[outline.id],
        )
        draft.order = 1
        draft.status = TaskStatus.ACTIVE
        storage.save_task(draft)

        revise = storage.create_task(
            "Revise draft",
            project="book",
            type=TaskType.ACTION,
            parent=parent.id,
            depends_on=[draft.id],
        )
        revise.order = 2
        revise.status = TaskStatus.ACTIVE
        storage.save_task(revise)

        graph.rebuild()

        tree = graph.format_tree(parent.id)

        # Check structure
        assert "Write Chapter 1" in tree
        assert "[project]" in tree
        assert "[active]" in tree
        assert "Outline chapter 1" in tree
        assert "Write first draft" in tree
        assert "Revise draft" in tree
        assert "[blocked]" in tree  # draft and revise are blocked
        assert "Progress: 0/3 complete" in tree
        assert "Next action: Outline chapter 1" in tree

    def test_format_tree_with_checkboxes(self, graph: TaskGraph, storage: TaskStorage):
        """format_tree shows checkboxes for task status."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        done = storage.create_task("Done Task", project="test", parent=parent.id)
        done.status = TaskStatus.DONE
        done.order = 0
        storage.save_task(done)

        pending = storage.create_task("Pending Task", project="test", parent=parent.id)
        pending.status = TaskStatus.ACTIVE
        pending.order = 1
        storage.save_task(pending)

        graph.rebuild()

        tree = graph.format_tree(parent.id)

        assert "[x] Done Task" in tree
        assert "[ ] Pending Task" in tree

    def test_format_tree_nonexistent_task(self, graph: TaskGraph):
        """format_tree handles missing task gracefully."""
        graph.rebuild()
        tree = graph.format_tree("20260112-nonexistent")

        assert "Task not found" in tree

    def test_format_tree_compact(self, graph: TaskGraph, storage: TaskStorage):
        """format_tree_compact omits metadata."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        child = storage.create_task("Child", project="test", parent=parent.id)
        storage.save_task(child)

        graph.rebuild()

        tree = graph.format_tree_compact(parent.id)

        assert "Parent" in tree
        assert "Child" in tree
        # Should not include metadata
        assert "[order=" not in tree
        assert "Progress:" not in tree

    def test_format_tree_nested_children(self, graph: TaskGraph, storage: TaskStorage):
        """format_tree handles deeply nested structures."""
        root = storage.create_task("Root", project="test")
        storage.save_task(root)

        child = storage.create_task("Child", project="test", parent=root.id)
        storage.save_task(child)

        grandchild = storage.create_task("Grandchild", project="test", parent=child.id)
        storage.save_task(grandchild)

        graph.rebuild()

        tree = graph.format_tree(root.id)

        assert "Root" in tree
        assert "Child" in tree
        assert "Grandchild" in tree
        # Check indentation is present (nested structure)
        lines = tree.split("\n")
        assert any("│" in line or "├" in line or "└" in line for line in lines)

    def test_format_tree_with_custom_options(
        self, graph: TaskGraph, storage: TaskStorage
    ):
        """format_tree respects custom display options."""
        parent = storage.create_task("Parent", project="test")
        storage.save_task(parent)

        child = storage.create_task("Child", project="test", parent=parent.id)
        storage.save_task(child)

        graph.rebuild()

        options = TreeDisplayOptions(
            show_type=False,
            show_status=False,
            show_order=False,
            show_blocked=False,
            show_progress=False,
            show_next_action=False,
        )
        tree = graph.format_tree(parent.id, options)

        # Should not include type/status/order
        assert "[task]" not in tree
        assert "[inbox]" not in tree
        assert "[order=" not in tree


class TestAdditionalQueries:
    """Test additional query methods."""

    def test_get_task(self, graph: TaskGraph, storage: TaskStorage):
        """get_task retrieves by ID."""
        task = storage.create_task("Test Task", project="test")
        storage.save_task(task)

        graph.rebuild()

        result = graph.get_task(task.id)

        assert result is not None
        assert result.id == task.id
        assert result.title == "Test Task"

    def test_get_task_nonexistent(self, graph: TaskGraph):
        """get_task returns None for missing task."""
        graph.rebuild()
        result = graph.get_task("20260112-nonexistent")
        assert result is None

    def test_get_roots(self, graph: TaskGraph, storage: TaskStorage):
        """get_roots returns all tasks without parents."""
        root1 = storage.create_task("Root 1", project="test")
        storage.save_task(root1)

        root2 = storage.create_task("Root 2", project="test")
        storage.save_task(root2)

        child = storage.create_task("Child", project="test", parent=root1.id)
        storage.save_task(child)

        graph.rebuild()

        roots = graph.get_roots()

        root_ids = {r.id for r in roots}
        assert root1.id in root_ids
        assert root2.id in root_ids
        assert child.id not in root_ids

    def test_get_by_project(self, graph: TaskGraph, storage: TaskStorage):
        """get_by_project returns all tasks in a project."""
        storage.save_task(storage.create_task("Task A1", project="proj-a"))
        storage.save_task(storage.create_task("Task A2", project="proj-a"))
        storage.save_task(storage.create_task("Task B1", project="proj-b"))

        graph.rebuild()

        proj_a = graph.get_by_project("proj-a")

        assert len(proj_a) == 2
        assert all(t.project == "proj-a" for t in proj_a)


class TestLoadRebuild:
    """Test index load and rebuild."""

    def test_load_returns_false_if_no_index(self, graph: TaskGraph):
        """load returns False when index doesn't exist."""
        result = graph.load()
        assert result is False

    def test_rebuild_then_load(self, graph: TaskGraph, storage: TaskStorage):
        """rebuild creates index that can be loaded."""
        storage.save_task(storage.create_task("Task 1", project="test"))
        storage.save_task(storage.create_task("Task 2", project="test"))

        graph.rebuild()

        # Create new graph instance
        graph2 = TaskGraph(graph._index.data_root)
        result = graph2.load()

        assert result is True
        roots = graph2.get_roots()
        assert len(roots) == 2
