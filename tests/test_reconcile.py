"""Unit tests for deterministic task status reconciliation logic in lib/py/reconcile.py.

Verifies the governing invariant and status mapping:
- Every unfinished-work finding terminates in a queued task or a review decision.
- merge_ready strictly means an open, mergeable PR awaiting merge.
- reconcile NEVER writes in_progress.
- Failed PRs (CI red, conflicts, CHANGES_REQUESTED) get a follow-up fix task at queued, and original parked at blocked.
- Delivery with no PR/branch re-queues original to queued.
- Merged PRs with open children stay merge_ready (no cascading close).
- Merged PRs with unmet AC move to review.
- Merged PRs with all AC met complete to done.
"""

from __future__ import annotations

import pytest
from reconcile import (
    CloseRouteClass,
    PRState,
    ReconcileAction,
    ReconcileDecision,
    evaluate_pr_state,
    format_fix_task_body,
    pr_state_from_gh_json,
)


def test_in_progress_invariant_rejected():
    """ReconcileDecision must reject 'in_progress' as target_status or follow_up_status."""
    with pytest.raises(ValueError, match="Invariant violation"):
        ReconcileDecision(
            action=ReconcileAction.MAINTAIN,
            target_status="in_progress",
            create_follow_up=False,
        )

    with pytest.raises(ValueError, match="Invariant violation"):
        ReconcileDecision(
            action=ReconcileAction.CREATE_FIX_TASK,
            target_status="blocked",
            create_follow_up=True,
            follow_up_status="in_progress",
        )


def test_no_branch_or_pr_requeues_original():
    """Delivery that never produced a PR or remote branch re-queues original to queued."""
    # Case 1: no PR opened
    state1 = PRState(has_pr=False, head_branch="feature/my-branch", worktree_path="/worktrees/feat")
    decision1 = evaluate_pr_state(state1)
    assert decision1.action == ReconcileAction.REQUEUE_ORIGINAL
    assert decision1.target_status == "queued"
    assert not decision1.create_follow_up
    assert "no PR for branch" in decision1.annotation

    # Case 2: no remote branch
    state2 = PRState(has_remote_branch=False, head_branch="feature/unpushed")
    decision2 = evaluate_pr_state(state2)
    assert decision2.action == ReconcileAction.REQUEUE_ORIGINAL
    assert decision2.target_status == "queued"
    assert not decision2.create_follow_up


def test_open_pr_ci_failing_creates_fix_task():
    """Open PR with failing CI parks original at blocked and creates follow-up fix task at queued."""
    state = PRState(
        is_open=True,
        ci_failing=True,
        pr_number=123,
        pr_url="https://github.com/org/repo/pull/123",
        head_branch="feature/fix-1",
        failure_details="pytest: FAILURE",
    )
    decision = evaluate_pr_state(state)
    assert decision.action == ReconcileAction.CREATE_FIX_TASK
    assert decision.target_status == "blocked"
    assert decision.create_follow_up is True
    assert decision.follow_up_status == "queued"
    assert "CI red on PR #123" in decision.annotation


def test_open_pr_conflicts_creates_fix_task():
    """Open PR with conflicts (DIRTY) parks original at blocked and creates follow-up fix task at queued."""
    state = PRState(
        is_open=True,
        has_conflicts=True,
        pr_number=124,
        pr_url="https://github.com/org/repo/pull/124",
        head_branch="feature/fix-2",
    )
    decision = evaluate_pr_state(state)
    assert decision.action == ReconcileAction.CREATE_FIX_TASK
    assert decision.target_status == "blocked"
    assert decision.create_follow_up is True
    assert decision.follow_up_status == "queued"
    assert "conflicts on PR #124" in decision.annotation


def test_open_pr_changes_requested_creates_fix_task():
    """Open PR with CHANGES_REQUESTED review parks original at blocked and creates follow-up fix task at queued."""
    state = PRState(
        is_open=True,
        changes_requested=True,
        pr_number=125,
        pr_url="https://github.com/org/repo/pull/125",
        head_branch="feature/fix-3",
    )
    decision = evaluate_pr_state(state)
    assert decision.action == ReconcileAction.CREATE_FIX_TASK
    assert decision.target_status == "blocked"
    assert decision.create_follow_up is True
    assert decision.follow_up_status == "queued"
    assert "changes requested on PR #125" in decision.annotation


