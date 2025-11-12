#!/usr/bin/env python3
"""FastMCP server for task management.

Provides MCP tools for viewing, archiving, and creating tasks.
Exposes existing task management functionality via structured MCP interface.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from fastmcp import FastMCP

from bots.skills.tasks import task_ops
from bots.skills.tasks.models import (
    ArchiveTasksRequest,
    ArchiveTasksResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    ErrorResponse,
    ModifyTaskRequest,
    ModifyTaskResponse,
    Task,
    TaskFilter,
    UnarchiveTasksRequest,
    UnarchiveTasksResponse,
    ViewTasksRequest,
    ViewTasksResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("task-manager")

# Global data directory (set once at startup)
DATA_DIR: Path | None = None


def get_or_init_data_dir() -> Path:
    """Get data directory, initializing if needed."""
    global DATA_DIR
    if DATA_DIR is None:
        DATA_DIR = task_ops.get_data_dir()
        logger.info(f"Using data directory: {DATA_DIR}")
    return DATA_DIR


@mcp.tool()
def view_tasks(
    page: int = 1,
    per_page: int = 10,
    sort: str = "priority",
    compact: bool = False,
    priority_filter: list[int] | None = None,
    project_filter: str | None = None,
    status_filter: str | None = None,
) -> dict:
    """View tasks with filtering, sorting, and pagination.

    Lists active tasks from inbox and queue directories with optional filtering.
    Supports multiple sort orders and pagination for large task lists.

    Args:
        page: Page number (1-indexed), default 1
        per_page: Tasks per page (1-100), default 10
        sort: Sort order - "priority", "date", or "due"
        compact: Compact one-line format vs full details
        priority_filter: Filter by priority levels (0-3), e.g., [1, 2]
        project_filter: Filter by project slug
        status_filter: Filter by status

    Returns:
        ViewTasksResponse with task list and pagination info

    Raises:
        TaskDirectoryNotFoundError: If data directory doesn't exist
    """
    try:
        data_dir = get_or_init_data_dir()

        # Validate request
        request = ViewTasksRequest(
            page=page,
            per_page=per_page,
            sort=sort,  # type: ignore[arg-type]
            compact=compact,
            filters=TaskFilter(
                priority=priority_filter,
                project=project_filter,
                status=status_filter,
            )
            if any([priority_filter, project_filter, status_filter])
            else None,
        )

        # Load all tasks
        all_tasks = task_ops.load_all_tasks(data_dir, include_archived=False)

        # Apply filters
        filtered_tasks = all_tasks
        if request.filters:
            if request.filters.priority:
                filtered_tasks = [
                    t for t in filtered_tasks if t.priority in request.filters.priority
                ]
            if request.filters.project:
                filtered_tasks = [
                    t for t in filtered_tasks if t.project == request.filters.project
                ]
            if request.filters.status:
                filtered_tasks = [
                    t for t in filtered_tasks if t.status == request.filters.status
                ]

        # Sort tasks
        def priority_key(t: Task) -> tuple:
            p = t.priority if t.priority is not None else 9999
            d = t.due if t.due else datetime.max.replace(tzinfo=UTC)
            c = t.created
            return (p, d, c)

        def date_key(t: Task) -> datetime:
            return t.created

        def due_key(t: Task) -> tuple:
            has_due = t.due is not None
            due_date = t.due if t.due else datetime.max.replace(tzinfo=UTC)
            priority = t.priority if t.priority is not None else 9999
            return (not has_due, due_date, priority)

        if request.sort == "priority":
            sorted_tasks = sorted(filtered_tasks, key=priority_key)
        elif request.sort == "date":
            sorted_tasks = sorted(filtered_tasks, key=date_key, reverse=True)
        elif request.sort == "due":
            sorted_tasks = sorted(filtered_tasks, key=due_key)
        else:
            sorted_tasks = filtered_tasks

        # Paginate
        total = len(sorted_tasks)
        start = (request.page - 1) * request.per_page
        end = min(start + request.per_page, total)

        # Clamp to valid page
        if start >= total > 0:
            last_page = (total - 1) // request.per_page + 1
            request.page = last_page
            start = (request.page - 1) * request.per_page
            end = min(start + request.per_page, total)

        page_tasks = sorted_tasks[start:end]

        # If compact mode, remove body from tasks
        if request.compact:
            for task in page_tasks:
                task.body = None

        response = ViewTasksResponse(
            success=True,
            total_tasks=total,
            page=request.page,
            per_page=request.per_page,
            tasks=page_tasks,
            message=f"Showing {start + 1}-{end} of {total} tasks"
            if total > 0
            else "No tasks found",
        )

        logger.info(
            f"view_tasks: page={request.page}, total={total}, filters={request.filters}"
        )
        return response.model_dump()

    except task_ops.TaskDirectoryNotFoundError as e:
        logger.error(f"view_tasks failed: {e}")
        error = ErrorResponse(
            error_type="TaskDirectoryNotFoundError",
            message=str(e),
            context={"expected_paths": "$ACA/data or ./data"},
        )
        return error.model_dump()
    except Exception as e:
        logger.exception("view_tasks unexpected error")
        error = ErrorResponse(
            error_type=type(e).__name__,
            message=f"Unexpected error: {e}",
        )
        return error.model_dump()


@mcp.tool()
def archive_tasks(identifiers: list[str]) -> dict:
    """Archive one or more tasks.

    Moves tasks from inbox/queue to archived folder and updates status.
    Supports batch operations for archiving multiple tasks at once.

    Supports multiple identifier formats:
    - Index from current view: "3", "#5" (requires view_tasks first)
    - Task ID: "20251110-abc123" (with or without .md extension)
    - Filename: "20251110-abc123.md"

    Args:
        identifiers: Task identifiers (index, task ID, or filename)

    Returns:
        ArchiveTasksResponse with per-file results and summary

    Raises:
        ValidationError: If identifiers list is empty
    """
    try:
        data_dir = get_or_init_data_dir()

        # Validate request
        request = ArchiveTasksRequest(identifiers=identifiers)

        # Archive each task
        results = []
        success_count = 0
        failure_count = 0

        for identifier in request.identifiers:
            # Resolve identifier to filename
            try:
                filename = task_ops.resolve_identifier(identifier, data_dir)
                result = task_ops.archive_task(filename, data_dir)
                # Add resolution info to result
                if result["success"] and identifier != filename:
                    result["resolved_from"] = identifier
                results.append(result)
                if result["success"]:
                    success_count += 1
                else:
                    failure_count += 1
            except ValueError as e:
                # Resolution failed
                results.append(
                    {
                        "success": False,
                        "message": f"Cannot resolve identifier '{identifier}': {e}",
                        "identifier": identifier,
                    }
                )
                failure_count += 1

        response = ArchiveTasksResponse(
            success=failure_count == 0,
            results=results,
            success_count=success_count,
            failure_count=failure_count,
        )

        logger.info(f"archive_tasks: {success_count} succeeded, {failure_count} failed")
        return response.model_dump()

    except Exception as e:
        logger.exception("archive_tasks unexpected error")
        error = ErrorResponse(
            error_type=type(e).__name__,
            message=f"Unexpected error: {e}",
        )
        return error.model_dump()


@mcp.tool()
def unarchive_tasks(identifiers: list[str]) -> dict:
    """Unarchive one or more tasks.

    Moves tasks from archived folder back to inbox and updates status.
    Supports batch operations for unarchiving multiple tasks at once.

    Supports multiple identifier formats:
    - Task ID: "20251110-abc123" (with or without .md extension)
    - Filename: "20251110-abc123.md"

    Note: Index-based resolution not supported for archived tasks (they're not in current view).

    Args:
        identifiers: Task identifiers (task ID or filename)

    Returns:
        UnarchiveTasksResponse with per-file results and summary

    Raises:
        ValidationError: If identifiers list is empty
    """
    try:
        data_dir = get_or_init_data_dir()

        # Validate request
        request = UnarchiveTasksRequest(identifiers=identifiers)

        # Unarchive each task
        results = []
        success_count = 0
        failure_count = 0

        for identifier in request.identifiers:
            # For unarchive, we don't use index resolution (archived tasks not in view)
            # But we still normalize the identifier (add .md if needed)
            filename = identifier if identifier.endswith(".md") else identifier + ".md"

            result = task_ops.unarchive_task(filename, data_dir)
            # Add resolution info to result if we modified the identifier
            if result["success"] and identifier != filename:
                result["resolved_from"] = identifier
            results.append(result)
            if result["success"]:
                success_count += 1
            else:
                failure_count += 1

        response = UnarchiveTasksResponse(
            success=failure_count == 0,
            results=results,
            success_count=success_count,
            failure_count=failure_count,
        )

        logger.info(
            f"unarchive_tasks: {success_count} succeeded, {failure_count} failed"
        )
        return response.model_dump()

    except Exception as e:
        logger.exception("unarchive_tasks unexpected error")
        error = ErrorResponse(
            error_type=type(e).__name__,
            message=f"Unexpected error: {e}",
        )
        return error.model_dump()


@mcp.tool()
def create_task(
    title: str,
    priority: int | None = None,
    task_type: str = "todo",
    project: str | None = None,
    due: str | None = None,
    body: str = "",
    tags: list[str] | None = None,
) -> dict:
    """Create a new task.

    Creates a new task in the inbox with generated ID and filename.
    Validates all inputs and ensures required fields are present.

    Args:
        title: Task title (required, non-empty)
        priority: Priority level 0-3 (0=urgent, 3=low)
        task_type: Task type, default "todo"
        project: Project slug for categorization
        due: Due date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        body: Task body content/description
        tags: List of tags

    Returns:
        CreateTaskResponse with task_id, filename, and path

    Raises:
        ValidationError: If title is empty or priority out of range
    """
    try:
        data_dir = get_or_init_data_dir()

        # Parse due date if provided
        due_datetime = None
        if due:
            try:
                due_datetime = datetime.fromisoformat(due.replace("Z", "+00:00"))
            except ValueError as e:
                error = ErrorResponse(
                    error_type="ValidationError",
                    message=f"Invalid due date format: {e}",
                    context={"expected_format": "YYYY-MM-DDTHH:MM:SSZ"},
                )
                return error.model_dump()

        # Validate request
        request = CreateTaskRequest(
            title=title,
            priority=priority,
            type=task_type,
            project=project,
            due=due_datetime,
            body=body,
            tags=tags or [],
        )

        # Create task
        result = task_ops.create_task(
            title=request.title,
            data_dir=data_dir,
            priority=request.priority,
            task_type=request.type,
            project=request.project,
            due=request.due,
            body=request.body,
            tags=request.tags,
        )

        if result["success"]:
            response = CreateTaskResponse(
                success=True,
                task_id=result["task_id"],
                filename=result["filename"],
                path=result["path"],
                message=result["message"],
            )
            logger.info(f"create_task: {result['filename']}")
            return response.model_dump()
        error = ErrorResponse(
            error_type="TaskCreationError",
            message=result["message"],
        )
        return error.model_dump()

    except Exception as e:
        logger.exception("create_task unexpected error")
        error = ErrorResponse(
            error_type=type(e).__name__,
            message=f"Unexpected error: {e}",
        )
        return error.model_dump()


@mcp.tool()
def modify_task(
    identifier: str,
    title: str | None = None,
    priority: int | None = None,
    project: str | None = None,
    classification: str | None = None,
    due: str | None = None,
    status: str | None = None,
    body: str | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
) -> dict:
    """Modify an existing task.

    Updates task fields without needing to archive and recreate.
    Supports partial updates - only provide fields you want to change.

    Supports multiple identifier formats:
    - Index from current view: "3", "#5" (requires view_tasks first)
    - Task ID: "20251110-abc123" (with or without .md extension)
    - Filename: "20251110-abc123.md"

    Args:
        identifier: Task identifier (index, task ID, or filename)
        title: New task title
        priority: New priority level 0-3
        project: New project slug
        classification: New classification
        due: New due date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        status: New status
        body: New body content
        add_tags: Tags to add to existing tags
        remove_tags: Tags to remove from existing tags

    Returns:
        ModifyTaskResponse with success status and modified fields

    Example:
        # Change priority
        modify_task(identifier="3", priority=1)

        # Update multiple fields
        modify_task(
            identifier="20251110-abc123",
            title="Updated title",
            project="new-project",
            add_tags=["urgent"]
        )
    """
    try:
        data_dir = get_or_init_data_dir()

        # Parse due date if provided
        due_datetime = None
        if due:
            try:
                due_datetime = datetime.fromisoformat(due.replace("Z", "+00:00"))
            except ValueError as e:
                error = ErrorResponse(
                    error_type="ValidationError",
                    message=f"Invalid due date format: {e}",
                    context={"expected_format": "YYYY-MM-DDTHH:MM:SSZ"},
                )
                return error.model_dump()

        # Validate request
        request = ModifyTaskRequest(
            identifier=identifier,
            title=title,
            priority=priority,
            project=project,
            classification=classification,
            due=due_datetime,
            status=status,
            body=body,
            add_tags=add_tags or [],
            remove_tags=remove_tags or [],
        )

        # Modify task
        result = task_ops.modify_task(
            identifier=request.identifier,
            data_dir=data_dir,
            title=request.title,
            priority=request.priority,
            project=request.project,
            classification=request.classification,
            due=request.due,
            status=request.status,
            body=request.body,
            add_tags=request.add_tags if request.add_tags else None,
            remove_tags=request.remove_tags if request.remove_tags else None,
        )

        if result["success"]:
            response = ModifyTaskResponse(
                success=True,
                message=result["message"],
                modified_fields=result.get("modified_fields", []),
                task_id=result.get("task_id"),
            )
            logger.info(
                f"modify_task: {result.get('task_id')} - modified {len(result.get('modified_fields', []))} fields"
            )
            return response.model_dump()
        error = ErrorResponse(
            error_type="TaskModificationError",
            message=result["message"],
        )
        return error.model_dump()

    except Exception as e:
        logger.exception("modify_task unexpected error")
        error = ErrorResponse(
            error_type=type(e).__name__,
            message=f"Unexpected error: {e}",
        )
        return error.model_dump()


if __name__ == "__main__":
    # Run the server
    mcp.run()
