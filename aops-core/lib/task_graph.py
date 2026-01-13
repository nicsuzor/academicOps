#!/usr/bin/env python3
"""Task Graph v2: Graph traversal and query functions for hierarchical tasks.

Provides a unified API for graph queries that returns Task objects.
Wraps TaskIndex for index-based queries with Task materialization.

Implements Phase 2 of specs/tasks-v2.md Section 3.2:
- Decomposition tree traversal (children, descendants, ancestors, root)
- Dependency graph queries (dependencies, dependents)
- Actionability queries (ready, blocked, next_actions)
- Tree display formatting (Section 5.2)

Usage:
    from lib.task_graph import TaskGraph

    graph = TaskGraph()
    graph.load()  # Load index, or rebuild() if stale

    children = graph.get_children("20260112-write-book")
    ready = graph.get_ready()
    tree = graph.format_tree("20260112-write-book")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lib.task_index import TaskIndex, TaskIndexEntry
from lib.task_model import Task, TaskStatus
from lib.task_storage import TaskStorage


@dataclass
class TreeDisplayOptions:
    """Options for tree display formatting."""

    show_type: bool = True
    show_status: bool = True
    show_order: bool = True
    show_blocked: bool = True
    show_progress: bool = True
    show_next_action: bool = True
    indent: str = "    "
    branch: str = "├── "
    last_branch: str = "└── "
    vertical: str = "│   "


class TaskGraph:
    """Graph traversal and query API for hierarchical tasks.

    Provides Task-returning methods that wrap TaskIndex queries.
    Materializes Task objects from index entries on demand.
    """

    def __init__(self, data_root: Path | None = None):
        """Initialize task graph.

        Args:
            data_root: Root data directory. Defaults to $ACA_DATA.
        """
        self._index = TaskIndex(data_root)
        self._storage = TaskStorage(data_root)

    def load(self) -> bool:
        """Load index from disk.

        Returns:
            True if loaded successfully, False if index missing/stale
        """
        return self._index.load()

    def rebuild(self) -> None:
        """Rebuild index from task files."""
        self._index.rebuild()

    def _entry_to_task(self, entry: TaskIndexEntry) -> Task | None:
        """Materialize Task from index entry.

        Args:
            entry: Index entry to materialize

        Returns:
            Task object, or None if file not found
        """
        return self._storage.get_task(entry.id)

    def _entries_to_tasks(self, entries: list[TaskIndexEntry]) -> list[Task]:
        """Materialize list of Tasks from index entries.

        Args:
            entries: Index entries to materialize

        Returns:
            List of Task objects (excludes None results)
        """
        tasks = []
        for entry in entries:
            task = self._entry_to_task(entry)
            if task is not None:
                tasks.append(task)
        return tasks

    # =========================================================================
    # Decomposition Tree Queries (Section 3.2)
    # =========================================================================

    def get_children(self, task_id: str) -> list[Task]:
        """Get direct children of a task.

        Args:
            task_id: Parent task ID

        Returns:
            List of child Tasks sorted by order
        """
        entries = self._index.get_children(task_id)
        return self._entries_to_tasks(entries)

    def get_descendants(self, task_id: str) -> list[Task]:
        """Get all descendants of a task (recursive).

        Args:
            task_id: Ancestor task ID

        Returns:
            List of all descendant Tasks
        """
        entries = self._index.get_descendants(task_id)
        return self._entries_to_tasks(entries)

    def get_ancestors(self, task_id: str) -> list[Task]:
        """Get path from task to root.

        Args:
            task_id: Task to trace ancestry of

        Returns:
            List of ancestors from immediate parent to root
        """
        entries = self._index.get_ancestors(task_id)
        return self._entries_to_tasks(entries)

    def get_root(self, task_id: str) -> Task | None:
        """Get root goal for a task.

        Args:
            task_id: Task to find root for

        Returns:
            Root task (furthest ancestor), or self if already root
        """
        entry = self._index.get_root(task_id)
        if entry is None:
            return None
        return self._entry_to_task(entry)

    # =========================================================================
    # Dependency Graph Queries (Section 3.2)
    # =========================================================================

    def get_dependencies(self, task_id: str) -> list[Task]:
        """Get tasks this task depends on.

        Args:
            task_id: Task ID

        Returns:
            List of dependency Tasks
        """
        entries = self._index.get_dependencies(task_id)
        return self._entries_to_tasks(entries)

    def get_dependents(self, task_id: str) -> list[Task]:
        """Get tasks that depend on this task (blocks).

        Args:
            task_id: Task ID

        Returns:
            List of dependent Tasks
        """
        entries = self._index.get_dependents(task_id)
        return self._entries_to_tasks(entries)

    # =========================================================================
    # Actionability Queries (Section 3.2)
    # =========================================================================

    def get_ready(self, project: str | None = None) -> list[Task]:
        """Get tasks ready to work on.

        Ready = leaf + no unmet dependencies + active/inbox status.

        Args:
            project: Filter by project (optional)

        Returns:
            List of ready Tasks sorted by priority
        """
        entries = self._index.get_ready_tasks(project)
        return self._entries_to_tasks(entries)

    def get_blocked(self) -> list[Task]:
        """Get tasks blocked by unmet dependencies.

        Returns:
            List of blocked Tasks
        """
        entries = self._index.get_blocked_tasks()
        return self._entries_to_tasks(entries)

    def get_next_actions(self, goal_id: str) -> list[Task]:
        """Get ready leaf tasks under a goal.

        Args:
            goal_id: Root goal task ID

        Returns:
            List of actionable Tasks under the goal
        """
        entries = self._index.get_next_actions(goal_id)
        return self._entries_to_tasks(entries)

    # =========================================================================
    # Additional Queries
    # =========================================================================

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        return self._storage.get_task(task_id)

    def get_roots(self) -> list[Task]:
        """Get all root tasks (no parent).

        Returns:
            List of root Tasks
        """
        entries = self._index.get_roots()
        return self._entries_to_tasks(entries)

    def get_by_project(self, project: str) -> list[Task]:
        """Get all tasks in a project.

        Args:
            project: Project slug

        Returns:
            List of Tasks in project
        """
        entries = self._index.get_by_project(project)
        return self._entries_to_tasks(entries)

    # =========================================================================
    # Tree Display (Section 5.2)
    # =========================================================================

    def format_tree(
        self,
        task_id: str,
        options: TreeDisplayOptions | None = None,
    ) -> str:
        """Format task hierarchy as ASCII tree.

        Displays the task and all its children in a tree structure,
        showing status, type, order, and blocked indicators.

        Args:
            task_id: Root task ID for the tree
            options: Display options (uses defaults if None)

        Returns:
            Formatted tree string

        Example output:
            Write Chapter 1 [project] [active]
            ├── [ ] Outline chapter 1 [action] [order=0]
            ├── [ ] Write first draft [action] [order=1] [blocked]
            └── [ ] Revise draft [action] [order=2] [blocked]

            Progress: 0/3 complete
            Next action: Outline chapter 1
        """
        if options is None:
            options = TreeDisplayOptions()

        task = self.get_task(task_id)
        if task is None:
            return f"Task not found: {task_id}"

        lines: list[str] = []

        # Root task header
        root_line = self._format_task_header(task, options)
        lines.append(root_line)

        # Get children sorted by order
        children = self.get_children(task_id)
        if children:
            # Get blocked task IDs for marking
            blocked_ids = {t.id for t in self.get_blocked()}

            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                child_lines = self._format_tree_node(
                    child, "", is_last, blocked_ids, options
                )
                lines.extend(child_lines)

        # Progress and next action
        if options.show_progress and children:
            lines.append("")
            completed = sum(1 for c in children if c.status == TaskStatus.DONE)
            total = len(children)
            lines.append(f"Progress: {completed}/{total} complete")

        if options.show_next_action:
            next_actions = self.get_next_actions(task_id)
            if next_actions:
                lines.append(f"Next action: {next_actions[0].title}")

        return "\n".join(lines)

    def _format_task_header(self, task: Task, options: TreeDisplayOptions) -> str:
        """Format task header line.

        Args:
            task: Task to format
            options: Display options

        Returns:
            Formatted header string
        """
        parts = [task.title]

        if options.show_type:
            parts.append(f"[{task.type.value}]")

        if options.show_status:
            parts.append(f"[{task.status.value}]")

        return " ".join(parts)

    def _format_tree_node(
        self,
        task: Task,
        prefix: str,
        is_last: bool,
        blocked_ids: set[str],
        options: TreeDisplayOptions,
    ) -> list[str]:
        """Format a single tree node and its children.

        Args:
            task: Task to format
            prefix: Current indentation prefix
            is_last: Whether this is the last sibling
            blocked_ids: Set of blocked task IDs
            options: Display options

        Returns:
            List of formatted lines
        """
        lines: list[str] = []

        # Determine branch character
        branch = options.last_branch if is_last else options.branch

        # Build task line
        checkbox = "[x]" if task.status == TaskStatus.DONE else "[ ]"
        parts = [f"{prefix}{branch}{checkbox} {task.title}"]

        if options.show_type:
            parts.append(f"[{task.type.value}]")

        if options.show_order:
            parts.append(f"[order={task.order}]")

        if options.show_blocked and task.id in blocked_ids:
            parts.append("[blocked]")

        lines.append(" ".join(parts))

        # Process children recursively
        children = self.get_children(task.id)
        if children:
            child_prefix = prefix + (options.vertical if not is_last else options.indent)
            for i, child in enumerate(children):
                child_is_last = i == len(children) - 1
                child_lines = self._format_tree_node(
                    child, child_prefix, child_is_last, blocked_ids, options
                )
                lines.extend(child_lines)

        return lines

    def format_tree_compact(self, task_id: str) -> str:
        """Format task hierarchy as compact tree (no metadata).

        Args:
            task_id: Root task ID

        Returns:
            Compact tree string
        """
        options = TreeDisplayOptions(
            show_type=False,
            show_status=False,
            show_order=False,
            show_blocked=False,
            show_progress=False,
            show_next_action=False,
        )
        return self.format_tree(task_id, options)
