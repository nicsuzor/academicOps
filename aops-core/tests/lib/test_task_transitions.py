"""Tests for task state transition guards and logging.

Per non-interactive-agent-workflow-spec.md:
- Tests valid state transitions
- Tests guard validation (invariants)
- Tests audit logging
- Tests idempotency
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from lib.task_model import (
    TRANSITION_TABLE,
    ApprovalType,
    Task,
    TaskStatus,
    get_all_transitions,
    get_transition_info,
)


class TestTransitionTable:
    """Tests for the transition table structure."""

    def test_transition_table_not_empty(self):
        """Transition table should have entries."""
        assert len(TRANSITION_TABLE) > 0

    def test_all_statuses_have_at_least_one_outgoing(self):
        """Most statuses should have at least one outgoing transition.

        Exception: DONE and CANCELLED are terminal.
        """
        terminal_statuses = {TaskStatus.DONE, TaskStatus.CANCELLED}
        for status in TaskStatus:
            if status in terminal_statuses:
                continue
            outgoing = [
                to_status
                for (from_status, to_status) in TRANSITION_TABLE
                if from_status == status
            ]
            assert len(outgoing) > 0, f"Status {status.value} has no outgoing transitions"

    def test_terminal_statuses_have_no_outgoing(self):
        """DONE and CANCELLED should have no outgoing transitions."""
        terminal_statuses = {TaskStatus.DONE, TaskStatus.CANCELLED}
        for status in terminal_statuses:
            outgoing = [
                to_status
                for (from_status, to_status) in TRANSITION_TABLE
                if from_status == status
            ]
            assert len(outgoing) == 0, f"Terminal status {status.value} has outgoing transitions"

    def test_get_transition_info_valid(self):
        """get_transition_info returns info for valid transitions."""
        info = get_transition_info(TaskStatus.ACTIVE, TaskStatus.DECOMPOSING)
        assert info is not None
        assert info["from"] == "active"
        assert info["to"] == "decomposing"
        assert "trigger" in info
        assert "guard" in info

    def test_get_transition_info_invalid(self):
        """get_transition_info returns None for invalid transitions."""
        # DONE -> ACTIVE is not valid
        info = get_transition_info(TaskStatus.DONE, TaskStatus.ACTIVE)
        assert info is None

    def test_get_all_transitions(self):
        """get_all_transitions returns all transitions."""
        transitions = get_all_transitions()
        assert len(transitions) == len(TRANSITION_TABLE)
        for t in transitions:
            assert "from" in t
            assert "to" in t
            assert "trigger" in t
            assert "guard" in t


class TestValidTransitions:
    """Tests for valid state transitions."""

    def test_active_to_decomposing(self):
        """ACTIVE -> DECOMPOSING should succeed."""
        task = Task(id="test-1", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(TaskStatus.DECOMPOSING, trigger="begin_breakdown")
        assert result.success
        assert task.status == TaskStatus.DECOMPOSING
        assert result.idempotency_key is not None

    def test_active_to_in_progress_with_worker_id(self):
        """ACTIVE -> IN_PROGRESS requires worker_id."""
        task = Task(id="test-2", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(
            TaskStatus.IN_PROGRESS,
            trigger="worker_claims",
            worker_id="polecat-claude-1",
        )
        assert result.success
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.worker_id == "polecat-claude-1"

    def test_decomposing_to_consensus(self):
        """DECOMPOSING -> CONSENSUS should succeed."""
        task = Task(id="test-3", title="Test", status=TaskStatus.DECOMPOSING)
        result = task.transition_to(TaskStatus.CONSENSUS, trigger="proposal_ready")
        assert result.success
        assert task.status == TaskStatus.CONSENSUS

    def test_consensus_to_waiting(self):
        """CONSENSUS -> WAITING should succeed."""
        task = Task(id="test-4", title="Test", status=TaskStatus.CONSENSUS)
        result = task.transition_to(TaskStatus.WAITING, trigger="all_approve")
        assert result.success
        assert task.status == TaskStatus.WAITING

    def test_in_progress_to_review_with_pr_url(self):
        """IN_PROGRESS -> REVIEW requires pr_url."""
        task = Task(
            id="test-5",
            title="Test",
            status=TaskStatus.IN_PROGRESS,
            worker_id="polecat-1",
        )
        result = task.transition_to(
            TaskStatus.REVIEW,
            trigger="pr_filed",
            pr_url="https://github.com/org/repo/pull/123",
        )
        assert result.success
        assert task.status == TaskStatus.REVIEW
        assert task.pr_url == "https://github.com/org/repo/pull/123"

    def test_review_to_merge_ready(self):
        """REVIEW -> MERGE_READY should succeed."""
        task = Task(
            id="test-6",
            title="Test",
            status=TaskStatus.REVIEW,
            pr_url="https://github.com/org/repo/pull/123",
        )
        result = task.transition_to(TaskStatus.MERGE_READY, trigger="review_consensus")
        assert result.success
        assert task.status == TaskStatus.MERGE_READY

    def test_merge_ready_to_done(self):
        """MERGE_READY -> DONE should succeed."""
        task = Task(
            id="test-7",
            title="Test",
            status=TaskStatus.MERGE_READY,
            pr_url="https://github.com/org/repo/pull/123",
        )
        result = task.transition_to(TaskStatus.DONE, trigger="merge_complete")
        assert result.success
        assert task.status == TaskStatus.DONE

    def test_blocked_to_active_unblock(self):
        """BLOCKED -> ACTIVE when unblock condition met."""
        task = Task(
            id="test-8",
            title="Test",
            status=TaskStatus.BLOCKED,
            unblock_condition="waiting for dependency X",
        )
        result = task.transition_to(TaskStatus.ACTIVE, trigger="unblock_condition_met")
        assert result.success
        assert task.status == TaskStatus.ACTIVE
        assert task.unblock_condition is None  # Cleared on unblock

    def test_failed_to_active_retry(self):
        """FAILED -> ACTIVE increments retry_count."""
        task = Task(
            id="test-9",
            title="Test",
            status=TaskStatus.FAILED,
            diagnostic="worker crashed",
            retry_count=1,
        )
        result = task.transition_to(TaskStatus.ACTIVE, trigger="user_retries")
        assert result.success
        assert task.status == TaskStatus.ACTIVE
        assert task.retry_count == 2  # Incremented


class TestInvalidTransitions:
    """Tests for invalid state transitions."""

    def test_done_cannot_transition(self):
        """DONE is terminal - no outgoing transitions."""
        task = Task(id="test-10", title="Test", status=TaskStatus.DONE)
        result = task.transition_to(TaskStatus.ACTIVE)
        assert not result.success
        assert "Invalid transition" in result.error

    def test_cancelled_cannot_transition(self):
        """CANCELLED is terminal - no outgoing transitions."""
        task = Task(id="test-11", title="Test", status=TaskStatus.CANCELLED)
        result = task.transition_to(TaskStatus.ACTIVE)
        assert not result.success
        assert "Invalid transition" in result.error

    def test_active_cannot_go_directly_to_done(self):
        """ACTIVE -> DONE is not valid (must go through workflow)."""
        task = Task(id="test-12", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(TaskStatus.DONE)
        assert not result.success
        assert "Invalid transition" in result.error


class TestGuardValidation:
    """Tests for guard validation."""

    def test_in_progress_requires_worker_id(self):
        """IN_PROGRESS requires worker_id to be set."""
        task = Task(id="test-20", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(TaskStatus.IN_PROGRESS)  # No worker_id
        assert not result.success
        assert "worker_id" in result.error.lower()

    def test_blocked_requires_unblock_condition(self):
        """BLOCKED requires unblock_condition to be set."""
        task = Task(id="test-21", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(TaskStatus.BLOCKED)  # No unblock_condition
        assert not result.success
        assert "unblock_condition" in result.error.lower()

    def test_blocked_with_unblock_condition(self):
        """BLOCKED succeeds with unblock_condition."""
        task = Task(id="test-22", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(
            TaskStatus.BLOCKED,
            unblock_condition="waiting for API key",
        )
        assert result.success
        assert task.unblock_condition == "waiting for API key"

    def test_failed_requires_diagnostic(self):
        """FAILED requires diagnostic to be set."""
        task = Task(id="test-23", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(TaskStatus.FAILED)  # No diagnostic
        assert not result.success
        assert "diagnostic" in result.error.lower()

    def test_failed_with_diagnostic(self):
        """FAILED succeeds with diagnostic."""
        task = Task(id="test-24", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(
            TaskStatus.FAILED,
            diagnostic="claim timeout after 30s",
        )
        assert result.success
        assert task.diagnostic == "claim timeout after 30s"

    def test_review_requires_pr_url(self):
        """REVIEW requires pr_url to be set."""
        task = Task(
            id="test-25",
            title="Test",
            status=TaskStatus.IN_PROGRESS,
            worker_id="polecat-1",
        )
        result = task.transition_to(TaskStatus.REVIEW)  # No pr_url
        assert not result.success
        assert "pr_url" in result.error.lower()

    def test_cancelled_requires_reason(self):
        """CANCELLED requires reason to be set."""
        task = Task(id="test-26", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(TaskStatus.CANCELLED)  # No reason
        assert not result.success
        assert "reason" in result.error.lower()

    def test_cancelled_with_reason(self):
        """CANCELLED succeeds with reason."""
        task = Task(id="test-27", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(
            TaskStatus.CANCELLED,
            reason="out of scope",
        )
        assert result.success
        assert task.status == TaskStatus.CANCELLED

    def test_decomposing_depth_limit(self):
        """DECOMPOSING -> DECOMPOSING fails at MAX_DEPTH."""
        task = Task(id="test-28", title="Test", status=TaskStatus.DECOMPOSING, depth=10)
        result = task.transition_to(TaskStatus.DECOMPOSING, trigger="iteration")
        assert not result.success
        assert "depth" in result.error.lower()

    def test_decomposing_under_depth_limit(self):
        """DECOMPOSING -> DECOMPOSING succeeds under MAX_DEPTH."""
        task = Task(id="test-29", title="Test", status=TaskStatus.DECOMPOSING, depth=5)
        result = task.transition_to(TaskStatus.DECOMPOSING, trigger="iteration")
        assert result.success


class TestIdempotency:
    """Tests for idempotent state transitions."""

    def test_idempotent_transition_same_key(self):
        """Repeated transition with same idempotency key succeeds."""
        task = Task(id="test-30", title="Test", status=TaskStatus.ACTIVE)

        # First transition
        result1 = task.transition_to(TaskStatus.DECOMPOSING)
        assert result1.success
        key1 = result1.idempotency_key

        # Manually set status back but keep key (simulating retry)
        # In practice, this would be detected via the stored key
        task2 = Task(
            id="test-30",
            title="Test",
            status=TaskStatus.ACTIVE,
            idempotency_key=key1,
        )

        # Same transition should recognize idempotency
        result2 = task2.transition_to(TaskStatus.DECOMPOSING)
        assert result2.success
        assert result2.idempotency_key == key1

    def test_idempotency_key_generated(self):
        """Idempotency key is generated on transition."""
        task = Task(id="test-31", title="Test", status=TaskStatus.ACTIVE)
        result = task.transition_to(TaskStatus.DECOMPOSING)
        assert result.idempotency_key is not None
        assert task.idempotency_key == result.idempotency_key
        # Key format: {task_id}-{from}-{to}-{timestamp}
        assert "test-31" in result.idempotency_key
        assert "active" in result.idempotency_key
        assert "decomposing" in result.idempotency_key


class TestAuditLogging:
    """Tests for audit log writing."""

    def test_audit_log_written(self, tmp_path: Path):
        """Transition writes to audit log."""
        log_path = tmp_path / "audit" / "transitions.jsonl"
        task = Task(id="test-40", title="Test", status=TaskStatus.ACTIVE)

        result = task.transition_to(
            TaskStatus.DECOMPOSING,
            trigger="begin_breakdown",
            actor="polecat",
            audit_log_path=log_path,
        )

        assert result.success
        assert log_path.exists()

        # Parse the log entry
        with log_path.open() as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["task"] == "test-40"
        assert entry["from"] == "active"
        assert entry["to"] == "decomposing"
        assert entry["trigger"] == "begin_breakdown"
        assert entry["actor"] == "polecat"
        assert "idempotency_key" in entry
        assert "ts" in entry

    def test_multiple_transitions_logged(self, tmp_path: Path):
        """Multiple transitions append to audit log."""
        log_path = tmp_path / "audit" / "transitions.jsonl"
        task = Task(id="test-41", title="Test", status=TaskStatus.ACTIVE)

        # First transition
        task.transition_to(
            TaskStatus.DECOMPOSING,
            audit_log_path=log_path,
        )

        # Second transition
        task.transition_to(
            TaskStatus.CONSENSUS,
            audit_log_path=log_path,
        )

        # Read all entries
        with log_path.open() as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 2
        assert entries[0]["to"] == "decomposing"
        assert entries[1]["to"] == "consensus"


class TestTaskHelpers:
    """Tests for task helper methods."""

    def test_can_transition_to_valid(self):
        """can_transition_to returns True for valid transitions."""
        task = Task(id="test-50", title="Test", status=TaskStatus.ACTIVE)
        assert task.can_transition_to(TaskStatus.DECOMPOSING)
        assert task.can_transition_to(TaskStatus.IN_PROGRESS)
        assert task.can_transition_to(TaskStatus.BLOCKED)

    def test_can_transition_to_invalid(self):
        """can_transition_to returns False for invalid transitions."""
        task = Task(id="test-51", title="Test", status=TaskStatus.ACTIVE)
        assert not task.can_transition_to(TaskStatus.DONE)
        assert not task.can_transition_to(TaskStatus.MERGE_READY)

    def test_get_valid_transitions(self):
        """get_valid_transitions returns all valid targets."""
        task = Task(id="test-52", title="Test", status=TaskStatus.ACTIVE)
        valid = task.get_valid_transitions()
        assert TaskStatus.DECOMPOSING in valid
        assert TaskStatus.IN_PROGRESS in valid
        assert TaskStatus.BLOCKED in valid
        assert TaskStatus.FAILED in valid
        assert TaskStatus.CANCELLED in valid
        # Invalid targets
        assert TaskStatus.DONE not in valid
        assert TaskStatus.MERGE_READY not in valid


class TestFieldClearing:
    """Tests for field clearing on status change."""

    def test_worker_id_cleared_on_non_in_progress(self):
        """worker_id is cleared when leaving IN_PROGRESS."""
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
        assert task.worker_id is None

    def test_unblock_condition_cleared_on_unblock(self):
        """unblock_condition is cleared when unblocking."""
        task = Task(
            id="test-61",
            title="Test",
            status=TaskStatus.BLOCKED,
            unblock_condition="waiting for X",
        )
        task.transition_to(TaskStatus.ACTIVE)
        assert task.unblock_condition is None

    def test_approval_fields_cleared_on_non_waiting(self):
        """approval_type and decision_deadline cleared when leaving WAITING."""
        task = Task(
            id="test-62",
            title="Test",
            status=TaskStatus.WAITING,
            approval_type=ApprovalType.STANDARD,
            decision_deadline=datetime.now(UTC),
        )
        task.transition_to(
            TaskStatus.IN_PROGRESS,
            worker_id="polecat-1",
        )
        assert task.approval_type is None
        assert task.decision_deadline is None
