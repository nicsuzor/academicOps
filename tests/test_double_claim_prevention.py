"""Tests for double-claim prevention in task manager.

These tests verify acceptance criteria for v1.1:
1. When user B attempts to claim a task already claimed by user A, the system rejects
2. Clear error message indicates the task is already claimed
3. Claimed-by information (assignee, timestamp) is visible in error
4. Original claimer's status remains unchanged
5. Same assignee can re-claim their own task (idempotent)

Note: Concurrent claim prevention (race conditions) requires file locking which is
out of scope for v1.1. The current implementation prevents sequential double-claims
but does not guarantee atomicity for truly concurrent operations.
"""

import re
from pathlib import Path
from unittest.mock import patch

import pytest
from lib.task_model import Task, TaskStatus, TaskType
from lib.task_storage import TaskStorage


@pytest.fixture
def storage(tmp_path: Path) -> TaskStorage:
    """Create a TaskStorage with temp data root."""
    return TaskStorage(data_root=tmp_path)


@pytest.fixture
def claimed_task(storage: TaskStorage) -> Task:
    """Create a task that is already claimed by user A."""
    task = storage.create_task(
        title="Already Claimed Task",
        type=TaskType.TASK,
    )
    task.status = TaskStatus.IN_PROGRESS
    task.assignee = "user_a"
    storage.save_task(task)
    return task


class TestDoubleClaimPrevention:
    """Test that double-claiming is prevented at the API level."""

    def test_claim_already_claimed_task_rejected(
        self, storage: TaskStorage, claimed_task: Task, tmp_path: Path
    ):
        """When user B attempts to claim a task already claimed by user A, reject."""
        # Import the server module and patch its data root
        from mcp_servers import tasks_server

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            # User B tries to claim the task
            result = tasks_server.update_task(
                id=claimed_task.id,
                status="in_progress",
                assignee="user_b",
            )

            # Should be rejected
            assert result["success"] is False
            assert "already claimed" in result["message"].lower()
            assert "user_a" in result["message"]

    def test_error_message_includes_claimer_info(
        self, storage: TaskStorage, claimed_task: Task, tmp_path: Path
    ):
        """Error message should include assignee and timestamp."""
        from mcp_servers import tasks_server

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            result = tasks_server.update_task(
                id=claimed_task.id,
                status="in_progress",
                assignee="user_b",
            )

            assert result["success"] is False
            # Check error contains required info
            assert "user_a" in result["message"]
            # Verify ISO timestamp format appears after "since" in message
            # Pattern: YYYY-MM-DDTHH:MM:SS (with optional timezone)
            iso_pattern = r"since \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
            assert re.search(iso_pattern, result["message"]), (
                f"Expected ISO timestamp after 'since' in message: {result['message']}"
            )

    def test_original_claimer_unchanged_after_rejected_claim(
        self, storage: TaskStorage, claimed_task: Task, tmp_path: Path
    ):
        """Original claimer's status remains unchanged after rejected claim attempt."""
        from mcp_servers import tasks_server

        original_assignee = claimed_task.assignee
        original_status = claimed_task.status

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            # User B tries to claim
            tasks_server.update_task(
                id=claimed_task.id,
                status="in_progress",
                assignee="user_b",
            )

            # Verify original task is unchanged
            task = storage.get_task(claimed_task.id)
            assert task.assignee == original_assignee
            assert task.status == original_status

    def test_same_assignee_can_reclaim_own_task(
        self, storage: TaskStorage, claimed_task: Task, tmp_path: Path
    ):
        """Same assignee can update their own claimed task (idempotent)."""
        from mcp_servers import tasks_server

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            # User A updates their own claimed task
            result = tasks_server.update_task(
                id=claimed_task.id,
                status="in_progress",
                assignee="user_a",
            )

            # Should succeed
            assert result["success"] is True

    def test_unclaimed_task_can_be_claimed(self, storage: TaskStorage, tmp_path: Path):
        """A task with status=active (unclaimed) can be claimed by anyone."""
        from mcp_servers import tasks_server

        # Create an unclaimed task
        task = storage.create_task(
            title="Unclaimed Task",
            type=TaskType.TASK,
        )
        task.status = TaskStatus.ACTIVE
        task.assignee = None
        storage.save_task(task)

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            result = tasks_server.update_task(
                id=task.id,
                status="in_progress",
                assignee="user_b",
            )

            assert result["success"] is True
            assert result["task"]["status"] == "in_progress"
            assert result["task"]["assignee"] == "user_b"

    def test_task_in_progress_without_assignee_can_be_claimed(
        self, storage: TaskStorage, tmp_path: Path
    ):
        """A task with status=in_progress but no assignee can be claimed."""
        from mcp_servers import tasks_server

        # Create a task in progress but without assignee (edge case)
        task = storage.create_task(
            title="In Progress No Assignee",
            type=TaskType.TASK,
        )
        task.status = TaskStatus.IN_PROGRESS
        task.assignee = None  # No assignee
        storage.save_task(task)

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            result = tasks_server.update_task(
                id=task.id,
                status="in_progress",
                assignee="user_b",
            )

            # Should succeed - task wasn't fully claimed
            assert result["success"] is True
            assert result["task"]["assignee"] == "user_b"

    def test_claim_without_specifying_assignee_uses_existing(
        self, storage: TaskStorage, claimed_task: Task, tmp_path: Path
    ):
        """When claiming without assignee param, use task's existing assignee for comparison."""
        from mcp_servers import tasks_server

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            # Just set status without specifying assignee
            result = tasks_server.update_task(
                id=claimed_task.id,
                status="in_progress",
                # No assignee specified
            )

            # Should succeed because we're not changing assignee
            assert result["success"] is True

    def test_rejected_claim_returns_task_data(
        self, storage: TaskStorage, claimed_task: Task, tmp_path: Path
    ):
        """Rejected claim should still return the current task data for visibility."""
        from mcp_servers import tasks_server

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            result = tasks_server.update_task(
                id=claimed_task.id,
                status="in_progress",
                assignee="user_b",
            )

            assert result["success"] is False
            # Task data should be included so user can see current state
            assert result["task"] is not None
            assert result["task"]["assignee"] == "user_a"


class TestClaimWithStatusAlias:
    """Test claim prevention works with status aliases like 'in-progress'."""

    def test_alias_in_progress_also_prevents_double_claim(
        self, storage: TaskStorage, claimed_task: Task, tmp_path: Path
    ):
        """Using 'in-progress' (hyphenated) should also prevent double-claim."""
        from mcp_servers import tasks_server

        with (
            patch.object(tasks_server, "_get_storage", return_value=storage),
            patch("mcp_servers.tasks_server.get_data_root", return_value=tmp_path),
        ):
            result = tasks_server.update_task(
                id=claimed_task.id,
                status="in-progress",  # Hyphenated alias
                assignee="user_b",
            )

            assert result["success"] is False
            assert "already claimed" in result["message"].lower()
