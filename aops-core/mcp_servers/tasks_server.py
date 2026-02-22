"""MCP server for task decomposition and graph operations.

Implements the data access layer for task management as defined in
specs/mcp-decomposition-tools-v2.md.
"""

import re
from datetime import datetime, timedelta
from typing import Any

from fastmcp import FastMCP
from lib.paths import get_data_root  # noqa: F401
from lib.task_index import TaskIndex, TaskIndexEntry
from lib.task_model import Task, TaskStatus, TaskType
from lib.task_storage import TaskStorage

# Initialize FastMCP server
mcp = FastMCP("tasks")


def _get_storage() -> TaskStorage:
    """Get task storage instance."""
    return TaskStorage()


def _get_index() -> TaskIndex:
    """Get task index instance."""
    index = TaskIndex()
    # Ensure index is up to date
    if not index.load():
        index.rebuild()
    return index


def _task_to_dict(task: Task) -> dict[str, Any]:
    """Convert Task to dict including body."""
    data = task.to_frontmatter()
    data["body"] = task.body
    return data


def _check_incomplete_markers(body: str | None) -> list[str]:
    """Check for incomplete markers in task body."""
    if not body:
        return []

    markers = []

    # 1. Remaining section headers
    # Matches # Remaining:, ## REMAINING:, etc.
    if re.search(r"^#+\s+remaining:", body, re.IGNORECASE | re.MULTILINE):
        markers.append("Remaining: section")

    # 2. X% complete
    # Matches "50% complete", "0% complete", "99% complete"
    # Logic: find N% complete, check if N < 100
    for match in re.finditer(r"(\d+)%\s+complete", body, re.IGNORECASE):
        try:
            percent = int(match.group(1))
            if percent < 100:
                markers.append(match.group(0))
        except ValueError:
            pass

    # 3. Unchecked items
    # Matches "- [ ] Item" or "* [ ] Item"
    for match in re.finditer(r"^[\-\*]\s+\[ \]\s+(.*)", body, re.MULTILINE):
        markers.append(match.group(1).strip())

    # 4. WIP / in-progress
    # Word boundaries
    match = re.search(r"\b(WIP)\b", body, re.IGNORECASE)
    if match:
        markers.append(match.group(1))

    match = re.search(r"\b(in-progress)\b", body, re.IGNORECASE)
    if match:
        markers.append(match.group(1))

    return markers


def _propagate_completion(task_ids: list[str]) -> None:
    """Propagate completion to unblock dependent tasks."""
    storage = _get_storage()
    index = _get_index()

    queue = list(task_ids)
    visited = set()

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        # Get tasks blocked by current_id
        entry = index.get_task(current_id)
        if not entry:
            continue

        for blocked_id in entry.blocks:
            blocked_task = storage.get_task(blocked_id)
            if not blocked_task:
                continue

            # Check dependencies
            all_deps_done = True
            for dep_id in blocked_task.depends_on:
                dep = storage.get_task(dep_id)
                if not dep or dep.status not in (TaskStatus.DONE, TaskStatus.CANCELLED):
                    all_deps_done = False
                    break

            if all_deps_done:
                if blocked_task.status == TaskStatus.BLOCKED:
                    blocked_task.status = TaskStatus.ACTIVE
                    storage.save_task(blocked_task)

                if blocked_task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
                    queue.append(blocked_id)


