#!/usr/bin/env python3
"""Task CLI - Command line interface for tasks-v2.

Provides command-line access to the task storage system.
Mirrors core bd functionality but for markdown-first tasks.

Usage:
    task list [--status STATUS] [--project PROJECT]
    task create TITLE [--project PROJECT] [--type TYPE]
    task show TASK_ID
    task complete TASK_ID
    task ready CALLER [--project PROJECT]
"""

import fcntl
import sys
from pathlib import Path

import click

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from lib.task_model import TaskStatus, TaskType  # noqa: E402
from lib.task_storage import TaskStorage  # noqa: E402


def get_storage() -> TaskStorage:
    """Get task storage instance."""
    return TaskStorage()


@click.group()
def main():
    """Task management CLI."""
    pass


@main.command()
@click.option("--status", "-s", help="Filter by status (inbox, active, done, etc.)")
@click.option("--project", "-p", help="Filter by project")
@click.option("--type", "-t", "task_type", help="Filter by type (goal, project, task, action)")
def list(status: str | None, project: str | None, task_type: str | None):
    """List tasks with optional filters."""
    storage = get_storage()

    # Convert string filters to enums
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            click.echo(f"Invalid status: {status}", err=True)
            click.echo(f"Valid values: {', '.join(s.value for s in TaskStatus)}", err=True)
            raise SystemExit(1)

    type_filter = None
    if task_type:
        try:
            type_filter = TaskType(task_type)
        except ValueError:
            click.echo(f"Invalid type: {task_type}", err=True)
            click.echo(f"Valid values: {', '.join(t.value for t in TaskType)}", err=True)
            raise SystemExit(1)

    tasks = storage.list_tasks(project=project, status=status_filter, type=type_filter)

    if not tasks:
        click.echo("No tasks found.")
        return

    # Simple table output
    for task in tasks:
        status_str = task.status.value[:4].upper()
        project_str = f"[{task.project}]" if task.project else "[inbox]"
        click.echo(f"{task.id}  {status_str}  {project_str}  {task.title}")


@main.command()
@click.argument("title")
@click.option("--project", "-p", help="Assign to project")
@click.option("--type", "-t", "task_type", default="task", help="Task type (goal, project, task, action)")
@click.option("--parent", help="Parent task ID for hierarchy")
@click.option("--priority", type=int, default=2, help="Priority 0-4 (0=critical, 4=someday)")
def create(title: str, project: str | None, task_type: str, parent: str | None, priority: int):
    """Create a new task."""
    storage = get_storage()

    try:
        type_enum = TaskType(task_type)
    except ValueError:
        click.echo(f"Invalid type: {task_type}", err=True)
        click.echo(f"Valid values: {', '.join(t.value for t in TaskType)}", err=True)
        raise SystemExit(1)

    task = storage.create_task(
        title=title,
        project=project,
        type=type_enum,
        parent=parent,
        priority=priority,
    )

    path = storage.save_task(task)
    click.echo(f"{task.id}")
    click.echo(f"Created: {path}")


@main.command()
@click.argument("task_id")
def show(task_id: str):
    """Show task details."""
    storage = get_storage()

    task = storage.get_task(task_id)
    if task is None:
        click.echo(f"Task not found: {task_id}", err=True)
        raise SystemExit(1)

    # Display task details
    click.echo(f"ID:       {task.id}")
    click.echo(f"Title:    {task.title}")
    click.echo(f"Type:     {task.type.value}")
    click.echo(f"Status:   {task.status.value}")
    click.echo(f"Priority: P{task.priority}")
    if task.project:
        click.echo(f"Project:  {task.project}")
    if task.parent:
        click.echo(f"Parent:   {task.parent}")
    if task.depends_on:
        click.echo(f"Depends:  {', '.join(task.depends_on)}")
    if task.tags:
        click.echo(f"Tags:     {', '.join(task.tags)}")
    if task.due:
        click.echo(f"Due:      {task.due.isoformat()}")
    click.echo(f"Created:  {task.created.isoformat()}")
    click.echo(f"Modified: {task.modified.isoformat()}")
    if task.body:
        click.echo()
        click.echo(task.body)


@main.command()
@click.argument("task_id")
def complete(task_id: str):
    """Mark a task as completed."""
    storage = get_storage()

    task = storage.get_task(task_id)
    if task is None:
        click.echo(f"Task not found: {task_id}", err=True)
        raise SystemExit(1)

    task.status = TaskStatus.DONE
    storage.save_task(task)
    click.echo(f"Completed: {task_id}")


@main.command()
@click.argument("task_id")
@click.option("--status", "-s", help="New status")
@click.option("--title", "-t", help="New title")
@click.option("--priority", "-P", type=int, help="New priority (0-4)")
@click.option("--project", "-p", help="Move to project")
def update(task_id: str, status: str | None, title: str | None, priority: int | None, project: str | None):
    """Update a task."""
    storage = get_storage()

    task = storage.get_task(task_id)
    if task is None:
        click.echo(f"Task not found: {task_id}", err=True)
        raise SystemExit(1)

    if status:
        try:
            task.status = TaskStatus(status)
        except ValueError:
            click.echo(f"Invalid status: {status}", err=True)
            raise SystemExit(1)

    if title:
        task.title = title

    if priority is not None:
        task.priority = priority

    if project is not None:
        task.project = project if project else None

    storage.save_task(task)
    click.echo(f"Updated: {task_id}")


@main.command()
@click.argument("caller")
@click.option("--project", "-p", default="", help="Filter by project (empty for all)")
def ready(caller: str, project: str):
    """Get next ready task and claim it atomically.

    Finds one ready task (leaf + no blockers), claims it by setting
    status to "active" and assignee to CALLER. Uses file locking to
    prevent race conditions.

    CALLER is who is claiming the task - typically 'nic' or 'bot'.

    Mirrors MCP claim_next_task behavior exactly.
    """
    storage = get_storage()
    tasks = storage.get_ready_tasks(project=project or None)

    if not tasks:
        click.echo("No ready tasks available" + (f" in project {project}" if project else ""))
        return

    # Try to claim tasks in priority order
    for task in tasks:
        task_path = storage._find_task_path(task.id)
        if task_path is None:
            continue

        lock_path = task_path.with_suffix(".lock")

        try:
            with open(lock_path, "w") as lock_file:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue  # Another process has lock, try next

                try:
                    # Re-load task to check still claimable
                    fresh_task = storage.get_task(task.id)
                    if fresh_task is None:
                        continue

                    if fresh_task.status not in (TaskStatus.INBOX, TaskStatus.ACTIVE):
                        continue
                    if fresh_task.assignee and fresh_task.assignee != caller:
                        continue

                    # Claim it
                    fresh_task.status = TaskStatus.ACTIVE
                    fresh_task.assignee = caller
                    storage.save_task(fresh_task)

                    project_str = f"[{fresh_task.project}]" if fresh_task.project else "[inbox]"
                    click.echo(f"{fresh_task.id}")
                    click.echo(f"P{fresh_task.priority}  {project_str}  {fresh_task.title}")
                    return

                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

        except Exception as e:
            click.echo(f"Warning: Failed to claim {task.id}: {e}", err=True)
            continue
        finally:
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass

    click.echo("No tasks available to claim (all locked or already assigned)")


if __name__ == "__main__":
    main()
