"""Deterministic evaluation logic for task status reconciliation against PR state.

Governing Invariant:
No thread is ever left with nobody to pick it up. Every reconcile finding that
represents unfinished work must terminate in exactly one of: a task standing
at `queued` for a worker, or a task at `review` parked on a decision Nic has to
make. A finding that is merely surfaced in a report is dropped.

`merge_ready` means strictly: an open, mergeable pull request awaiting merge.
`in_progress` is strictly reserved for live workers; reconcile NEVER writes `in_progress`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ReconcileAction(StrEnum):
    MAINTAIN = "maintain"                   # Stays merge_ready (open & green, or merged awaiting children)
    CREATE_FIX_TASK = "create_fix_task"     # Park original at 'blocked', create follow-up fix task at 'queued'
    REQUEUE_ORIGINAL = "requeue_original"   # Original -> 'queued' (no PR/branch produced)
    MOVE_TO_REVIEW = "move_to_review"       # Park original at 'review' (unmet AC or interpretation needed)
    COMPLETE = "complete"                   # Original -> 'done' (merged & all criteria met)
    ROUTE_CLOSED = "route_closed"           # PR closed without merge (route per §4)


class CloseRouteClass(StrEnum):
    WONTFIX = "wontfix"
    BAD_IMPLEMENTATION = "bad_implementation"
    RETRY_AS_IS = "retry_as_is"


@dataclass(frozen=True)
class PRState:
    """Observed state of a task's delivery artifact / pull request."""

    has_pr: bool = True
    has_remote_branch: bool = True
    is_open: bool = True
    is_merged: bool = False
    is_closed: bool = False
    is_draft: bool = False
    ci_failing: bool = False             # CI checks failed, errored, or timed out
    has_conflicts: bool = False          # mergeable == 'CONFLICTING' or mergeStateStatus == 'DIRTY'
    changes_requested: bool = False      # reviewDecision == 'CHANGES_REQUESTED'
    has_open_children: bool = False      # Open child tasks preventing close
    criteria_met: bool | None = None     # True: all AC met; False/None: unmet or needs interpretation
    pr_number: int | None = None
    pr_url: str | None = None
    head_branch: str | None = None
    worktree_path: str | None = None
    failure_details: str | None = None
    close_class: CloseRouteClass | None = None


@dataclass(frozen=True)
class ReconcileDecision:
    """Action and target status computed for a task during reconciliation."""

    action: ReconcileAction
    target_status: str                   # 'merge_ready', 'queued', 'blocked', 'review', 'done', 'cancelled'
    create_follow_up: bool               # True if a follow-up fix task must be created at 'queued'
    follow_up_status: str | None = None  # 'queued' when create_follow_up is True
    reason: str = ""
    annotation: str = ""

    def __post_init__(self) -> None:
        # Invariant: reconcile NEVER writes in_progress
        if self.target_status == "in_progress" or self.follow_up_status == "in_progress":
            raise ValueError(
                "Invariant violation: reconcile must never set status to 'in_progress'. "
                "'in_progress' is reserved exclusively for live workers."
            )


