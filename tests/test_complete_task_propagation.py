"""Tests for unblock propagation when completing tasks.

Tests that completing a task correctly unblocks dependent tasks if all
their dependencies are met.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add framework roots to path for lib imports
TESTS_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = TESTS_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.task_index import TaskIndex
from lib.task_model import TaskStatus
from lib.task_storage import TaskStorage


class TestCompleteTaskPropagation:
    """Test propagation of unblocks when completing tasks."""

    @pytest.fixture
    def storage(self, tmp_path: Path) -> TaskStorage:
        """Create a storage with some tasks."""
        # Create directory structure
        project_tasks = tmp_path / "testproj" / "tasks"
        project_tasks.mkdir(parents=True)
        inbox = tmp_path / "tasks" / "inbox"
        inbox.mkdir(parents=True)

        return TaskStorage(data_root=tmp_path)

    def test_single_dep_unblock(self, tmp_path: Path, storage: TaskStorage) -> None:
        """Completing a single dependency unblocks the dependent task."""
        from mcp_servers import tasks_server

        # Create A
        task_a = storage.create_task(title="Task A", project="testproj")
        storage.save_task(task_a)

        # Create B, depending on A
        task_b = storage.create_task(
            title="Task B",
            project="testproj",
            status=TaskStatus.BLOCKED,
            depends_on=[task_a.id],
        )
        storage.save_task(task_b)

        index = TaskIndex(tmp_path)
        index.rebuild()

        with patch.object(tasks_server, "_get_storage", return_value=storage):
            with patch.object(tasks_server, "_get_index", return_value=index):
                # Complete A
                result = tasks_server.complete_task.fn(task_a.id)
                assert result["success"] is True

        # Check if B is now ACTIVE
        updated_b = storage.get_task(task_b.id)
        assert updated_b.status == TaskStatus.ACTIVE

    def test_partial_deps_stay_blocked(self, tmp_path: Path, storage: TaskStorage) -> None:
        """Dependent task stays BLOCKED if only some dependencies are done."""
        from mcp_servers import tasks_server

        # Create A, B
        task_a = storage.create_task(title="Task A", project="testproj")
        storage.save_task(task_a)
        task_b = storage.create_task(title="Task B", project="testproj")
        storage.save_task(task_b)

        # Create C, depending on A and B
        task_c = storage.create_task(
            title="Task C",
            project="testproj",
            status=TaskStatus.BLOCKED,
            depends_on=[task_a.id, task_b.id],
        )
        storage.save_task(task_c)

        index = TaskIndex(tmp_path)
        index.rebuild()

        with patch.object(tasks_server, "_get_storage", return_value=storage):
            with patch.object(tasks_server, "_get_index", return_value=index):
                # Complete A
                result = tasks_server.complete_task.fn(task_a.id)
                assert result["success"] is True

        # Check if C is still BLOCKED
        updated_c = storage.get_task(task_c.id)
        assert updated_c.status == TaskStatus.BLOCKED

        with patch.object(tasks_server, "_get_storage", return_value=storage):
            # Refresh index for B's completion
            index.rebuild()
            with patch.object(tasks_server, "_get_index", return_value=index):
                # Complete B
                result = tasks_server.complete_task.fn(task_b.id)
                assert result["success"] is True

        # Check if C is now ACTIVE
        updated_c = storage.get_task(task_c.id)
        assert updated_c.status == TaskStatus.ACTIVE

    def test_chain_unblock(self, tmp_path: Path, storage: TaskStorage) -> None:
        """Chain of dependencies is unblocked recursively if intermediate tasks are already DONE."""
        from mcp_servers import tasks_server

        # A <- B <- C
        # A is ACTIVE
        # B is already DONE
        # C is BLOCKED by B (stays BLOCKED because unblock didn't propagate when B was completed)
        task_a = storage.create_task(title="Task A", project="testproj")
        storage.save_task(task_a)

        task_b = storage.create_task(
            title="Task B",
            project="testproj",
            depends_on=[task_a.id],
        )
        storage.save_task(task_b)

        task_c = storage.create_task(
            title="Task C",
            project="testproj",
            status=TaskStatus.BLOCKED,
            depends_on=[task_b.id],
        )
        storage.save_task(task_c)

        # Build index while A is still ACTIVE and B is ACTIVE
        index = TaskIndex(tmp_path)
        index.rebuild()

        # Mark B as DONE without propagating (simulate old bug)
        task_b.status = TaskStatus.DONE
        storage.save_task(task_b)

        # Now complete A. This should trigger propagation.
        # A completes -> checks B.
        # B is already DONE -> checks C.
        # C is BLOCKED, all deps (B) are DONE -> C becomes ACTIVE.
        with patch.object(tasks_server, "_get_storage", return_value=storage):
            with patch.object(tasks_server, "_get_index", return_value=index):
                # Complete A
                result = tasks_server.complete_task.fn(task_a.id)
                assert result["success"] is True

        # C should now become ACTIVE.
        updated_c = storage.get_task(task_c.id)
        assert updated_c.status == TaskStatus.ACTIVE

    def test_batch_complete_unblock(self, tmp_path: Path, storage: TaskStorage) -> None:
        """Batch completion also unblocks dependent tasks."""
        from mcp_servers import tasks_server

        # A, B <- C
        task_a = storage.create_task(title="Task A", project="testproj")
        storage.save_task(task_a)
        task_b = storage.create_task(title="Task B", project="testproj")
        storage.save_task(task_b)
        task_c = storage.create_task(
            title="Task C",
            project="testproj",
            status=TaskStatus.BLOCKED,
            depends_on=[task_a.id, task_b.id],
        )
        storage.save_task(task_c)

        index = TaskIndex(tmp_path)
        index.rebuild()

        with patch.object(tasks_server, "_get_storage", return_value=storage):
            with patch.object(tasks_server, "_get_index", return_value=index):
                # Complete A and B
                result = tasks_server.complete_tasks.fn([task_a.id, task_b.id])
                assert result["success"] is True

        # Check if C is now ACTIVE
        updated_c = storage.get_task(task_c.id)
        assert updated_c.status == TaskStatus.ACTIVE

    def test_update_task_unblock(self, tmp_path: Path, storage: TaskStorage) -> None:
        """Using update_task to set status=DONE also propagates unblocks."""
        from mcp_servers import tasks_server

        # Create A
        task_a = storage.create_task(title="Task A", project="testproj")
        storage.save_task(task_a)

        # Create B, depending on A
        task_b = storage.create_task(
            title="Task B",
            project="testproj",
            status=TaskStatus.BLOCKED,
            depends_on=[task_a.id],
        )
        storage.save_task(task_b)

        index = TaskIndex(tmp_path)
        index.rebuild()

        with patch.object(tasks_server, "_get_storage", return_value=storage):
            with patch.object(tasks_server, "_get_index", return_value=index):
                # Update A to DONE via update_task
                result = tasks_server.update_task.fn(task_a.id, status="done")
                assert result["success"] is True

        # Check if B is now ACTIVE
        updated_b = storage.get_task(task_b.id)
        assert updated_b.status == TaskStatus.ACTIVE
