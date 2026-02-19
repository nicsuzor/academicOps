#!/usr/bin/env python3
"""FastMCP server for Tasks v2 hierarchical task management.

Implements MCP tools per specs/tasks-v2.md Section 7.2:
- CRUD operations (create, get, update, complete)
- Graph queries (ready, blocked, tree, children, dependencies)
- Decomposition (decompose_task)
- Bulk operations (complete_tasks, reorder_children)

Usage:
    # Development
    fastmcp dev mcp_servers/tasks_server.py

    # Production (stdio)
    uv run python -m mcp_servers.tasks_server
"""

from __future__ import annotations

import logging
import re
import sys
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent  # up from mcp_servers/
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.paths import get_data_root
from lib.task_index import TaskIndex, TaskIndexEntry
from lib.task_model import Task, TaskComplexity, TaskStatus, TaskType
from lib.task_storage import TaskStorage

# Pre-compile regex patterns for performance
_INCOMPLETE_MARKER_PATTERN = re.compile(r"^-\s*\[ \]\s*(.+)$", re.MULTILINE)
_REMAINING_PATTERN = re.compile(r"^#+\s*Remaining:", re.IGNORECASE | re.MULTILINE)
_PERCENT_COMPLETE_PATTERN = re.compile(r"(\d+)%\s*complete", re.IGNORECASE)
_WIP_PATTERN = re.compile(r"\b(WIP|in-progress)\b", re.IGNORECASE)


def _resolve_status_alias(status: str) -> str:
    """Resolve status aliases to canonical status values."""
    return Task.STATUS_ALIASES.get(status, status)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("tasks-v2")


def _get_storage() -> TaskStorage:
    """Get TaskStorage instance with data root from environment."""
    return TaskStorage(get_data_root())


def _get_index() -> TaskIndex:
    """Get TaskIndex instance, loading from cache or rebuilding.

    Prefers fast-indexer Rust binary when available, falls back to Python.
    """
    index = TaskIndex(get_data_root())
    if not index.load():
        # Try fast rebuild first, fall back to Python
        if not index.rebuild_fast():
            index.rebuild()
    return index


def _truncate_body(body: str, max_length: int = 200) -> str:
    """Truncate body text to a brief extract.

    Extracts meaningful content, skipping markdown headers and relationship sections.
    Truncates at word boundaries and adds ellipsis if truncated.

    Args:
        body: Full body text
        max_length: Maximum length of extract (default: 200 chars)

    Returns:
        Truncated body text with ellipsis if truncated
    """
    if not body or len(body) <= max_length:
        return body

    # Skip common markdown headers and relationship sections
    lines = body.split("\n")
    content_lines = []
    skip_section = False
    found_content = False  # Track if we've found non-header content

    for line in lines:
        stripped = line.strip()
        # Skip relationship sections
        if stripped.startswith("## Relationships"):
            skip_section = True
            continue
        # Reset skip on new section
        if stripped.startswith("## ") and skip_section:
            skip_section = False
            continue
        if skip_section:
            continue
        # Skip empty lines at start
        if not stripped and not found_content:
            continue
        # Skip markdown H1 headers before any real content
        if stripped.startswith("# ") and not found_content:
            continue
        found_content = True
        content_lines.append(line)

    # Join and truncate
    content = "\n".join(content_lines).strip()
    if not content:
        content = body.strip()

    if len(content) <= max_length:
        return content

    # Truncate at word boundary
    truncated = content[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated.rstrip() + "..."


def _task_to_dict(task: Task, truncate_body: int | None = None) -> dict[str, Any]:
    """Convert Task to dictionary for MCP response.

    Args:
        task: Task instance
        truncate_body: If provided, truncate body to this many characters.
            Use for list/search results to reduce response size.

    Returns:
        Dictionary representation suitable for JSON serialization
    """
    body = task.body
    if truncate_body is not None:
        body = _truncate_body(body, truncate_body)

    return {
        "id": task.id,
        "title": task.title,
        "type": task.type.value,
        "status": task.status.value,
        "priority": task.priority,
        "order": task.order,
        "created": task.created.isoformat(),
        "modified": task.modified.isoformat(),
        "parent": task.parent,
        "depends_on": task.depends_on,
        "soft_depends_on": task.soft_depends_on,
        "depth": task.depth,
        "leaf": task.leaf,
        "due": task.due.isoformat() if task.due else None,
        "project": task.project,
        "tags": task.tags,
        "effort": task.effort,
        "context": task.context,
        "assignee": task.assignee,
        "complexity": task.complexity.value if task.complexity else None,
        "body": body,
        "children": task.children,
        "blocks": task.blocks,
        "soft_blocks": task.soft_blocks,
    }


def _index_entry_to_dict(entry: TaskIndexEntry) -> dict[str, Any]:
    """Convert TaskIndexEntry to dictionary for MCP response.

    Args:
        entry: TaskIndexEntry instance

    Returns:
        Dictionary representation suitable for JSON serialization
    """
    return entry.to_dict()


def _format_task_line(task: dict[str, Any], include_status: bool = True) -> str:
    """Format a single task as a readable line with ID.

    Args:
        task: Task dictionary (from _task_to_dict or _index_entry_to_dict)
        include_status: Whether to include status in output

    Returns:
        Formatted string like "[id] title (status)"
    """
    status_str = f" ({task['status']})" if include_status else ""
    return f"[{task['id']}] {task['title']}{status_str}"


def _format_task_list(tasks: list[dict[str, Any]], include_status: bool = True) -> str:
    """Format a list of tasks as readable lines with IDs.

    Args:
        tasks: List of task dictionaries
        include_status: Whether to include status in output

    Returns:
        Newline-separated formatted task lines
    """
    if not tasks:
        return "(no tasks)"
    return "\n".join(_format_task_line(t, include_status) for t in tasks)


def _format_tree(node: dict[str, Any], indent: int = 0) -> str:
    """Format a tree node recursively with IDs.

    Args:
        node: Tree node with 'task' and 'children' keys
        indent: Current indentation level

    Returns:
        Formatted tree string
    """
    task = node["task"]
    prefix = "  " * indent
    line = f"{prefix}[{task['id']}] {task['title']} ({task['status']})"
    lines = [line]

    for child in node.get("children", []):
        lines.append(_format_tree(child, indent + 1))

    return "\n".join(lines)


def _check_incomplete_markers(body: str) -> list[str]:
    """Check for incomplete checklist markers in the task body.

    Looks for:
    - Lines starting with '- [ ]'
    - 'Remaining:' section headers
    - Percentage complete < 100%
    - WIP or in-progress markers

    Args:
        body: Task body markdown

    Returns:
        List of incomplete items or markers found
    """
    if not body:
        return []

    incomplete = []

    # 1. Check for [ ] items
    for m in _INCOMPLETE_MARKER_PATTERN.finditer(body):
        incomplete.append(m.group(1).strip())

    # 2. Check for Remaining: section
    if _REMAINING_PATTERN.search(body):
        incomplete.append("Remaining: section")

    # 3. Check for X% complete (X < 100)
    for m in _PERCENT_COMPLETE_PATTERN.finditer(body):
        try:
            percent = int(m.group(1))
            if percent < 100:
                incomplete.append(f"{percent}% complete")
        except ValueError:
            continue

    # 4. Check for WIP/in-progress
    for m in _WIP_PATTERN.finditer(body):
        incomplete.append(m.group(0))

    return incomplete


def _format_incomplete_items_error(incomplete: list[str]) -> str:
    """Format error message for incomplete checklist items.

    Args:
        incomplete: List of incomplete item descriptions

    Returns:
        Formatted error message
    """
    return (
        f"Cannot complete task with {len(incomplete)} incomplete items: "
        f"{', '.join(incomplete[:3])}{'...' if len(incomplete) > 3 else ''}. "
        "Mark items as [x] or use force=True to bypass."
    )


def _propagate_unblocks(
    storage: TaskStorage, index: TaskIndex, completed_ids: list[str]
) -> list[str]:
    """Recursively propagate unblocks to dependent tasks.

    When tasks are completed, check if any blocked tasks now have all their
    dependencies met. If so, transition them to ACTIVE.

    Args:
        storage: TaskStorage instance
        index: TaskIndex instance
        completed_ids: List of task IDs that were just completed
            (status=DONE or CANCELLED)

    Returns:
        List of task IDs that were unblocked
    """
    unblocked_ids = []
    to_check = deque(completed_ids)
    processed = set()

    # Track what we know is completed to avoid redundant storage reads
    # Note: we only trust DONE and CANCELLED statuses
    completed_cache = set(completed_ids)

    while to_check:
        current_id = to_check.popleft()
        if current_id in processed:
            continue
        processed.add(current_id)

        # Find tasks that depend on current_id
        # Note: index might be slightly stale but relationships (blocks) are stable
        dependents = index.get_dependents(current_id)

        for dep_entry in dependents:
            # Skip if already unblocked in this pass
            if dep_entry.id in unblocked_ids:
                continue

            # Load full task to check all its dependencies and current status
            dep_task = storage.get_task(dep_entry.id)
            if not dep_task:
                continue

            # Only transition tasks that are currently BLOCKED
            # If it's already ACTIVE or IN_PROGRESS, no need to transition.
            # If it's already DONE, we might need to recurse (it might have been
            # waiting for this dependency to unblock its own dependents).
            if dep_task.status == TaskStatus.BLOCKED:
                # Check if all dependencies are now met
                all_deps_met = True
                for did in dep_task.depends_on:
                    if did in completed_cache:
                        continue

                    d_task = storage.get_task(did)
                    if not d_task or d_task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED):
                        all_deps_met = False
                        break
                    else:
                        completed_cache.add(did)

                if all_deps_met:
                    # Transition to ACTIVE
                    logger.info(f"Unblocking task {dep_task.id} (dependencies met)")
                    dep_task.transition_to(TaskStatus.ACTIVE, trigger="unblock_condition_met")
                    storage.save_task(dep_task)
                    unblocked_ids.append(dep_task.id)
                    # We don't need to add to to_check here because it's not DONE,
                    # so it doesn't unblock its own dependents yet.

            elif dep_task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
                # Task is already done, but it might now unblock its dependents
                # if current_id was its last unmet dependency.
                completed_cache.add(dep_task.id)
                to_check.append(dep_task.id)

    return unblocked_ids


