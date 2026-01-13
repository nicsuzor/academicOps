#!/usr/bin/env python3
"""Tests for Tasks v2 MCP server.

Tests all MCP tools exposed by mcp_servers/tasks_server.py:
- CRUD operations (create, get, update, complete)
- Query operations (ready, blocked, tree, children, dependencies)
- Decomposition operations
- Bulk operations
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest


@pytest.fixture
def task_data_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create temporary data directory for task tests.

    Sets up the directory structure expected by Tasks v2:
    - $ACA_DATA/<project>/tasks/ for project tasks
    - $ACA_DATA/tasks/inbox/ for inbox tasks
    - $ACA_DATA/tasks/index.json for the index

    Args:
        tmp_path: pytest temp directory
        monkeypatch: pytest monkeypatch fixture

    Returns:
        Path to temporary data root
    """
    data_root = tmp_path / "data"

    # Create global tasks directory
    (data_root / "tasks" / "inbox").mkdir(parents=True)

    # Create a test project directory
    (data_root / "book" / "tasks").mkdir(parents=True)

    # Set environment variable
    monkeypatch.setenv("ACA_DATA", str(data_root))
    monkeypatch.setenv("AOPS", str(tmp_path / "aops"))

    # Create minimal AOPS structure for paths.py validation
    (tmp_path / "aops" / "lib").mkdir(parents=True)

    return data_root


class TestCreateTask:
    """Test create_task tool."""

    def test_create_minimal_task(self, task_data_dir: Path):
        """Test creating task with only required fields."""
        from mcp_servers.tasks_server import create_task

        result = create_task.fn(title="Test task")

        assert result["success"] is True
        assert result["task"]["title"] == "Test task"
        assert result["task"]["type"] == "task"
        assert result["task"]["status"] == "inbox"
        assert result["task"]["priority"] == 2

        # Verify ID format
        task_id = result["task"]["id"]
        assert task_id.startswith(datetime.now(UTC).strftime("%Y%m%d"))

    def test_create_task_with_all_fields(self, task_data_dir: Path):
        """Test creating task with all optional fields."""
        from mcp_servers.tasks_server import create_task

        result = create_task.fn(
            title="Full task",
            type="goal",
            project="book",
            priority=1,
            order=5,
            due="2026-12-31T23:59:59Z",
            tags=["important", "urgent"],
            body="This is the task body.",
        )

        assert result["success"] is True
        task = result["task"]
        assert task["title"] == "Full task"
        assert task["type"] == "goal"
        assert task["project"] == "book"
        assert task["priority"] == 1
        assert task["order"] == 5
        assert "important" in task["tags"]
        assert task["body"] == "This is the task body."

    def test_create_task_with_parent(self, task_data_dir: Path):
        """Test creating task with parent relationship."""
        from mcp_servers.tasks_server import create_task

        # Create parent
        parent_result = create_task.fn(title="Parent task", type="goal", project="book")
        assert parent_result["success"] is True
        parent_id = parent_result["task"]["id"]

        # Create child
        child_result = create_task.fn(
            title="Child task",
            type="task",
            project="book",
            parent=parent_id,
        )

        assert child_result["success"] is True
        assert child_result["task"]["parent"] == parent_id
        assert child_result["task"]["depth"] == 1

    def test_create_task_with_dependencies(self, task_data_dir: Path):
        """Test creating task with depends_on."""
        from mcp_servers.tasks_server import create_task

        # Create dependency
        dep_result = create_task.fn(title="Dependency task", project="book")
        assert dep_result["success"] is True
        dep_id = dep_result["task"]["id"]

        # Create dependent task
        result = create_task.fn(
            title="Dependent task",
            project="book",
            depends_on=[dep_id],
        )

        assert result["success"] is True
        assert dep_id in result["task"]["depends_on"]

    def test_create_task_invalid_type(self, task_data_dir: Path):
        """Test creating task with invalid type fails."""
        from mcp_servers.tasks_server import create_task

        result = create_task.fn(title="Bad task", type="invalid")

        assert result["success"] is False
        assert "Invalid task type" in result["message"]

    def test_create_task_invalid_due_date(self, task_data_dir: Path):
        """Test creating task with invalid due date fails."""
        from mcp_servers.tasks_server import create_task

        result = create_task.fn(title="Bad task", due="not-a-date")

        assert result["success"] is False
        assert "Invalid due date" in result["message"]