def _compute_graph_metrics(
    index: TaskIndex, tasks: list[TaskIndexEntry] | None = None
) -> dict[str, Any]:
    """Compute graph metrics for a set of tasks (or all tasks in index)."""
    if tasks is None:
        tasks = list(index._tasks.values())

    total_tasks = len(tasks)
    tasks_by_status = {}
    tasks_by_type = {}
    orphan_count = 0
    root_count = 0
    leaf_count = 0
    max_depth = 0
    total_depth = 0

    # Dependency stats
    total_edges = 0
    max_in_degree = 0
    max_out_degree = 0
    tasks_with_high_out_degree = []  # (id, title, out_degree)

    # Readiness stats
    ready_count = 0
    blocked_count = 0
    in_progress_count = 0

    for task in tasks:
        # Counts
        tasks_by_status[task.status] = tasks_by_status.get(task.status, 0) + 1
        tasks_by_type[task.type] = tasks_by_type.get(task.type, 0) + 1

        if not task.parent and not task.depends_on:
            orphan_count += 1
        if not task.parent:
            root_count += 1
        if task.leaf:
            leaf_count += 1

        if task.depth > max_depth:
            max_depth = task.depth
        total_depth += task.depth

        # Dependencies
        out_degree = len(task.blocks)  # tasks depending on this
        in_degree = len(task.depends_on)  # dependencies of this

        total_edges += out_degree  # This counts each edge once (from source)

        if in_degree > max_in_degree:
            max_in_degree = in_degree
        if out_degree > max_out_degree:
            max_out_degree = out_degree

    sorted_by_out = sorted(tasks, key=lambda t: len(t.blocks), reverse=True)
    tasks_with_high_out_degree = [
        {"id": t.id, "title": t.title, "out_degree": len(t.blocks)}
        for t in sorted_by_out[:10]
        if len(t.blocks) > 0
    ]

    # Readiness re-calculation
    for task in tasks:
        if task.status == TaskStatus.ACTIVE.value and task.leaf:
            if task.id in index._ready:
                ready_count += 1
            elif task.id in index._blocked:
                blocked_count += 1
        elif task.status == TaskStatus.BLOCKED.value:
            blocked_count += 1
        elif task.status == TaskStatus.IN_PROGRESS.value:
            in_progress_count += 1

    avg_depth = total_depth / total_tasks if total_tasks > 0 else 0.0

    return {
        "total_tasks": total_tasks,
        "tasks_by_status": tasks_by_status,
        "tasks_by_type": tasks_by_type,
        "orphan_count": orphan_count,
        "root_count": root_count,
        "leaf_count": leaf_count,
        "max_depth": max_depth,
        "avg_depth": avg_depth,
        "dependency_stats": {
            "total_edges": total_edges,
            "max_in_degree": max_in_degree,
            "max_out_degree": max_out_degree,
            "tasks_with_high_out_degree": tasks_with_high_out_degree,
        },
        "readiness_stats": {
            "ready_count": ready_count,
            "blocked_count": blocked_count,
            "in_progress_count": in_progress_count,
        },
    }


@mcp.tool()
def get_graph_metrics(
    scope: str = "all",  # "all", "project", or task_id for subtree
    scope_id: str | None = None,
) -> dict[str, Any]:
    """
    Return raw graph metrics. Agent interprets health.
    """
    index = _get_index()

    # Filter tasks based on scope
    tasks = []
    if scope == "all":
        tasks = list(index._tasks.values())
    elif scope == "project" and scope_id:
        tasks = index.get_by_project(scope_id)
    elif scope_id:  # subtree
        tasks = index.get_descendants(scope_id)
        # Include root of subtree
        root = index.get_task(scope_id)
        if root:
            tasks.append(root)

    return _compute_graph_metrics(index, tasks)


