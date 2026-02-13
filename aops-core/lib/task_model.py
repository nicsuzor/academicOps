#!/usr/bin/env python3
"""Task Model v2: Hierarchical task decomposition with graph relationships.

Implements the Task model per specs/tasks-v2.md with:
- Graph relationships (parent, depends_on, children, blocks)
- Hierarchical decomposition (goal → project → task → action)
- YAML frontmatter serialization
- Validation and type safety
- State transition guards and logging (per non-interactive-agent-workflow-spec.md)

Usage:
    from lib.task_model import Task, TaskType, TaskStatus, TaskComplexity

    task = Task(
        id="20260112-write-book",
        title="Write a new book",
        type=TaskType.GOAL,
        project="book",
    )
    task.to_file(path)

    loaded = Task.from_file(path)

    # State transitions with guards
    result = task.transition_to(
        TaskStatus.IN_PROGRESS,
        trigger="worker_claims",
        actor="polecat-claude",
        worker_id="polecat-claude-1",
    )
    if not result.success:
        print(f"Transition failed: {result.error}")
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

import yaml

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Enum)


class TaskType(Enum):
    """Semantic task levels for hierarchical decomposition."""

    GOAL = "goal"  # Multi-month/year outcome
    PROJECT = "project"  # Coherent body of work
    EPIC = "epic"  # Group of tasks aimed at a milestone
    TASK = "task"  # Discrete deliverable
    ACTION = "action"  # Single work session
    BUG = "bug"  # Defect to fix
    FEATURE = "feature"  # New functionality
    LEARN = "learn"  # Observational tracking (not actionable)


class TaskStatus(Enum):
    """Task lifecycle states.

    See specs/non-interactive-agent-workflow-spec.md for full state machine.
    """

    # Pre-work states
    INBOX = "inbox"  # New task, not yet triaged
    ACTIVE = "active"  # Ready to be claimed (no blockers)

    # Decomposition phase (Phase 1)
    DECOMPOSING = "decomposing"  # Effectual planner iterating on breakdown

    # Review phase (Phase 2)
    CONSENSUS = "consensus"  # Multi-agent review in progress

    # Approval phase (Phase 3)
    WAITING = "waiting"  # Awaiting user decision

    # Execution phase (Phase 4)
    IN_PROGRESS = "in_progress"  # Worker executing approved plan

    # PR phase (Phase 5)
    REVIEW = "review"  # PR filed, awaiting review consensus
    MERGE_READY = "merge_ready"  # Reviews done, awaiting merge approval
    MERGING = "merging"  # Currently being merged (merge slot)

    # Terminal states
    DONE = "done"  # Completed (Phase 6: knowledge captured)
    CANCELLED = "cancelled"  # Abandoned, with reason

    # Special states
    BLOCKED = "blocked"  # External dependency, with unblock_condition
    DORMANT = "dormant"  # User-initiated backburner
    FAILED = "failed"  # Unrecoverable error, with diagnostic


class TaskComplexity(Enum):
    """Task complexity classification for routing decisions.

    Used by hydrator to determine execution strategy:
    - mechanical/requires-judgment → EXECUTE path
    - multi-step → EXECUTE with orchestration
    - needs-decomposition/blocked-human → TRIAGE path
    """

    MECHANICAL = "mechanical"  # Clear deliverable, known path, single session
    REQUIRES_JUDGMENT = "requires-judgment"  # Needs exploration within bounds
    MULTI_STEP = "multi-step"  # Multi-session orchestration
    NEEDS_DECOMPOSITION = "needs-decomposition"  # Must break down first
    BLOCKED_HUMAN = "blocked-human"  # Requires human decision/input


class ApprovalType(Enum):
    """Approval type for tasks in WAITING status.

    Used to differentiate standard approvals from escalated ones
    that require immediate attention due to unresolved reviewer concerns.
    """

    STANDARD = "standard"  # Normal approval flow
    ESCALATED = "escalated"  # Has unresolved concerns from review


# =============================================================================
# State Transition System
# =============================================================================


@dataclass
class TransitionResult:
    """Result of a state transition attempt."""

    success: bool
    from_status: TaskStatus
    to_status: TaskStatus
    error: str | None = None
    idempotency_key: str | None = None


@dataclass
class TransitionLogEntry:
    """Audit log entry for a state transition."""

    ts: datetime
    task: str
    from_status: str
    to_status: str
    trigger: str
    actor: str
    idempotency_key: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ts": self.ts.isoformat(),
            "task": self.task,
            "from": self.from_status,
            "to": self.to_status,
            "trigger": self.trigger,
            "actor": self.actor,
            "idempotency_key": self.idempotency_key,
        }


class TransitionError(Exception):
    """Raised when a state transition is invalid."""

    def __init__(self, message: str, from_status: TaskStatus, to_status: TaskStatus):
        super().__init__(message)
        self.from_status = from_status
        self.to_status = to_status


# Type alias for guard functions
# Guard functions take (task, **kwargs) and return (bool, str | None)
# where str is the error message if guard fails
GuardFunc = Callable[..., tuple[bool, str | None]]


def _guard_always_pass(task: Task, **kwargs: Any) -> tuple[bool, str | None]:
    """Guard that always passes (no additional requirements)."""
    return True, None


def _guard_lock_acquired(task: Task, **kwargs: Any) -> tuple[bool, str | None]:
    """Guard: lock must be acquired (checked externally, trust caller)."""
    # Lock acquisition is handled at the task manager level, not here
    return True, None


def _guard_unblock_condition_set(task: Task, **kwargs: Any) -> tuple[bool, str | None]:
    """Guard: unblock_condition must be provided for BLOCKED status."""
    unblock_condition = kwargs.get("unblock_condition") or task.unblock_condition
    if not unblock_condition:
        return False, "unblock_condition is required for BLOCKED status"
    return True, None


def _guard_diagnostic_set(task: Task, **kwargs: Any) -> tuple[bool, str | None]:
    """Guard: diagnostic must be provided for FAILED status."""
    diagnostic = kwargs.get("diagnostic") or task.diagnostic
    if not diagnostic:
        return False, "diagnostic is required for FAILED status"
    return True, None


def _guard_depth_under_limit(task: Task, **kwargs: Any) -> tuple[bool, str | None]:
    """Guard: depth must be under MAX_DEPTH (10) for decomposing iterations."""
    max_depth = 10
    if task.depth >= max_depth:
        return False, f"depth ({task.depth}) exceeds MAX_DEPTH ({max_depth})"
    return True, None


def _guard_pr_url_set(task: Task, **kwargs: Any) -> tuple[bool, str | None]:
    """Guard: pr_url must be provided for REVIEW/MERGE_READY status."""
    pr_url = kwargs.get("pr_url") or task.pr_url
    if not pr_url:
        return False, "pr_url is required for REVIEW/MERGE_READY status"
    return True, None


def _guard_worker_id_set(task: Task, **kwargs: Any) -> tuple[bool, str | None]:
    """Guard: worker_id must be provided for IN_PROGRESS status."""
    worker_id = kwargs.get("worker_id") or task.worker_id
    if not worker_id:
        return False, "worker_id is required for IN_PROGRESS status"
    return True, None


def _guard_reason_set(task: Task, **kwargs: Any) -> tuple[bool, str | None]:
    """Guard: reason must be provided for cancellation."""
    reason = kwargs.get("reason")
    if not reason:
        return False, "reason is required for CANCELLED status"
    return True, None


# Transition table: (from_status, to_status) -> (guard_func, trigger_description)
# Per non-interactive-agent-workflow-spec.md Section "Transition Table"
TRANSITION_TABLE: dict[tuple[TaskStatus, TaskStatus], tuple[GuardFunc, str]] = {
    # From INBOX
    (TaskStatus.INBOX, TaskStatus.ACTIVE): (_guard_always_pass, "triaged"),
    (TaskStatus.INBOX, TaskStatus.CANCELLED): (_guard_reason_set, "user_cancels"),
    # From ACTIVE (pending in spec is our ACTIVE)
    (TaskStatus.ACTIVE, TaskStatus.DECOMPOSING): (_guard_always_pass, "begin_breakdown"),
    (TaskStatus.ACTIVE, TaskStatus.IN_PROGRESS): (_guard_worker_id_set, "worker_claims"),
    (TaskStatus.ACTIVE, TaskStatus.BLOCKED): (_guard_unblock_condition_set, "dependency_discovered"),
    (TaskStatus.ACTIVE, TaskStatus.FAILED): (_guard_diagnostic_set, "claim_timeout"),
    (TaskStatus.ACTIVE, TaskStatus.CANCELLED): (_guard_reason_set, "user_cancels"),
    # From DECOMPOSING
    (TaskStatus.DECOMPOSING, TaskStatus.DECOMPOSING): (_guard_depth_under_limit, "iteration_complete"),
    (TaskStatus.DECOMPOSING, TaskStatus.CONSENSUS): (_guard_always_pass, "proposal_ready"),
    (TaskStatus.DECOMPOSING, TaskStatus.BLOCKED): (_guard_unblock_condition_set, "external_dependency_found"),
    (TaskStatus.DECOMPOSING, TaskStatus.FAILED): (_guard_diagnostic_set, "exception_or_depth_exceeded"),
    (TaskStatus.DECOMPOSING, TaskStatus.CANCELLED): (_guard_reason_set, "user_cancels"),
    # From CONSENSUS
    (TaskStatus.CONSENSUS, TaskStatus.WAITING): (_guard_always_pass, "all_reviewers_approve"),
    (TaskStatus.CONSENSUS, TaskStatus.DECOMPOSING): (_guard_always_pass, "any_reviewer_blocks"),
    (TaskStatus.CONSENSUS, TaskStatus.FAILED): (_guard_diagnostic_set, "all_reviewers_unavailable"),
    (TaskStatus.CONSENSUS, TaskStatus.CANCELLED): (_guard_reason_set, "user_cancels"),
    # From WAITING
    (TaskStatus.WAITING, TaskStatus.IN_PROGRESS): (_guard_worker_id_set, "user_approves"),
    (TaskStatus.WAITING, TaskStatus.DECOMPOSING): (_guard_always_pass, "user_requests_changes"),
    (TaskStatus.WAITING, TaskStatus.ACTIVE): (_guard_always_pass, "user_sends_back"),
    (TaskStatus.WAITING, TaskStatus.DORMANT): (_guard_always_pass, "user_backburners"),
    (TaskStatus.WAITING, TaskStatus.CANCELLED): (_guard_reason_set, "user_cancels"),
    (TaskStatus.WAITING, TaskStatus.FAILED): (_guard_diagnostic_set, "approval_timeout"),
    # From IN_PROGRESS
    (TaskStatus.IN_PROGRESS, TaskStatus.REVIEW): (_guard_pr_url_set, "pr_filed"),
    (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED): (_guard_unblock_condition_set, "dependency_discovered"),
    (TaskStatus.IN_PROGRESS, TaskStatus.FAILED): (_guard_diagnostic_set, "worker_crash_or_timeout"),
    (TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED): (_guard_reason_set, "user_cancels"),
    # From REVIEW
    (TaskStatus.REVIEW, TaskStatus.MERGE_READY): (_guard_always_pass, "review_consensus_reached"),
    (TaskStatus.REVIEW, TaskStatus.IN_PROGRESS): (_guard_worker_id_set, "changes_requested"),
    (TaskStatus.REVIEW, TaskStatus.BLOCKED): (_guard_unblock_condition_set, "dependency_discovered"),
    (TaskStatus.REVIEW, TaskStatus.FAILED): (_guard_diagnostic_set, "review_timeout"),
    (TaskStatus.REVIEW, TaskStatus.CANCELLED): (_guard_reason_set, "pr_closed_without_merge"),
    # From MERGE_READY
    (TaskStatus.MERGE_READY, TaskStatus.MERGING): (_guard_always_pass, "merge_started"),
    (TaskStatus.MERGE_READY, TaskStatus.DONE): (_guard_always_pass, "user_approves_merge"),
    (TaskStatus.MERGE_READY, TaskStatus.REVIEW): (_guard_always_pass, "last_minute_concern"),
    (TaskStatus.MERGE_READY, TaskStatus.CANCELLED): (_guard_reason_set, "user_declines"),
    # From MERGING
    (TaskStatus.MERGING, TaskStatus.DONE): (_guard_always_pass, "merge_complete"),
    (TaskStatus.MERGING, TaskStatus.FAILED): (_guard_diagnostic_set, "merge_failed"),
    # From BLOCKED
    (TaskStatus.BLOCKED, TaskStatus.ACTIVE): (_guard_always_pass, "unblock_condition_met"),
    (TaskStatus.BLOCKED, TaskStatus.DECOMPOSING): (_guard_always_pass, "unblock_condition_met"),
    (TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS): (_guard_worker_id_set, "unblock_condition_met"),
    (TaskStatus.BLOCKED, TaskStatus.REVIEW): (_guard_pr_url_set, "unblock_condition_met"),
    (TaskStatus.BLOCKED, TaskStatus.FAILED): (_guard_diagnostic_set, "blocked_timeout"),
    (TaskStatus.BLOCKED, TaskStatus.CANCELLED): (_guard_reason_set, "user_cancels"),
    # From DORMANT
    (TaskStatus.DORMANT, TaskStatus.ACTIVE): (_guard_always_pass, "user_reactivates"),
    (TaskStatus.DORMANT, TaskStatus.CANCELLED): (_guard_reason_set, "user_cancels"),
    # From FAILED
    (TaskStatus.FAILED, TaskStatus.ACTIVE): (_guard_always_pass, "user_retries"),
    (TaskStatus.FAILED, TaskStatus.CANCELLED): (_guard_reason_set, "user_abandons"),
    # Terminal states - only explicit transitions allowed
    # DONE and CANCELLED are terminal - no outgoing transitions
}


def _generate_idempotency_key(task_id: str, from_status: TaskStatus, to_status: TaskStatus) -> str:
    """Generate an idempotency key for a state transition.

    Format: {task_id}-{from_status}-{to_status}-{timestamp_epoch}
    """
    ts = int(datetime.now(UTC).timestamp())
    return f"{task_id}-{from_status.value}-{to_status.value}-{ts}"


def _validate_state_invariants(task: Task, new_status: TaskStatus, **kwargs: Any) -> tuple[bool, str | None]:
    """Validate state invariants for the target status.

    Args:
        task: The task being transitioned
        new_status: The target status
        **kwargs: Additional fields being set

    Returns:
        (is_valid, error_message)
    """
    # Check invariants based on target status
    if new_status == TaskStatus.BLOCKED:
        unblock_condition = kwargs.get("unblock_condition") or task.unblock_condition
        if not unblock_condition:
            return False, "BLOCKED status requires unblock_condition field"

    if new_status == TaskStatus.FAILED:
        diagnostic = kwargs.get("diagnostic") or task.diagnostic
        if not diagnostic:
            return False, "FAILED status requires diagnostic field"

    if new_status == TaskStatus.IN_PROGRESS:
        worker_id = kwargs.get("worker_id") or task.worker_id
        if not worker_id:
            return False, "IN_PROGRESS status requires worker_id field"

    if new_status in (TaskStatus.REVIEW, TaskStatus.MERGE_READY):
        pr_url = kwargs.get("pr_url") or task.pr_url
        if not pr_url:
            return False, f"{new_status.value} status requires pr_url field"

    return True, None


def _safe_parse_enum(
    value: str | None,
    enum_cls: type[E],
    default: E,
    field_name: str,
    task_id: str | None = None,
) -> E:
    """Safely parse an enum value, coercing invalid values to default with warning.

    Args:
        value: String value to parse (or None)
        enum_cls: Enum class to parse into
        default: Default value if parsing fails or value is None
        field_name: Field name for warning message
        task_id: Task ID for warning message (optional)

    Returns:
        Parsed enum value, or default if invalid
    """
    if value is None:
        return default

    try:
        return enum_cls(value)
    except ValueError:
        task_ref = f" (task: {task_id})" if task_id else ""
        logger.warning(
            "Invalid %s '%s'%s, coercing to '%s'",
            field_name,
            value,
            task_ref,
            default.value,
        )
        return default


@dataclass
class Task:
    """Task model with graph relationships for hierarchical decomposition.

    Core schema fields per specs/tasks-v2.md Section 1.
    """

    # Required fields
    id: str
    title: str

    # Core metadata
    type: TaskType = TaskType.TASK
    status: TaskStatus = TaskStatus.ACTIVE
    priority: int = 2  # 0-4 (0=critical, 4=someday)
    order: int = 0  # Sibling ordering (lower = first)
    created: datetime = field(default_factory=lambda: datetime.now(UTC))
    modified: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Graph relationships (stored in frontmatter)
    parent: str | None = None  # Parent task ID (null = root)
    depends_on: list[str] = field(default_factory=list)  # Must complete first (blocking)
    soft_depends_on: list[str] = field(default_factory=list)  # Context hints (non-blocking)

    # Decomposition metadata
    depth: int = 0  # Distance from root (0 = root goal)
    leaf: bool = True  # True if no children (actionable)

    # Optional fields
    due: datetime | None = None
    planned: datetime | None = None
    project: str | None = None  # Project slug
    tags: list[str] = field(default_factory=list)
    effort: str | None = None  # Estimated effort
    context: str | None = None  # @home, @computer, etc.
    assignee: str | None = None  # Task owner: 'nic' or 'polecat'
    complexity: TaskComplexity | None = None  # Routing classification (set by hydrator)

    # Workflow state fields (per non-interactive-agent-workflow-spec.md)
    unblock_condition: str | None = None  # Required when status=BLOCKED
    diagnostic: str | None = None  # Required when status=FAILED
    pr_url: str | None = None  # Required when status=REVIEW or MERGE_READY
    worker_id: str | None = None  # Required when status=IN_PROGRESS
    approval_type: ApprovalType | None = None  # Set when status=WAITING
    decision_deadline: datetime | None = None  # Set when status=WAITING
    retry_count: int = 0  # Incremented on each retry from FAILED
    idempotency_key: str | None = None  # For state transition deduplication

    # Body content (markdown below frontmatter)
    body: str = ""

    # Computed relationships (populated by index, not stored in file)
    children: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)  # Inverse of depends_on
    soft_blocks: list[str] = field(default_factory=list)  # Inverse of soft_depends_on

    def __post_init__(self) -> None:
        """Validate task after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate task fields."""
        if not self.id:
            raise ValueError("Task id is required")
        if not self.title:
            raise ValueError("Task title is required")
        # Accept:
        # - New format: <project>-<hash8> (e.g., aops-a1b2c3d4, ns-12345678)
        # - Legacy format: YYYYMMDD-slug (e.g., 20260119-my-task)
        # - Simple slug for permalinks (e.g., my-task-id)
        if not re.match(r"^[\w-]+$", self.id):
            raise ValueError(f"Task id must be slug format: {self.id}")
        if not 0 <= self.priority <= 4:
            raise ValueError(f"Priority must be 0-4, got {self.priority}")
        if self.depth < 0:
            raise ValueError(f"Depth must be non-negative, got {self.depth}")

    @classmethod
    def generate_id(cls, title: str, project: str | None = None) -> str:
        """Generate a task ID using project prefix and UUID hash.

        Args:
            title: Task title (used for slug in filename, not ID)
            project: Project slug (defaults to 'ns' for no-project)

        Returns:
            ID in format <project>-<uuid[:8]>"""
        prefix = project if project else "ns"
        hash_part = uuid.uuid4().hex[:8]
        return f"{prefix}-{hash_part}"

    @classmethod
    def slugify_title(cls, title: str, max_length: int = 50) -> str:
        """Generate a URL-safe slug from title.

        Args:
            title: Task title to slugify
            max_length: Maximum slug length

        Returns:
            Slugified title for use in filenames
        """
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)  # Remove non-word chars
        slug = re.sub(r"[\s_]+", "-", slug)  # Replace spaces/underscores
        slug = re.sub(r"-+", "-", slug)  # Collapse multiple dashes
        slug = slug.strip("-")[:max_length]
        return slug

    def to_frontmatter(self) -> dict[str, Any]:
        """Convert task to frontmatter dictionary.

        Returns:
            Dictionary suitable for YAML serialization
        """
        # Generate permalink (stable identifier)
        permalink = self.id

        # Generate alias list (filename slug + id for multiple link resolution)
        slug = self.slugify_title(self.title)
        alias = [f"{self.id}-{slug}", self.id]

        fm: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "permalink": permalink,
            "alias": alias,
            "type": self.type.value,
            "status": self.status.value,
            "priority": self.priority,
            "order": self.order,
            "created": self.created.isoformat(),
            "modified": self.modified.isoformat(),
            "parent": self.parent,
            "depends_on": self.depends_on if self.depends_on else [],
            "soft_depends_on": self.soft_depends_on if self.soft_depends_on else [],
            "depth": self.depth,
            "leaf": self.leaf,
        }

        # Optional fields (only include if set)
        if self.due:
            fm["due"] = self.due.isoformat()
        if self.planned:
            fm["planned"] = self.planned.isoformat()
        if self.project:
            fm["project"] = self.project
        if self.tags:
            fm["tags"] = self.tags
        if self.effort:
            fm["effort"] = self.effort
        if self.context:
            fm["context"] = self.context
        if self.assignee:
            fm["assignee"] = self.assignee
        if self.complexity:
            fm["complexity"] = self.complexity.value

        # Workflow state fields (only include if set)
        if self.unblock_condition:
            fm["unblock_condition"] = self.unblock_condition
        if self.diagnostic:
            fm["diagnostic"] = self.diagnostic
        if self.pr_url:
            fm["pr_url"] = self.pr_url
        if self.worker_id:
            fm["worker_id"] = self.worker_id
        if self.approval_type:
            fm["approval_type"] = self.approval_type.value
        if self.decision_deadline:
            fm["decision_deadline"] = self.decision_deadline.isoformat()
        if self.retry_count:
            fm["retry_count"] = self.retry_count
        if self.idempotency_key:
            fm["idempotency_key"] = self.idempotency_key

        return fm

    # Status aliases for convenience (hyphenated forms)
    STATUS_ALIASES = {
        "in-progress": "in_progress",
        "merge-ready": "merge_ready",
    }

    @classmethod
    def from_frontmatter(cls, fm: dict[str, Any], body: str = "") -> Task:
        """Create Task from frontmatter dictionary.

        Args:
            fm: Frontmatter dictionary from YAML
            body: Markdown body content

        Returns:
            Task instance
        """
        # Resolve ID: prefer id > task_id > permalink
        task_id = fm.get("id") or fm.get("task_id") or fm.get("permalink")
        if not task_id:
            raise ValueError("Task frontmatter missing id, task_id, or permalink")

        # Parse timestamps
        created = fm.get("created")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(UTC)

        modified = fm.get("modified") or fm.get("updated")
        if isinstance(modified, str):
            modified = datetime.fromisoformat(modified)
        elif modified is None:
            modified = datetime.now(UTC)

        due = fm.get("due")
        if isinstance(due, str):
            due = datetime.fromisoformat(due)

        planned = fm.get("planned")
        if isinstance(planned, str):
            planned = datetime.fromisoformat(planned)

        decision_deadline = fm.get("decision_deadline")
        if isinstance(decision_deadline, str):
            decision_deadline = datetime.fromisoformat(decision_deadline)

        # Parse type - require explicit type field (skip non-task files)
        task_type_str = fm.get("type")
        if task_type_str is None:
            raise ValueError(f"Missing 'type' field for item {task_id} - not a task file")
        try:
            task_type = TaskType(task_type_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid type '{task_type_str}' for item {task_id} - not a task"
            ) from e

        # Map status aliases and parse with graceful coercion
        status_str = fm.get("status", "active")
        if isinstance(status_str, str):
            status_str = cls.STATUS_ALIASES.get(status_str, status_str)
        status = _safe_parse_enum(status_str, TaskStatus, TaskStatus.ACTIVE, "status", task_id)

        # Parse numeric fields (may come as strings from YAML)
        priority = fm.get("priority", 2)
        if isinstance(priority, str):
            priority = int(priority) if priority.isdigit() else 2
        order = fm.get("order", 0)
        if isinstance(order, str):
            order = int(order) if order.isdigit() else 0
        depth = fm.get("depth", 0)
        if isinstance(depth, str):
            depth = int(depth) if depth.isdigit() else 0

        # Parse complexity (optional field - None is valid)
        complexity_str = fm.get("complexity")
        complexity: TaskComplexity | None = None
        if complexity_str is not None:
            try:
                complexity = TaskComplexity(complexity_str)
            except ValueError:
                logger.warning(
                    "Invalid complexity '%s' (task: %s), ignoring",
                    complexity_str,
                    task_id,
                )

        # Parse approval_type (optional field - None is valid)
        approval_type_str = fm.get("approval_type")
        approval_type: ApprovalType | None = None
        if approval_type_str is not None:
            try:
                approval_type = ApprovalType(approval_type_str)
            except ValueError:
                logger.warning(
                    "Invalid approval_type '%s' (task: %s), ignoring",
                    approval_type_str,
                    task_id,
                )

        # Parse retry_count (defaults to 0)
        retry_count = fm.get("retry_count", 0)
        if isinstance(retry_count, str):
            retry_count = int(retry_count) if retry_count.isdigit() else 0

        return cls(
            id=task_id,
            title=fm["title"],
            type=task_type,
            status=status,
            priority=priority,
            order=order,
            created=created,
            modified=modified,
            parent=fm.get("parent"),
            depends_on=fm.get("depends_on", []),
            soft_depends_on=fm.get("soft_depends_on", []),
            depth=depth,
            leaf=fm.get("leaf", True),
            due=due,
            planned=planned,
            project=fm.get("project"),
            tags=fm.get("tags", []),
            effort=fm.get("effort"),
            context=fm.get("context"),
            assignee=fm.get("assignee"),
            complexity=complexity,
            # Workflow state fields
            unblock_condition=fm.get("unblock_condition"),
            diagnostic=fm.get("diagnostic"),
            pr_url=fm.get("pr_url"),
            worker_id=fm.get("worker_id"),
            approval_type=approval_type,
            decision_deadline=decision_deadline,
            retry_count=retry_count,
            idempotency_key=fm.get("idempotency_key"),
            body=body,
        )

    def _render_relationships(self) -> str:
        """Render relationships section as markdown.

        Returns:
            Markdown string with relationship links, or empty string if no relationships
        """
        lines = []

        # depends_on: tasks this task depends on (from frontmatter) - blocking
        for dep_id in self.depends_on:
            lines.append(f"- [depends_on] [[{dep_id}]]")

        # soft_depends_on: tasks this task soft-depends on (from frontmatter) - non-blocking
        for soft_dep_id in self.soft_depends_on:
            lines.append(f"- [soft_depends_on] [[{soft_dep_id}]]")

        # blocks: tasks that depend on this task (computed inverse of depends_on)
        for block_id in self.blocks:
            lines.append(f"- [blocks] [[{block_id}]]")

        # soft_blocks: tasks that soft-depend on this task (computed inverse of soft_depends_on)
        for soft_block_id in self.soft_blocks:
            lines.append(f"- [soft_blocks] [[{soft_block_id}]]")

        # parent: parent task (from frontmatter)
        if self.parent:
            lines.append(f"- [parent] [[{self.parent}]]")

        # children: child tasks (computed inverse)
        for child_id in self.children:
            lines.append(f"- [child] [[{child_id}]]")

        if not lines:
            return ""

        return "## Relationships\n\n" + "\n".join(lines)

    def to_markdown(self) -> str:
        """Convert task to markdown with YAML frontmatter.

        Returns:
            Full markdown content with frontmatter and body
        """
        fm = self.to_frontmatter()
        yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)

        parts = ["---", yaml_str.rstrip(), "---", ""]

        # Add title as H1 if body doesn't start with it
        if not self.body.strip().startswith(f"# {self.title}"):
            parts.append(f"# {self.title}")
            parts.append("")

        # Add body content (strip any existing Relationships section)
        if self.body:
            body_clean = self._strip_relationships_section(self.body)
            parts.append(body_clean)

        # Add relationships section at the end
        relationships = self._render_relationships()
        if relationships:
            parts.append("")
            parts.append(relationships)

        return "\n".join(parts)

    def _strip_relationships_section(self, body: str) -> str:
        """Remove existing Relationships section from body.

        Args:
            body: Markdown body content

        Returns:
            Body with Relationships section removed
        """
        # Match ## Relationships followed by content until next ## or end
        # Use lookahead to preserve the next section's newlines
        pattern = r"\n*## Relationships\n[\s\S]*?(?=\n\n## |\Z)"
        result = re.sub(pattern, "", body)
        # Normalize multiple newlines and strip trailing whitespace
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.rstrip()

    @classmethod
    def from_markdown(cls, content: str) -> Task:
        """Parse task from markdown with YAML frontmatter.

        Args:
            content: Full markdown content

        Returns:
            Task instance

        Raises:
            ValueError: If frontmatter is missing or invalid
        """
        if not content.startswith("---"):
            raise ValueError("Task file must start with YAML frontmatter (---)")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid frontmatter format")

        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e

        if not fm:
            raise ValueError("Empty frontmatter")
        # Accept id, task_id, or permalink as the ID field
        if "id" not in fm and "task_id" not in fm and "permalink" not in fm:
            raise ValueError("Task frontmatter missing required field: id, task_id, or permalink")
        if "title" not in fm:
            raise ValueError("Task frontmatter missing required field: title")

        body = parts[2].strip()
        return cls.from_frontmatter(fm, body)

    def to_file(self, path: Path) -> None:
        """Write task to file.

        Args:
            path: File path to write to
        """
        # Update modified timestamp
        self.modified = datetime.now(UTC)
        content = self.to_markdown()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @classmethod
    def from_file(cls, path: Path) -> Task:
        """Load task from file.

        Args:
            path: File path to read from

        Returns:
            Task instance
        """
        content = path.read_text(encoding="utf-8")
        return cls.from_markdown(content)

    def is_ready(self) -> bool:
        """Check if task is ready to work on.

        A task is ready if:
        - It's a leaf (has no children)
        - It has no unmet dependencies
        - Status is active (not in_progress, blocked, etc.)
        - Type is not LEARN (observational, not actionable)
        """
        if not self.leaf:
            return False
        if self.depends_on:
            return False  # Index should filter by completed deps
        if self.type == TaskType.LEARN:
            return False  # Learn tasks are observational, not actionable
        return self.status == TaskStatus.ACTIVE

    def is_blocked(self) -> bool:
        """Check if task is blocked by dependencies."""
        return bool(self.depends_on) or self.status == TaskStatus.BLOCKED

    def add_child(self, child_id: str) -> None:
        """Mark this task as having a child (no longer a leaf).

        Args:
            child_id: ID of child task
        """
        if child_id not in self.children:
            self.children.append(child_id)
        self.leaf = False

    def complete(self) -> None:
        """Mark task as done."""
        self.status = TaskStatus.DONE
        self.modified = datetime.now(UTC)

    # =========================================================================
    # State Transition System
    # =========================================================================

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Check if a transition to the given status is valid.

        Only checks if the transition exists in the table, not guards.

        Args:
            new_status: Target status

        Returns:
            True if transition is valid
        """
        return (self.status, new_status) in TRANSITION_TABLE

    def get_valid_transitions(self) -> list[TaskStatus]:
        """Get list of valid target statuses from current status.

        Returns:
            List of valid target statuses
        """
        return [
            to_status
            for (from_status, to_status) in TRANSITION_TABLE
            if from_status == self.status
        ]

    def transition_to(
        self,
        new_status: TaskStatus,
        *,
        trigger: str = "manual",
        actor: str = "system",
        audit_log_path: Path | None = None,
        # Optional fields to set during transition
        unblock_condition: str | None = None,
        diagnostic: str | None = None,
        pr_url: str | None = None,
        worker_id: str | None = None,
        approval_type: ApprovalType | None = None,
        decision_deadline: datetime | None = None,
        reason: str | None = None,
    ) -> TransitionResult:
        """Attempt a state transition with guard validation and logging.

        Args:
            new_status: Target status
            trigger: What triggered this transition (for audit)
            actor: Who/what is performing the transition (for audit)
            audit_log_path: Path to JSONL audit log (optional)
            unblock_condition: Set when transitioning to BLOCKED
            diagnostic: Set when transitioning to FAILED
            pr_url: Set when transitioning to REVIEW/MERGE_READY
            worker_id: Set when transitioning to IN_PROGRESS
            approval_type: Set when transitioning to WAITING
            decision_deadline: Set when transitioning to WAITING
            reason: Set when transitioning to CANCELLED

        Returns:
            TransitionResult indicating success/failure

        Example:
            result = task.transition_to(
                TaskStatus.IN_PROGRESS,
                trigger="worker_claims",
                actor="polecat-claude",
                worker_id="polecat-claude-1",
            )
        """
        from_status = self.status

        # Check if transition is explicitly defined in table (even if self-transition)
        transition_key = (from_status, new_status)
        is_explicit = transition_key in TRANSITION_TABLE

        # Check if already at target status (no-op), unless it's an explicit self-transition
        # (like DECOMPOSING -> DECOMPOSING iteration) which must run guards.
        if from_status == new_status and not is_explicit:
            return TransitionResult(
                success=True,
                from_status=from_status,
                to_status=new_status,
                idempotency_key=self.idempotency_key,
            )

        # Check idempotency - if same transition with same key, return success
        if self.idempotency_key:
            # Parse existing key: {task_id}-{from}-{to}-{ts}
            parts = self.idempotency_key.rsplit("-", 3)
            if len(parts) >= 3:
                existing_from = parts[-3] if len(parts) > 3 else parts[0]
                existing_to = parts[-2]
                if existing_from == from_status.value and existing_to == new_status.value:
                    # Idempotent - same transition already applied
                    return TransitionResult(
                        success=True,
                        from_status=from_status,
                        to_status=new_status,
                        idempotency_key=self.idempotency_key,
                    )

        # Check if transition is valid
        transition_key = (from_status, new_status)
        if transition_key not in TRANSITION_TABLE:
            valid_targets = self.get_valid_transitions()
            valid_names = [s.value for s in valid_targets]
            return TransitionResult(
                success=False,
                from_status=from_status,
                to_status=new_status,
                error=f"Invalid transition: {from_status.value} -> {new_status.value}. "
                f"Valid targets: {valid_names}",
            )

        guard_func, _ = TRANSITION_TABLE[transition_key]

        # Build kwargs for guard
        kwargs: dict[str, Any] = {
            "unblock_condition": unblock_condition,
            "diagnostic": diagnostic,
            "pr_url": pr_url,
            "worker_id": worker_id,
            "approval_type": approval_type,
            "decision_deadline": decision_deadline,
            "reason": reason,
        }

        # Run guard
        guard_passed, guard_error = guard_func(self, **kwargs)
        if not guard_passed:
            return TransitionResult(
                success=False,
                from_status=from_status,
                to_status=new_status,
                error=f"Guard failed: {guard_error}",
            )

        # Validate state invariants
        invariant_valid, invariant_error = _validate_state_invariants(
            self, new_status, **kwargs
        )
        if not invariant_valid:
            return TransitionResult(
                success=False,
                from_status=from_status,
                to_status=new_status,
                error=f"State invariant violated: {invariant_error}",
            )

        # Generate idempotency key
        idempotency_key = _generate_idempotency_key(self.id, from_status, new_status)

        # Apply transition
        self.status = new_status
        self.modified = datetime.now(UTC)
        self.idempotency_key = idempotency_key

        # Set optional fields
        if unblock_condition is not None:
            self.unblock_condition = unblock_condition
        if diagnostic is not None:
            self.diagnostic = diagnostic
        if pr_url is not None:
            self.pr_url = pr_url
        if worker_id is not None:
            self.worker_id = worker_id
        if approval_type is not None:
            self.approval_type = approval_type
        if decision_deadline is not None:
            self.decision_deadline = decision_deadline

        # Clear fields that don't apply to new status
        if new_status not in (TaskStatus.BLOCKED,):
            self.unblock_condition = None
        if new_status not in (TaskStatus.FAILED,):
            # Keep diagnostic for history when retrying
            pass
        # Keep worker_id and pr_url for audit trail on terminal states
        if new_status not in (TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELLED, TaskStatus.REVIEW, TaskStatus.MERGE_READY, TaskStatus.MERGING):
            self.worker_id = None
        if new_status not in (TaskStatus.REVIEW, TaskStatus.MERGE_READY, TaskStatus.MERGING, TaskStatus.DONE, TaskStatus.CANCELLED):
            self.pr_url = None
        if new_status not in (TaskStatus.WAITING,):
            self.approval_type = None
            self.decision_deadline = None

        # Increment retry count if transitioning from FAILED
        if from_status == TaskStatus.FAILED and new_status == TaskStatus.ACTIVE:
            self.retry_count += 1

        # Log transition
        log_entry = TransitionLogEntry(
            ts=datetime.now(UTC),
            task=self.id,
            from_status=from_status.value,
            to_status=new_status.value,
            trigger=trigger,
            actor=actor,
            idempotency_key=idempotency_key,
        )

        # Write to audit log if path provided
        if audit_log_path:
            self._write_audit_log(log_entry, audit_log_path)

        # Also log to Python logger
        logger.info(
            "Task %s: %s -> %s (trigger=%s, actor=%s)",
            self.id,
            from_status.value,
            new_status.value,
            trigger,
            actor,
        )

        return TransitionResult(
            success=True,
            from_status=from_status,
            to_status=new_status,
            idempotency_key=idempotency_key,
        )

    def _write_audit_log(self, entry: TransitionLogEntry, log_path: Path) -> None:
        """Write a transition log entry to the audit log.

        Args:
            entry: Log entry to write
            log_path: Path to JSONL audit log file
        """
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except OSError as e:
            logger.warning("Failed to write audit log: %s", e)

    @classmethod
    def get_default_audit_log_path(cls) -> Path:
        """Get the default audit log path.

        Returns:
            Path to data/aops-core/audit/transitions.jsonl
        """
        # Assuming we're in the aops-core directory structure
        return Path("data/aops-core/audit/transitions.jsonl")

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r}, type={self.type.value})"


# =============================================================================
# Utility Functions
# =============================================================================


def get_transition_info(from_status: TaskStatus, to_status: TaskStatus) -> dict[str, Any] | None:
    """Get information about a specific transition.

    Args:
        from_status: Source status
        to_status: Target status

    Returns:
        Dict with guard and trigger info, or None if transition is invalid
    """
    key = (from_status, to_status)
    if key not in TRANSITION_TABLE:
        return None

    guard_func, trigger = TRANSITION_TABLE[key]
    return {
        "from": from_status.value,
        "to": to_status.value,
        "trigger": trigger,
        "guard": guard_func.__name__,
    }


def get_all_transitions() -> list[dict[str, Any]]:
    """Get all valid transitions.

    Returns:
        List of transition info dicts
    """
    return [
        {
            "from": from_status.value,
            "to": to_status.value,
            "trigger": trigger,
            "guard": guard_func.__name__,
        }
        for (from_status, to_status), (guard_func, trigger) in TRANSITION_TABLE.items()
    ]