class TestGetTask:
    """Test get_task tool."""

    def test_get_existing_task(self, task_data_dir: Path):
        """Test getting an existing task."""
        from mcp_servers.tasks_server import create_task, get_task

        # Create task first
        create_result = create_task.fn(title="Test task", body="Test body")
        assert create_result["success"] is True
        task_id = create_result["task"]["id"]

        # Get task
        result = get_task.fn(id=task_id)

        assert result["success"] is True
        assert result["task"]["id"] == task_id
        assert result["task"]["title"] == "Test task"
        # Body includes auto-generated H1 header from to_markdown()
        assert "Test body" in result["task"]["body"]

    def test_get_nonexistent_task(self, task_data_dir: Path):
        """Test getting a task that doesn't exist."""
        from mcp_servers.tasks_server import get_task

        result = get_task.fn(id="20260101-nonexistent")

        assert result["success"] is False
        assert result["task"] is None
        assert "not found" in result["message"].lower()


class TestUpdateTask:
    """Test update_task tool."""

    def test_update_title(self, task_data_dir: Path):
        """Test updating task title."""
        from mcp_servers.tasks_server import create_task, update_task

        # Create task
        create_result = create_task.fn(title="Original title")
        task_id = create_result["task"]["id"]

        # Update title
        result = update_task.fn(id=task_id, title="New title")

        assert result["success"] is True
        assert result["task"]["title"] == "New title"
        assert "title" in result["modified_fields"]

    def test_update_multiple_fields(self, task_data_dir: Path):
        """Test updating multiple fields at once."""
        from mcp_servers.tasks_server import create_task, update_task

        # Create task
        create_result = create_task.fn(title="Test task", priority=2)
        task_id = create_result["task"]["id"]

        # Update multiple fields
        result = update_task.fn(
            id=task_id,
            title="Updated title",
            priority=1,
            status="active",
            tags=["new-tag"],
        )

        assert result["success"] is True
        assert result["task"]["title"] == "Updated title"
        assert result["task"]["priority"] == 1
        assert result["task"]["status"] == "active"
        assert "new-tag" in result["task"]["tags"]
        assert set(result["modified_fields"]) == {"title", "priority", "status", "tags"}

    def test_update_nonexistent_task(self, task_data_dir: Path):
        """Test updating a task that doesn't exist."""
        from mcp_servers.tasks_server import update_task

        result = update_task.fn(id="20260101-nonexistent", title="New title")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_update_no_changes(self, task_data_dir: Path):
        """Test updating with no fields provided."""
        from mcp_servers.tasks_server import create_task, update_task

        # Create task
        create_result = create_task.fn(title="Test task")
        task_id = create_result["task"]["id"]

        # Update with no fields
        result = update_task.fn(id=task_id)

        assert result["success"] is True
        assert result["modified_fields"] == []
        assert "No changes" in result["message"]

    def test_update_invalid_status(self, task_data_dir: Path):
        """Test updating with invalid status fails."""
        from mcp_servers.tasks_server import create_task, update_task

        create_result = create_task.fn(title="Test task")
        task_id = create_result["task"]["id"]

        result = update_task.fn(id=task_id, status="invalid")

        assert result["success"] is False
        assert "Invalid status" in result["message"]

    def test_update_clear_optional_field(self, task_data_dir: Path):
        """Test clearing optional fields with empty string."""
        from mcp_servers.tasks_server import create_task, update_task

        # Create task with project
        create_result = create_task.fn(title="Test task", project="book")
        task_id = create_result["task"]["id"]

        # Clear project
        result = update_task.fn(id=task_id, project="")

        assert result["success"] is True
        assert result["task"]["project"] is None


class TestCompleteTask:
    """Test complete_task tool."""

    def test_complete_task(self, task_data_dir: Path):
        """Test completing a task."""
        from mcp_servers.tasks_server import complete_task, create_task

        # Create task
        create_result = create_task.fn(title="Task to complete")
        task_id = create_result["task"]["id"]

        # Complete task
        result = complete_task.fn(id=task_id)

        assert result["success"] is True
        assert result["task"]["status"] == "done"

    def test_complete_nonexistent_task(self, task_data_dir: Path):
        """Test completing a task that doesn't exist."""
        from mcp_servers.tasks_server import complete_task

        result = complete_task.fn(id="20260101-nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"].lower()


