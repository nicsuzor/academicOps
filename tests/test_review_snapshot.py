"""Tests for get_review_snapshot() MCP tool and _compute_graph_metrics() helper."""

from __future__ import annotations

import sys
from pathlib import Path

from lib.task_index import TaskIndex
from lib.task_model import TaskStatus, TaskType
from lib.task_storage import TaskStorage

# Import the internal helper and raw function directly
# The MCP decorator wraps functions, so we import before decoration
# or access the underlying function

# Add mcp_servers to path
_SCRIPT_DIR = Path(__file__).parent.resolve()
_MCP_SERVERS_DIR = _SCRIPT_DIR.parent / "mcp_servers"
sys.path.insert(0, str(_MCP_SERVERS_DIR))


class TestComputeGraphMetrics:
    """Test _compute_graph_metrics helper function."""

    def test_empty_index_returns_zero_metrics(self, tmp_path: Path) -> None:
        """Empty index should return zeroed metrics."""
        from mcp_servers.tasks_server import _compute_graph_metrics

        # Setup empty index
        (tmp_path / "tasks").mkdir(parents=True)
        index = TaskIndex(tmp_path)
        index.rebuild()

        metrics = _compute_graph_metrics(index)

        assert metrics["total_tasks"] == 0
        assert metrics["tasks_by_status"] == {}
        assert metrics["orphan_count"] == 0
        assert metrics["dependency_stats"]["total_edges"] == 0

    def test_metrics_counts_tasks_by_status(self, tmp_path: Path) -> None:
        """Metrics should count tasks by status correctly."""
        from mcp_servers.tasks_server import _compute_graph_metrics

        # Setup tasks
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        storage = TaskStorage(tmp_path)

        # Create tasks with different statuses
        for i, status in enumerate([TaskStatus.ACTIVE, TaskStatus.ACTIVE, TaskStatus.DONE]):
            task = storage.create_task(
                title=f"Task {i}",
                type=TaskType.TASK,
                status=status,
            )
            storage.save_task(task)

        index = TaskIndex(tmp_path)
        index.rebuild()

        metrics = _compute_graph_metrics(index)

        assert metrics["total_tasks"] == 3
        assert metrics["tasks_by_status"]["active"] == 2
        assert metrics["tasks_by_status"]["done"] == 1

    def test_metrics_computes_dependency_stats(self, tmp_path: Path) -> None:
        """Metrics should compute dependency in/out degrees."""
        from mcp_servers.tasks_server import _compute_graph_metrics

        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        storage = TaskStorage(tmp_path)

        # Create: A blocks B and C (out_degree=2)
        task_a = storage.create_task(title="Task A", type=TaskType.TASK)
        storage.save_task(task_a)

        task_b = storage.create_task(
            title="Task B",
            type=TaskType.TASK,
            depends_on=[task_a.id],
        )
        storage.save_task(task_b)

        task_c = storage.create_task(
            title="Task C",
            type=TaskType.TASK,
            depends_on=[task_a.id],
        )
        storage.save_task(task_c)

        index = TaskIndex(tmp_path)
        index.rebuild()

        metrics = _compute_graph_metrics(index)

        assert metrics["dependency_stats"]["total_edges"] == 2
        assert metrics["dependency_stats"]["max_out_degree"] == 2
        assert metrics["dependency_stats"]["max_in_degree"] == 1
        # Task A should be in high out-degree list
        high_out = metrics["dependency_stats"]["tasks_with_high_out_degree"]
        assert len(high_out) == 1
        assert high_out[0]["id"] == task_a.id
        assert high_out[0]["out_degree"] == 2


