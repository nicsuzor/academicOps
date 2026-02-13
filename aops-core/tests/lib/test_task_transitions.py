#!/usr/bin/env python3
"""Tests for Task state transitions and guards."""

from datetime import UTC, datetime

import pytest

from lib.task_model import (
    ApprovalType,
    Task,
    TaskStatus,
    TaskType,
    TransitionResult,
)


@pytest.fixture
def task() -> Task:
    return Task(id="test-123", title="Test Task")


class TestHappyPath:
    """Test standard lifecycle transitions."""

    def test_inbox_to_active(self, task):
        """INBOX -> ACTIVE (triage)."""
        task.status = TaskStatus.INBOX
        result = task.transition_to(TaskStatus.ACTIVE)
        assert result.success
        assert task.status == TaskStatus.ACTIVE

    def test_active_to_in_progress(self, task):
        """ACTIVE -> IN_PROGRESS (claim)."""
        result = task.transition_to(
            TaskStatus.IN_PROGRESS,
            worker_id="polecat-1",
        )
        assert result.success
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.worker_id == "polecat-1"

    def test_in_progress_to_review(self, task):
        """IN_PROGRESS -> REVIEW (PR filed)."""
        task.status = TaskStatus.IN_PROGRESS
        task.worker_id = "polecat-1"
        result = task.transition_to(
            TaskStatus.REVIEW,
            pr_url="https://github.com/org/repo/pull/1",
        )
        assert result.success
        assert task.status == TaskStatus.REVIEW
        assert task.pr_url == "https://github.com/org/repo/pull/1"

    def test_review_to_merge_ready(self, task):
        """REVIEW -> MERGE_READY (consensus)."""
        task.status = TaskStatus.REVIEW
        task.pr_url = "https://github.com/org/repo/pull/1"
        result = task.transition_to(TaskStatus.MERGE_READY)
        assert result.success
        assert task.status == TaskStatus.MERGE_READY

    def test_merge_ready_to_merging(self, task):
        """MERGE_READY -> MERGING (slot acquired)."""
        task.status = TaskStatus.MERGE_READY
        task.pr_url = "https://github.com/org/repo/pull/1"
        result = task.transition_to(TaskStatus.MERGING)
        assert result.success
        assert task.status == TaskStatus.MERGING

    def test_merging_to_done(self, task):
        """MERGING -> DONE (merged)."""
        task.status = TaskStatus.MERGING
        result = task.transition_to(TaskStatus.DONE)
        assert result.success
        assert task.status == TaskStatus.DONE


class TestGuardValidation:
    """Test transition guards enforce requirements."""

    def test_blocked_requires_unblock_condition(self, task):
        """ACTIVE -> BLOCKED requires unblock_condition."""
        result = task.transition_to(TaskStatus.BLOCKED)
        assert not result.success
        assert "unblock_condition" in result.error

        result = task.transition_to(
            TaskStatus.BLOCKED,
            unblock_condition="Wait for API key",
        )
        assert result.success
        assert task.unblock_condition == "Wait for API key"

    def test_failed_requires_diagnostic(self, task):
        """ACTIVE -> FAILED requires diagnostic."""
        result = task.transition_to(TaskStatus.FAILED)
        assert not result.success
        assert "diagnostic" in result.error

        result = task.transition_to(
            TaskStatus.FAILED,
            diagnostic="API timeout",
        )
        assert result.success
        assert task.diagnostic == "API timeout"

    def test_in_progress_requires_worker_id(self, task):
        """ACTIVE -> IN_PROGRESS requires worker_id."""
        result = task.transition_to(TaskStatus.IN_PROGRESS)
        assert not result.success
        assert "worker_id" in result.error

    def test_review_requires_pr_url(self, task):
        """IN_PROGRESS -> REVIEW requires pr_url."""
        task.status = TaskStatus.IN_PROGRESS
        task.worker_id = "polecat-1"
        result = task.transition_to(TaskStatus.REVIEW)
        assert not result.success
        assert "pr_url" in result.error

    def test_cancelled_requires_reason(self, task):
        """ACTIVE -> CANCELLED requires reason."""
        result = task.transition_to(TaskStatus.CANCELLED)
        assert not result.success
        assert "reason" in result.error

    def test_decomposing_depth_limit(self):
        """DECOMPOSING -> DECOMPOSING fails at MAX_DEPTH."""
        task = Task(id="test-28", title="Test", status=TaskStatus.DECOMPOSING, depth=10)
        # Note: Self-transitions are allowed if explicit in table, but guard checks depth
        # However, Task.transition_to checks guards for ALL transitions in table.
        # But if it's a self-transition that is NOT in table, it returns success early (idempotent).
        # DECOMPOSING->DECOMPOSING IS in table, so it runs guards.
        result = task.transition_to(TaskStatus.DECOMPOSING, trigger="iteration")
        # Guard should fail because depth=10
        assert not result.success
        assert "exceeds MAX_DEPTH" in result.error


class TestFieldClearing:
    """Tests for field clearing on status change."""

    def test_worker_id_preserved_on_review(self):
        """worker_id is preserved when moving to REVIEW (audit trail)."""
        task = Task(
            id="test-60",
            title="Test",
            status=TaskStatus.IN_PROGRESS,
            worker_id="polecat-1",
        )
        task.transition_to(
            TaskStatus.REVIEW,
            pr_url="https://github.com/org/repo/pull/1",
        )
        assert task.worker_id == "polecat-1"

    def test_unblock_condition_cleared_on_unblock(self):
        """unblock_condition is cleared when unblocking."""
        task = Task(
            id="test-61",
            title="Test",
            status=TaskStatus.BLOCKED,
            unblock_condition="Waiting for X",
        )
        task.transition_to(TaskStatus.ACTIVE)
        assert task.unblock_condition is None

    def test_pr_url_preserved_on_merge(self):
        """pr_url is preserved on merge."""
        task = Task(
            id="test-62",
            title="Test",
            status=TaskStatus.MERGE_READY,
            pr_url="http://github.com/pr/1",
        )
        task.transition_to(TaskStatus.MERGING)
        assert task.pr_url == "http://github.com/pr/1"


class TestIdempotency:
    """Test idempotent transitions."""

    def test_same_status_is_noop(self, task):
        """Transition to current status is success (no-op)."""
        result = task.transition_to(TaskStatus.ACTIVE)
        assert result.success
        assert result.idempotency_key == task.idempotency_key

    def test_retry_failed_increments_counter(self, task):
        """FAILED -> ACTIVE increments retry_count."""
        task.status = TaskStatus.FAILED
        task.diagnostic = "Error"
        task.retry_count = 0

        result = task.transition_to(TaskStatus.ACTIVE)
        assert result.success
        assert task.retry_count == 1