class TestGetReadyTasks:
    """Test get_ready_tasks tool."""

    def test_get_ready_tasks_empty(self, task_data_dir: Path):
        """Test getting ready tasks when none exist."""
        from mcp_servers.tasks_server import get_ready_tasks

        result = get_ready_tasks.fn()

        assert result["success"] is True
        assert result["tasks"] == []
        assert result["count"] == 0

    def test_get_ready_tasks(self, task_data_dir: Path):
        """Test getting ready tasks."""
        from mcp_servers.tasks_server import create_task, get_ready_tasks

        # Create some tasks
        create_task.fn(title="Task 1", project="book")
        create_task.fn(title="Task 2", project="book")

        result = get_ready_tasks.fn()

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["tasks"]) == 2

    def test_get_ready_tasks_filter_by_project(self, task_data_dir: Path):
        """Test filtering ready tasks by project."""
        from mcp_servers.tasks_server import create_task, get_ready_tasks

        # Create tasks in different projects
        create_task.fn(title="Book task", project="book")
        create_task.fn(title="Inbox task")  # No project (inbox)

        result = get_ready_tasks.fn(project="book")

        assert result["success"] is True
        assert result["count"] == 1
        assert result["tasks"][0]["project"] == "book"


class TestGetBlockedTasks:
    """Test get_blocked_tasks tool."""

    def test_get_blocked_tasks_empty(self, task_data_dir: Path):
        """Test getting blocked tasks when none exist."""
        from mcp_servers.tasks_server import get_blocked_tasks

        result = get_blocked_tasks.fn()

        assert result["success"] is True
        assert result["tasks"] == []
        assert result["count"] == 0

    def test_get_blocked_tasks_with_dependencies(self, task_data_dir: Path):
        """Test getting tasks blocked by dependencies."""
        from mcp_servers.tasks_server import create_task, get_blocked_tasks

        # Create dependency (incomplete)
        dep_result = create_task.fn(title="Dependency", project="book")
        dep_id = dep_result["task"]["id"]

        # Create dependent task
        create_task.fn(title="Blocked task", project="book", depends_on=[dep_id])

        result = get_blocked_tasks.fn()

        assert result["success"] is True
        assert result["count"] == 1
        assert result["tasks"][0]["title"] == "Blocked task"


class TestGetTaskTree:
    """Test get_task_tree tool."""

    def test_get_tree_single_task(self, task_data_dir: Path):
        """Test getting tree for a task with no children."""
        from mcp_servers.tasks_server import create_task, get_task_tree

        # Create task
        create_result = create_task.fn(title="Root task", project="book")
        task_id = create_result["task"]["id"]

        result = get_task_tree.fn(id=task_id)

        assert result["success"] is True
        assert result["tree"]["task"]["id"] == task_id
        assert result["tree"]["children"] == []

    def test_get_tree_with_children(self, task_data_dir: Path):
        """Test getting tree for a task with children."""
        from mcp_servers.tasks_server import create_task, decompose_task, get_task_tree

        # Create parent
        parent_result = create_task.fn(title="Parent", type="project", project="book")
        parent_id = parent_result["task"]["id"]

        # Decompose into children
        decompose_task.fn(
            id=parent_id,
            children=[
                {"title": "Child 1", "type": "action"},
                {"title": "Child 2", "type": "action"},
            ],
        )

        result = get_task_tree.fn(id=parent_id)

        assert result["success"] is True
        assert len(result["tree"]["children"]) == 2

    def test_get_tree_nonexistent(self, task_data_dir: Path):
        """Test getting tree for nonexistent task."""
        from mcp_servers.tasks_server import get_task_tree

        result = get_task_tree.fn(id="20260101-nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"].lower()


class TestGetChildren:
    """Test get_children tool."""

    def test_get_children_empty(self, task_data_dir: Path):
        """Test getting children for a leaf task."""
        from mcp_servers.tasks_server import create_task, get_children

        # Create leaf task
        create_result = create_task.fn(title="Leaf task", project="book")
        task_id = create_result["task"]["id"]

        result = get_children.fn(id=task_id)

        assert result["success"] is True
        assert result["tasks"] == []
        assert result["count"] == 0

    def test_get_children_with_children(self, task_data_dir: Path):
        """Test getting children for a parent task."""
        from mcp_servers.tasks_server import create_task, decompose_task, get_children

        # Create parent
        parent_result = create_task.fn(title="Parent", type="project", project="book")
        parent_id = parent_result["task"]["id"]

        # Decompose
        decompose_task.fn(
            id=parent_id,
            children=[
                {"title": "Child 1", "order": 0},
                {"title": "Child 2", "order": 1},
            ],
        )

        result = get_children.fn(id=parent_id)

        assert result["success"] is True
        assert result["count"] == 2
        # Verify order
        assert result["tasks"][0]["title"] == "Child 1"
        assert result["tasks"][1]["title"] == "Child 2"

    def test_get_children_nonexistent_parent(self, task_data_dir: Path):
        """Test getting children for nonexistent parent."""
        from mcp_servers.tasks_server import get_children

        result = get_children.fn(id="20260101-nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"].lower()


