import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
TESTS_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = TESTS_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(FRAMEWORK_ROOT / "aops-core"))

from mcp_servers import tasks_server


@pytest.fixture
def mock_task_index():
    """Fixture to create a mock TaskIndex."""
    mock_index = MagicMock()

    # task1 is a ready leaf task
    task1 = MagicMock()
    task1.id = "task1"
    task1.title = "Task 1"
    task1.status = "active"
    task1.type = "task"
    task1.parent = None
    task1.depends_on = []
    task1.blocks = ["task2"]
    task1.leaf = False  # It's a parent
    task1.depth = 0
    task1.project = "proj1"

    # task2 is blocked by task1 (if task1 were not done)
    # but for this test, let's say task1 is also active.
    task2 = MagicMock()
    task2.id = "task2"
    task2.title = "Task 2"
    task2.status = "active"
    task2.type = "task"
    task2.parent = "task1"
    task2.depends_on = ["task1"]
    task2.blocks = []
    task2.leaf = True
    task2.depth = 1
    task2.project = "proj1"

    # task3 is done
    task3 = MagicMock()
    task3.id = "task3"
    task3.title = "Task 3"
    task3.status = "done"
    task3.type = "task"
    task3.parent = None
    task3.depends_on = []
    task3.blocks = []
    task3.leaf = True
    task3.depth = 0
    task3.project = "proj2"

    # task4 is a ready root task
    task4 = MagicMock()
    task4.id = "task4"
    task4.title = "Task 4"
    task4.status = "active"
    task4.type = "action"
    task4.parent = None
    task4.depends_on = []
    task4.blocks = []
    task4.leaf = True
    task4.depth = 0
    task4.project = "proj1"

    mock_index._tasks = {"task1": task1, "task2": task2, "task3": task3, "task4": task4}

    def get_task(task_id):
        return mock_index._tasks.get(task_id)

    def get_descendants(task_id):
        if task_id == "task1":
            return [task2]
        return []

    mock_index.get_task.side_effect = get_task
    mock_index.get_descendants.side_effect = get_descendants

    return mock_index


def test_get_graph_metrics_all_scope(mock_task_index):
    with patch("mcp_servers.tasks_server._get_index", return_value=mock_task_index):
        result = tasks_server.get_graph_metrics(scope="all")

        assert result["success"] is True
        stats = result["stats"]
        assert stats["total_tasks"] == 4
        assert stats["tasks_by_status"] == {"active": 3, "done": 1}
        assert stats["tasks_by_type"] == {"task": 3, "action": 1}
        assert stats["root_count"] == 3  # task1, task3, task4
        assert stats["leaf_count"] == 3  # task2, task3, task4
        assert stats["max_depth"] == 1
        assert round(stats["avg_depth"], 2) == round(1 / 4, 2)
        assert stats["dependency_stats"]["total_edges"] == 1
        assert stats["dependency_stats"]["max_in_degree"] == 1
        assert stats["dependency_stats"]["max_out_degree"] == 1
        assert len(stats["dependency_stats"]["tasks_with_high_out_degree"]) == 1
        # Readiness check: task4 is ready, task2 is blocked by task1
        assert stats["readiness_stats"]["ready_count"] == 1
        assert stats["readiness_stats"]["blocked_count"] == 1
        assert stats["readiness_stats"]["in_progress_count"] == 0


def test_get_graph_metrics_project_scope(mock_task_index):
    with patch("mcp_servers.tasks_server._get_index", return_value=mock_task_index):
        result = tasks_server.get_graph_metrics(scope="project", scope_id="proj1")

        assert result["success"] is True
        stats = result["stats"]
        assert stats["total_tasks"] == 3
        assert stats["tasks_by_status"]["active"] == 3
        assert stats["root_count"] == 2  # task1, task4
        assert stats["leaf_count"] == 2  # task2, task4
        assert stats["readiness_stats"]["ready_count"] == 1
        assert stats["readiness_stats"]["blocked_count"] == 1


def test_get_graph_metrics_task_id_scope(mock_task_index):
    with patch("mcp_servers.tasks_server._get_index", return_value=mock_task_index):
        result = tasks_server.get_graph_metrics(scope="task_id", scope_id="task1")

        assert result["success"] is True
        stats = result["stats"]
        assert stats["total_tasks"] == 2  # task1 and its descendant task2
        assert stats["tasks_by_status"]["active"] == 2
        assert stats["root_count"] == 1  # task1 is the root of this subtree
        assert stats["leaf_count"] == 1
        assert stats["readiness_stats"]["ready_count"] == 0
        assert stats["readiness_stats"]["blocked_count"] == 1


def test_get_graph_metrics_no_tasks_in_scope(mock_task_index):
    with patch("mcp_servers.tasks_server._get_index", return_value=mock_task_index):
        result = tasks_server.get_graph_metrics(scope="project", scope_id="nonexistent")

        assert result["success"] is True
        assert result["message"] == "No tasks found in scope."
        assert result["stats"]["total_tasks"] == 0
