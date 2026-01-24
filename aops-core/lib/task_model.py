#!/usr/bin/env python3
"""Task Model v2: Hierarchical task decomposition with graph relationships.

Implements the Task model per specs/tasks-v2.md with:
- Graph relationships (parent, depends_on, children, blocks)
- Hierarchical decomposition (goal → project → task → action)
- YAML frontmatter serialization
- Validation and type safety

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
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


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
    """Task lifecycle states."""

    INBOX = "inbox"  # Captured but not committed
    ACTIVE = "active"  # Currently workable (no blockers)
    BLOCKED = "blocked"  # Waiting on dependencies
    WAITING = "waiting"  # Waiting on external input
    REVIEW = "review"  # Awaiting human review before completion
    DONE = "done"  # Completed
    CANCELLED = "cancelled"  # Abandoned


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
    status: TaskStatus = TaskStatus.INBOX
    priority: int = 2  # 0-4 (0=critical, 4=someday)
    order: int = 0  # Sibling ordering (lower = first)
    created: datetime = field(default_factory=lambda: datetime.now(UTC))
    modified: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Graph relationships (stored in frontmatter)
    parent: str | None = None  # Parent task ID (null = root)
    depends_on: list[str] = field(default_factory=list)  # Must complete first

    # Decomposition metadata
    depth: int = 0  # Distance from root (0 = root goal)
    leaf: bool = True  # True if no children (actionable)

    # Optional fields
    due: datetime | None = None
    project: str | None = None  # Project slug
    tags: list[str] = field(default_factory=list)
    effort: str | None = None  # Estimated effort
    context: str | None = None  # @home, @computer, etc.
    assignee: str | None = None  # Task owner: 'nic' or 'bot'
    complexity: TaskComplexity | None = None  # Routing classification (set by hydrator)

    # Body content (markdown below frontmatter)
    body: str = ""

    # Computed relationships (populated by index, not stored in file)
    children: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)

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
        if not re.match(r"^[\w]+-[\w-]+$", self.id):
            raise ValueError(
                f"Task id must be slug format: {self.id}"
            )
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
            ID in format <project>-<uuid[:8]>
        """
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
            "depth": self.depth,
            "leaf": self.leaf,
        }

        # Optional fields (only include if set)
        if self.due:
            fm["due"] = self.due.isoformat()
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

        return fm

    # Status aliases for backwards compatibility
    STATUS_ALIASES = {
        "todo": "inbox",
        "open": "inbox",
        "in_progress": "active",
        "in-progress": "active",
        "in_review": "review",
        "in-review": "review",
        "complete": "done",
        "completed": "done",
        "closed": "done",
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

        # Parse enums
        task_type = fm.get("type", "task")
        if isinstance(task_type, str):
            task_type = TaskType(task_type)

        # Map status aliases
        status = fm.get("status", "inbox")
        if isinstance(status, str):
            status = cls.STATUS_ALIASES.get(status, status)
            status = TaskStatus(status)

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

        # Parse complexity
        complexity = fm.get("complexity")
        if isinstance(complexity, str):
            complexity = TaskComplexity(complexity)

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
            depth=depth,
            leaf=fm.get("leaf", True),
            due=due,
            project=fm.get("project"),
            tags=fm.get("tags", []),
            effort=fm.get("effort"),
            context=fm.get("context"),
            assignee=fm.get("assignee"),
            complexity=complexity,
            body=body,
        )

    def _render_relationships(self) -> str:
        """Render relationships section as markdown.

        Returns:
            Markdown string with relationship links, or empty string if no relationships
        """
        lines = []

        # depends_on: tasks this task depends on (from frontmatter)
        for dep_id in self.depends_on:
            lines.append(f"- [depends_on] [[{dep_id}]]")

        # blocks: tasks that depend on this task (computed inverse)
        for block_id in self.blocks:
            lines.append(f"- [blocks] [[{block_id}]]")

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
        - Status is active or inbox
        - Type is not LEARN (observational, not actionable)
        """
        if not self.leaf:
            return False
        if self.depends_on:
            return False  # Index should filter by completed deps
        if self.type == TaskType.LEARN:
            return False  # Learn tasks are observational, not actionable
        return self.status in (TaskStatus.ACTIVE, TaskStatus.INBOX)

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

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r}, type={self.type.value})"