class TestGetDependencies:
    """Test get_dependencies tool."""

    def test_get_dependencies_empty(self, task_data_dir: Path):
        """Test getting dependencies for a task with none."""
        from mcp_servers.tasks_server import create_task, get_dependencies

        create_result = create_task.fn(title="No deps", project="book")
        task_id = create_result["task"]["id"]

        result = get_dependencies.fn(id=task_id)

        assert result["success"] is True
        assert result["tasks"] == []
        assert result["count"] == 0

    def test_get_dependencies_with_deps(self, task_data_dir: Path):
        """Test getting dependencies for a task with dependencies."""
        from mcp_servers.tasks_server import create_task, get_dependencies

        # Create dependencies
        dep1_result = create_task.fn(title="Dep 1", project="book")
        dep2_result = create_task.fn(title="Dep 2", project="book")
        dep1_id = dep1_result["task"]["id"]
        dep2_id = dep2_result["task"]["id"]

        # Create dependent task
        create_result = create_task.fn(
            title="Dependent",
            project="book",
            depends_on=[dep1_id, dep2_id],
        )
        task_id = create_result["task"]["id"]

        result = get_dependencies.fn(id=task_id)

        assert result["success"] is True
        assert result["count"] == 2
        dep_ids = [t["id"] for t in result["tasks"]]
        assert dep1_id in dep_ids
        assert dep2_id in dep_ids


class TestDecomposeTask:
    """Test decompose_task tool."""

    def test_decompose_task(self, task_data_dir: Path):
        """Test decomposing a task into children."""
        from mcp_servers.tasks_server import create_task, decompose_task, get_task

        # Create parent
        parent_result = create_task.fn(title="Parent", type="project", project="book")
        parent_id = parent_result["task"]["id"]

        # Decompose
        result = decompose_task.fn(
            id=parent_id,
            children=[
                {"title": "Step 1", "type": "action", "order": 0},
                {"title": "Step 2", "type": "action", "order": 1},
                {"title": "Step 3", "type": "action", "order": 2},
            ],
        )

        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["tasks"]) == 3

        # Verify parent is no longer a leaf
        parent = get_task.fn(id=parent_id)
        assert parent["task"]["leaf"] is False

        # Verify children have correct parent
        for child in result["tasks"]:
            assert child["parent"] == parent_id

    def test_decompose_with_dependencies(self, task_data_dir: Path):
        """Test decomposing with internal dependencies."""
        from mcp_servers.tasks_server import create_task, decompose_task

        # Create parent
        parent_result = create_task.fn(title="Parent", type="project", project="book")
        parent_id = parent_result["task"]["id"]

        # Create first child to get its ID
        result1 = decompose_task.fn(
            id=parent_id,
            children=[{"title": "Step 1", "type": "action", "order": 0}],
        )
        step1_id = result1["tasks"][0]["id"]

        # Create dependent child (note: this is a second decomposition)
        from mcp_servers.tasks_server import create_task as ct

        child_result = ct.fn(
            title="Step 2",
            type="action",
            project="book",
            parent=parent_id,
            depends_on=[step1_id],
            order=1,
        )

        assert child_result["success"] is True
        assert step1_id in child_result["task"]["depends_on"]

    def test_decompose_empty_children(self, task_data_dir: Path):
        """Test decomposing with empty children list fails."""
        from mcp_servers.tasks_server import create_task, decompose_task

        parent_result = create_task.fn(title="Parent", project="book")
        parent_id = parent_result["task"]["id"]

        result = decompose_task.fn(id=parent_id, children=[])

        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_decompose_missing_title(self, task_data_dir: Path):
        """Test decomposing with child missing title fails."""
        from mcp_servers.tasks_server import create_task, decompose_task

        parent_result = create_task.fn(title="Parent", project="book")
        parent_id = parent_result["task"]["id"]

        result = decompose_task.fn(
            id=parent_id,
            children=[{"type": "action"}],  # Missing title
        )

        assert result["success"] is False
        assert "title" in result["message"].lower()

    def test_decompose_nonexistent_parent(self, task_data_dir: Path):
        """Test decomposing nonexistent parent fails."""
        from mcp_servers.tasks_server import decompose_task

        result = decompose_task.fn(
            id="20260101-nonexistent",
            children=[{"title": "Child"}],
        )

        assert result["success"] is False
        assert "not found" in result["message"].lower()


