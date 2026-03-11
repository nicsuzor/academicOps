#!/usr/bin/env python3
"""ASCII Tree Generator: Visualize task hierarchies in plain text.

Implements the read-only ASCII view generator per specs/bd-markdown-integration.md.
Used for injecting task trees into project documentation and daily notes.

Usage:
    from lib.task_index import TaskIndex
    from lib.ascii_tree import AsciiTreeGenerator

    index = TaskIndex()
    index.load()
    generator = AsciiTreeGenerator(index)
    print(generator.generate_tree("root-task-id"))
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.task_index import TaskIndex, TaskIndexEntry


class AsciiTreeGenerator:
    """Generates ASCII tree visualizations of task hierarchies."""

    def __init__(self, index: TaskIndex):
        """Initialize generator with task index.

        Args:
            index: TaskIndex instance for looking up tasks and children
        """
        self.index = index

    def generate_tree(self, root_id: str) -> str:
        """Generate ASCII tree for a root task and its descendants.

        Args:
            root_id: ID of the root task

        Returns:
            Multiline string containing the ASCII tree
        """
        root = self.index.get_task(root_id)
        if not root:
            return f"(Task not found: {root_id})"

        lines: list[str] = []

        # Format root node (no tree prefix)
        self._format_root(root, lines)

        # Format children recursively
        children = self.index.get_children(root_id)
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            self._format_child(child, "", is_last, lines)

        return "\n".join(lines)

    def generate_project_tree(self, project: str) -> str:
        """Generate ASCII tree for all root tasks in a project.

        Args:
            project: Project slug

        Returns:
            Multiline string containing the ASCII trees for all project roots
        """
        tasks = self.index.get_by_project(project)
        if not tasks:
            return f"(No tasks found in project: {project})"

        project_ids = {t.id for t in tasks}

        # A task is a root in this project context if:
        # 1. It has no parent
        # 2. OR its parent is not in the project (e.g. parent is a goal outside the project)
        roots = [t for t in tasks if not t.parent or t.parent not in project_ids]

        if not roots:
            # Should be unreachable if tasks exists, unless there's a cycle?
            # Or if all tasks have parents in project but form a cycle.
            # Assume acyclic.
            pass

        # Sort roots by priority, then order, then title
        roots.sort(key=lambda t: (t.priority, t.order, t.title))

        trees: list[str] = []
        for root in roots:
            trees.append(self.generate_tree(root.id))

        return "\n\n".join(trees)

    def _format_root(self, node: TaskIndexEntry, lines: list[str]) -> None:
        """Format the root node line."""
        symbol = self._get_status_symbol(node.status)
        text = self._format_node_text(node)
        lines.append(f"{symbol} {text}")

    def _format_child(
        self, node: TaskIndexEntry, prefix: str, is_last: bool, lines: list[str]
    ) -> None:
        """Format a child node and recurse."""
        connector = "└─" if is_last else "├─"
        symbol = self._get_status_symbol(node.status)
        text = self._format_node_text(node)

        lines.append(f"{prefix}{connector}{symbol} {text}")

        # Recurse
        children = self.index.get_children(node.id)
        child_prefix = prefix + ("  " if is_last else "│ ")

        for i, child in enumerate(children):
            is_last_child = i == len(children) - 1
            self._format_child(child, child_prefix, is_last_child, lines)

    def _format_node_text(self, node: TaskIndexEntry) -> str:
        """Format the text part of a node (ID + annotations + title)."""
        parts = [node.id]

        # Priority
        parts.append(f"[P{node.priority}]")

        # Type (only if epic)
        if node.type == "epic":
            parts.append("[epic]")

        # Assignee
        if node.assignee:
            parts.append(f"@{node.assignee}")

        # Title
        parts.append(node.title)

        return " ".join(parts)

    def _get_status_symbol(self, status: str) -> str:
        """Get status symbol per spec."""
        # ○ Open (active, inbox, waiting)
        # ● Closed (done, cancelled)
        # ◐ In-progress
        # ⊘ Blocked

        if status in ("done", "cancelled"):
            return "●"
        if status == "in_progress":
            return "◐"
        if status == "blocked":
            return "⊘"
        return "○"
