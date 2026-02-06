#!/usr/bin/env python3
"""Task Index v2: Graph-aware index for hierarchical tasks.

Implements index schema per specs/tasks-v2.md Section 6:
- Computed fields: children, blocks, ready, blocked
- Project grouping
- Root task identification
- Fast graph queries via JSON index

Index Schema:
    {
      "version": 2,
      "generated": "ISO timestamp",
      "tasks": {
        "task-id": {
          "id", "title", "type", "status", "order",
          "parent", "children": [computed],
          "depends_on", "blocks": [computed],
          "depth", "leaf", "project", "path"
        }
      },
      "by_project": { "project": ["task-ids"] },
      "roots": ["root-task-ids"],
      "ready": ["actionable-task-ids"],
      "blocked": ["blocked-task-ids"]
    }

Usage:
    from lib.task_index import TaskIndex

    index = TaskIndex()
    index.rebuild()

    ready = index.get_ready_tasks()
    children = index.get_children("20260112-write-book")
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.paths import get_data_root
from lib.task_model import Task, TaskStatus, TaskType
from lib.task_storage import TaskStorage

logger = logging.getLogger(__name__)


@dataclass
class TaskIndexEntry:
    """Index entry for a single task.

    Contains all fields needed for fast queries without file I/O.
    """

    id: str
    title: str
    type: str
    status: str
    priority: int
    order: int
    parent: str | None
    children: list[str]  # Computed: inverse of parent
    depends_on: list[str]
    blocks: list[str]  # Computed: inverse of depends_on
    soft_depends_on: list[str] = field(
        default_factory=list
    )  # Non-blocking context hints
    soft_blocks: list[str] = field(
        default_factory=list
    )  # Computed: inverse of soft_depends_on
    depth: int = 0
    leaf: bool = True
    project: str | None = None
    path: str = ""
    due: str | None = None
    tags: list[str] = field(default_factory=list)
    assignee: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "status": self.status,
            "priority": self.priority,
            "order": self.order,
            "parent": self.parent,
            "children": self.children,
            "depends_on": self.depends_on,
            "blocks": self.blocks,
            "soft_depends_on": self.soft_depends_on,
            "soft_blocks": self.soft_blocks,
            "depth": self.depth,
            "leaf": self.leaf,
            "project": self.project,
            "path": self.path,
            "due": self.due,
            "tags": self.tags,
            "assignee": self.assignee,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskIndexEntry:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            type=data["type"],
            status=data["status"],
            priority=data.get("priority", 2),
            order=data.get("order", 0),
            parent=data.get("parent"),
            children=data.get("children", []),
            depends_on=data.get("depends_on", []),
            blocks=data.get("blocks", []),
            soft_depends_on=data.get("soft_depends_on", []),
            soft_blocks=data.get("soft_blocks", []),
            depth=data.get("depth", 0),
            leaf=data.get("leaf", True),
            project=data.get("project"),
            path=data["path"],
            due=data.get("due"),
            tags=data.get("tags", []),
            assignee=data.get("assignee"),
        )

    @classmethod
    def from_task(cls, task: Task, path: str) -> TaskIndexEntry:
        """Create from Task model."""
        return cls(
            id=task.id,
            title=task.title,
            type=task.type.value,
            status=task.status.value,
            priority=task.priority,
            order=task.order,
            parent=task.parent,
            children=[],  # Computed during index build
            depends_on=task.depends_on,
            blocks=[],  # Computed during index build
            soft_depends_on=task.soft_depends_on,
            soft_blocks=[],  # Computed during index build
            depth=task.depth,
            leaf=task.leaf,
            project=task.project,
            path=path,
            due=task.due.isoformat() if task.due else None,
            tags=task.tags,
            assignee=task.assignee,
        )


def _find_fast_indexer() -> Path | None:
    """Find the fast-indexer binary.

    Looks for the binary in the following locations:
    1. FAST_INDEXER_PATH environment variable
    2. Relative to this module: ../../lib/fast-indexer/target/release/fast-indexer
    3. On PATH

    Returns:
        Path to binary if found, None otherwise
    """
    import os

    # 1. Environment variable
    if env_path := os.environ.get("FAST_INDEXER_PATH"):
        p = Path(env_path)
        if p.exists() and p.is_file():
            return p

    # 2. Relative to module (development location)
    module_dir = Path(__file__).parent
    dev_binary = (
        module_dir.parent.parent
        / "lib"
        / "fast-indexer"
        / "target"
        / "release"
        / "fast-indexer"
    )
    if dev_binary.exists():
        return dev_binary

    # 3. On PATH
    if path_binary := shutil.which("fast-indexer"):
        return Path(path_binary)

    return None


class TaskIndex:
    """Graph-aware index for fast task queries.

    Maintains a JSON index with computed relationships:
    - children: Tasks that have this task as parent
    - blocks: Tasks that depend on this task
    - ready: Leaf tasks with no unmet dependencies
    - blocked: Tasks with unmet dependencies

    Supports two rebuild modes:
    - rebuild(): Pure Python implementation (fallback)
    - rebuild_fast(): Uses fast-indexer Rust binary (default when available)
    """

    VERSION = 2

    # Task types that can be claimed by workers (actionable work items)
    CLAIMABLE_TYPES = {
        TaskType.TASK.value,
        TaskType.ACTION.value,
        TaskType.BUG.value,
        TaskType.FEATURE.value,
    }

    def __init__(self, data_root: Path | None = None):
        """Initialize task index.

        Args:
            data_root: Root data directory. Defaults to $ACA_DATA.
        """
        self.data_root = data_root or get_data_root()
        self.storage = TaskStorage(self.data_root)
        self._tasks: dict[str, TaskIndexEntry] = {}
        self._by_project: dict[str, list[str]] = {}
        self._roots: list[str] = []
        self._ready: list[str] = []
        self._blocked: list[str] = []
        self._generated: str | None = None
        self._fast_indexer_path: Path | None = _find_fast_indexer()

    @property
    def index_path(self) -> Path:
        """Path to index.json file."""
        return self.data_root / "tasks" / "index.json"

    def rebuild(self) -> None:
        """Rebuild index from task files.

        Scans all project directories and inbox for task files,
        computes graph relationships, and writes index.json.
        """
        self._tasks = {}
        self._by_project = {}
        self._roots = []
        self._ready = []
        self._blocked = []

        # Load all tasks with their paths
        for task, path in self.storage._iter_all_tasks_with_paths():
            rel_path = str(path.relative_to(self.data_root))
            entry = TaskIndexEntry.from_task(task, rel_path)
            self._tasks[task.id] = entry

        # Compute children (inverse of parent)
        for task_id, entry in self._tasks.items():
            if entry.parent and entry.parent in self._tasks:
                self._tasks[entry.parent].children.append(task_id)

        # Compute blocks (inverse of depends_on)
        for task_id, entry in self._tasks.items():
            for dep_id in entry.depends_on:
                if dep_id in self._tasks:
                    self._tasks[dep_id].blocks.append(task_id)

        # Compute soft_blocks (inverse of soft_depends_on)
        for task_id, entry in self._tasks.items():
            for soft_dep_id in entry.soft_depends_on:
                if soft_dep_id in self._tasks:
                    self._tasks[soft_dep_id].soft_blocks.append(task_id)

        # Update leaf status based on computed children AND frontmatter
        # A task is a leaf only if:
        # 1. It has no computed children, AND
        # 2. Its frontmatter says leaf=True (respects explicit non-leaf declarations)
        for task_id, entry in self._tasks.items():
            has_children = len(entry.children) > 0
            # If frontmatter said leaf=False, keep it False (declared parent)
            # If we found children, set to False
            # Only True if both: frontmatter=True AND no children found
            entry.leaf = not has_children and entry.leaf

        # Compute project groupings
        for task_id, entry in self._tasks.items():
            project = entry.project or "inbox"
            if project not in self._by_project:
                self._by_project[project] = []
            self._by_project[project].append(task_id)

        # Identify roots (no parent OR parent doesn't exist in index)
        # Orphan tasks (with non-existent parents) are treated as roots
        self._roots = [
            tid
            for tid, e in self._tasks.items()
            if e.parent is None or e.parent not in self._tasks
        ]

        # Compute ready and blocked
        completed_statuses = {TaskStatus.DONE.value, TaskStatus.CANCELLED.value}
        completed_ids = {
            tid for tid, e in self._tasks.items() if e.status in completed_statuses
        }

        for task_id, entry in self._tasks.items():
            # Skip completed tasks
            if entry.status in completed_statuses:
                continue

            # Check if blocked
            unmet_deps = [d for d in entry.depends_on if d not in completed_ids]
            if unmet_deps or entry.status == TaskStatus.BLOCKED.value:
                self._blocked.append(task_id)
            elif (
                entry.leaf
                and entry.status == TaskStatus.ACTIVE.value
                and entry.type in self.CLAIMABLE_TYPES
            ):
                self._ready.append(task_id)

        # Sort ready by priority
        self._ready.sort(
            key=lambda tid: (
                self._tasks[tid].priority,
                self._tasks[tid].order,
                self._tasks[tid].title,
            )
        )

        self._generated = datetime.now().astimezone().replace(microsecond=0).isoformat()
        self._save()

    def _save(self) -> None:
        """Write index to JSON file."""
        index_data = {
            "version": self.VERSION,
            "generated": self._generated,
            "tasks": {tid: e.to_dict() for tid, e in self._tasks.items()},
            "by_project": self._by_project,
            "roots": self._roots,
            "ready": self._ready,
            "blocked": self._blocked,
        }

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

    def rebuild_fast(self) -> bool:
        """Rebuild index using fast-indexer Rust binary.

        This is significantly faster than the Python implementation,
        especially for large task collections.

        Returns:
            True if fast rebuild succeeded, False if binary not available
            or failed (caller should fall back to Python rebuild).
        """
        if not self._fast_indexer_path:
            logger.debug("fast-indexer binary not found, falling back to Python")
            return False

        # Scan from data_root to find tasks in all project directories
        # (e.g., aops/tasks/, academic/tasks/, hdr/tasks/, tasks/inbox/)
        scan_dir = self.data_root
        if not scan_dir.exists():
            logger.warning("Data root does not exist: %s", scan_dir)
            return False

        # Run fast-indexer with mcp-index format
        # Output goes to tasks/index (fast-indexer adds .json extension)
        output_base = str(self.index_path).removesuffix(".json")
        cmd = [
            str(self._fast_indexer_path),
            str(scan_dir),
            "-f",
            "mcp-index",
            "-o",
            output_base,
            "--quiet",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warning(
                    "fast-indexer failed (exit %d): %s",
                    result.returncode,
                    result.stderr,
                )
                return False

            # Load the generated index into memory
            if not self.load():
                logger.warning("Failed to load index generated by fast-indexer")
                return False

            logger.info("Rebuilt index using fast-indexer: %s tasks", len(self._tasks))
            return True

        except subprocess.TimeoutExpired:
            logger.warning("fast-indexer timed out")
            return False
        except OSError as e:
            logger.warning("Failed to run fast-indexer: %s", e)
            return False

    def load(self) -> bool:
        """Load index from JSON file.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.index_path.exists():
            return False

        try:
            with open(self.index_path, encoding="utf-8") as f:
                data = json.load(f)

            if data.get("version") != self.VERSION:
                return False

            self._generated = data.get("generated")
            self._tasks = {
                tid: TaskIndexEntry.from_dict(entry)
                for tid, entry in data.get("tasks", {}).items()
            }
            self._by_project = data.get("by_project", {})
            self._roots = data.get("roots", [])
            self._ready = data.get("ready", [])
            self._blocked = data.get("blocked", [])

            return True
        except (json.JSONDecodeError, KeyError, TypeError):
            return False

    def get_task(self, task_id: str) -> TaskIndexEntry | None:
        """Get task entry by ID.

        Args:
            task_id: Task ID

        Returns:
            TaskIndexEntry if found, None otherwise
        """
        return self._tasks.get(task_id)

    def get_children(self, task_id: str) -> list[TaskIndexEntry]:
        """Get direct children of a task.

        Args:
            task_id: Parent task ID

        Returns:
            List of child entries sorted by order
        """
        entry = self._tasks.get(task_id)
        if not entry:
            return []

        children = [self._tasks[cid] for cid in entry.children if cid in self._tasks]
        children.sort(key=lambda e: (e.order, e.title))
        return children

    def get_descendants(self, task_id: str) -> list[TaskIndexEntry]:
        """Get all descendants of a task.

        Args:
            task_id: Ancestor task ID

        Returns:
            List of all descendant entries
        """
        descendants = []
        to_visit = [task_id]

        while to_visit:
            current_id = to_visit.pop(0)
            entry = self._tasks.get(current_id)
            if not entry:
                continue

            for child_id in entry.children:
                if child_id in self._tasks:
                    descendants.append(self._tasks[child_id])
                    to_visit.append(child_id)

        return descendants

    def get_ancestors(self, task_id: str) -> list[TaskIndexEntry]:
        """Get path from task to root.

        Args:
            task_id: Task ID

        Returns:
            List of ancestors from parent to root
        """
        ancestors = []
        entry = self._tasks.get(task_id)

        while entry and entry.parent:
            parent = self._tasks.get(entry.parent)
            if parent:
                ancestors.append(parent)
                entry = parent
            else:
                break

        return ancestors

    def get_root(self, task_id: str) -> TaskIndexEntry | None:
        """Get root goal for a task.

        Args:
            task_id: Task ID

        Returns:
            Root entry, or self if already root
        """
        ancestors = self.get_ancestors(task_id)
        if ancestors:
            return ancestors[-1]
        return self._tasks.get(task_id)

    # Tags that indicate human-assigned tasks (excluded when caller is 'bot')
    HUMAN_TAGS = {"nic", "human"}

    def get_ready_tasks(
        self, project: str | None = None, caller: str | None = None
    ) -> list[TaskIndexEntry]:
        """Get tasks ready to work on.

        Args:
            project: Filter by project
            caller: Filter by assignee - returns tasks where assignee is None
                    or assignee matches caller. If caller is None, returns all.
                    When caller is 'bot', also excludes tasks with human tags
                    ('nic', 'human') in their tags list.

        Returns:
            List of ready task entries sorted by priority (P0 first), then order, then title
        """
        entries = [self._tasks[tid] for tid in self._ready if tid in self._tasks]

        if project is not None:
            entries = [e for e in entries if e.project == project]

        # Filter by assignee: show if unassigned OR assigned to caller
        if caller is not None:
            entries = [e for e in entries if e.assignee is None or e.assignee == caller]

            # When caller is 'bot', also exclude tasks with human tags
            if caller == "bot":
                entries = [e for e in entries if not (set(e.tags) & self.HUMAN_TAGS)]

        # Sort by priority (lower is higher priority), then order, then title
        entries.sort(key=lambda e: (e.priority, e.order, e.title))
        return entries

    def get_blocked_tasks(self) -> list[TaskIndexEntry]:
        """Get tasks blocked by dependencies.

        Returns:
            List of blocked task entries
        """
        return [self._tasks[tid] for tid in self._blocked if tid in self._tasks]

    def get_roots(self) -> list[TaskIndexEntry]:
        """Get all root tasks (no parent).

        Returns:
            List of root task entries
        """
        return [self._tasks[tid] for tid in self._roots if tid in self._tasks]

    def get_by_project(self, project: str) -> list[TaskIndexEntry]:
        """Get all tasks in a project.

        Args:
            project: Project slug

        Returns:
            List of task entries in project
        """
        task_ids = self._by_project.get(project, [])
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

    def get_dependencies(self, task_id: str) -> list[TaskIndexEntry]:
        """Get tasks this task depends on.

        Args:
            task_id: Task ID

        Returns:
            List of dependency entries
        """
        entry = self._tasks.get(task_id)
        if not entry:
            return []

        return [self._tasks[did] for did in entry.depends_on if did in self._tasks]

    def get_dependents(self, task_id: str) -> list[TaskIndexEntry]:
        """Get tasks that depend on this task (blocks).

        Args:
            task_id: Task ID

        Returns:
            List of dependent entries
        """
        entry = self._tasks.get(task_id)
        if not entry:
            return []

        return [self._tasks[bid] for bid in entry.blocks if bid in self._tasks]

    def get_next_actions(self, goal_id: str) -> list[TaskIndexEntry]:
        """Get ready leaf tasks under a goal.

        Args:
            goal_id: Root goal task ID

        Returns:
            List of ready actions under the goal
        """
        descendants = self.get_descendants(goal_id)
        ready_ids = set(self._ready)

        actions = [e for e in descendants if e.id in ready_ids]
        actions.sort(key=lambda e: (e.priority, e.order, e.title))
        return actions

    def stats(self) -> dict[str, Any]:
        """Get index statistics.

        Returns:
            Dictionary with counts and status
        """
        status_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}

        for entry in self._tasks.values():
            status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
            type_counts[entry.type] = type_counts.get(entry.type, 0) + 1

        return {
            "version": self.VERSION,
            "generated": self._generated,
            "total": len(self._tasks),
            "ready": len(self._ready),
            "blocked": len(self._blocked),
            "roots": len(self._roots),
            "projects": len(self._by_project),
            "by_status": status_counts,
            "by_type": type_counts,
        }