# =============================================================================
# CRUD OPERATIONS
# =============================================================================


@mcp.tool()
def create_task(
    task_title: str,
    type: str = "task",
    status: str | None = None,
    project: str | None = None,
    parent: str | None = None,
    depends_on: list[str] | None = None,
    soft_depends_on: list[str] | None = None,
    order: int = 0,
    priority: int = 2,
    due: str | None = None,
    tags: list[str] | None = None,
    body: str = "",
    assignee: str | None = None,
    complexity: str | None = None,
) -> dict[str, Any]:
    """Create a new task in the hierarchical task system.

    Creates a task with graph relationships for decomposition workflows.
    Tasks are stored as markdown files with YAML frontmatter.

    Args:
        task_title: Task title (required)
        type: Task type - "goal", "project", "epic", "task", "action", "bug", "feature", or "learn" (default: "task")
        status: Task status - "active", "in_progress", "blocked", "waiting", "review", "merge_ready", "done", or "cancelled" (default: "active")
        project: Project slug for organization (determines storage location)
        parent: Parent task ID for hierarchical relationships
        depends_on: List of task IDs this task depends on (blocking)
        soft_depends_on: List of task IDs for non-blocking context relationships
        order: Sibling ordering (lower = first, default: 0)
        priority: Priority 0-4 (0=critical, 4=someday, default: 2)
        due: Due date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        tags: List of tags for categorization
        body: Markdown body content
        assignee: Task owner - typically 'human' or 'polecat'
        complexity: Task complexity for routing - "mechanical", "requires-judgment",
            "multi-step", "needs-decomposition", or "blocked-human" (default: None)

    Returns:
        Dictionary with:
        - success: True if created
        - task: Full task data
        - message: Status message

    Example:
        create_task(
            task_title="Write Chapter 1",
            type="project",
            project="book",
            parent="20260112-write-book",
            assignee="human",
            complexity="multi-step"
        )
    """
    try:
        storage = _get_storage()

        from lib.task_model import get_human_assignee

        default_assignee = get_human_assignee() if type in ("goal", "project", "epic") else None
        effective_assignee = assignee if assignee is not None else default_assignee

        # Validate title
        title_stripped = task_title.strip() if task_title else ""
        if not title_stripped:
            return {
                "success": False,
                "message": "Task title is required and cannot be empty or whitespace-only",
            }

        # Check slugified title has minimum length
        slug = Task.slugify_title(title_stripped)
        if len(slug) < 3:
            return {
                "success": False,
                "message": f"Task title must produce a slug of at least 3 characters. "
                f"Title '{title_stripped}' produces slug '{slug}' which is too short.",
            }

        # Parse task type
        try:
            task_type = TaskType(type)
        except ValueError:
            return {
                "success": False,
                "message": f"Invalid task type: {type}. Must be one of: goal, project, epic, task, action, bug, feature, learn",
            }

        # Parse status (with alias support)
        task_status = TaskStatus.ACTIVE
        if status:
            try:
                resolved_status = _resolve_status_alias(status)
                task_status = TaskStatus(resolved_status)
            except ValueError:
                return {
                    "success": False,
                    "message": f"Invalid status: {status}. Must be one of: active, in_progress, blocked, waiting, review, merge_ready, done, cancelled",
                }

        # Parse due date
        due_datetime = None
        if due:
            try:
                due_datetime = datetime.fromisoformat(due.replace("Z", "+00:00"))
            except ValueError as e:
                return {
                    "success": False,
                    "message": f"Invalid due date format: {e}. Use ISO format: YYYY-MM-DDTHH:MM:SSZ",
                }

        # Parse complexity
        task_complexity = None
        if complexity:
            try:
                task_complexity = TaskComplexity(complexity)
            except ValueError:
                return {
                    "success": False,
                    "message": f"Invalid complexity: {complexity}. Must be one of: mechanical, requires-judgment, multi-step, needs-decomposition, blocked-human",
                }

        # Create task
        task = storage.create_task(
            title=task_title,
            project=project,
            type=task_type,
            status=task_status,
            parent=parent,
            depends_on=depends_on,
            soft_depends_on=soft_depends_on,
            priority=priority,
            due=due_datetime,
            tags=tags,
            body=body,
            assignee=effective_assignee,
            complexity=task_complexity,
        )
        task.order = order

        # Save task
        path = storage.save_task(task)

        # Rebuild index to include new task
        index = TaskIndex(get_data_root())
        index.rebuild()

        logger.info(f"create_task: {task.id} -> {path}")

        return {
            "success": True,
            "task": _task_to_dict(task),
            "message": f"Created task: {task.id}",
        }

    except Exception as e:
        logger.exception("create_task failed")
        return {
            "success": False,
            "message": f"Failed to create task: {e}",
        }


@mcp.tool()
def get_task(id: str) -> dict[str, Any]:
    """Get a task by ID.

    Loads the full task data from the markdown file.

    Args:
        id: Task ID (e.g., "20260112-write-book")

    Returns:
        Dictionary with:
        - success: True if found
        - task: Full task data (or None if not found)
        - message: Status message
    """
    try:
        storage = _get_storage()
        task = storage.get_task(id)

        if task is None:
            return {
                "success": False,
                "task": None,
                "message": f"Task not found: {id}",
            }

        # Load index for computed fields (children, blocks, soft_blocks)
        index = _get_index()
        entry = index.get_task(id)
        if entry:
            task.children = entry.children
            task.blocks = entry.blocks
            task.soft_blocks = entry.soft_blocks

        return {
            "success": True,
            "task": _task_to_dict(task),
            "message": f"Found task: {task.title}",
        }

    except Exception as e:
        logger.exception("get_task failed")
        return {
            "success": False,
            "task": None,
            "message": f"Failed to get task: {e}",
        }