class TestCompleteTasks:
    """Test complete_tasks bulk tool."""

    def test_complete_multiple_tasks(self, task_data_dir: Path):
        """Test completing multiple tasks at once."""
        from mcp_servers.tasks_server import complete_tasks, create_task

        # Create tasks
        task1 = create_task.fn(title="Task 1", project="book")
        task2 = create_task.fn(title="Task 2", project="book")
        task3 = create_task.fn(title="Task 3", project="book")

        ids = [task1["task"]["id"], task2["task"]["id"], task3["task"]["id"]]

        result = complete_tasks.fn(ids=ids)

        assert result["success"] is True
        assert result["success_count"] == 3
        assert result["failure_count"] == 0
        assert len(result["tasks"]) == 3

        # All tasks should be done
        for task in result["tasks"]:
            assert task["status"] == "done"

    def test_complete_tasks_partial_failure(self, task_data_dir: Path):
        """Test completing with some invalid IDs."""
        from mcp_servers.tasks_server import complete_tasks, create_task

        # Create one valid task
        task1 = create_task.fn(title="Valid task", project="book")
        valid_id = task1["task"]["id"]

        result = complete_tasks.fn(ids=[valid_id, "20260101-nonexistent"])

        assert result["success"] is False
        assert result["success_count"] == 1
        assert result["failure_count"] == 1
        assert len(result["failures"]) == 1

    def test_complete_tasks_empty_list(self, task_data_dir: Path):
        """Test completing with empty list."""
        from mcp_servers.tasks_server import complete_tasks

        result = complete_tasks.fn(ids=[])

        assert result["success"] is True
        assert result["success_count"] == 0


class TestReorderChildren:
    """Test reorder_children tool."""

    def test_reorder_children(self, task_data_dir: Path):
        """Test reordering children."""
        from mcp_servers.tasks_server import (
            create_task,
            decompose_task,
            get_children,
            reorder_children,
        )

        # Create parent with children
        parent_result = create_task.fn(title="Parent", type="project", project="book")
        parent_id = parent_result["task"]["id"]

        decompose_result = decompose_task.fn(
            id=parent_id,
            children=[
                {"title": "First", "order": 0},
                {"title": "Second", "order": 1},
                {"title": "Third", "order": 2},
            ],
        )

        child_ids = [t["id"] for t in decompose_result["tasks"]]

        # Reverse order
        reversed_order = list(reversed(child_ids))
        result = reorder_children.fn(parent_id=parent_id, order=reversed_order)

        assert result["success"] is True

        # Verify new order
        children = get_children.fn(id=parent_id)
        titles = [c["title"] for c in children["tasks"]]
        assert titles == ["Third", "Second", "First"]

    def test_reorder_invalid_parent(self, task_data_dir: Path):
        """Test reordering with invalid parent."""
        from mcp_servers.tasks_server import reorder_children

        result = reorder_children.fn(
            parent_id="20260101-nonexistent",
            order=["a", "b"],
        )

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_reorder_invalid_child_ids(self, task_data_dir: Path):
        """Test reordering with invalid child IDs."""
        from mcp_servers.tasks_server import create_task, decompose_task, reorder_children

        # Create parent with children
        parent_result = create_task.fn(title="Parent", type="project", project="book")
        parent_id = parent_result["task"]["id"]

        decompose_task.fn(
            id=parent_id,
            children=[{"title": "Child", "order": 0}],
        )

        # Try to reorder with invalid ID
        result = reorder_children.fn(
            parent_id=parent_id,
            order=["invalid-child-id"],
        )

        assert result["success"] is False
        assert "Invalid" in result["message"]


class TestRebuildIndex:
    """Test rebuild_index tool."""

    def test_rebuild_index(self, task_data_dir: Path):
        """Test rebuilding the index."""
        from mcp_servers.tasks_server import create_task, rebuild_index

        # Create some tasks
        create_task.fn(title="Task 1", project="book")
        create_task.fn(title="Task 2", project="book")

        result = rebuild_index.fn()

        assert result["success"] is True
        assert result["stats"]["total"] == 2


