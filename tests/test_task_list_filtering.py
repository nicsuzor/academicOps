#!/usr/bin/env python3
"""Tests for 'task list' filtering behavior."""

import os
import subprocess
import sys
import pytest
from pathlib import Path

# CLI is invoked via subprocess to test actual entry point behavior
CLI_CMD = [sys.executable, "-m", "scripts.task_cli"]

def run_cli(*args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the task CLI with given arguments."""
    cmd = CLI_CMD + list(args)
    # Merge with current env if custom env provided
    run_env = None
    if env:
        run_env = os.environ.copy()
        run_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or Path(__file__).parent.parent,
        env=run_env,
    )

@pytest.fixture
def aca_data(tmp_path):
    """Setup ACA_DATA env var."""
    return {"ACA_DATA": str(tmp_path)}

def get_task_id(stdout):
    """Extract task ID from create output."""
    for line in stdout.splitlines():
        if "ID:" in line:
            return line.split("ID:")[-1].strip()
    # Fallback to searching for date-like ID
    for word in stdout.split():
        if word.startswith("20") and len(word) >= 8:
             return word.strip()
    return None

class TestTaskListFiltering:
    
    def test_list_hides_done_and_cancelled_by_default(self, aca_data):
        """'task list' should not show done or cancelled tasks by default."""
        # Create tasks
        res = run_cli("create", "Active Task", env=aca_data)
        active_id = get_task_id(res.stdout)
        
        res = run_cli("create", "Done Task", env=aca_data)
        done_id = get_task_id(res.stdout)
        run_cli("complete", done_id, env=aca_data)
        
        res = run_cli("create", "Cancelled Task", env=aca_data)
        cancelled_id = get_task_id(res.stdout)
        run_cli("update", cancelled_id, "--status", "cancelled", env=aca_data)
        
        # List tasks
        result = run_cli("list", "--plain", env=aca_data)
        
        assert active_id in result.stdout
        assert done_id not in result.stdout
        assert cancelled_id not in result.stdout
        
    def test_list_all_shows_everything(self, aca_data):
        """'task list --all' should show done and cancelled tasks."""
        # Create tasks
        res = run_cli("create", "Active Task", env=aca_data)
        active_id = get_task_id(res.stdout)
        
        res = run_cli("create", "Done Task", env=aca_data)
        done_id = get_task_id(res.stdout)
        run_cli("complete", done_id, env=aca_data)
        
        # List tasks with --all
        result = run_cli("list", "--all", "--plain", env=aca_data)
        
        assert active_id in result.stdout
        assert done_id in result.stdout
        
    def test_list_status_done_shows_done(self, aca_data):
        """'task list --status done' should show done tasks."""
        # Create tasks
        res = run_cli("create", "Done Task", env=aca_data)
        done_id = get_task_id(res.stdout)
        run_cli("complete", done_id, env=aca_data)
        
        # List tasks with --status done
        result = run_cli("list", "--status", "done", "--plain", env=aca_data)
        
        assert done_id in result.stdout

    def test_list_status_cancelled_shows_cancelled(self, aca_data):
        """'task list --status cancelled' should show cancelled tasks."""
        # Create tasks
        res = run_cli("create", "Cancelled Task", env=aca_data)
        cancelled_id = get_task_id(res.stdout)
        run_cli("update", cancelled_id, "--status", "cancelled", env=aca_data)
        
        # List tasks with --status cancelled
        result = run_cli("list", "--status", "cancelled", "--plain", env=aca_data)
        
        assert cancelled_id in result.stdout