class TestGetReviewSnapshot:
    """Test get_review_snapshot MCP tool.

    Note: The get_review_snapshot function is decorated with @mcp.tool(),
    which wraps it in a FunctionTool. We access the underlying function
    via the .fn attribute.
    """

    def _get_snapshot_fn(self):
        """Get the raw function from the MCP tool wrapper."""
        from mcp_servers.tasks_server import get_review_snapshot

        # FastMCP tools have a .fn attribute for the raw function
        if hasattr(get_review_snapshot, "fn"):
            return get_review_snapshot.fn
        return get_review_snapshot

    def test_snapshot_returns_success_and_timestamp(self, tmp_path: Path, monkeypatch) -> None:
        """Snapshot should return success=True and current timestamp."""
        monkeypatch.setenv("ACA_DATA", str(tmp_path))

        (tmp_path / "tasks").mkdir(parents=True)

        # Rebuild index
        index = TaskIndex(tmp_path)
        index.rebuild()

        fn = self._get_snapshot_fn()
        result = fn(since_days=1)

        assert result["success"] is True
        assert "timestamp" in result
        assert "metrics" in result
        assert "changes_since" in result
        assert "staleness" in result
        assert "velocity" in result

    def test_snapshot_includes_metrics(self, tmp_path: Path, monkeypatch) -> None:
        """Snapshot should include graph metrics."""
        monkeypatch.setenv("ACA_DATA", str(tmp_path))

        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        storage = TaskStorage(tmp_path)

        # Create a task
        task = storage.create_task(title="Test Task", type=TaskType.TASK)
        storage.save_task(task)

        # Rebuild index
        index = TaskIndex(tmp_path)
        index.rebuild()

        fn = self._get_snapshot_fn()
        result = fn(since_days=1)

        assert result["success"] is True
        assert result["metrics"]["total_tasks"] == 1
        assert "tasks_by_status" in result["metrics"]

    def test_snapshot_tracks_created_tasks(self, tmp_path: Path, monkeypatch) -> None:
        """Snapshot should list recently created tasks."""
        monkeypatch.setenv("ACA_DATA", str(tmp_path))

        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        storage = TaskStorage(tmp_path)

        # Create a task (will be within last 1 day)
        task = storage.create_task(title="New Task", type=TaskType.TASK)
        storage.save_task(task)

        index = TaskIndex(tmp_path)
        index.rebuild()

        fn = self._get_snapshot_fn()
        result = fn(since_days=1)

        assert result["success"] is True
        assert len(result["changes_since"]["tasks_created"]) == 1
        assert result["changes_since"]["tasks_created"][0]["title"] == "New Task"

    def test_snapshot_velocity_counts(self, tmp_path: Path, monkeypatch) -> None:
        """Snapshot should count tasks created in last 7 days."""
        monkeypatch.setenv("ACA_DATA", str(tmp_path))

        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        storage = TaskStorage(tmp_path)

        # Create tasks
        for i in range(3):
            task = storage.create_task(title=f"Task {i}", type=TaskType.TASK)
            storage.save_task(task)

        # Complete one
        task = storage.create_task(
            title="Completed Task",
            type=TaskType.TASK,
            status=TaskStatus.DONE,
        )
        storage.save_task(task)

        index = TaskIndex(tmp_path)
        index.rebuild()

        fn = self._get_snapshot_fn()
        result = fn(since_days=1)

        assert result["success"] is True
        assert result["velocity"]["created_last_7_days"] == 4
        assert result["velocity"]["completed_last_7_days"] == 1

    def test_snapshot_staleness_detection(self, tmp_path: Path, monkeypatch) -> None:
        """Snapshot should identify oldest ready and in_progress tasks."""
        monkeypatch.setenv("ACA_DATA", str(tmp_path))

        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        storage = TaskStorage(tmp_path)

        # Create an active (ready) task
        ready_task = storage.create_task(
            title="Ready Task",
            type=TaskType.TASK,
            status=TaskStatus.ACTIVE,
        )
        storage.save_task(ready_task)

        # Create an in-progress task
        wip_task = storage.create_task(
            title="WIP Task",
            type=TaskType.TASK,
            status=TaskStatus.IN_PROGRESS,
        )
        storage.save_task(wip_task)

        index = TaskIndex(tmp_path)
        index.rebuild()

        fn = self._get_snapshot_fn()
        result = fn(since_days=1)

        assert result["success"] is True
        # Staleness should have entries (tasks just created, so days will be ~0)
        staleness = result["staleness"]
        assert staleness["oldest_ready_task"] is not None
        assert staleness["oldest_ready_task"]["task"]["title"] == "Ready Task"
        assert staleness["oldest_in_progress"] is not None
        assert staleness["oldest_in_progress"]["task"]["title"] == "WIP Task"
