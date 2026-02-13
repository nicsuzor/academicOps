#!/usr/bin/env python3
"""Integration tests for tasks_server.py validation logic."""

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
    complete_task,
    update_task,
    get_task,
)

@pytest.fixture
def clean_aca_data(tmp_path):
    """Sets up a temporary data directory."""
    old_data = os.environ.get("ACA_DATA")
    os.environ["ACA_DATA"] = str(tmp_path)
    yield tmp_path
    if old_data:
        os.environ["ACA_DATA"] = old_data
    else:
        del os.environ["ACA_DATA"]

def test_complete_task_with_incomplete_markers(clean_aca_data):
    """Test that complete_task fails if there are incomplete markers."""
    # Create a task with incomplete markers
    body = "## Tasks\n- [ ] Item 1\n- [x] Item 2\n- [ ] Item 3"
    res = create_task.fn(task_title="Test Task", body=body)
    assert res["success"]
    task_id = res["task"]["id"]

    # Try to complete it without force
    res_comp = complete_task.fn(id=task_id)
    assert not res_comp["success"]
    assert "incomplete items" in res_comp["message"]
    assert "Item 1" in res_comp["message"]
    assert "Item 3" in res_comp["message"]

    # Verify status is still active
    res_get = get_task.fn(id=task_id)
    assert res_get["task"]["status"] == "active"

    # Complete it with force
    res_force = complete_task.fn(id=task_id, force=True)
    assert res_force["success"]
    assert res_force["task"]["status"] == "done"

def test_update_task_status_done_with_incomplete_markers(clean_aca_data):
    """Test that update_task status=done fails if there are incomplete markers."""
    # Create a task with incomplete markers
    body = "- [ ] Item A"
    res = create_task.fn(task_title="Test Update", body=body)
    assert res["success"]
    task_id = res["task"]["id"]

    # Try to update status to done without force
    res_upd = update_task.fn(id=task_id, status="done")
    assert not res_upd["success"]
    assert "incomplete items" in res_upd["message"]

    # Complete it with force
    res_force = update_task.fn(id=task_id, status="done", force=True)
    assert res_force["success"]
    assert res_force["task"]["status"] == "done"

def test_update_task_body_and_status_done(clean_aca_data):
    """Test that update_task checks the NEW body if body is updated in same call."""
    # Create a task without markers
    res = create_task.fn(task_title="Test Body Update")
    assert res["success"]
    task_id = res["task"]["id"]

    # Update body with markers and set status to done in same call
    res_upd = update_task.fn(id=task_id, body="- [ ] New Item", status="done")
    assert not res_upd["success"]
    assert "incomplete items" in res_upd["message"]

    # Update body to mark as done and set status to done
    res_ok = update_task.fn(id=task_id, body="- [x] New Item", status="done")
    assert res_ok["success"]
    assert res_ok["task"]["status"] == "done"

def test_complete_task_no_markers(clean_aca_data):
    """Test that complete_task succeeds if there are no incomplete markers."""
    # Create a task without markers or with only completed ones
    body = "No markers here\n- [x] Done item"
    res = create_task.fn(task_title="Clean Task", body=body)
    assert res["success"]
    task_id = res["task"]["id"]

    res_comp = complete_task.fn(id=task_id)
    assert res_comp["success"]
    assert res_comp["task"]["status"] == "done"
