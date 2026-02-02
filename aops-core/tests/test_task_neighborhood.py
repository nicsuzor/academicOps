"""Tests for get_task_neighborhood() MCP tool.

Tests the graph neighborhood data access tool per P#78 (Dumb Server, Smart Agent):
- Returns raw graph data for agent interpretation
- No similarity scoring or candidate selection
- Complete relationship data exposed
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# Add framework roots to path for lib imports
import sys

TESTS_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = TESTS_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.task_index import TaskIndex
from lib.task_model import Task, TaskStatus, TaskType
from lib.task_storage import TaskStorage


class TestGetTaskNeighborhood:
    """Test get_task_neighborhood() returns correct graph data."""

    @pytest.fixture
    def storage_with_tasks(self, tmp_path: Path) -> TaskStorage:
        """Create a storage with a graph of related tasks."""
        # Create directory structure
        project_tasks = tmp_path / "testproj" / "tasks"
        project_tasks.mkdir(parents=True)
        inbox = tmp_path / "tasks" / "inbox"
        inbox.mkdir(parents=True)

        storage = TaskStorage(data_root=tmp_path)

        # Create parent task
        parent = storage.create_task(
            title="Parent Goal",
            project="testproj",
            type=TaskType.GOAL,
        )
        storage.save_task(parent)

        # Create target task (the one we'll query)
        target = storage.create_task(
            title="Target Task",
            project="testproj",
            type=TaskType.TASK,
            parent=parent.id,
        )
        storage.save_task(target)

        # Create child of target
        child = storage.create_task(
            title="Child Action",
            project="testproj",
            type=TaskType.ACTION,
            parent=target.id,
        )
        storage.save_task(child)

        # Create task that depends on target (target blocks this)
        dependent = storage.create_task(
            title="Dependent Task",
            project="testproj",
            type=TaskType.TASK,
            depends_on=[target.id],
        )
        storage.save_task(dependent)

        # Create task that target depends on
        dependency = storage.create_task(
            title="Dependency Task",
            project="testproj",
            type=TaskType.TASK,
        )
        storage.save_task(dependency)

        # Update target to depend on dependency
        target.depends_on = [dependency.id]
        storage.save_task(target)

        # Create task with soft dependency on target
        soft_dependent = storage.create_task(
            title="Soft Dependent Task",
            project="testproj",
            type=TaskType.TASK,
            soft_depends_on=[target.id],
        )
        storage.save_task(soft_dependent)

        # Create orphan task (no parent, no dependencies)
        orphan = storage.create_task(
            title="Orphan Task",
            project="testproj",
            type=TaskType.TASK,
        )
        storage.save_task(orphan)

        # Create another project task (not orphan - has parent)
        sibling = storage.create_task(
            title="Sibling Task",
            project="testproj",
            type=TaskType.TASK,
            parent=parent.id,
        )
        storage.save_task(sibling)

        # Build index
        index = TaskIndex(tmp_path)
        index.rebuild()

        # Store IDs for test access
        storage._test_ids = {
            "parent": parent.id,
            "target": target.id,
            "child": child.id,
            "dependent": dependent.id,
            "dependency": dependency.id,
            "soft_dependent": soft_dependent.id,
            "orphan": orphan.id,
            "sibling": sibling.id,
        }

        return storage

    def test_task_not_found(self, tmp_path: Path) -> None:
        """Returns error when task doesn't exist."""
        from mcp_servers import tasks_server

        # Setup minimal storage
        inbox = tmp_path / "tasks" / "inbox"
        inbox.mkdir(parents=True)

        storage = TaskStorage(data_root=tmp_path)

        # Build empty index
        index = TaskIndex(tmp_path)
        index.rebuild()

        with patch.object(tasks_server, "_get_storage", return_value=storage):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn("nonexistent-id")

        assert result["success"] is False
        assert result["task"] is None
        assert "not found" in result["message"].lower()

    def test_returns_task_data(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Returns full task data for the requested task."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True
        assert result["task"] is not None
        assert result["task"]["id"] == target_id
        assert result["task"]["title"] == "Target Task"
        assert result["task"]["type"] == "task"

    def test_returns_parent_relationship(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Returns parent task in existing_relationships."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]
        parent_id = storage_with_tasks._test_ids["parent"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True
        parent = result["existing_relationships"]["parent"]
        assert parent is not None
        assert parent["id"] == parent_id
        assert parent["title"] == "Parent Goal"

    def test_returns_children_relationship(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Returns child tasks in existing_relationships."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]
        child_id = storage_with_tasks._test_ids["child"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True
        children = result["existing_relationships"]["children"]
        assert len(children) == 1
        assert children[0]["id"] == child_id
        assert children[0]["title"] == "Child Action"

    def test_returns_depends_on_relationship(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Returns dependency tasks in existing_relationships."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]
        dependency_id = storage_with_tasks._test_ids["dependency"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True
        depends_on = result["existing_relationships"]["depends_on"]
        assert len(depends_on) == 1
        assert depends_on[0]["id"] == dependency_id
        assert depends_on[0]["title"] == "Dependency Task"

    def test_returns_blocks_relationship(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Returns tasks that depend on this task in existing_relationships."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]
        dependent_id = storage_with_tasks._test_ids["dependent"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True
        blocks = result["existing_relationships"]["blocks"]
        assert len(blocks) == 1
        assert blocks[0]["id"] == dependent_id
        assert blocks[0]["title"] == "Dependent Task"

    def test_returns_soft_blocks_relationship(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Returns tasks that soft-depend on this task in existing_relationships."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]
        soft_dependent_id = storage_with_tasks._test_ids["soft_dependent"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True
        soft_blocks = result["existing_relationships"]["soft_blocks"]
        assert len(soft_blocks) == 1
        assert soft_blocks[0]["id"] == soft_dependent_id
        assert soft_blocks[0]["title"] == "Soft Dependent Task"

    def test_returns_same_project_tasks(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Returns all tasks in the same project (excluding self)."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True
        same_project = result["same_project_tasks"]

        # Should include all project tasks except target itself
        # parent, child, dependent, dependency, soft_dependent, orphan, sibling = 7 tasks
        assert len(same_project) == 7

        # Target should NOT be in the list
        task_ids = [t["id"] for t in same_project]
        assert target_id not in task_ids

        # All others should be present
        for key in ["parent", "child", "dependent", "dependency", "soft_dependent", "orphan", "sibling"]:
            assert storage_with_tasks._test_ids[key] in task_ids

    def test_returns_orphan_tasks(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Returns tasks with no parent AND no dependencies."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]
        orphan_id = storage_with_tasks._test_ids["orphan"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True
        orphans = result["orphan_tasks"]

        # Should include orphan task and parent (parent has no parent or deps)
        orphan_ids = [t["id"] for t in orphans]
        assert orphan_id in orphan_ids

        # Target should NOT be in orphans (even if it has no parent in some cases)
        assert target_id not in orphan_ids

    def test_no_similarity_scoring(self, tmp_path: Path, storage_with_tasks: TaskStorage) -> None:
        """Verify no similarity scores are returned (P#78 compliance)."""
        from mcp_servers import tasks_server

        index = TaskIndex(tmp_path)
        index.rebuild()

        target_id = storage_with_tasks._test_ids["target"]

        with patch.object(tasks_server, "_get_storage", return_value=storage_with_tasks):
            with patch.object(tasks_server, "_get_index", return_value=index):
                result = tasks_server.get_task_neighborhood.fn(target_id)

        assert result["success"] is True

        # Check no similarity-related fields exist
        assert "similar_tasks" not in result
        assert "similarity_score" not in result
        assert "confidence" not in result
        assert "potential_parents" not in result
        assert "potential_dependencies" not in result

        # Also check nested structures
        if result["existing_relationships"]:
            for key, value in result["existing_relationships"].items():
                if isinstance(value, list):
                    for item in value:
                        assert "similarity" not in item
                        assert "confidence" not in item
                elif isinstance(value, dict):
                    assert "similarity" not in value
                    assert "confidence" not in value
