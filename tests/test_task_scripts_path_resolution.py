#!/usr/bin/env python3
"""Integration tests for task script path resolution consistency.

Tests verify that all task scripts (task_add.py, task_view.py, task_process.py)
use consistent path resolution and can find tasks created by each other.

Relates to GitHub issue #174.
"""

import json
import subprocess
import tempfile
from pathlib import Path


def test_all_scripts_find_same_tasks():
    """Verify all task scripts use consistent path resolution.

    This test creates a task using task_add.py, then verifies both
    task_view.py and task_process.py can find and interact with it.

    Integration test pattern: Uses real task files in temporary directory,
    no mocking of internal code.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange - Get script paths
        scripts_dir = Path(__file__).parent.parent / "scripts"
        task_add = scripts_dir / "task_add.py"
        task_view = scripts_dir / "task_view.py"
        task_process = scripts_dir / "task_process.py"

        # Act 1 - Create task using task_add.py
        result_add = subprocess.run(
            [
                "python3",
                str(task_add),
                "--title",
                "Test task for path resolution",
                "--priority",
                "1",
                "--project",
                "test-path",
            ],
            check=False,
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )

        # Assert task created successfully
        assert result_add.returncode == 0, f"task_add.py failed: {result_add.stderr}"
        task_data = json.loads(result_add.stdout)
        task_id = task_data["id"]

        # Verify task file exists
        task_file = Path(tmpdir) / "data" / "tasks" / "inbox" / f"{task_id}.json"
        assert task_file.exists(), f"Task file not created at {task_file}"

        # Act 2 - Verify task_view.py can see the task
        result_view = subprocess.run(
            ["python3", str(task_view)],
            check=False,
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )

        # Assert task_view.py runs successfully
        assert result_view.returncode == 0, f"task_view.py failed: {result_view.stderr}"

        # Verify task appears in current_view.json
        view_file = Path(tmpdir) / "data" / "views" / "current_view.json"
        assert view_file.exists(), "current_view.json not created"

        view_data = json.loads(view_file.read_text())
        task_ids_in_view = [t.get("id") for t in view_data.get("tasks", [])]
        assert task_id in task_ids_in_view, (
            f"task_view.py didn't find task {task_id}. Found: {task_ids_in_view}"
        )

        # Act 3 - Verify task_process.py can find and modify the task
        result_process = subprocess.run(
            ["python3", str(task_process), "modify", task_id, "--priority", "2"],
            check=False,
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )

        # Assert task_process.py can find and modify the task
        # Parse JSON output (task_process.py outputs multiple JSON lines)
        stdout_lines = [
            line.strip()
            for line in result_process.stdout.strip().split("\n")
            if line.strip()
        ]

        # First line is the error/success result, last line might be empty return value
        process_result = {}
        for line in stdout_lines:
            try:
                parsed = json.loads(line)
                if parsed:  # Skip empty dicts
                    process_result = parsed
                    break
            except json.JSONDecodeError:
                continue

        assert process_result.get("success") is True, (
            f"task_process.py returned success=False: {process_result}\n"
            f"Full stdout: {result_process.stdout}\n"
            f"Stderr: {result_process.stderr}"
        )
        assert task_id in process_result.get("taskId", ""), (
            f"task_process.py modified wrong task: {process_result}"
        )

        # Verify modification actually happened
        modified_task = json.loads(task_file.read_text())
        assert modified_task["priority"] == 2, (
            f"Priority not updated. Expected 2, got {modified_task.get('priority')}"
        )


def test_task_process_fails_fast_when_data_directory_missing():
    """Verify task_process.py fails explicitly when data directory doesn't exist.

    Fail-fast principle: Scripts should fail immediately with clear error,
    not silently search wrong locations or use fallback logic.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange - Empty directory with no data/ subdirectory
        scripts_dir = Path(__file__).parent.parent / "scripts"
        task_process = scripts_dir / "task_process.py"

        # Act - Try to modify task when data directory doesn't exist
        result = subprocess.run(
            [
                "python3",
                str(task_process),
                "modify",
                "20250101-12345678",
                "--priority",
                "2",
            ],
            check=False,
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )

        # Assert - Should fail with non-zero exit code
        assert result.returncode != 0, (
            f"task_process.py should exit with error when data directory missing. "
            f"Exit code: {result.returncode}, Stderr: {result.stderr}, Stdout: {result.stdout}"
        )

        # Assert - Error message should mention data directory
        error_output = result.stderr.lower()
        assert (
            "data" in error_output
            or "directory" in error_output
            or "not found" in error_output
        ), (
            f"Error message should mention data directory or not found. Got stderr: {result.stderr}"
        )
