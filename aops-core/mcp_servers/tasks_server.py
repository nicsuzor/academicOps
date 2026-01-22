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
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP

import sys
from pathlib import Path

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent  # up from mcp_servers/
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.paths import get_data_root
from lib.task_index import TaskIndex, TaskIndexEntry
from lib.task_model import Task, TaskStatus, TaskType
from lib.task_storage import TaskStorage

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


def _task_to_dict(task: Task) -> dict[str, Any]:
    """Convert Task to dictionary for MCP response.

    Args:
        task: Task instance

    Returns:
        Dictionary representation suitable for JSON serialization
    """
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
        "depth": task.depth,
        "leaf": task.leaf,
        "due": task.due.isoformat() if task.due else None,
        "project": task.project,
        "tags": task.tags,
        "effort": task.effort,
        "context": task.context,
        "body": task.body,
        "children": task.children,
        "blocks": task.blocks,
    }


def _index_entry_to_dict(entry: TaskIndexEntry) -> dict[str, Any]:
    """Convert TaskIndexEntry to dictionary for MCP response.

    Args:
        entry: TaskIndexEntry instance

    Returns:
        Dictionary representation suitable for JSON serialization
    """
    return entry.to_dict()


# =============================================================================
# CRUD OPERATIONS
# =============================================================================


@mcp.tool()
def create_task(
    title: str,
    type: str = "task",
    project: Optional[str] = None,
    parent: Optional[str] = None,
    depends_on: Optional[list[str]] = None,
    order: int = 0,
    priority: int = 2,
    due: Optional[str] = None,
    tags: Optional[list[str]] = None,
    body: str = "",
) -> dict[str, Any]:
    """Create a new task in the hierarchical task system.

    Creates a task with graph relationships for decomposition workflows.
    Tasks are stored as markdown files with YAML frontmatter.

    Args:
        title: Task title (required)
        type: Task type - "goal", "project", "task", or "action" (default: "task")
        project: Project slug for organization (determines storage location)
        parent: Parent task ID for hierarchical relationships
        depends_on: List of task IDs this task depends on
        order: Sibling ordering (lower = first, default: 0)
        priority: Priority 0-4 (0=critical, 4=someday, default: 2)
        due: Due date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        tags: List of tags for categorization
        body: Markdown body content

    Returns:
        Dictionary with:
        - success: True if created
        - task: Full task data
        - message: Status message

    Example:
        create_task(
            title="Write Chapter 1",
            type="project",
            project="book",
            parent="20260112-write-book"
        )
    """
    try:
        storage = _get_storage()

        # Parse task type
        try:
            task_type = TaskType(type)
        except ValueError:
            return {
                "success": False,
                "message": f"Invalid task type: {type}. Must be one of: goal, project, task, action",
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

        # Create task
        task = storage.create_task(
            title=title,
            project=project,
            type=task_type,
            parent=parent,
            depends_on=depends_on,
            priority=priority,
            due=due_datetime,
            tags=tags,
            body=body,
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

        # Load index for computed fields (children, blocks)
        index = _get_index()
        entry = index.get_task(id)
        if entry:
            task.children = entry.children
            task.blocks = entry.blocks

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
    title: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    order: Optional[int] = None,
    parent: Optional[str] = None,
    depends_on: Optional[list[str]] = None,
    due: Optional[str] = None,
    project: Optional[str] = None,
    tags: Optional[list[str]] = None,
    effort: Optional[str] = None,
    context: Optional[str] = None,
    body: Optional[str] = None,
) -> dict[str, Any]:
    """Update an existing task.

    Only provided fields are updated. Pass None to leave field unchanged.

    Args:
        id: Task ID to update (required)
        title: New title
        type: New type - "goal", "project", "task", or "action"
        status: New status - "inbox", "active", "blocked", "waiting", "done", "cancelled"
        priority: New priority 0-4
        order: New sibling order
        parent: New parent task ID (or "" to clear)
        depends_on: New dependency list (replaces existing)
        due: New due date in ISO format (or "" to clear)
        project: New project slug (or "" to clear)
        tags: New tags list (replaces existing)
        effort: New effort estimate (or "" to clear)
        context: New context (or "" to clear)
        body: New body content

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
        if title is not None:
            task.title = title
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
                task.status = TaskStatus(status)
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
            task.body = body
            modified_fields.append("body")

        # Save if anything changed
        if modified_fields:
            storage.save_task(task)
            # Rebuild index
            index = TaskIndex(get_data_root())
            index.rebuild()

        logger.info(f"update_task: {id} - modified {modified_fields}")

        return {
            "success": True,
            "task": _task_to_dict(task),
            "modified_fields": modified_fields,
            "message": f"Updated task: {task.title}"
            if modified_fields
            else "No changes made",
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
def complete_task(id: str) -> dict[str, Any]:
    """Mark a task as done.

    Updates status to "done" and sets modified timestamp.

    Args:
        id: Task ID to complete

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

        task.complete()
        storage.save_task(task)

        # Rebuild index
        index = TaskIndex(get_data_root())
        index.rebuild()

        logger.info(f"complete_task: {id}")

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
def get_ready_tasks(project: str) -> dict[str, Any]:
    """Get tasks ready to work on.

    Ready tasks are:
    - Leaves (no children)
    - No unmet dependencies (all depends_on are done/cancelled)
    - Status is "active" or "inbox"

    Args:
        project: Filter by project slug, or empty string "" for all projects

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of ready task entries (sorted by priority)
        - count: Number of ready tasks
        - message: Status message
    """
    try:
        index = _get_index()
        ready = index.get_ready_tasks(project=project or None)

        return {
            "success": True,
            "tasks": [_index_entry_to_dict(e) for e in ready],
            "count": len(ready),
            "message": f"Found {len(ready)} ready tasks"
            + (f" in project {project}" if project else ""),
        }

    except Exception as e:
        logger.exception("get_ready_tasks failed")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "message": f"Failed to get ready tasks: {e}",
        }