@mcp.tool()
def get_task_scoring_factors(
    ready_only: bool = True,
    include_done: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Return tasks with raw scoring factors. Agent computes VOI.
    """
    index = _get_index()

    tasks = []
    if ready_only:
        tasks = index.get_ready_tasks()
    else:
        tasks = list(index._tasks.values())

    if not include_done:
        tasks = [
            t for t in tasks if t.status not in (TaskStatus.DONE.value, TaskStatus.CANCELLED.value)
        ]

    # Limit results
    tasks = tasks[:limit]

    results = []
    for task in tasks:
        full_task = _get_storage().get_task(task.id)
        if not full_task:
            continue

        parent_chain_length = len(index.get_ancestors(task.id))

        results.append(
            {
                "id": task.id,
                "title": task.title,
                "type": task.type,
                "status": task.status,
                "priority": task.priority,
                "created_age_days": (datetime.now().astimezone() - full_task.created).days,
                "modified_age_days": (datetime.now().astimezone() - full_task.modified).days,
                "complexity": full_task.complexity.value if full_task.complexity else None,
                "blocking_count": len(task.blocks),
                "blocked_by_count": len(task.depends_on),
                "soft_blocking_count": len(task.soft_blocks),
                "child_count": len(task.children),
                "parent_chain_length": parent_chain_length,
                "tags": task.tags,
                "project": task.project,
                "body_length": len(full_task.body),
                "has_acceptance_criteria": "acceptance" in full_task.body.lower()
                or "[ ]" in full_task.body,
            }
        )

    return {"success": True, "tasks": results}


@mcp.tool()
def get_decomposition_context(
    task_id: str,
) -> dict[str, Any]:
    """
    Return context for decomposition. Agent proposes breakdown.
    """
    storage = _get_storage()
    index = _get_index()

    task = storage.get_task(task_id)
    if not task:
        return {"success": False, "message": "Task not found"}

    children = storage.get_children(task_id)

    parent = None
    siblings = []
    if task.parent:
        parent = storage.get_task(task.parent)
        if parent:
            siblings = [t for t in storage.get_children(task.parent) if t.id != task_id]

    project_tasks = []
    if task.project:
        project_entries = index.get_by_project(task.project)
        project_tasks = [e.to_dict() for e in project_entries if e.id != task_id]

    return {
        "success": True,
        "task": _task_to_dict(task),
        "existing_children": [_task_to_dict(c) for c in children],
        "parent_context": {
            "parent": _task_to_dict(parent) if parent else None,
            "siblings": [_task_to_dict(s) for s in siblings],
        },
        "project_context": {
            "project": task.project,
            "project_tasks": project_tasks,
        },
    }


@mcp.tool()
def get_task_neighborhood(
    task_id: str,
) -> dict[str, Any]:
    """
    Return the task and its graph neighborhood. Agent decides relationships.
    """
    storage = _get_storage()
    index = _get_index()

    task = storage.get_task(task_id)
    if not task:
        return {"success": False, "message": "Task not found", "task": None}

    # Helpers
    children = storage.get_children(task_id)

    depends_on = []
    for dep_id in task.depends_on:
        dep = storage.get_task(dep_id)
        if dep:
            depends_on.append(dep)

    blocks = []
    entry = index.get_task(task_id)
    if entry:
        for block_id in entry.blocks:
            block = storage.get_task(block_id)
            if block:
                blocks.append(block)

    same_project_tasks = []
    if task.project:
        project_entries = index.get_by_project(task.project)
        same_project_tasks = [e.to_dict() for e in project_entries if e.id != task_id]

    orphan_tasks = []
    for _, t_entry in index._tasks.items():
        if not t_entry.parent and not t_entry.depends_on:
            orphan_tasks.append(t_entry.to_dict())

    # Soft blocks
    soft_blocks = []
    if entry:
        for sb_id in entry.soft_blocks:
            sb = storage.get_task(sb_id)
            if sb:
                soft_blocks.append(sb)

    return {
        "success": True,
        "task": _task_to_dict(task),
        "existing_relationships": {
            "parent": _task_to_dict(storage.get_task(task.parent)) if task.parent else None,
            "children": [_task_to_dict(c) for c in children],
            "depends_on": [_task_to_dict(d) for d in depends_on],
            "blocks": [_task_to_dict(b) for b in blocks],
            "soft_blocks": [_task_to_dict(sb) for sb in soft_blocks],
        },
        "same_project_tasks": same_project_tasks,
        "orphan_tasks": orphan_tasks,
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
    """
    index = _get_index()
    storage = _get_storage()

    tasks = list(index._tasks.values())

    if project:
        tasks = [t for t in tasks if t.project == project]
    if status:
        tasks = [t for t in tasks if t.status == status]
    if min_depth is not None:
        tasks = [t for t in tasks if t.depth >= min_depth]
    if min_blocking_count is not None:
        tasks = [t for t in tasks if len(t.blocks) >= min_blocking_count]

    results = []
    for task in tasks:
        full_task = storage.get_task(task.id)
        if not full_task:
            continue

        ready_days = None
        if task.status == TaskStatus.ACTIVE.value and task.leaf:
            ready_days = (datetime.now().astimezone() - full_task.modified).days

        results.append(
            {
                "id": task.id,
                "title": task.title,
                "type": task.type,
                "status": task.status,
                "project": task.project,
                "tags": task.tags,
                "depth": task.depth,
                "parent": task.parent,
                "child_count": len(task.children),
                "blocking_count": len(task.blocks),
                "blocked_by_count": len(task.depends_on),
                "is_leaf": task.leaf,
                "created": full_task.created.isoformat(),
                "modified": full_task.modified.isoformat(),
                "ready_days": ready_days,
            }
        )

    return {"success": True, "tasks": results}


@mcp.tool()
def get_review_snapshot(
    since_days: int = 1,
) -> dict[str, Any]:
    """
    Return snapshot data for periodic review. Agent generates report.
    """
    index = _get_index()
    storage = _get_storage()

    metrics = _compute_graph_metrics(index)

    since_date = datetime.now().astimezone() - timedelta(days=since_days)

    created_since = []
    completed_since = []
    modified_since = []

    oldest_ready = None
    oldest_in_progress = None

    completed_last_7 = 0
    created_last_7 = 0
    date_7_days_ago = datetime.now().astimezone() - timedelta(days=7)

    for task in storage._iter_all_tasks():
        if task.created >= since_date:
            created_since.append(_task_to_dict(task))
        if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED) and task.modified >= since_date:
            completed_since.append(_task_to_dict(task))
        if task.modified >= since_date:
            modified_since.append(_task_to_dict(task))

        if task.created >= date_7_days_ago:
            created_last_7 += 1
        if (
            task.status in (TaskStatus.DONE, TaskStatus.CANCELLED)
            and task.modified >= date_7_days_ago
        ):
            completed_last_7 += 1

        if task.status == TaskStatus.ACTIVE:
            days_ready = (datetime.now().astimezone() - task.modified).days
            if oldest_ready is None or days_ready > oldest_ready["days_ready"]:
                oldest_ready = {"task": _task_to_dict(task), "days_ready": days_ready}

        if task.status == TaskStatus.IN_PROGRESS:
            days_in_progress = (datetime.now().astimezone() - task.modified).days
            if (
                oldest_in_progress is None
                or days_in_progress > oldest_in_progress["days_in_progress"]
            ):
                oldest_in_progress = {
                    "task": _task_to_dict(task),
                    "days_in_progress": days_in_progress,
                }

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "signals": {},
        "changes_since": {
            "tasks_created": created_since,
            "tasks_completed": completed_since,
            "tasks_modified": modified_since,
        },
        "staleness": {
            "oldest_ready_task": oldest_ready,
            "oldest_in_progress": oldest_in_progress,
        },
        "velocity": {
            "completed_last_7_days": completed_last_7,
            "created_last_7_days": created_last_7,
        },
    }


