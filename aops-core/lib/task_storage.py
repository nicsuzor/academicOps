#!/usr/bin/env python3
"""Task Storage v2: Flat file storage for hierarchical tasks.

Implements file storage per specs/tasks-v2.md Section 2:
- Tasks stored flat within project directories
- Graph defines hierarchy via frontmatter, not folders
- Project grouping provides natural namespace
- Global inbox for tasks without project assignment

Directory Structure:
    $ACA_DATA/
    ├── book/
    │   └── tasks/
    │       ├── 20260112-write-book.md
    │       └── ...
    ├── dissertation/
    │   └── tasks/
    │       └── ...
    └── tasks/
        ├── index.json
        └── inbox/
            └── 20260112-random-idea.md

Usage:
    from lib.task_storage import TaskStorage

    storage = TaskStorage()
    task = storage.create_task("Write a book", project="book", type=TaskType.GOAL)
    storage.save_task(task)

    loaded = storage.get_task("20260112-write-book")
    all_tasks = storage.list_tasks(project="book")
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterator

from filelock import FileLock

from lib.paths import get_data_root
from lib.task_model import Task, TaskComplexity, TaskStatus, TaskType

# Directories to exclude from recursive task scanning
# These contain non-task data that shouldn't be indexed
EXCLUDED_DIRS = frozenset({
    "archive",      # Historical data, not active tasks
    "sessions",     # Session transcripts
    "contacts",     # Contact information
    "assets",       # Media files
    "diagrams",     # Diagram files
    "dotfiles",     # Configuration files
    "metrics",      # Metrics data
    "qa",           # QA test data
})


class TaskStorage:
    """Flat file storage for tasks organized by project.

    Tasks are stored as markdown files with YAML frontmatter.
    Each project has its own tasks/ subdirectory.
    Tasks without a project go to the global inbox.
    """

    def __init__(self, data_root: Path | None = None):
        """Initialize task storage.

        Args:
            data_root: Root data directory. Defaults to $ACA_DATA.
        """
        self.data_root = data_root or get_data_root()

    def _get_project_tasks_dir(self, project: str | None) -> Path:
        """Get tasks directory for a project.

        Args:
            project: Project slug, or None for inbox

        Returns:
            Path to project's tasks directory
        """
        if project:
            return self.data_root / project / "tasks"
        return self.data_root / "tasks" / "inbox"

    def _get_task_path(self, task: Task) -> Path:
        """Get file path for a task.

        Args:
            task: Task to get path for

        Returns:
            Path where task file should be stored
        """
        tasks_dir = self._get_project_tasks_dir(task.project)
        slug = Task.slugify_title(task.title)
        return tasks_dir / f"{task.id}-{slug}.md"

    def _find_task_path(self, task_id: str) -> Path | None:
        """Find existing task file by ID.

        Searches all project directories and inbox for task file.
        Supports both new format (<id>-<slug>.md) and legacy format (<id>.md).

        Args:
            task_id: Task ID to find

        Returns:
            Path if found, None otherwise
        """
        # Search top-level tasks/ directory (legacy location)
        tasks_dir = self.data_root / "tasks"
        if tasks_dir.exists():
            for path in tasks_dir.glob(f"{task_id}*.md"):
                if path.is_file() and (path.stem == task_id or path.stem.startswith(f"{task_id}-")):
                    return path

        # Search inbox
        inbox_dir = self.data_root / "tasks" / "inbox"
        if inbox_dir.exists():
            for path in inbox_dir.glob(f"{task_id}*.md"):
                if path.stem == task_id or path.stem.startswith(f"{task_id}-"):
                    return path

        # Search all project directories
        for project_dir in self.data_root.iterdir():
            if not project_dir.is_dir():
                continue
            if project_dir.name.startswith("."):
                continue
            if project_dir.name == "tasks":
                continue  # Skip global tasks dir

            tasks_dir = project_dir / "tasks"
            if tasks_dir.exists():
                for path in tasks_dir.glob(f"{task_id}*.md"):
                    if path.stem == task_id or path.stem.startswith(f"{task_id}-"):
                        return path

        return None

    def create_task(
        self,
        title: str,
        *,
        project: str | None = None,
        type: TaskType = TaskType.TASK,
        parent: str | None = None,
        depends_on: list[str] | None = None,
        priority: int = 2,
        due: datetime | None = None,
        tags: list[str] | None = None,
        body: str = "",
        assignee: str | None = None,
        complexity: TaskComplexity | None = None,
    ) -> Task:
        """Create a new task with auto-generated ID.

        Args:
            title: Task title
            project: Project slug (None for inbox)
            type: Task type (goal, project, epic, task, action, bug, feature, learn)
            parent: Parent task ID for hierarchy
            depends_on: List of dependency task IDs
            priority: Priority 0-4 (0=critical, 4=someday)
            due: Optional due date
            tags: Optional tags
            body: Markdown body content
            assignee: Task owner - typically 'nic' (human) or 'bot' (agent)
            complexity: Task complexity for routing decisions (set by hydrator)

        Returns:
            New Task instance (not yet saved)
        """
        task_id = Task.generate_id(title, project=project)

        # Compute depth from parent
        depth = 0
        if parent:
            parent_task = self.get_task(parent)
            if parent_task:
                depth = parent_task.depth + 1

        return Task(
            id=task_id,
            title=title,
            type=type,
            status=TaskStatus.INBOX,
            priority=priority,
            project=project,
            parent=parent,
            depends_on=depends_on or [],
            depth=depth,
            leaf=True,
            due=due,
            tags=tags or [],
            body=body,
            assignee=assignee,
            complexity=complexity,
        )

    def save_task(self, task: Task) -> Path:
        """Save task to file with file locking and atomic writes.

        Uses file locking to prevent concurrent modification conflicts.
        Writes to temp file first, then renames for atomicity.

        Creates parent directories if needed.
        Updates parent task's leaf status if this task has a parent.
        Populates inverse relationships (children, blocks) for rendering.

        Args:
            task: Task to save

        Returns:
            Path where task was saved
        """
        # Populate inverse relationships for markdown rendering
        self._populate_inverse_relationships(task)

        path = self._get_task_path(task)
        self._atomic_write(path, task)

        # Update parent's leaf status
        if task.parent:
            parent = self.get_task(task.parent)
            if parent:
                parent.add_child(task.id)
                self._populate_inverse_relationships(parent)
                parent_path = self._find_task_path(task.parent)
                if parent_path:
                    self._atomic_write(parent_path, parent)

        return path

    def _populate_inverse_relationships(self, task: Task) -> None:
        """Populate inverse relationships (children, blocks) for a task.

        Scans all tasks to compute:
        - children: tasks that have this task as parent
        - blocks: tasks that depend on this task

        Args:
            task: Task to populate relationships for
        """
        children = []
        blocks = []

        for other_task in self._iter_all_tasks():
            # Skip self
            if other_task.id == task.id:
                continue

            # Children: tasks that have this task as parent
            if other_task.parent == task.id:
                children.append(other_task.id)

            # Blocks: tasks that depend on this task
            if task.id in other_task.depends_on:
                blocks.append(other_task.id)

        task.children = children
        task.blocks = blocks

    def _atomic_write(self, path: Path, task: Task) -> None:
        """Write task to file atomically with file locking.

        Uses a .lock file to coordinate concurrent access.
        Writes to temp file first, then renames for atomicity.

        Args:
            path: Target file path
            task: Task to write
        """
        import os

        lock_path = path.with_suffix(path.suffix + ".lock")
        lock = FileLock(lock_path, timeout=10)

        with lock:
            # Update modified timestamp
            task.modified = task.modified.__class__.now(task.modified.tzinfo)

            # Create parent directory if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file in same directory (for atomic rename)
            fd, temp_path = tempfile.mkstemp(
                suffix=".tmp",
                prefix=path.stem + "_",
                dir=path.parent,
            )
            try:
                os.close(fd)  # Close the file descriptor from mkstemp
                temp = Path(temp_path)
                temp.write_text(task.to_markdown(), encoding="utf-8")
                # Atomic rename (on POSIX systems)
                temp.rename(path)
            except Exception:
                # Clean up temp file on error
                Path(temp_path).unlink(missing_ok=True)
                raise

    def get_task(self, task_id: str) -> Task | None:
        """Load task by ID.

        Args:
            task_id: Task ID to load

        Returns:
            Task if found, None otherwise
        """
        path = self._find_task_path(task_id)
        if path is None:
            return None
        return Task.from_file(path)

    def delete_task(self, task_id: str) -> bool:
        """Delete task file.

        Args:
            task_id: Task ID to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._find_task_path(task_id)
        if path is None:
            return False
        path.unlink()
        return True

    def list_tasks(
        self,
        project: str | None = None,
        status: TaskStatus | None = None,
        type: TaskType | None = None,
    ) -> list[Task]:
        """List tasks with optional filters.

        Args:
            project: Filter by project (None = all projects)
            status: Filter by status
            type: Filter by type

        Returns:
            List of matching tasks
        """
        tasks = []
        for task in self._iter_all_tasks():
            if project is not None and task.project != project:
                continue
            if status is not None and task.status != status:
                continue
            if type is not None and task.type != type:
                continue
            tasks.append(task)

        # Sort by order, then priority, then title
        tasks.sort(key=lambda t: (t.order, t.priority, t.title))
        return tasks

    def _iter_all_tasks(self) -> Iterator[Task]:
        """Iterate over all task files in $ACA_DATA.

        Recursively scans all markdown files with valid task frontmatter
        (type: goal|project|epic|task|action|bug|feature|learn). Skips excluded directories
        and files that fail to parse as valid tasks.

        Yields:
            Task instances from anywhere in $ACA_DATA
        """
        for task, _path in self._iter_all_tasks_with_paths():
            yield task

    def _iter_all_tasks_with_paths(self) -> Iterator[tuple[Task, Path]]:
        """Iterate over all task files with their paths.

        Yields:
            Tuples of (Task, Path) for each valid task file
        """
        valid_types = {t.value for t in TaskType}

        for md_file in self._iter_markdown_files():
            try:
                task = Task.from_file(md_file)
                # Verify it has a valid task type
                if task.type.value in valid_types:
                    yield task, md_file
            except (ValueError, OSError, KeyError):
                # Skip files that aren't valid tasks
                continue

    def _iter_markdown_files(self) -> Iterator[Path]:
        """Iterate over all markdown files in $ACA_DATA.

        Recursively walks the data directory, skipping excluded
        directories and hidden files/folders.

        Yields:
            Path to each .md file
        """
        for root, dirs, files in self.data_root.walk():
            # Filter out excluded and hidden directories (in-place modification)
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in EXCLUDED_DIRS
            ]

            for filename in files:
                if filename.endswith(".md") and not filename.startswith("."):
                    yield root / filename

    def get_children(self, task_id: str) -> list[Task]:
        """Get direct children of a task.

        Args:
            task_id: Parent task ID

        Returns:
            List of child tasks sorted by order
        """
        children = []
        for task in self._iter_all_tasks():
            if task.parent == task_id:
                children.append(task)

        children.sort(key=lambda t: (t.order, t.title))
        return children

    def get_descendants(self, task_id: str) -> list[Task]:
        """Get all descendants of a task (recursive).

        Args:
            task_id: Ancestor task ID

        Returns:
            List of all descendant tasks
        """
        descendants = []
        to_visit = [task_id]

        while to_visit:
            current_id = to_visit.pop(0)
            children = self.get_children(current_id)
            for child in children:
                descendants.append(child)
                to_visit.append(child.id)

        return descendants

    def get_ancestors(self, task_id: str) -> list[Task]:
        """Get path from task to root.

        Args:
            task_id: Task to trace ancestry of

        Returns:
            List of ancestors from immediate parent to root
        """
        ancestors = []
        task = self.get_task(task_id)

        while task and task.parent:
            parent = self.get_task(task.parent)
            if parent:
                ancestors.append(parent)
                task = parent
            else:
                break

        return ancestors

    def get_root(self, task_id: str) -> Task | None:
        """Get root goal for a task.

        Args:
            task_id: Task to find root for

        Returns:
            Root task (furthest ancestor), or self if already root
        """
        task = self.get_task(task_id)
        if task is None:
            return None

        ancestors = self.get_ancestors(task_id)
        if ancestors:
            return ancestors[-1]
        return task

    def get_ready_tasks(self, project: str | None = None) -> list[Task]:
        """Get tasks ready to work on.

        Ready = leaf + no unmet dependencies + active/inbox status.

        Args:
            project: Filter by project

        Returns:
            List of ready tasks sorted by priority
        """
        # Get all completed task IDs for dependency checking
        completed_ids = {
            t.id
            for t in self._iter_all_tasks()
            if t.status in (TaskStatus.DONE, TaskStatus.CANCELLED)
        }

        ready = []
        for task in self._iter_all_tasks():
            if project is not None and task.project != project:
                continue

            # Must be a leaf
            if not task.leaf:
                continue

            # Must be active or inbox
            if task.status not in (TaskStatus.ACTIVE, TaskStatus.INBOX):
                continue

            # All dependencies must be completed
            unmet_deps = [d for d in task.depends_on if d not in completed_ids]
            if unmet_deps:
                continue

            ready.append(task)

        ready.sort(key=lambda t: (t.priority, t.order, t.title))
        return ready

    def get_blocked_tasks(self) -> list[Task]:
        """Get tasks blocked by dependencies.

        Returns:
            List of blocked tasks
        """
        completed_ids = {
            t.id
            for t in self._iter_all_tasks()
            if t.status in (TaskStatus.DONE, TaskStatus.CANCELLED)
        }

        blocked = []
        for task in self._iter_all_tasks():
            if task.status == TaskStatus.BLOCKED:
                blocked.append(task)
                continue

            # Check for unmet dependencies
            if task.depends_on:
                unmet = [d for d in task.depends_on if d not in completed_ids]
                if unmet:
                    blocked.append(task)

        return blocked

    def decompose_task(
        self,
        task_id: str,
        children: list[dict],
    ) -> list[Task]:
        """Decompose a task into children.

        Creates child tasks and updates parent's leaf status.

        Args:
            task_id: Parent task to decompose
            children: List of child definitions with keys:
                - title (required)
                - type (optional, defaults to action)
                - order (optional, auto-assigned if not provided)
                - depends_on (optional)

        Returns:
            List of created child tasks

        Raises:
            ValueError: If parent task not found
        """
        parent = self.get_task(task_id)
        if parent is None:
            raise ValueError(f"Parent task not found: {task_id}")

        created_tasks = []
        for i, child_def in enumerate(children):
            title = child_def["title"]
            task_type = child_def.get("type", TaskType.ACTION)
            if isinstance(task_type, str):
                task_type = TaskType(task_type)

            order = child_def.get("order", i)
            depends_on = child_def.get("depends_on", [])

            child = self.create_task(
                title=title,
                project=parent.project,
                type=task_type,
                parent=task_id,
                depends_on=depends_on,
                priority=parent.priority,
            )
            child.order = order

            self.save_task(child)
            created_tasks.append(child)

        return created_tasks
