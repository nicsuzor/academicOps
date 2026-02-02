#!/usr/bin/env python3
"""Integration tests for tasks_server.py MCP tools."""

import os
import sys
from pathlib import Path
import pytest

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
TESTS_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = TESTS_ROOT.parent
AOPS_CORE_ROOT = FRAMEWORK_ROOT / "aops-core"

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

# Now we can import the server functions
from mcp_servers.tasks_server import (
    create_task,
    get_tasks_with_topology,
    update_task,
)

@pytest.fixture(scope="module")
def task_server_setup(tmp_path_factory):
    """
    Sets up a temporary data directory and creates a set of tasks
    for testing the tasks_server functionality.
    """
    tmp_path = tmp_path_factory.mktemp("data")
    os.environ["ACA_DATA"] = str(tmp_path)

    # --- Create Test Data ---
    # Call the underlying function on the tool object
    p_a_root_res = create_task.fn(task_title="Project A Root", project="proj-a", type="project")
    assert p_a_root_res["success"]
    p_a_root_id = p_a_root_res["task"]["id"]

    p_a_child1_res = create_task.fn(task_title="Child 1 (A)", project="proj-a", parent=p_a_root_id)
    assert p_a_child1_res["success"]
    p_a_child1_id = p_a_child1_res["task"]["id"]

    blocker_res = create_task.fn(task_title="Blocker Task", project="proj-a", status="active")
    assert blocker_res["success"]
    blocker_id = blocker_res["task"]["id"]
    update_task.fn(id=p_a_child1_id, depends_on=[blocker_id])

    p_b_root_res = create_task.fn(task_title="Project B Root", project="proj-b", type="project")
    assert p_b_root_res["success"]
    p_b_root_id = p_b_root_res["task"]["id"]

    hub_res = create_task.fn(task_title="Hub Task", project="proj-b", type="task", parent=p_b_root_id)
    assert hub_res["success"]
    hub_id = hub_res["task"]["id"]

    create_task.fn(task_title="Spoke 1", project="proj-b", depends_on=[hub_id])
    create_task.fn(task_title="Spoke 2", project="proj-b", depends_on=[hub_id])

    parent_id = p_b_root_id
    for i in range(5):
        res = create_task.fn(task_title=f"Deep Task {i+1}", project="proj-b", parent=parent_id)
        assert res["success"]
        parent_id = res["task"]["id"]
    
    create_task.fn(task_title="A done task", project="proj-a", status="done")
    create_task.fn(task_title="Ready Task", project="proj-a", status="active")

    yield {
        "p_a_root_id": p_a_root_id,
        "p_a_child1_id": p_a_child1_id,
        "blocker_id": blocker_id,
        "hub_id": hub_id,
        "deep_task_id": parent_id,
    }

    del os.environ["ACA_DATA"]


class TestGetTasksWithTopology:
    def test_no_filters(self, task_server_setup):
        """Test that with no filters, it returns all tasks."""
        result = get_tasks_with_topology.fn()
        assert result["success"]
        assert result["count"] == 14

    def test_filter_by_project(self, task_server_setup):
        """Test filtering by project."""
        result = get_tasks_with_topology.fn(project="proj-a")
        assert result["success"]
        for task in result["tasks"]:
            assert task["project"] == "proj-a"
        assert result["count"] == 5

    def test_filter_by_status(self, task_server_setup):
        """Test filtering by status."""
        result = get_tasks_with_topology.fn(status="done")
        assert result["success"]
        assert result["count"] == 1
        assert result["tasks"][0]["title"] == "A done task"

    def test_filter_by_min_depth(self, task_server_setup):
        """Test filtering by minimum depth."""
        task_ids = task_server_setup
        result = get_tasks_with_topology.fn(min_depth=5)
        assert result["success"]
        assert result["count"] == 1
        assert result["tasks"][0]["id"] == task_ids["deep_task_id"]

    def test_filter_by_min_blocking_count(self, task_server_setup):
        """Test filtering by minimum blocking count."""
        task_ids = task_server_setup
        result = get_tasks_with_topology.fn(min_blocking_count=2)
        assert result["success"]
        assert result["count"] == 1
        assert result["tasks"][0]["id"] == task_ids["hub_id"]
        assert result["tasks"][0]["blocking_count"] == 2

    def test_topology_metrics_are_correct(self, task_server_setup):
        """Check a specific task to ensure all metrics are correct."""
        task_ids = task_server_setup
        hub_id = task_ids["hub_id"]
        result = get_tasks_with_topology.fn(project="proj-b")
        assert result["success"]

        hub_task = next((t for t in result["tasks"] if t["id"] == hub_id), None)
        assert hub_task is not None

        assert hub_task["depth"] == 1
        assert hub_task["is_leaf"] is True # It has no children, so it is a leaf
        assert hub_task["child_count"] == 0
        assert hub_task["blocking_count"] == 2 # Blocks 2 spokes
        assert hub_task["blocked_by_count"] == 0 # Depends on nothing

        p_a_child1_id = task_ids["p_a_child1_id"]
        result_a = get_tasks_with_topology.fn(project="proj-a")
        child1_task = next((t for t in result_a["tasks"] if t["id"] == p_a_child1_id), None)
        assert child1_task is not None

        assert child1_task["is_leaf"] is True
        assert child1_task["blocked_by_count"] == 1
        assert child1_task["blocking_count"] == 0

    def test_ready_days_calculation(self, task_server_setup):
        """Test that ready_days is calculated for active tasks."""
        result = get_tasks_with_topology.fn(status="active")
        assert result["success"]
        
        ready_task = next((t for t in result["tasks"] if t["title"] == "Ready Task"), None)
        assert ready_task is not None
        assert "ready_days" in ready_task
        assert ready_task["ready_days"] is not None
        assert ready_task["ready_days"] >= 0

        result_done = get_tasks_with_topology.fn(status="done")
        done_task = result_done["tasks"][0]
        assert done_task["ready_days"] is None