def test_open_pr_green_maintains_merge_ready():
    """Open PR with green CI, no conflicts, and no blocking review stays merge_ready."""
    state = PRState(
        is_open=True,
        ci_failing=False,
        has_conflicts=False,
        changes_requested=False,
        pr_number=126,
        pr_url="https://github.com/org/repo/pull/126",
    )
    decision = evaluate_pr_state(state)
    assert decision.action == ReconcileAction.MAINTAIN
    assert decision.target_status == "merge_ready"
    assert decision.create_follow_up is False


def test_merged_pr_with_open_children_stays_merge_ready():
    """Merged PR close-blocked by open children stays merge_ready (never cascade-closes)."""
    state = PRState(
        is_open=False,
        is_merged=True,
        has_open_children=True,
        criteria_met=True,
        pr_number=127,
    )
    decision = evaluate_pr_state(state)
    assert decision.action == ReconcileAction.MAINTAIN
    assert decision.target_status == "merge_ready"
    assert decision.create_follow_up is False
    assert "close-blocked on open children" in decision.annotation


def test_merged_pr_unmet_ac_moves_to_review():
    """Merged PR with unmet AC or requiring interpretation moves to review parked on human."""
    state = PRState(
        is_open=False,
        is_merged=True,
        has_open_children=False,
        criteria_met=False,
        pr_number=128,
    )
    decision = evaluate_pr_state(state)
    assert decision.action == ReconcileAction.MOVE_TO_REVIEW
    assert decision.target_status == "review"
    assert decision.create_follow_up is False


def test_merged_pr_all_ac_met_completes():
    """Merged PR with all AC observably met completes to done."""
    state = PRState(
        is_open=False,
        is_merged=True,
        has_open_children=False,
        criteria_met=True,
        pr_number=129,
    )
    decision = evaluate_pr_state(state)
    assert decision.action == ReconcileAction.COMPLETE
    assert decision.target_status == "done"
    assert decision.create_follow_up is False


def test_closed_pr_routing():
    """Closed without merge routes per §4 classification."""
    # wontfix -> cancelled
    st_wontfix = PRState(
        is_open=False, is_closed=True, close_class=CloseRouteClass.WONTFIX, pr_number=130
    )
    dec_wontfix = evaluate_pr_state(st_wontfix)
    assert dec_wontfix.target_status == "cancelled"

    # bad-implementation -> cancelled
    st_bad = PRState(
        is_open=False, is_closed=True, close_class=CloseRouteClass.BAD_IMPLEMENTATION, pr_number=131
    )
    dec_bad = evaluate_pr_state(st_bad)
    assert dec_bad.target_status == "cancelled"

    # retry-as-is -> queued
    st_retry = PRState(
        is_open=False, is_closed=True, close_class=CloseRouteClass.RETRY_AS_IS, pr_number=132
    )
    dec_retry = evaluate_pr_state(st_retry)
    assert dec_retry.target_status == "queued"


def test_pr_state_from_gh_json():
    """Verify parsing gh pr view JSON payloads."""
    raw_gh_clean = {
        "number": 200,
        "state": "OPEN",
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "APPROVED",
        "statusCheckRollup": [{"name": "pytest", "conclusion": "SUCCESS"}],
        "headRefName": "feat/xyz",
        "url": "https://github.com/org/repo/pull/200",
    }
    state = pr_state_from_gh_json(raw_gh_clean)
    assert state.is_open
    assert not state.ci_failing
    assert not state.has_conflicts
    assert not state.changes_requested
    assert state.pr_number == 200

    raw_gh_dirty = {
        "number": 201,
        "state": "OPEN",
        "mergeable": "CONFLICTING",
        "mergeStateStatus": "DIRTY",
        "reviewDecision": "",
        "statusCheckRollup": [{"name": "ci", "conclusion": "FAILURE"}],
        "headRefName": "feat/dirty",
        "url": "https://github.com/org/repo/pull/201",
    }
    state_dirty = pr_state_from_gh_json(raw_gh_dirty)
    assert state_dirty.ci_failing
    assert state_dirty.has_conflicts
    assert "ci: FAILURE" in (state_dirty.failure_details or "")


def test_format_fix_task_body():
    """Verify formatting follow-up fix task body."""
    body = format_fix_task_body(
        original_task_id="task-1234abcd",
        pr_number=42,
        pr_url="https://github.com/org/repo/pull/42",
        failure_details="pytest failed: test_foo",
        head_branch="polecat/task-1234abcd",
        worktree_path="/worktrees/task-1234abcd",
    )
    assert "task-1234abcd" in body
    assert "[#42](https://github.com/org/repo/pull/42)" in body
    assert "`polecat/task-1234abcd`" in body
    assert "`/worktrees/task-1234abcd`" in body
    assert "pytest failed: test_foo" in body