class TestGetIndexStats:
    """Test get_index_stats tool."""

    def test_get_index_stats(self, task_data_dir: Path):
        """Test getting index statistics."""
        from mcp_servers.tasks_server import create_task, get_index_stats

        # Create some tasks
        create_task.fn(title="Goal", type="goal", project="book")
        create_task.fn(title="Task", type="task", project="book")

        result = get_index_stats.fn()

        assert result["success"] is True
        assert result["stats"]["total"] == 2
        assert "by_type" in result["stats"]
        assert "by_status" in result["stats"]


class TestIntegrationWorkflow:
    """Integration tests for complete workflows."""

    def test_book_writing_workflow(self, task_data_dir: Path):
        """Test a realistic book-writing decomposition workflow."""
        from mcp_servers.tasks_server import (
            complete_task,
            create_task,
            decompose_task,
            get_ready_tasks,
            get_task_tree,
        )

        # Create root goal
        goal_result = create_task.fn(
            title="Write a book",
            type="goal",
            project="book",
        )
        goal_id = goal_result["task"]["id"]

        # Decompose into chapters
        chapters = decompose_task.fn(
            id=goal_id,
            children=[
                {"title": "Write Chapter 1", "type": "project", "order": 0},
                {"title": "Write Chapter 2", "type": "project", "order": 1},
            ],
        )
        ch1_id = chapters["tasks"][0]["id"]

        # Decompose Chapter 1 into actions
        ch1_actions = decompose_task.fn(
            id=ch1_id,
            children=[
                {"title": "Outline Ch1", "type": "action", "order": 0},
                {"title": "Draft Ch1", "type": "action", "order": 1},
                {"title": "Revise Ch1", "type": "action", "order": 2},
            ],
        )

        # Check tree structure
        tree = get_task_tree.fn(id=goal_id)
        assert tree["success"] is True
        assert len(tree["tree"]["children"]) == 2  # Two chapters
        assert len(tree["tree"]["children"][0]["children"]) == 3  # Ch1 has 3 actions

        # Check ready tasks - only leaf tasks with no deps should be ready
        ready = get_ready_tasks.fn(project="book")
        assert ready["success"] is True
        # Ch1 actions and Ch2 should be ready (Ch2 is still a leaf)
        ready_titles = [t["title"] for t in ready["tasks"]]
        assert "Outline Ch1" in ready_titles

        # Complete first action
        outline_id = ch1_actions["tasks"][0]["id"]
        complete_task.fn(id=outline_id)

        # Check that outline is no longer in ready tasks
        ready_after = get_ready_tasks.fn(project="book")
        ready_titles_after = [t["title"] for t in ready_after["tasks"]]
        assert "Outline Ch1" not in ready_titles_after

    def test_dependency_chain_workflow(self, task_data_dir: Path):
        """Test workflow with sequential dependencies."""
        from mcp_servers.tasks_server import (
            complete_task,
            create_task,
            get_blocked_tasks,
            get_ready_tasks,
        )

        # Create three tasks with dependencies
        task1 = create_task.fn(title="Step 1", project="book")
        task1_id = task1["task"]["id"]

        task2 = create_task.fn(
            title="Step 2",
            project="book",
            depends_on=[task1_id],
        )
        task2_id = task2["task"]["id"]

        task3 = create_task.fn(
            title="Step 3",
            project="book",
            depends_on=[task2_id],
        )

        # Check ready - only Step 1 should be ready
        ready = get_ready_tasks.fn(project="book")
        ready_titles = [t["title"] for t in ready["tasks"]]
        assert ready_titles == ["Step 1"]

        # Check blocked - Step 2 and 3 should be blocked
        blocked = get_blocked_tasks.fn()
        blocked_titles = [t["title"] for t in blocked["tasks"]]
        assert "Step 2" in blocked_titles
        assert "Step 3" in blocked_titles

        # Complete Step 1
        complete_task.fn(id=task1_id)

        # Now Step 2 should be ready
        ready_after = get_ready_tasks.fn(project="book")
        ready_titles_after = [t["title"] for t in ready_after["tasks"]]
        assert "Step 2" in ready_titles_after
        assert "Step 1" not in ready_titles_after

        # Step 3 should still be blocked
        blocked_after = get_blocked_tasks.fn()
        blocked_titles_after = [t["title"] for t in blocked_after["tasks"]]
        assert "Step 3" in blocked_titles_after
        assert "Step 2" not in blocked_titles_after