def evaluate_pr_state(pr_state: PRState) -> ReconcileDecision:
    """Compute the target status and required action for a task given PR state.

    Resulting mapping:
    - No branch on remote, or branch with no PR -> original -> `queued`, note existing branch/worktree
    - PR open, CI failing -> create follow-up fix task at `queued`; park original as `blocked`
    - PR open, DIRTY (conflicts) -> create follow-up fix task at `queued`; park original as `blocked`
    - PR open, CHANGES_REQUESTED -> create follow-up fix task at `queued`; park original as `blocked`
    - PR open, green, no blocking review -> stays `merge_ready`
    - PR merged, close blocked by open children -> stays `merge_ready` (awaiting child; no cascade)
    - PR merged, AC unmet or needs interpreting -> `review` (parked on human decision)
    - PR merged, all AC met, no blocking children -> `done`
    - PR closed without merge -> route per §4 (wontfix -> cancelled, bad-implementation -> cancelled + sibling, retry-as-is -> queued)
    """
    # 1. Delivery that never produced a PR or remote branch
    if not pr_state.has_remote_branch or not pr_state.has_pr:
        ref_desc = pr_state.head_branch or pr_state.worktree_path or "unrecorded branch"
        return ReconcileDecision(
            action=ReconcileAction.REQUEUE_ORIGINAL,
            target_status="queued",
            create_follow_up=False,
            reason="Delivery incomplete with no PR or remote branch; returning original to queued.",
            annotation=f"no PR for branch {ref_desc}",
        )

    # 2. PR is open
    if pr_state.is_open and not pr_state.is_merged and not pr_state.is_closed:
        pr_ref = f"PR #{pr_state.pr_number}" if pr_state.pr_number is not None else "open PR"

        if pr_state.ci_failing:
            return ReconcileDecision(
                action=ReconcileAction.CREATE_FIX_TASK,
                target_status="blocked",
                create_follow_up=True,
                follow_up_status="queued",
                reason=f"{pr_ref} has failing CI; parking original as blocked and queuing follow-up fix task.",
                annotation=f"CI red on {pr_ref}",
            )

        if pr_state.has_conflicts:
            return ReconcileDecision(
                action=ReconcileAction.CREATE_FIX_TASK,
                target_status="blocked",
                create_follow_up=True,
                follow_up_status="queued",
                reason=f"{pr_ref} has merge conflicts (DIRTY); parking original as blocked and queuing follow-up fix task.",
                annotation=f"conflicts on {pr_ref}",
            )

        if pr_state.changes_requested:
            return ReconcileDecision(
                action=ReconcileAction.CREATE_FIX_TASK,
                target_status="blocked",
                create_follow_up=True,
                follow_up_status="queued",
                reason=f"{pr_ref} has CHANGES_REQUESTED; parking original as blocked and queuing follow-up fix task.",
                annotation=f"changes requested on {pr_ref}",
            )

        # Green, mergeable, no blocking review -> stays merge_ready awaiting Nic's merge
        return ReconcileDecision(
            action=ReconcileAction.MAINTAIN,
            target_status="merge_ready",
            create_follow_up=False,
            reason=f"{pr_ref} is open, green, mergeable, and awaiting merge.",
            annotation=f"{pr_ref} open and mergeable",
        )

    # 3. PR is merged
    if pr_state.is_merged:
        pr_ref = f"PR #{pr_state.pr_number}" if pr_state.pr_number is not None else "PR"

        if pr_state.has_open_children:
            return ReconcileDecision(
                action=ReconcileAction.MAINTAIN,
                target_status="merge_ready",
                create_follow_up=False,
                reason=f"{pr_ref} merged but task has open children; stays merge_ready awaiting children.",
                annotation=f"{pr_ref} merged; close-blocked on open children",
            )

        if pr_state.criteria_met is not True:
            return ReconcileDecision(
                action=ReconcileAction.MOVE_TO_REVIEW,
                target_status="review",
                create_follow_up=False,
                reason=f"{pr_ref} merged but acceptance criteria unmet or require interpretation; parked at review.",
                annotation=f"{pr_ref} merged; acceptance criteria require review",
            )

        return ReconcileDecision(
            action=ReconcileAction.COMPLETE,
            target_status="done",
            create_follow_up=False,
            reason=f"{pr_ref} merged and all acceptance criteria observably met.",
            annotation=f"{pr_ref} merged; verified complete",
        )

    # 4. PR is closed without merge
    if pr_state.is_closed:
        pr_ref = f"PR #{pr_state.pr_number}" if pr_state.pr_number is not None else "PR"
        close_class = pr_state.close_class or CloseRouteClass.BAD_IMPLEMENTATION

        if close_class == CloseRouteClass.WONTFIX:
            return ReconcileDecision(
                action=ReconcileAction.ROUTE_CLOSED,
                target_status="cancelled",
                create_follow_up=False,
                reason=f"{pr_ref} closed as wontfix / not planned; cancelling task with recorded reason.",
                annotation=f"{pr_ref} closed: wontfix",
            )
        elif close_class == CloseRouteClass.RETRY_AS_IS:
            return ReconcileDecision(
                action=ReconcileAction.ROUTE_CLOSED,
                target_status="queued",
                create_follow_up=False,
                reason=f"{pr_ref} closed due to transient/unrelated infra issue; re-queueing to queued.",
                annotation=f"{pr_ref} closed: retry-as-is",
            )
        else:  # BAD_IMPLEMENTATION / ambiguous
            return ReconcileDecision(
                action=ReconcileAction.ROUTE_CLOSED,
                target_status="cancelled",
                create_follow_up=False,
                reason=f"{pr_ref} closed without merge (bad-implementation); cancelling original and filing sibling investigation.",
                annotation=f"{pr_ref} closed: bad-implementation",
            )

    # Fallback / unreachable under standard enums
    return ReconcileDecision(
        action=ReconcileAction.MAINTAIN,
        target_status="merge_ready",
        create_follow_up=False,
        reason="No state change detected.",
    )