@mcp.tool()
def update_task(
    id: str,
    title: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    assignee: str | None = None,
    project: str | None = None,
    parent: str | None = None,
    depends_on: list[str] | None = None,
    tags: list[str] | None = None,
    body: str | None = None,
    due: str | None = None,  # ISO format
) -> dict[str, Any]:
    """Update a task."""
    storage = _get_storage()
    task = storage.get_task(id)
    if not task:
        return {"success": False, "message": "Task not found"}

    # Double claim prevention
    if status:
        s = status.replace("-", "_")
        try:
            new_status = TaskStatus(s)
        except ValueError:
            return {"success": False, "message": f"Invalid status: {status}"}

        if new_status == TaskStatus.IN_PROGRESS and assignee:
            if (
                task.status == TaskStatus.IN_PROGRESS
                and task.assignee
                and task.assignee != assignee
            ):
                return {
                    "success": False,
                    "message": f"Task already claimed by {task.assignee} since {task.modified.isoformat()}",
                    "task": _task_to_dict(task),
                }

    if title is not None:
        task.title = title
    if status is not None:
        s = status.replace("-", "_")
        try:
            task.status = TaskStatus(s)
        except ValueError:
            return {"success": False, "message": f"Invalid status: {status}"}
    if priority is not None:
        task.priority = priority
    if assignee is not None:
        task.assignee = assignee
    if project is not None:
        task.project = project
    if parent is not None:
        task.parent = parent
    if depends_on is not None:
        task.depends_on = depends_on
    if tags is not None:
        task.tags = tags
    if body is not None:
        task.body = body
    if due is not None:
        pass

    storage.save_task(task)

    # Propagate unblocks if completion
    if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
        _propagate_completion([task.id])

    return {"success": True, "task": _task_to_dict(task)}


@mcp.tool()
def create_task(
    title: str,
    project: str | None = None,
    type: str = "task",
    status: str = "active",
    parent: str | None = None,
    depends_on: list[str] | None = None,
    priority: int = 2,
    assignee: str | None = None,
    body: str = "",
) -> dict[str, Any]:
    """Create a new task."""
    storage = _get_storage()

    task = storage.create_task(
        title=title,
        project=project,
        type=TaskType(type),
        status=TaskStatus(status),
        parent=parent,
        depends_on=depends_on,
        priority=priority,
        assignee=assignee,
        body=body,
    )

    storage.save_task(task)
    return {"success": True, "task": _task_to_dict(task)}


@mcp.tool()
def complete_task(id: str) -> dict[str, Any]:
    """Complete a task and propagate unblocks."""
    storage = _get_storage()
    task = storage.get_task(id)
    if not task:
        return {"success": False, "message": "Task not found"}

    task.status = TaskStatus.DONE
    storage.save_task(task)

    _propagate_completion([id])

    return {"success": True, "task": _task_to_dict(task)}


@mcp.tool()
def complete_tasks(ids: list[str]) -> dict[str, Any]:
    """Complete multiple tasks and propagate unblocks."""
    storage = _get_storage()
    updated = []

    for id in ids:
        task = storage.get_task(id)
        if task:
            task.status = TaskStatus.DONE
            storage.save_task(task)
            updated.append(task)

    _propagate_completion(ids)

    return {"success": True, "tasks": [_task_to_dict(t) for t in updated]}


if __name__ == "__main__":
    mcp.run()