@mcp.tool()
def update_task(
    id: str,
    task_title: str | None = None,
    type: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    order: int | None = None,
    parent: str | None = None,
    depends_on: list[str] | None = None,
    soft_depends_on: list[str] | None = None,
    due: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
    effort: str | None = None,
    context: str | None = None,
    body: str | None = None,
    replace_body: bool = False,
    assignee: str | None = None,
    complexity: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Update an existing task.

    Only provided fields are updated. Pass None to leave field unchanged.

    Args:
        id: Task ID to update (required)
        task_title: New title
        type: New type - "goal", "project", "epic", "task", "action", "bug", "feature", or "learn"
        status: New status - "active", "in_progress", "blocked", "waiting", "review", "merge_ready", "done", "cancelled"
        priority: New priority 0-4
        order: New sibling order
        parent: New parent task ID (or "" to clear)
        depends_on: New blocking dependency list (replaces existing)
        soft_depends_on: New non-blocking context dependency list (replaces existing)
        due: New due date in ISO format (or "" to clear)
        project: New project slug (or "" to clear)
        tags: New tags list (replaces existing)
        effort: New effort estimate (or "" to clear)
        context: New context (or "" to clear)
        body: Body content to append (default) or replace. Appended with double newline separator.
        replace_body: If True, replace body instead of appending (default: False)
        assignee: Task owner - 'human' or 'polecat' (or "" to clear)
        complexity: Task complexity - "mechanical", "requires-judgment", "multi-step",
            "needs-decomposition", or "blocked-human" (or "" to clear)
        force: If True, bypass validation checks when setting status=done (default: False)

    Returns:
        Dictionary with:
        - success: True if updated
        - task: Updated task data
        - modified_fields: List of fields that were changed
        - message: Status message
    """
    try:
        storage = _get_storage()
        task = storage.get_task(id)

        if task is None:
            return {
                "success": False,
                "task": None,
                "modified_fields": [],
                "message": f"Task not found: {id}",
            }

        modified_fields = []

        # Update fields if provided
        if task_title is not None:
            task.title = task_title
            modified_fields.append("title")

        if type is not None:
            try:
                task.type = TaskType(type)
                modified_fields.append("type")
            except ValueError:
                return {
                    "success": False,
                    "task": None,
                    "modified_fields": [],
                    "message": f"Invalid task type: {type}",
                }

        if status is not None:
            try:
                resolved_status = _resolve_status_alias(status)
                new_status = TaskStatus(resolved_status)

                # Double-claim prevention: reject if task is already claimed by someone else
                # A task is "claimed" when status=IN_PROGRESS and has an assignee
                if new_status == TaskStatus.IN_PROGRESS:
                    is_already_claimed = (
                        task.status == TaskStatus.IN_PROGRESS and task.assignee is not None
                    )
                    # Determine who is trying to claim
                    new_assignee = assignee if assignee is not None else task.assignee

                    if is_already_claimed and new_assignee != task.assignee:
                        return {
                            "success": False,
                            "task": _task_to_dict(task),
                            "modified_fields": [],
                            "message": (
                                f"Task already claimed by '{task.assignee}' "
                                f"(status: in_progress since {task.modified.isoformat()}). "
                                f"Cannot claim for '{new_assignee}'."
                            ),
                        }

                # Validation: Check for incomplete checklist markers when marking DONE
                if new_status == TaskStatus.DONE and not force:
                    # Note: we check current task body. If body is also being updated in this
                    # same call, we should ideally check the combined body.
                    combined_body = task.body
                    if body is not None:
                        if replace_body or not task.body:
                            combined_body = body
                        else:
                            combined_body = task.body + "\n\n" + body

                    incomplete = _check_incomplete_markers(combined_body)
                    if incomplete:
                        return {
                            "success": False,
                            "task": _task_to_dict(task),
                            "modified_fields": [],
                            "message": _format_incomplete_items_error(incomplete),
                        }

                task.status = new_status
                modified_fields.append("status")
            except ValueError:
                return {
                    "success": False,
                    "task": None,
                    "modified_fields": [],
                    "message": f"Invalid status: {status}",
                }

        if priority is not None:
            if not 0 <= priority <= 4:
                return {
                    "success": False,
                    "task": None,
                    "modified_fields": [],
                    "message": f"Invalid priority: {priority}. Must be 0-4.",
                }
            task.priority = priority
            modified_fields.append("priority")

        if order is not None:
            task.order = order
            modified_fields.append("order")

        if parent is not None:
            task.parent = parent if parent else None
            modified_fields.append("parent")

        if depends_on is not None:
            task.depends_on = depends_on
            modified_fields.append("depends_on")

        if soft_depends_on is not None:
            task.soft_depends_on = soft_depends_on
            modified_fields.append("soft_depends_on")

        if due is not None:
            if due == "":
                task.due = None
            else:
                try:
                    task.due = datetime.fromisoformat(due.replace("Z", "+00:00"))
                except ValueError as e:
                    return {
                        "success": False,
                        "task": None,
                        "modified_fields": [],
                        "message": f"Invalid due date format: {e}",
                    }
            modified_fields.append("due")

        if project is not None:
            task.project = project if project else None
            modified_fields.append("project")

        if tags is not None:
            task.tags = tags
            modified_fields.append("tags")

        if effort is not None:
            task.effort = effort if effort else None
            modified_fields.append("effort")

        if context is not None:
            task.context = context if context else None
            modified_fields.append("context")

        if body is not None:
            if replace_body or not task.body:
                task.body = body
            else:
                task.body = task.body + "\n\n" + body
            modified_fields.append("body")

        if assignee is not None:
            task.assignee = assignee if assignee else None
            modified_fields.append("assignee")

        if complexity is not None:
            if complexity == "":
                task.complexity = None
            else:
                try:
                    task.complexity = TaskComplexity(complexity)
                except ValueError:
                    return {
                        "success": False,
                        "task": None,
                        "modified_fields": [],
                        "message": f"Invalid complexity: {complexity}. Must be one of: mechanical, requires-judgment, multi-step, needs-decomposition, blocked-human",
                    }
            modified_fields.append("complexity")

        # Save if anything changed
        if modified_fields:
            storage.save_task(task)

            # If status changed to DONE or CANCELLED, propagate unblocks
            index = _get_index()
            if "status" in modified_fields and task.status in (
                TaskStatus.DONE,
                TaskStatus.CANCELLED,
            ):
                _propagate_unblocks(storage, index, [id])

            # Rebuild index
            index.rebuild()

        logger.info(f"update_task: {id} - modified {modified_fields}")

        return {
            "success": True,
            "task": _task_to_dict(task),
            "modified_fields": modified_fields,
            "message": f"Updated task: {task.title}" if modified_fields else "No changes made",
        }

    except Exception as e:
        logger.exception("update_task failed")
        return {
            "success": False,
            "task": None,
            "modified_fields": [],
            "message": f"Failed to update task: {e}",
        }


@mcp.tool()
def complete_task(id: str, force: bool = False) -> dict[str, Any]:
    """Mark a task as done.

    Updates status to "done" and sets modified timestamp.
    Validates that there are no incomplete checklist markers in the body
    unless force=True is provided.

    Args:
        id: Task ID to complete
        force: If True, bypass validation checks (default: False)

    Returns:
        Dictionary with:
        - success: True if completed
        - task: Updated task data
        - message: Status message
    """
    try:
        storage = _get_storage()
        task = storage.get_task(id)

        if task is None:
            return {
                "success": False,
                "task": None,
                "message": f"Task not found: {id}",
            }

        # Validation: Check for incomplete checklist markers
        if not force:
            incomplete = _check_incomplete_markers(task.body)
            if incomplete:
                return {
                    "success": False,
                    "task": _task_to_dict(task),
                    "message": _format_incomplete_items_error(incomplete),
                }

        task.complete()
        storage.save_task(task)

        # Propagate unblocks to dependent tasks
        index = _get_index()
        unblocked = _propagate_unblocks(storage, index, [id])

        # Rebuild index
        index.rebuild()

        logger.info(
            f"complete_task: {id}" + (f" (unblocked {len(unblocked)} tasks)" if unblocked else "")
        )

        return {
            "success": True,
            "task": _task_to_dict(task),
            "message": f"Completed task: {task.title}",
        }

    except Exception as e:
        logger.exception("complete_task failed")
        return {
            "success": False,
            "task": None,
            "message": f"Failed to complete task: {e}",
        }


# =============================================================================
# QUERY OPERATIONS
# =============================================================================


@mcp.tool()
def get_blocked_tasks(project: str, limit: int = 5) -> dict[str, Any]:
    """Get tasks blocked by dependencies.

    Returns tasks that have unmet dependencies or status "blocked".

    Args:
        project: Filter by project slug, or empty string "" for all projects
        limit: Maximum number of tasks to return (default: 5, use 0 for unlimited)

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of blocked task entries
        - count: Number of blocked tasks returned
        - total: Total number of blocked tasks available
        - message: Status message
    """
    try:
        index = _get_index()
        blocked = index.get_blocked_tasks()

        # Filter by project if specified
        if project:
            blocked = [e for e in blocked if e.project == project]

        total = len(blocked)
        # Apply limit (0 or negative means unlimited)
        if limit > 0:
            blocked = blocked[:limit]

        task_dicts = [_index_entry_to_dict(e) for e in blocked]
        return {
            "success": True,
            "tasks": task_dicts,
            "count": len(blocked),
            "total": total,
            "formatted": _format_task_list(task_dicts),
            "message": f"Found {len(blocked)} blocked tasks"
            + (f" (of {total} total)" if total > len(blocked) else "")
            + (f" in project {project}" if project else ""),
        }

    except Exception as e:
        logger.exception("get_blocked_tasks failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to get blocked tasks: {e}",
        }


@mcp.tool()
def get_review_tasks(project: str = "", limit: int = 5) -> dict[str, Any]:
    """Get tasks awaiting human review.

    Returns tasks with status "review" that are waiting for human verification
    before being marked complete.

    Args:
        project: Filter by project slug, or empty string "" for all projects
        limit: Maximum number of tasks to return (default: 5, use 0 for unlimited)

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of review task entries
        - count: Number of review tasks returned
        - total: Total number of review tasks available
        - message: Status message
    """
    try:
        index = _get_index()

        # Get all tasks in review status
        review_tasks = [
            entry for entry in index._tasks.values() if entry.status == TaskStatus.REVIEW.value
        ]

        # Filter by project if specified
        if project:
            review_tasks = [e for e in review_tasks if e.project == project]

        # Sort by priority, then order, then title
        review_tasks.sort(key=lambda e: (e.priority, e.order, e.title))

        total = len(review_tasks)
        # Apply limit (0 or negative means unlimited)
        if limit > 0:
            review_tasks = review_tasks[:limit]

        task_dicts = [_index_entry_to_dict(e) for e in review_tasks]
        return {
            "success": True,
            "tasks": task_dicts,
            "count": len(review_tasks),
            "total": total,
            "formatted": _format_task_list(task_dicts),
            "message": f"Found {len(review_tasks)} tasks in review"
            + (f" (of {total} total)" if total > len(review_tasks) else "")
            + (f" in project {project}" if project else ""),
        }

    except Exception as e:
        logger.exception("get_review_tasks failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to get review tasks: {e}",
        }


@mcp.tool()
def get_task_tree(
    id: str | None = None,
    exclude_status: list[str] | None = None,
    max_depth: int | None = None,
    project: str | None = None,
    root_types: list[str] | None = None,
) -> dict[str, Any]:
    """Get the decomposition tree for a task, or all root tasks.

    Returns the task and all its descendants in a tree structure.
    If no ID is provided, returns trees for all root tasks.

    Args:
        id: Root task ID to get tree for. If not provided, returns all root trees.
        exclude_status: List of statuses to exclude (e.g., ["done", "cancelled"])
        max_depth: Maximum tree depth (0 = roots only, 1 = roots + children, etc.)
        project: Filter roots by project slug (only applies when id is None)
        root_types: Filter root tasks by type (e.g., ["project"]). Defaults to
            ["project"] to show project-level grouping. Pass [] or None with
            explicit empty list to see all root types including goals.

    Returns:
        Dictionary with:
        - success: True if task found (or roots exist)
        - tree: Tree node (if id provided) or list of tree nodes (if no id)
            Each node has structure:
            - task: Task data
            - children: List of child tree nodes (recursive)
        - message: Status message
    """
    try:
        index = _get_index()
        exclude_set = set(exclude_status) if exclude_status else set()

        def should_include(entry: TaskIndexEntry) -> bool:
            """Check if task should be included based on filters."""
            if entry.status in exclude_set:
                return False
            return True

        def build_tree(entry: TaskIndexEntry, depth: int = 0) -> dict[str, Any] | None:
            """Recursively build tree structure with filtering."""
            if not should_include(entry):
                return None

            # Get children if within depth limit
            children_nodes = []
            if max_depth is None or depth < max_depth:
                children = index.get_children(entry.id)
                for child in children:
                    child_tree = build_tree(child, depth + 1)
                    if child_tree is not None:
                        children_nodes.append(child_tree)

            return {
                "task": _index_entry_to_dict(entry),
                "children": children_nodes,
            }

        # If no ID provided, return all root trees
        if id is None:
            roots = index.get_roots()
            if not roots:
                return {
                    "success": True,
                    "tree": [],
                    "message": "No root tasks found",
                }

            # Filter roots by type - default to project-level grouping
            # Use ["project"] as default; pass [] explicitly to see all roots
            effective_root_types = root_types if root_types is not None else ["project"]
            if effective_root_types:
                roots = [r for r in roots if r.type in effective_root_types]

            # Filter roots by project if specified
            if project:
                roots = [r for r in roots if r.project == project]

            trees = []
            for root in roots:
                tree = build_tree(root, 0)
                if tree is not None:
                    trees.append(tree)

            formatted_trees = "\n\n".join(_format_tree(t) for t in trees)
            filters_desc = []
            if effective_root_types:
                filters_desc.append(f"root_types={effective_root_types}")
            if exclude_status:
                filters_desc.append(f"excluding {exclude_status}")
            if max_depth is not None:
                filters_desc.append(f"depth≤{max_depth}")
            if project:
                filters_desc.append(f"project={project}")
            filter_msg = f" ({', '.join(filters_desc)})" if filters_desc else ""

            return {
                "success": True,
                "tree": trees,
                "formatted": formatted_trees,
                "message": f"Found {len(trees)} root task trees{filter_msg}",
            }

        # Single task tree
        root = index.get_task(id)

        if root is None:
            return {
                "success": False,
                "tree": None,
                "message": f"Task not found: {id}",
            }

        tree = build_tree(root, 0)

        if tree is None:
            return {
                "success": False,
                "tree": None,
                "message": f"Task excluded by filters: {id}",
            }

        return {
            "success": True,
            "tree": tree,
            "formatted": _format_tree(tree),
            "message": f"Tree for: {root.title}",
        }

    except Exception as e:
        logger.exception("get_task_tree failed")
        return {
            "success": False,
            "tree": None,
            "message": f"Failed to get task tree: {e}",
        }


@mcp.tool()
def get_children(id: str) -> dict[str, Any]:
    """Get direct children of a task.

    Returns immediate child tasks sorted by order.

    Args:
        id: Parent task ID

    Returns:
        Dictionary with:
        - success: True if parent found
        - tasks: List of child task entries
        - count: Number of children
        - message: Status message
    """
    try:
        index = _get_index()

        # Verify parent exists
        parent = index.get_task(id)
        if parent is None:
            return {
                "success": False,
                "tasks": [],
                "count": 0,
                "message": f"Parent task not found: {id}",
            }

        children = index.get_children(id)

        task_dicts = [_index_entry_to_dict(e) for e in children]
        return {
            "success": True,
            "tasks": task_dicts,
            "count": len(children),
            "formatted": _format_task_list(task_dicts),
            "message": f"Found {len(children)} children for: {parent.title}",
        }

    except Exception as e:
        logger.exception("get_children failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to get children: {e}",
        }


@mcp.tool()
def get_dependencies(id: str) -> dict[str, Any]:
    """Get tasks that this task depends on.

    Returns the list of tasks in depends_on field.

    Args:
        id: Task ID to get dependencies for

    Returns:
        Dictionary with:
        - success: True if task found
        - tasks: List of dependency task entries
        - count: Number of dependencies
        - message: Status message
    """
    try:
        index = _get_index()

        # Get task
        task = index.get_task(id)
        if task is None:
            return {
                "success": False,
                "tasks": [],
                "count": 0,
                "message": f"Task not found: {id}",
            }

        deps = index.get_dependencies(id)

        task_dicts = [_index_entry_to_dict(e) for e in deps]
        return {
            "success": True,
            "tasks": task_dicts,
            "count": len(deps),
            "formatted": _format_task_list(task_dicts),
            "message": f"Found {len(deps)} dependencies for: {task.title}",
        }

    except Exception as e:
        logger.exception("get_dependencies failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to get dependencies: {e}",
        }


@mcp.tool()
def get_tasks_with_topology(
    project: str | None = None,
    status: str | None = None,
    min_depth: int | None = None,
    min_blocking_count: int | None = None,
) -> dict[str, Any]:
    """
    Return tasks with their topology metrics. Agent identifies issues.

    Returns list of tasks, each with:
        - id, title, type, status, project, tags
        - depth: int                    # levels from root
        - parent: str | None
        - child_count: int
        - blocking_count: int           # tasks depending on this
        - blocked_by_count: int         # dependencies this has
        - is_leaf: bool
        - created: datetime
        - modified: datetime
        - ready_days: float | None      # days since became ready (if status=active)
    """
    try:
        index = _get_index()
        storage = _get_storage()
        now = datetime.now().astimezone()

        # Get all tasks from the index
        all_tasks = index._tasks.values()

        # Apply filters
        filtered_entries = []
        for entry in all_tasks:
            if project is not None and entry.project != project:
                continue
            if status is not None and entry.status != status:
                continue
            if min_depth is not None and entry.depth < min_depth:
                continue
            if min_blocking_count is not None and len(entry.blocks) < min_blocking_count:
                continue
            filtered_entries.append(entry)

        # Build response dictionaries
        task_dicts = []
        for entry in filtered_entries:
            # The index doesn't store timestamps, so we need to load the full task
            full_task = storage.get_task(entry.id)
            if not full_task:
                continue  # Skip if task file was deleted but index not rebuilt

            ready_days = None
            if entry.status == "active":
                # Use timezone-aware datetime for comparison
                ready_days = (now - full_task.modified).total_seconds() / (24 * 3600)

            task_dict = {
                "id": entry.id,
                "title": entry.title,
                "type": entry.type,
                "status": entry.status,
                "project": entry.project,
                "tags": entry.tags,
                "depth": entry.depth,
                "parent": entry.parent,
                "child_count": len(entry.children),
                "blocking_count": len(entry.blocks),
                "blocked_by_count": len(entry.depends_on),
                "is_leaf": entry.leaf,
                "created": full_task.created.isoformat(),
                "modified": full_task.modified.isoformat(),
                "ready_days": ready_days,
            }
            task_dicts.append(task_dict)

        return {
            "success": True,
            "tasks": task_dicts,
            "count": len(task_dicts),
            "message": f"Found {len(task_dicts)} tasks matching criteria.",
        }

    except Exception as e:
        logger.exception("get_tasks_with_topology failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to get tasks with topology: {e}",
        }


# =============================================================================
# DECOMPOSITION OPERATIONS
# =============================================================================


@mcp.tool()
def decompose_task(id: str, children: list[dict]) -> dict[str, Any]:
    """Decompose a task into children.

    Creates child tasks and updates parent's leaf status to false.

    Args:
        id: Parent task ID to decompose
        children: List of child definitions, each with:
            - title: Child task title (required)
            - type: Task type (default: "action")
            - order: Sibling order (default: auto-assigned)
            - depends_on: List of dependency IDs (optional)

    Returns:
        Dictionary with:
        - success: True if decomposition succeeded
        - tasks: List of created child tasks
        - count: Number of children created
        - message: Status message

    Example:
        decompose_task(
            id="20260112-write-ch1",
            children=[
                {"title": "Outline chapter 1", "type": "action", "order": 0},
                {"title": "Write first draft", "type": "action", "order": 1,
                 "depends_on": ["20260112-ch1-outline"]},
                {"title": "Revise draft", "type": "action", "order": 2,
                 "depends_on": ["20260112-ch1-draft"]}
            ]
        )
    """
    try:
        storage = _get_storage()

        # Validate children list
        if not children:
            return {
                "success": False,
                "tasks": [],
                "count": 0,
                "message": "Children list cannot be empty",
            }

        for i, child in enumerate(children):
            if "title" not in child:
                return {
                    "success": False,
                    "tasks": [],
                    "count": 0,
                    "message": f"Child {i} missing required 'title' field",
                }

            # Validate child title
            child_title = child["title"].strip() if child["title"] else ""
            if not child_title:
                return {
                    "success": False,
                    "tasks": [],
                    "count": 0,
                    "message": f"Child {i} title is empty or whitespace-only",
                }

            child_slug = Task.slugify_title(child_title)
            if len(child_slug) < 3:
                return {
                    "success": False,
                    "tasks": [],
                    "count": 0,
                    "message": f"Child {i} title '{child_title}' produces slug '{child_slug}' "
                    f"which is too short (minimum 3 characters)",
                }

        # Decompose
        created = storage.decompose_task(id, children)

        # Rebuild index
        index = TaskIndex(get_data_root())
        index.rebuild()

        logger.info(f"decompose_task: {id} -> {len(created)} children")

        return {
            "success": True,
            "tasks": [_task_to_dict(t) for t in created],
            "count": len(created),
            "message": f"Created {len(created)} child tasks",
        }

    except ValueError as e:
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": str(e),
        }
    except Exception as e:
        logger.exception("decompose_task failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to decompose task: {e}",
        }


# =============================================================================
# BULK OPERATIONS
# =============================================================================


@mcp.tool()
def complete_tasks(ids: list[str]) -> dict[str, Any]:
    """Mark multiple tasks as done.

    Batch operation to complete multiple tasks at once.

    Args:
        ids: List of task IDs to complete

    Returns:
        Dictionary with:
        - success: True if all tasks completed
        - tasks: List of completed task data
        - success_count: Number of tasks completed
        - failure_count: Number of tasks that failed
        - failures: List of failure details
        - message: Status message
    """
    try:
        storage = _get_storage()
        completed = []
        failures = []

        for task_id in ids:
            task = storage.get_task(task_id)
            if task is None:
                failures.append(
                    {
                        "id": task_id,
                        "reason": "Task not found",
                    }
                )
                continue

            try:
                task.complete()
                storage.save_task(task)
                completed.append(_task_to_dict(task, truncate_body=100))
            except Exception as e:
                failures.append(
                    {
                        "id": task_id,
                        "reason": str(e),
                    }
                )

        # Propagate unblocks and rebuild index once at the end
        if completed:
            completed_ids = [t["id"] for t in completed]
            index = _get_index()
            unblocked = _propagate_unblocks(storage, index, completed_ids)
            index.rebuild()

            logger.info(
                f"complete_tasks: {len(completed)} completed, "
                f"{len(unblocked)} unblocked, {len(failures)} failed"
            )
        else:
            logger.info(f"complete_tasks: 0 completed, {len(failures)} failed")

        return {
            "success": len(failures) == 0,
            "tasks": completed,
            "success_count": len(completed),
            "failure_count": len(failures),
            "failures": failures,
            "message": f"Completed {len(completed)} tasks"
            + (f", {len(failures)} failed" if failures else ""),
        }

    except Exception as e:
        logger.exception("complete_tasks failed")
        return {
            "success": False,
            "tasks": [],
            "success_count": 0,
            "failure_count": len(ids),
            "failures": [{"id": tid, "reason": str(e)} for tid in ids],
            "message": f"Failed to complete tasks: {e}",
        }


@mcp.tool()
def reset_stalled_tasks(
    hours: float = 4.0,
    project: str | None = None,
    assignee: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Reset stalled in_progress tasks back to active.

    Finds tasks that have been in_progress for longer than the specified duration
    without modification and resets them to active status.

    Args:
        hours: Hours since last modification to consider stalled (default: 4.0)
        project: Filter by project (optional)
        assignee: Filter by assignee (optional)
        dry_run: If True, only list tasks that would be reset (default: False)

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of reset task IDs
        - count: Number of tasks reset
        - message: Status message
    """
    try:
        storage = _get_storage()
        # Use timezone-aware comparison
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        # List all in_progress tasks matching filters
        candidates = storage.list_tasks(
            status=TaskStatus.IN_PROGRESS,
            project=project,
            assignee=assignee,
        )

        stalled = []
        for task in candidates:
            # Ensure task.modified is timezone-aware or comparable
            task_mod = task.modified
            if task_mod.tzinfo is None:
                task_mod = task_mod.replace(tzinfo=UTC)

            if task_mod < cutoff:
                stalled.append(task)

        if dry_run:
            return {
                "success": True,
                "tasks": [t.id for t in stalled],
                "count": len(stalled),
                "message": f"Found {len(stalled)} stalled tasks (dry run)",
            }

        reset_ids = []
        for task in stalled:
            task.status = TaskStatus.ACTIVE
            task.assignee = None  # Clear assignee
            storage.save_task(task)
            reset_ids.append(task.id)

        # Rebuild index if any tasks changed
        if reset_ids:
            _get_index().rebuild_fast()

        logger.info(f"reset_stalled_tasks: reset {len(reset_ids)} tasks")

        return {
            "success": True,
            "tasks": reset_ids,
            "count": len(reset_ids),
            "message": f"Reset {len(reset_ids)} stalled tasks",
        }

    except Exception as e:
        logger.exception("reset_stalled_tasks failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to reset stalled tasks: {e}",
        }


@mcp.tool()
def reorder_children(parent_id: str, order: list[str]) -> dict[str, Any]:
    """Reorder children of a parent task.

    Updates the order field of child tasks to match the provided sequence.

    Args:
        parent_id: Parent task ID
        order: List of child task IDs in desired order

    Returns:
        Dictionary with:
        - success: True if reordering succeeded
        - message: Status message
    """
    try:
        storage = _get_storage()
        index = _get_index()

        # Verify parent exists
        parent = index.get_task(parent_id)
        if parent is None:
            return {
                "success": False,
                "message": f"Parent task not found: {parent_id}",
            }

        # Get current children
        current_children = set(parent.children)
        order_set = set(order)

        # Validate all IDs in order are actual children
        invalid_ids = order_set - current_children
        if invalid_ids:
            return {
                "success": False,
                "message": f"Invalid child IDs: {invalid_ids}",
            }

        # Update order for each child
        for new_order, child_id in enumerate(order):
            task = storage.get_task(child_id)
            if task:
                task.order = new_order
                storage.save_task(task)

        # Rebuild index
        index_new = TaskIndex(get_data_root())
        index_new.rebuild()

        logger.info(f"reorder_children: {parent_id} -> {len(order)} children reordered")

        return {
            "success": True,
            "message": f"Reordered {len(order)} children",
        }

    except Exception as e:
        logger.exception("reorder_children failed")
        return {
            "success": False,
            "message": f"Failed to reorder children: {e}",
        }


# =============================================================================
# LIST AND SEARCH OPERATIONS
# =============================================================================


@mcp.tool()
def list_tasks(
    project: str | None = None,
    status: str | None = None,
    type: str | None = None,
    priority: int | None = None,
    priority_max: int | None = None,
    assignee: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """List tasks with optional filters.

    Args:
        project: Filter by project slug
        status: Filter by status - "active", "in_progress", "blocked", "waiting", "review", "merge_ready", "done", "cancelled"
        type: Filter by type - "goal", "project", "epic", "task", "action", "bug", "feature", or "learn"
        priority: Filter by exact priority (0-4)
        priority_max: Filter by priority <= N (e.g. 1 for P0 and P1)
        assignee: Filter by assignee - typically "polecat" (agent) or "human"
        limit: Maximum number of tasks to return (default: 5, use 0 for unlimited)

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of task entries
        - count: Number of tasks returned
        - total: Total number of tasks matching filters
        - message: Status message
    """
    try:
        storage = _get_storage()

        # Parse optional filters (with alias support)
        task_status = None
        if status:
            try:
                resolved_status = _resolve_status_alias(status)
                task_status = TaskStatus(resolved_status)
            except ValueError:
                return {
                    "success": False,
                    "tasks": [],
                    "count": 0,
                    "message": f"Invalid status: {status}",
                }

        task_type = None
        if type:
            try:
                task_type = TaskType(type)
            except ValueError:
                return {
                    "success": False,
                    "tasks": [],
                    "count": 0,
                    "message": f"Invalid type: {type}",
                }

        tasks = storage.list_tasks(
            project=project,
            status=task_status,
            type=task_type,
            priority=priority,
            priority_max=priority_max,
            assignee=assignee,
        )
        total = len(tasks)
        # Apply limit (0 or negative means unlimited)
        if limit > 0:
            tasks = tasks[:limit]

        # Truncate body to 100 chars for list results to reduce response size
        task_dicts = [_task_to_dict(t, truncate_body=100) for t in tasks]
        return {
            "success": True,
            "tasks": task_dicts,
            "count": len(tasks),
            "total": total,
            "formatted": _format_task_list(task_dicts),
            "message": f"Found {len(tasks)} tasks"
            + (f" (of {total} total)" if total > len(tasks) else ""),
        }

    except Exception as e:
        logger.exception("list_tasks failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to list tasks: {e}",
        }


@mcp.tool()
def delete_task(id: str) -> dict[str, Any]:
    """Delete a task by ID.

    Permanently removes the task file. This cannot be undone.

    Args:
        id: Task ID to delete

    Returns:
        Dictionary with:
        - success: True if deleted
        - message: Status message
    """
    try:
        storage = _get_storage()

        # Verify task exists first
        task = storage.get_task(id)
        if task is None:
            return {
                "success": False,
                "message": f"Task not found: {id}",
            }

        # Delete it
        deleted = storage.delete_task(id)

        if deleted:
            # Rebuild index
            index = TaskIndex(get_data_root())
            index.rebuild()

            logger.info(f"delete_task: {id}")

            return {
                "success": True,
                "message": f"Deleted task: {id}",
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete task: {id}",
            }

    except Exception as e:
        logger.exception("delete_task failed")
        return {
            "success": False,
            "message": f"Failed to delete task: {e}",
        }


@mcp.tool()
def search_tasks(query: str, limit: int = 10) -> dict[str, Any]:
    """Search tasks by text query.

    Searches task titles and body content for matching text.
    Case-insensitive substring matching.

    Args:
        query: Search text to match
        limit: Maximum number of results (default: 10, use 0 for unlimited)

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of matching task entries
        - count: Number of matches returned
        - message: Status message
    """
    try:
        storage = _get_storage()
        query_lower = query.lower()

        matches = []
        for task in storage._iter_all_tasks():
            # Search in title and body
            if query_lower in task.title.lower() or query_lower in task.body.lower():
                matches.append(task)

            # Apply limit during iteration (0 or negative means unlimited)
            if limit > 0 and len(matches) >= limit:
                break

        # Sort by priority then title
        matches.sort(key=lambda t: (t.priority, t.title))

        # Truncate body to 200 chars for search results to reduce response size
        task_dicts = [_task_to_dict(t, truncate_body=200) for t in matches]
        return {
            "success": True,
            "tasks": task_dicts,
            "count": len(matches),
            "formatted": _format_task_list(task_dicts),
            "message": f"Found {len(matches)} tasks matching '{query}'",
        }

    except Exception as e:
        logger.exception("search_tasks failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to search tasks: {e}",
        }


@mcp.tool()
def dedup_tasks(delete: bool = False) -> dict[str, Any]:
    """Find and optionally remove duplicate tasks.

    Identifies tasks with identical titles OR identical IDs (different files
    with same frontmatter id). When delete=True, keeps the task that is 'done'
    (if any), otherwise keeps the newest.

    Args:
        delete: If True, delete duplicates (keeps done or newest). Default: False (dry run)

    Returns:
        Dictionary with:
        - success: True
        - duplicates: List of duplicate groups, each with:
            - title: The duplicate title (or ID for ID duplicates)
            - keep: Task ID to keep
            - remove: List of task IDs that are/would be deleted
        - total_duplicates: Total number of duplicate tasks found
        - deleted_ids: List of deleted task IDs (only if delete=True)
        - message: Status message
    """
    try:
        storage = _get_storage()

        from collections import defaultdict

        # Group tasks by title AND by ID (using file path as unique key)
        by_title: dict[str, list[tuple[Task, Path]]] = defaultdict(list)
        by_id: dict[str, list[tuple[Task, Path]]] = defaultdict(list)

        for task, path in storage._iter_all_tasks_with_paths():
            by_title[task.title].append((task, path))
            by_id[task.id].append((task, path))

        # Find title duplicates (same title, different files)
        title_duplicates = {title: tasks for title, tasks in by_title.items() if len(tasks) > 1}

        # Find ID duplicates (same ID in frontmatter, different files)
        # These are MORE serious - they indicate data corruption
        id_duplicates = {task_id: tasks for task_id, tasks in by_id.items() if len(tasks) > 1}

        # Merge: ID duplicates take precedence (use ID as key)
        duplicates: dict[str, list[tuple[Task, Path]]] = {}

        # Add ID duplicates first (keyed by "ID: {id}")
        for task_id, tasks in id_duplicates.items():
            duplicates[f"ID: {task_id}"] = tasks

        # Add title duplicates that aren't already covered by ID duplicates
        covered_paths = set()
        for tasks in id_duplicates.values():
            for _, path in tasks:
                covered_paths.add(path)

        for title, tasks in title_duplicates.items():
            # Filter out tasks already in ID duplicates
            remaining = [(t, p) for t, p in tasks if p not in covered_paths]
            if len(remaining) > 1:
                duplicates[title] = remaining

        if not duplicates:
            return {
                "success": True,
                "duplicates": [],
                "total_duplicates": 0,
                "deleted_ids": [],
                "message": "No duplicate tasks found",
            }

        result_groups = []
        to_delete: list[tuple[Task, Path]] = []

        for key, task_path_pairs in sorted(duplicates.items()):
            # Sort: done status first, then by modified date (newest first)
            task_path_pairs.sort(
                key=lambda tp: (
                    0 if tp[0].status.value == "done" else 1,
                    -tp[0].modified.timestamp(),
                )
            )

            keep_task, keep_path = task_path_pairs[0]
            remove_pairs = task_path_pairs[1:]
            to_delete.extend(remove_pairs)

            result_groups.append(
                {
                    "title": key,
                    "keep": keep_task.id,
                    "keep_path": str(keep_path),
                    "keep_status": keep_task.status.value,
                    "remove": [
                        {"id": t.id, "path": str(p), "title": t.title} for t, p in remove_pairs
                    ],
                }
            )

        deleted_ids = []
        deleted_paths = []
        if delete and to_delete:
            for task, path in to_delete:
                # Delete by path (file), not by ID (since IDs may be duplicated)
                try:
                    path.unlink()
                    deleted_ids.append(task.id)
                    deleted_paths.append(str(path))
                except OSError as e:
                    logger.warning(f"Failed to delete {path}: {e}")

            # Rebuild index after deletions
            index = TaskIndex(get_data_root())
            index.rebuild()

            logger.info(f"dedup_tasks: deleted {len(deleted_ids)} duplicates")

        total_dups = sum(len(g["remove"]) for g in result_groups)
        id_dup_count = sum(1 for k in duplicates.keys() if k.startswith("ID: "))
        title_dup_count = len(duplicates) - id_dup_count

        msg_parts = []
        if id_dup_count:
            msg_parts.append(f"{id_dup_count} ID duplicate(s)")
        if title_dup_count:
            msg_parts.append(f"{title_dup_count} title duplicate(s)")

        return {
            "success": True,
            "duplicates": result_groups,
            "total_duplicates": total_dups,
            "deleted_ids": deleted_ids,
            "deleted_paths": deleted_paths if delete else [],
            "message": f"Found {' and '.join(msg_parts)} ({total_dups} files to remove)"
            + (f", deleted {len(deleted_ids)}" if delete else ", use delete=True to remove"),
        }

    except Exception as e:
        logger.exception("dedup_tasks failed")
        return {
            "success": False,
            "duplicates": [],
            "total_duplicates": 0,
            "deleted_ids": [],
            "message": f"Failed to deduplicate tasks: {e}",
        }


# =============================================================================
# GRAPH NEIGHBORHOOD OPERATIONS
# =============================================================================


@mcp.tool()
def get_task_neighborhood(task_id: str) -> dict[str, Any]:
    """Return the task and its graph neighborhood. Agent decides relationships.

    This tool provides raw graph data for the agent to reason about relationships.
    Per P#78 (Dumb Server, Smart Agent): server returns data, agent interprets meaning.

    The agent can use the returned data to:
    - Identify similar tasks by reading titles (LLM judgment)
    - Suggest relationship types (depends_on, soft_depends_on, parent)
    - Find potential parents from orphan_tasks list

    Args:
        task_id: Task ID to get neighborhood for

    Returns:
        Dictionary with:
        - success: True if task found
        - task: Full task data (title, body, tags, project, etc.)
        - existing_relationships:
            - parent: task | None
            - children: list[task]
            - depends_on: list[task]
            - blocks: list[task] (tasks that depend on this)
            - soft_depends_on: list[task]
            - soft_blocks: list[task]
        - same_project_tasks: list[task] (ALL tasks in same project, for agent to find similar)
        - orphan_tasks: list[task] (tasks with no parent AND no dependencies - potential parents/peers)
        - message: Status message
    """
    try:
        storage = _get_storage()
        index = _get_index()

        # Get the task
        task = storage.get_task(task_id)
        if task is None:
            return {
                "success": False,
                "task": None,
                "existing_relationships": None,
                "same_project_tasks": [],
                "orphan_tasks": [],
                "message": f"Task not found: {task_id}",
            }

        # Get index entry for computed fields
        entry = index.get_task(task_id)
        if entry:
            task.children = entry.children
            task.blocks = entry.blocks
            task.soft_blocks = entry.soft_blocks

        # Build existing relationships
        existing_relationships: dict[str, Any] = {
            "parent": None,
            "children": [],
            "depends_on": [],
            "blocks": [],
            "soft_depends_on": [],
            "soft_blocks": [],
        }

        # Parent
        if task.parent:
            parent_task = storage.get_task(task.parent)
            if parent_task:
                existing_relationships["parent"] = _task_to_dict(parent_task, truncate_body=200)

        # Children
        children_entries = index.get_children(task_id)
        for child_entry in children_entries:
            child_task = storage.get_task(child_entry.id)
            if child_task:
                existing_relationships["children"].append(
                    _task_to_dict(child_task, truncate_body=200)
                )

        # Depends on (blocking dependencies)
        for dep_id in task.depends_on:
            dep_task = storage.get_task(dep_id)
            if dep_task:
                existing_relationships["depends_on"].append(
                    _task_to_dict(dep_task, truncate_body=200)
                )

        # Blocks (tasks that depend on this task)
        if entry:
            for blocker_id in entry.blocks:
                blocker_task = storage.get_task(blocker_id)
                if blocker_task:
                    existing_relationships["blocks"].append(
                        _task_to_dict(blocker_task, truncate_body=200)
                    )

        # Soft depends on (non-blocking context)
        for soft_dep_id in task.soft_depends_on:
            soft_dep_task = storage.get_task(soft_dep_id)
            if soft_dep_task:
                existing_relationships["soft_depends_on"].append(
                    _task_to_dict(soft_dep_task, truncate_body=200)
                )

        # Soft blocks (tasks that soft-depend on this task)
        if entry:
            for soft_blocker_id in entry.soft_blocks:
                soft_blocker_task = storage.get_task(soft_blocker_id)
                if soft_blocker_task:
                    existing_relationships["soft_blocks"].append(
                        _task_to_dict(soft_blocker_task, truncate_body=200)
                    )

        # Same project tasks (excluding the task itself)
        same_project_tasks = []
        if task.project:
            project_entries = index.get_by_project(task.project)
            for proj_entry in project_entries:
                if proj_entry.id != task_id:
                    proj_task = storage.get_task(proj_entry.id)
                    if proj_task:
                        same_project_tasks.append(_task_to_dict(proj_task, truncate_body=100))

        # Orphan tasks: tasks with no parent AND no dependencies
        # These are potential candidates for relationship creation
        orphan_tasks = []
        for tid, idx_entry in index._tasks.items():
            if tid == task_id:
                continue
            # No parent and no dependencies = orphan
            if idx_entry.parent is None and not idx_entry.depends_on:
                orphan_task = storage.get_task(tid)
                if orphan_task:
                    orphan_tasks.append(_task_to_dict(orphan_task, truncate_body=100))

        logger.info(
            f"get_task_neighborhood: {task_id} - "
            f"{len(same_project_tasks)} project tasks, {len(orphan_tasks)} orphans"
        )

        return {
            "success": True,
            "task": _task_to_dict(task),
            "existing_relationships": existing_relationships,
            "same_project_tasks": same_project_tasks,
            "orphan_tasks": orphan_tasks,
            "message": f"Neighborhood for: {task.title}",
        }

    except Exception as e:
        logger.exception("get_task_neighborhood failed")
        return {
            "success": False,
            "task": None,
            "existing_relationships": None,
            "same_project_tasks": [],
            "orphan_tasks": [],
            "message": f"Failed to get task neighborhood: {e}",
        }


# =============================================================================
# INDEX OPERATIONS
# =============================================================================


@mcp.tool()
def rebuild_index(force: bool) -> dict[str, Any]:
    """Rebuild the task index from files.

    Scans all task files and rebuilds the JSON index with computed
    relationships (children, blocks, ready, blocked).

    Prefers fast-indexer Rust binary when available for better performance.

    Args:
        force: Force rebuild even if index is fresh (pass false for normal rebuild)

    Returns:
        Dictionary with:
        - success: True if rebuild succeeded
        - stats: Index statistics
        - message: Status message
    """
    try:
        index = TaskIndex(get_data_root())
        # Try fast rebuild first, fall back to Python
        if not index.rebuild_fast():
            index.rebuild()
        stats = index.stats()

        logger.info(f"rebuild_index: {stats['total']} tasks indexed")

        return {
            "success": True,
            "stats": stats,
            "message": f"Indexed {stats['total']} tasks",
        }

    except Exception as e:
        logger.exception("rebuild_index failed")
        return {
            "success": False,
            "stats": {},
            "message": f"Failed to rebuild index: {e}",
        }


@mcp.tool()
def get_index_stats(include_projects: bool) -> dict[str, Any]:
    """Get task index statistics.

    Returns counts and status information about the task index.

    Args:
        include_projects: Include per-project breakdown (pass true for full stats)

    Returns:
        Dictionary with:
        - success: True
        - stats: Index statistics including:
            - total: Total task count
            - ready: Ready task count
            - blocked: Blocked task count
            - roots: Root task count
            - projects: Project count
            - by_status: Counts by status
            - by_type: Counts by type
        - message: Status message
    """
    try:
        index = _get_index()
        stats = index.stats()

        return {
            "success": True,
            "stats": stats,
            "message": f"Index has {stats['total']} tasks",
        }

    except Exception as e:
        logger.exception("get_index_stats failed")
        return {
            "success": False,
            "stats": {},
            "message": f"Failed to get index stats: {e}",
        }


@mcp.tool()
def get_graph_metrics(
    scope: str = "all",  # "all", "project", or task_id for subtree
    scope_id: str | None = None,
) -> dict[str, Any]:
    """
    Return raw graph metrics. Agent interprets health.
    Returns:
        - total_tasks: int
        - tasks_by_status: dict[str, int]  # {active: 10, done: 50, ...}
        - tasks_by_type: dict[str, int]    # {task: 30, action: 20, ...}
        - orphan_count: int                 # tasks with no parent or dependencies
        - root_count: int
        - leaf_count: int
        - max_depth: int
        - avg_depth: float
        - dependency_stats:
            - total_edges: int
            - max_in_degree: int           # most dependencies on single task
            - max_out_degree: int          # single task blocking most others
            - tasks_with_high_out_degree: list[{id, title, out_degree}]  # raw data
        - readiness_stats:
            - ready_count: int
            - blocked_count: int
            - in_progress_count: int
    """
    try:
        index = _get_index()

        tasks = list(index._tasks.values())

        if scope == "project" and scope_id:
            tasks = [t for t in tasks if t.project == scope_id]
        elif scope == "task_id" and scope_id:
            root_task = index.get_task(scope_id)
            if root_task:
                tasks = [root_task] + index.get_descendants(scope_id)
            else:
                tasks = []

        if not tasks:
            return {
                "success": True,
                "stats": {
                    "total_tasks": 0,
                    "tasks_by_status": {},
                    "tasks_by_type": {},
                    "orphan_count": 0,
                    "root_count": 0,
                    "leaf_count": 0,
                    "max_depth": 0,
                    "avg_depth": 0.0,
                    "dependency_stats": {
                        "total_edges": 0,
                        "max_in_degree": 0,
                        "max_out_degree": 0,
                        "tasks_with_high_out_degree": [],
                    },
                    "readiness_stats": {
                        "ready_count": 0,
                        "blocked_count": 0,
                        "in_progress_count": 0,
                    },
                },
                "message": "No tasks found in scope.",
            }

        total_tasks = len(tasks)
        tasks_by_status = {}
        tasks_by_type = {}
        orphan_count = 0
        leaf_count = 0
        total_depth = 0
        max_depth = 0
        total_edges = 0
        max_in_degree = 0
        max_out_degree = 0
        in_progress_count = 0

        tasks_with_high_out_degree = []

        for task in tasks:
            tasks_by_status[task.status] = tasks_by_status.get(task.status, 0) + 1
            tasks_by_type[task.type] = tasks_by_type.get(task.type, 0) + 1
            if not task.parent and not task.depends_on:
                orphan_count += 1
            if task.leaf:
                leaf_count += 1
            total_depth += task.depth
            if task.depth > max_depth:
                max_depth = task.depth

            in_degree = len(task.depends_on)
            total_edges += in_degree
            if in_degree > max_in_degree:
                max_in_degree = in_degree

            out_degree = len(task.blocks)
            if out_degree > max_out_degree:
                max_out_degree = out_degree
            if out_degree > 0:
                tasks_with_high_out_degree.append(
                    {"id": task.id, "title": task.title, "out_degree": out_degree}
                )

            if task.status == "in_progress":
                in_progress_count += 1

        # Scope-specific root count
        task_ids_in_scope = {t.id for t in tasks}
        root_count = sum(1 for t in tasks if not t.parent or t.parent not in task_ids_in_scope)

        # Readiness stats need to be recalculated for the current scope
        completed_statuses = {TaskStatus.DONE.value, TaskStatus.CANCELLED.value}
        completed_ids_in_scope = {t.id for t in tasks if t.status in completed_statuses}

        ready_count = 0
        blocked_count = 0
        for task in tasks:
            if task.status in completed_statuses:
                continue

            # Check for unmet dependencies *within the scope*
            unmet_deps = [
                d
                for d in task.depends_on
                if d in task_ids_in_scope and d not in completed_ids_in_scope
            ]

            if unmet_deps or task.status == TaskStatus.BLOCKED.value:
                blocked_count += 1
            elif task.leaf and task.status == TaskStatus.ACTIVE.value:
                ready_count += 1

        stats = {
            "total_tasks": total_tasks,
            "tasks_by_status": tasks_by_status,
            "tasks_by_type": tasks_by_type,
            "orphan_count": orphan_count,
            "root_count": root_count,
            "leaf_count": leaf_count,
            "max_depth": max_depth,
            "avg_depth": round(total_depth / total_tasks, 2) if total_tasks > 0 else 0.0,
            "dependency_stats": {
                "total_edges": total_edges,
                "max_in_degree": max_in_degree,
                "max_out_degree": max_out_degree,
                "tasks_with_high_out_degree": sorted(
                    tasks_with_high_out_degree,
                    key=lambda x: x["out_degree"],
                    reverse=True,
                ),
            },
            "readiness_stats": {
                "ready_count": ready_count,
                "blocked_count": blocked_count,
                "in_progress_count": in_progress_count,
            },
        }

        return {
            "success": True,
            "stats": stats,
            "message": f"Calculated graph metrics for {total_tasks} tasks.",
        }

    except Exception as e:
        logger.exception("get_graph_metrics failed")
        return {
            "success": False,
            "stats": {},
            "message": f"Failed to get graph metrics: {e}",
        }


# =============================================================================
# GRAPH METRICS AND REVIEW
# =============================================================================


def _compute_graph_metrics(
    index: TaskIndex,
    scope: str = "all",
    scope_id: str | None = None,
) -> dict[str, Any]:
    """Compute raw graph metrics from task index.

    Internal helper that computes metrics for get_graph_metrics() and
    get_review_snapshot(). Returns deterministic counts and metrics
    without interpretation (per P#78).

    Args:
        index: TaskIndex instance
        scope: "all", "project", or "subtree"
        scope_id: Project slug (for scope="project") or task_id (for scope="subtree")

    Returns:
        Dictionary with graph metrics
    """
    # Get tasks based on scope
    if scope == "project" and scope_id:
        entries = index.get_by_project(scope_id)
    elif scope == "subtree" and scope_id:
        root = index.get_task(scope_id)
        if root:
            entries = [root] + index.get_descendants(scope_id)
        else:
            entries = []
    else:
        entries = list(index._tasks.values())

    if not entries:
        return {
            "total_tasks": 0,
            "tasks_by_status": {},
            "tasks_by_type": {},
            "orphan_count": 0,
            "root_count": 0,
            "leaf_count": 0,
            "max_depth": 0,
            "avg_depth": 0.0,
            "dependency_stats": {
                "total_edges": 0,
                "max_in_degree": 0,
                "max_out_degree": 0,
                "tasks_with_high_out_degree": [],
            },
            "readiness_stats": {
                "ready_count": 0,
                "blocked_count": 0,
                "in_progress_count": 0,
            },
        }

    entry_ids = {e.id for e in entries}

    # Basic counts
    tasks_by_status: dict[str, int] = {}
    tasks_by_type: dict[str, int] = {}
    depths: list[int] = []
    leaf_count = 0
    orphan_count = 0
    in_progress_count = 0

    for entry in entries:
        # Status counts
        tasks_by_status[entry.status] = tasks_by_status.get(entry.status, 0) + 1
        # Type counts
        tasks_by_type[entry.type] = tasks_by_type.get(entry.type, 0) + 1
        # Depth tracking
        depths.append(entry.depth)
        # Leaf counting
        if entry.leaf:
            leaf_count += 1
        # Orphan: no parent AND no dependencies (within scope)
        has_parent_in_scope = entry.parent and entry.parent in entry_ids
        has_deps_in_scope = any(d in entry_ids for d in entry.depends_on)
        if not has_parent_in_scope and not has_deps_in_scope:
            orphan_count += 1
        # In-progress
        if entry.status == "in_progress":
            in_progress_count += 1

    # Root count (tasks with no parent within scope)
    root_count = sum(1 for e in entries if not e.parent or e.parent not in entry_ids)

    # Depth stats
    max_depth = max(depths) if depths else 0
    avg_depth = sum(depths) / len(depths) if depths else 0.0

    # Dependency stats
    total_edges = 0
    in_degrees: dict[str, int] = {}  # How many deps each task has
    out_degrees: dict[str, int] = {}  # How many tasks depend on each task

    for entry in entries:
        # In-degree: count dependencies this task has (within scope)
        deps_in_scope = [d for d in entry.depends_on if d in entry_ids]
        in_degrees[entry.id] = len(deps_in_scope)
        total_edges += len(deps_in_scope)

        # Out-degree: count tasks that depend on this task (within scope)
        blocks_in_scope = [b for b in entry.blocks if b in entry_ids]
        out_degrees[entry.id] = len(blocks_in_scope)

    max_in_degree = max(in_degrees.values()) if in_degrees else 0
    max_out_degree = max(out_degrees.values()) if out_degrees else 0

    # Tasks with high out-degree (return all with out_degree > 0, sorted desc)
    # Agent applies its own threshold
    tasks_with_high_out_degree = [
        {"id": e.id, "title": e.title, "out_degree": out_degrees.get(e.id, 0)}
        for e in entries
        if out_degrees.get(e.id, 0) > 0
    ]
    tasks_with_high_out_degree.sort(key=lambda x: -x["out_degree"])

    # Readiness stats
    ready_ids = set(index._ready)
    blocked_ids = set(index._blocked)
    ready_count = sum(1 for e in entries if e.id in ready_ids)
    blocked_count = sum(1 for e in entries if e.id in blocked_ids)

    return {
        "total_tasks": len(entries),
        "tasks_by_status": tasks_by_status,
        "tasks_by_type": tasks_by_type,
        "orphan_count": orphan_count,
        "root_count": root_count,
        "leaf_count": leaf_count,
        "max_depth": max_depth,
        "avg_depth": round(avg_depth, 2),
        "dependency_stats": {
            "total_edges": total_edges,
            "max_in_degree": max_in_degree,
            "max_out_degree": max_out_degree,
            "tasks_with_high_out_degree": tasks_with_high_out_degree[:20],  # Limit output
        },
        "readiness_stats": {
            "ready_count": ready_count,
            "blocked_count": blocked_count,
            "in_progress_count": in_progress_count,
        },
    }


@mcp.tool()
def get_review_snapshot(since_days: int = 1) -> dict[str, Any]:
    """Return snapshot data for periodic review. Agent generates report.

    Provides raw data for the agent to analyze and interpret. Server does NOT
    make recommendations or identify issues - per P#78 "Dumb Server, Smart Agent".

    Args:
        since_days: Number of days to look back for changes (default: 1)

    Returns:
        Dictionary with:
        - success: True if snapshot generated
        - timestamp: Current timestamp
        - metrics: Graph metrics (from get_graph_metrics logic)
        - changes_since:
            - tasks_created: List of tasks created in last N days
            - tasks_completed: List of tasks completed in last N days
            - tasks_modified: List of tasks modified in last N days
        - staleness:
            - oldest_ready_task: {task, days_ready} or None
            - oldest_in_progress: {task, days_in_progress} or None
        - velocity:
            - completed_last_7_days: int
            - created_last_7_days: int
        - message: Status message
    """
    try:
        from datetime import timedelta

        storage = _get_storage()
        index = _get_index()

        now = datetime.now(UTC)
        cutoff = now - timedelta(days=since_days)
        velocity_cutoff = now - timedelta(days=7)

        # Compute metrics
        metrics = _compute_graph_metrics(index)

        # Track changes and velocity
        tasks_created: list[dict[str, Any]] = []
        tasks_completed: list[dict[str, Any]] = []
        tasks_modified: list[dict[str, Any]] = []
        completed_last_7_days = 0
        created_last_7_days = 0

        # Track staleness - oldest ready and in_progress tasks
        oldest_ready_task: dict[str, Any] | None = None
        oldest_in_progress: dict[str, Any] | None = None
        oldest_ready_days = 0.0
        oldest_in_progress_days = 0.0

        # Iterate all tasks to compute changes and staleness
        for task in storage._iter_all_tasks():
            task_dict = _task_to_dict(task, truncate_body=100)

            # Created timestamp
            created_ts = task.created
            if created_ts.tzinfo is None:
                created_ts = created_ts.replace(tzinfo=UTC)

            # Modified timestamp
            modified_ts = task.modified
            if modified_ts.tzinfo is None:
                modified_ts = modified_ts.replace(tzinfo=UTC)

            # Changes since cutoff
            if created_ts >= cutoff:
                tasks_created.append(task_dict)
            if modified_ts >= cutoff and task.status.value == "done":
                tasks_completed.append(task_dict)
            elif modified_ts >= cutoff and created_ts < cutoff:
                # Modified but not created in window (and not a completion)
                tasks_modified.append(task_dict)

            # Velocity (7-day window)
            if created_ts >= velocity_cutoff:
                created_last_7_days += 1
            if task.status.value == "done" and modified_ts >= velocity_cutoff:
                completed_last_7_days += 1

            # Staleness: check ready tasks
            if task.id in index._ready:
                # Use modified date as proxy for "became ready" date
                # (Tasks become ready when deps complete, which triggers a modification)
                days_ready = (now - modified_ts).total_seconds() / 86400
                if days_ready > oldest_ready_days:
                    oldest_ready_days = days_ready
                    oldest_ready_task = {
                        "task": task_dict,
                        "days_ready": round(days_ready, 1),
                    }

            # Staleness: check in_progress tasks
            if task.status.value == "in_progress":
                days_in_progress = (now - modified_ts).total_seconds() / 86400
                if days_in_progress > oldest_in_progress_days:
                    oldest_in_progress_days = days_in_progress
                    oldest_in_progress = {
                        "task": task_dict,
                        "days_in_progress": round(days_in_progress, 1),
                    }

        # Sort changes by modified date (most recent first)
        tasks_created.sort(key=lambda t: t["created"], reverse=True)
        tasks_completed.sort(key=lambda t: t["modified"], reverse=True)
        tasks_modified.sort(key=lambda t: t["modified"], reverse=True)

        snapshot = {
            "success": True,
            "timestamp": now.isoformat(),
            "metrics": metrics,
            "changes_since": {
                "since_days": since_days,
                "tasks_created": tasks_created[:50],  # Limit output
                "tasks_completed": tasks_completed[:50],
                "tasks_modified": tasks_modified[:50],
            },
            "staleness": {
                "oldest_ready_task": oldest_ready_task,
                "oldest_in_progress": oldest_in_progress,
            },
            "velocity": {
                "completed_last_7_days": completed_last_7_days,
                "created_last_7_days": created_last_7_days,
            },
            "message": (
                f"Review snapshot generated: {metrics['total_tasks']} total tasks, "
                f"{len(tasks_created)} created, {len(tasks_completed)} completed "
                f"in last {since_days} day(s)"
            ),
        }

        logger.info(f"get_review_snapshot: {snapshot['message']}")
        return snapshot

    except Exception as e:
        logger.exception("get_review_snapshot failed")
        return {
            "success": False,
            "timestamp": datetime.now().astimezone().isoformat(),
            "metrics": {},
            "changes_since": {},
            "staleness": {},
            "velocity": {},
            "message": f"Failed to generate review snapshot: {e}",
        }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    mcp.run()