@mcp.tool()
def get_blocked_tasks(project: str) -> dict[str, Any]:
    """Get tasks blocked by dependencies.

    Returns tasks that have unmet dependencies or status "blocked".

    Args:
        project: Filter by project slug, or empty string "" for all projects

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of blocked task entries
        - count: Number of blocked tasks
        - message: Status message
    """
    try:
        index = _get_index()
        blocked = index.get_blocked_tasks()

        # Filter by project if specified
        if project:
            blocked = [e for e in blocked if e.project == project]

        return {
            "success": True,
            "tasks": [_index_entry_to_dict(e) for e in blocked],
            "count": len(blocked),
            "message": f"Found {len(blocked)} blocked tasks"
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
def get_task_tree(id: str) -> dict[str, Any]:
    """Get the decomposition tree for a task.

    Returns the task and all its descendants in a tree structure.

    Args:
        id: Root task ID to get tree for

    Returns:
        Dictionary with:
        - success: True if task found
        - tree: Tree node with structure:
            - task: Task data
            - children: List of child tree nodes (recursive)
        - message: Status message
    """
    try:
        index = _get_index()
        root = index.get_task(id)

        if root is None:
            return {
                "success": False,
                "tree": None,
                "message": f"Task not found: {id}",
            }

        def build_tree(entry: TaskIndexEntry) -> dict[str, Any]:
            """Recursively build tree structure."""
            children = index.get_children(entry.id)
            return {
                "task": _index_entry_to_dict(entry),
                "children": [build_tree(child) for child in children],
            }

        tree = build_tree(root)

        return {
            "success": True,
            "tree": tree,
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

        return {
            "success": True,
            "tasks": [_index_entry_to_dict(e) for e in children],
            "count": len(children),
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

        return {
            "success": True,
            "tasks": [_index_entry_to_dict(e) for e in deps],
            "count": len(deps),
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


# =============================================================================
# DECOMPOSITION OPERATIONS
# =============================================================================


@mcp.tool()
def decompose_task(id: str, children: list) -> dict[str, Any]:
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
                completed.append(_task_to_dict(task))
            except Exception as e:
                failures.append(
                    {
                        "id": task_id,
                        "reason": str(e),
                    }
                )

        # Rebuild index once at the end
        if completed:
            index = TaskIndex(get_data_root())
            index.rebuild()

        logger.info(
            f"complete_tasks: {len(completed)} completed, {len(failures)} failed"
        )

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
    project: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List tasks with optional filters.

    Args:
        project: Filter by project slug
        status: Filter by status - "inbox", "active", "blocked", "waiting", "done", "cancelled"
        type: Filter by type - "goal", "project", "task", "action"
        limit: Maximum number of tasks to return (default: 50)

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of task entries
        - count: Number of tasks returned
        - message: Status message
    """
    try:
        storage = _get_storage()

        # Parse optional filters
        task_status = None
        if status:
            try:
                task_status = TaskStatus(status)
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

        tasks = storage.list_tasks(project=project, status=task_status, type=task_type)
        tasks = tasks[:limit]

        return {
            "success": True,
            "tasks": [_task_to_dict(t) for t in tasks],
            "count": len(tasks),
            "message": f"Found {len(tasks)} tasks",
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
def search_tasks(query: str, limit: int = 20) -> dict[str, Any]:
    """Search tasks by text query.

    Searches task titles and body content for matching text.
    Case-insensitive substring matching.

    Args:
        query: Search text to match
        limit: Maximum number of results (default: 20)

    Returns:
        Dictionary with:
        - success: True
        - tasks: List of matching task entries
        - count: Number of matches
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

            if len(matches) >= limit:
                break

        # Sort by priority then title
        matches.sort(key=lambda t: (t.priority, t.title))

        return {
            "success": True,
            "tasks": [_task_to_dict(t) for t in matches],
            "count": len(matches),
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


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    mcp.run()