def pr_state_from_gh_json(
    pr_dict: Mapping[str, Any],
    has_remote_branch: bool = True,
    has_open_children: bool = False,
    criteria_met: bool | None = None,
    worktree_path: str | None = None,
    close_class: CloseRouteClass | None = None,
) -> PRState:
    """Parse a GitHub CLI JSON dictionary (from `gh pr view --json ...`) into PRState."""
    state_str = str(pr_dict.get("state", "OPEN")).upper()
    is_merged = state_str == "MERGED" or bool(pr_dict.get("mergedAt"))
    is_closed = state_str == "CLOSED" and not is_merged
    is_open = state_str == "OPEN" and not is_merged and not is_closed

    is_draft = bool(pr_dict.get("isDraft", False))

    mergeable_str = str(pr_dict.get("mergeable", "UNKNOWN")).upper()
    merge_state_status = str(pr_dict.get("mergeStateStatus", "UNKNOWN")).upper()
    has_conflicts = (
        mergeable_str == "CONFLICTING"
        or merge_state_status == "DIRTY"
    )

    review_decision = str(pr_dict.get("reviewDecision", "")).upper()
    changes_requested = review_decision == "CHANGES_REQUESTED"

    # Check status check rollup
    status_check_rollup = pr_dict.get("statusCheckRollup", [])
    ci_failing = False
    failure_details: list[str] = []

    if isinstance(status_check_rollup, list):
        for check in status_check_rollup:
            if isinstance(check, dict):
                conclusion = str(check.get("conclusion") or check.get("state") or "").upper()
                name = str(check.get("name") or check.get("context") or "check")
                if conclusion in {"FAILURE", "ERROR", "TIMED_OUT", "ACTION_REQUIRED", "CANCELLED"}:
                    ci_failing = True
                    failure_details.append(f"{name}: {conclusion}")
    elif isinstance(status_check_rollup, dict):
        state = str(status_check_rollup.get("state", "")).upper()
        if state in {"FAILURE", "ERROR"}:
            ci_failing = True
            failure_details.append(f"Rollup state: {state}")

    pr_number = pr_dict.get("number")
    if pr_number is not None:
        try:
            pr_number = int(pr_number)
        except (ValueError, TypeError):
            pr_number = None

    pr_url = pr_dict.get("url")
    head_branch = pr_dict.get("headRefName")

    return PRState(
        has_pr=True,
        has_remote_branch=has_remote_branch,
        is_open=is_open,
        is_merged=is_merged,
        is_closed=is_closed,
        is_draft=is_draft,
        ci_failing=ci_failing,
        has_conflicts=has_conflicts,
        changes_requested=changes_requested,
        has_open_children=has_open_children,
        criteria_met=criteria_met,
        pr_number=pr_number,
        pr_url=str(pr_url) if pr_url else None,
        head_branch=str(head_branch) if head_branch else None,
        worktree_path=worktree_path,
        failure_details="; ".join(failure_details) if failure_details else None,
        close_class=close_class,
    )


def format_fix_task_body(
    original_task_id: str,
    pr_number: int,
    pr_url: str,
    failure_details: str,
    head_branch: str,
    worktree_path: str | None = None,
) -> str:
    """Format the markdown body for a follow-up fix task created for a failed PR."""
    worktree_line = f"- **Preserved Worktree**: `{worktree_path}`\n" if worktree_path else ""
    return (
        f"## Context\n\n"
        f"Follow-up fix task automatically queued by `reconcile` for failing PR on `{original_task_id}`.\n\n"
        f"## PR Details\n\n"
        f"- **Pull Request**: [#{pr_number}]({pr_url})\n"
        f"- **Head Branch**: `{head_branch}`\n"
        f"{worktree_line}"
        f"- **Original Task**: `{original_task_id}`\n\n"
        f"## Failure Details\n\n"
        f"> {failure_details}\n\n"
        f"## Instructions\n\n"
        f"Resume the existing branch `{head_branch}` (do not open a parallel PR). "
        f"Resolve the failure described above, verify all checks pass, and push changes."
    )
