#!/usr/bin/env python3
"""Task CLI v2: Command-line interface for hierarchical task management.

Implements CLI commands per specs/tasks-v2.md Section 7.1:
- Core: add, show, done, edit
- Graph queries: ready, blocked, tree, deps
- Decomposition: decompose, reorder
- Index: index rebuild, index stats

Usage:
    task add "Write a book" --type=goal --project=book
    task show 20260112-write-book
    task ready --project=book
    task tree 20260112-write-book
    task done 20260112-outline-chapter
    task index rebuild
"""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import click

from lib.task_index import TaskIndex
from lib.task_model import Task, TaskStatus, TaskType
from lib.task_storage import TaskStorage

if TYPE_CHECKING:
    from lib.task_index import TaskIndexEntry


def get_storage() -> TaskStorage:
    """Get TaskStorage instance.

    Returns:
        TaskStorage connected to $ACA_DATA
    """
    return TaskStorage()


def get_index() -> TaskIndex:
    """Get TaskIndex instance with loaded data.

    Returns:
        TaskIndex with data loaded from index.json
    """
    index = TaskIndex()
    if not index.load():
        click.echo("Index not found or outdated. Run: task index rebuild", err=True)
        index.rebuild()
    return index


def format_task_line(
    task: Task | TaskIndexEntry,
    *,
    show_status: bool = True,
    show_type: bool = True,
    indent: int = 0,
) -> str:
    """Format task as single line for display.

    Args:
        task: Task or TaskIndexEntry to format
        show_status: Include status indicator
        show_type: Include type label
        indent: Number of spaces to indent

    Returns:
        Formatted task line
    """
    # Handle both Task and TaskIndexEntry
    status = task.status.value if isinstance(task.status, TaskStatus) else task.status
    task_type = task.type.value if isinstance(task.type, TaskType) else task.type

    # Status indicator
    status_char = {
        "inbox": " ",
        "active": "*",
        "blocked": "!",
        "waiting": "?",
        "done": "x",
        "cancelled": "-",
    }.get(status, " ")

    parts = []

    # Checkbox style
    checkbox = f"[{status_char}]"
    parts.append(checkbox)

    # Title
    parts.append(task.title)

    # Type label
    if show_type:
        parts.append(f"[{task_type}]")

    # Status label (if blocked or waiting)
    if show_status and status in ("blocked", "waiting"):
        parts.append(f"[{status}]")

    line = " ".join(parts)
    return " " * indent + line


def format_tree(
    task_id: str,
    index: TaskIndex,
    *,
    indent: int = 0,
    prefix: str = "",
    is_last: bool = True,
) -> list[str]:
    """Format task tree recursively.

    Args:
        task_id: Root task ID
        index: TaskIndex for lookups
        indent: Current indentation level
        prefix: Tree branch prefix
        is_last: Whether this is last sibling

    Returns:
        List of formatted lines
    """
    entry = index.get_task(task_id)
    if not entry:
        return []

    lines = []

    # Build connector
    if indent == 0:
        connector = ""
    elif is_last:
        connector = prefix + "\\-- "
    else:
        connector = prefix + "|-- "

    # Format this task
    status_char = {
        "inbox": " ",
        "active": "*",
        "blocked": "!",
        "waiting": "?",
        "done": "x",
        "cancelled": "-",
    }.get(entry.status, " ")

    line = f"{connector}[{status_char}] {entry.title} [{entry.type}]"
    if entry.depends_on:
        line += " [blocked]"
    lines.append(line)

    # Recurse to children
    children = index.get_children(task_id)
    for i, child in enumerate(children):
        is_last_child = i == len(children) - 1
        if indent == 0:
            child_prefix = ""
        elif is_last:
            child_prefix = prefix + "    "
        else:
            child_prefix = prefix + "|   "

        child_lines = format_tree(
            child.id,
            index,
            indent=indent + 1,
            prefix=child_prefix,
            is_last=is_last_child,
        )
        lines.extend(child_lines)

    return lines


# CLI Group


@click.group()
@click.version_option(version="2.0.0", prog_name="task")
def cli() -> None:
    """Task v2: Hierarchical task management CLI.

    Manages tasks with graph relationships for hierarchical decomposition.
    Tasks are markdown files with YAML frontmatter stored in project directories.
    """
    pass


# Core Commands


@cli.command()
@click.argument("title")
@click.option(
    "--type",
    "task_type",
    type=click.Choice(["goal", "project", "task", "action"]),
    default="task",
    help="Task type (goal, project, task, action)",
)
@click.option("--project", "-p", help="Project slug for task grouping")
@click.option("--parent", help="Parent task ID for hierarchy")
@click.option("--depends-on", "-d", multiple=True, help="Dependency task IDs")
@click.option("--priority", type=int, default=2, help="Priority 0-4 (0=critical)")
@click.option("--tags", "-t", multiple=True, help="Tags for the task")
def add(
    title: str,
    task_type: str,
    project: str | None,
    parent: str | None,
    depends_on: tuple[str, ...],
    priority: int,
    tags: tuple[str, ...],
) -> None:
    """Add a new task.

    Creates a task file with the given title and options.
    Auto-generates ID from date and slugified title.

    Examples:
        task add "Write a book" --type=goal --project=book
        task add "Outline chapter 1" --parent=20260112-write-book
        task add "Research topic" -d 20260112-outline -p book
    """
    storage = get_storage()

    # Convert type string to enum
    type_enum = TaskType(task_type)

    # Create task
    task = storage.create_task(
        title=title,
        project=project,
        type=type_enum,
        parent=parent,
        depends_on=list(depends_on) if depends_on else None,
        priority=priority,
        tags=list(tags) if tags else None,
    )

    # Save task
    path = storage.save_task(task)

    click.echo(f"Created: {task.id}")
    click.echo(f"  Title:   {task.title}")
    click.echo(f"  Type:    {task.type.value}")
    click.echo(f"  Project: {task.project or 'inbox'}")
    click.echo(f"  Path:    {path}")


@cli.command()
@click.argument("task_id")
def show(task_id: str) -> None:
    """Show task details with children.

    Displays task metadata and hierarchical children tree.

    Examples:
        task show 20260112-write-book
    """
    index = get_index()
    storage = get_storage()

    # Load full task from file
    task = storage.get_task(task_id)
    if not task:
        click.echo(f"Task not found: {task_id}", err=True)
        sys.exit(1)

    # Header
    click.echo(f"\n{task.title} [{task.type.value}] [{task.status.value}]")
    click.echo("=" * 60)

    # Metadata
    click.echo(f"ID:       {task.id}")
    click.echo(f"Project:  {task.project or 'inbox'}")
    click.echo(f"Priority: {task.priority}")
    click.echo(f"Depth:    {task.depth}")
    click.echo(f"Leaf:     {task.leaf}")

    if task.parent:
        click.echo(f"Parent:   {task.parent}")

    if task.depends_on:
        click.echo(f"Depends:  {', '.join(task.depends_on)}")

    if task.due:
        click.echo(f"Due:      {task.due.isoformat()}")

    if task.tags:
        click.echo(f"Tags:     {', '.join(task.tags)}")

    if task.context:
        click.echo(f"Context:  {task.context}")

    # Children tree
    entry = index.get_task(task_id)
    if entry and entry.children:
        click.echo("\nChildren:")
        children = index.get_children(task_id)
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "\\--" if is_last else "|--"
            click.echo(f"  {connector} {format_task_line(child, indent=0)}")

        # Progress
        total = len(children)
        done = sum(1 for c in children if c.status in ("done", "cancelled"))
        click.echo(f"\nProgress: {done}/{total} complete")

    # Body content
    if task.body.strip():
        click.echo("\n---")
        # Skip title if it's just the H1
        body = task.body.strip()
        if body.startswith(f"# {task.title}"):
            body = body[len(f"# {task.title}") :].strip()
        if body:
            click.echo(body[:500])  # Truncate long bodies
            if len(task.body) > 500:
                click.echo("...")


@cli.command()
@click.argument("task_ids", nargs=-1, required=True)
def done(task_ids: tuple[str, ...]) -> None:
    """Mark tasks as done.

    Completes one or more tasks by ID.

    Examples:
        task done 20260112-outline-chapter
        task done 20260112-task1 20260112-task2 20260112-task3
    """
    storage = get_storage()

    for task_id in task_ids:
        task = storage.get_task(task_id)
        if not task:
            click.echo(f"Task not found: {task_id}", err=True)
            continue

        task.complete()
        storage.save_task(task)
        click.echo(f"Completed: {task_id} - {task.title}")


@cli.command()
@click.argument("task_id")
def edit(task_id: str) -> None:
    """Open task file in $EDITOR.

    Opens the task markdown file for editing.

    Examples:
        task edit 20260112-write-book
    """
    import os

    storage = get_storage()
    path = storage._find_task_path(task_id)

    if not path:
        click.echo(f"Task not found: {task_id}", err=True)
        sys.exit(1)

    editor = os.environ.get("EDITOR", "vim")

    try:
        subprocess.run([editor, str(path)], check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Editor exited with error: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo(f"Editor not found: {editor}", err=True)
        sys.exit(1)


# Graph Query Commands


@cli.command()
@click.option("--project", "-p", help="Filter by project")
@click.option("--limit", "-n", type=int, default=20, help="Max tasks to show")
def ready(project: str | None, limit: int) -> None:
    """List actionable tasks.

    Shows leaf tasks with no unmet dependencies.

    Examples:
        task ready
        task ready --project=book
        task ready -n 10
    """
    index = get_index()
    tasks = index.get_ready_tasks(project=project)

    if not tasks:
        click.echo("No ready tasks found.")
        return

    click.echo(f"\nReady Tasks ({len(tasks)} total):")
    click.echo("-" * 40)

    for task in tasks[:limit]:
        line = format_task_line(task, show_status=False)
        project_label = f"[{task.project}]" if task.project else "[inbox]"
        click.echo(f"{line} {project_label}")

    if len(tasks) > limit:
        click.echo(f"\n... and {len(tasks) - limit} more")


@cli.command()
def blocked() -> None:
    """List blocked tasks.

    Shows tasks with unmet dependencies.

    Examples:
        task blocked
    """
    index = get_index()
    tasks = index.get_blocked_tasks()

    if not tasks:
        click.echo("No blocked tasks found.")
        return

    click.echo(f"\nBlocked Tasks ({len(tasks)} total):")
    click.echo("-" * 40)

    for task in tasks:
        # Show what it's blocked by
        deps = index.get_dependencies(task.id)
        unmet = [d for d in deps if d.status not in ("done", "cancelled")]

        line = format_task_line(task, show_status=False)
        if unmet:
            blockers = ", ".join(d.title[:20] for d in unmet[:3])
            if len(unmet) > 3:
                blockers += f", +{len(unmet) - 3} more"
            click.echo(f"{line}")
            click.echo(f"    blocked by: {blockers}")
        else:
            click.echo(f"{line}")


@cli.command()
@click.argument("task_id")
def tree(task_id: str) -> None:
    """Show decomposition tree.

    Displays hierarchical tree of task and all descendants.

    Examples:
        task tree 20260112-write-book
    """
    index = get_index()

    if not index.get_task(task_id):
        click.echo(f"Task not found: {task_id}", err=True)
        sys.exit(1)

    lines = format_tree(task_id, index)
    for line in lines:
        click.echo(line)

    # Summary
    descendants = index.get_descendants(task_id)
    total = len(descendants) + 1  # Include root
    done_count = sum(1 for d in descendants if d.status in ("done", "cancelled"))
    root = index.get_task(task_id)
    if root and root.status in ("done", "cancelled"):
        done_count += 1

    click.echo(f"\nTotal: {total} tasks, {done_count} complete")


@cli.command()
@click.argument("task_id")
def deps(task_id: str) -> None:
    """Show dependency graph.

    Displays what this task depends on and what depends on it.

    Examples:
        task deps 20260112-write-draft
    """
    index = get_index()

    entry = index.get_task(task_id)
    if not entry:
        click.echo(f"Task not found: {task_id}", err=True)
        sys.exit(1)

    click.echo(f"\n{entry.title}")
    click.echo("=" * 40)

    # Dependencies (what this depends on)
    dependencies = index.get_dependencies(task_id)
    if dependencies:
        click.echo("\nDepends on:")
        for dep in dependencies:
            status = "[done]" if dep.status in ("done", "cancelled") else "[pending]"
            click.echo(f"  <- {dep.title} {status}")
    else:
        click.echo("\nDepends on: (none)")

    # Dependents (what depends on this)
    dependents = index.get_dependents(task_id)
    if dependents:
        click.echo("\nBlocks:")
        for dep in dependents:
            status = "[done]" if dep.status in ("done", "cancelled") else "[waiting]"
            click.echo(f"  -> {dep.title} {status}")
    else:
        click.echo("\nBlocks: (none)")


# Decomposition Commands


@cli.command()
@click.argument("task_id")
@click.option("--title", "-t", multiple=True, help="Child task titles")
@click.option(
    "--type",
    "child_type",
    type=click.Choice(["goal", "project", "task", "action"]),
    default="action",
    help="Type for child tasks",
)
@click.option("--sequential", "-s", is_flag=True, help="Add dependencies between children")
def decompose(
    task_id: str,
    title: tuple[str, ...],
    child_type: str,
    sequential: bool,
) -> None:
    """Decompose task into children.

    Creates child tasks under the parent task.
    Use --sequential to add dependencies between children.

    Examples:
        task decompose 20260112-write-ch1 -t "Outline" -t "Draft" -t "Revise"
        task decompose 20260112-write-ch1 -t "Outline" -t "Draft" --sequential
    """
    storage = get_storage()

    parent = storage.get_task(task_id)
    if not parent:
        click.echo(f"Task not found: {task_id}", err=True)
        sys.exit(1)

    if not title:
        click.echo("No child titles provided. Use -t to add children.", err=True)
        sys.exit(1)

    # Build children definitions
    children_defs: list[dict] = []
    created_ids: list[str] = []

    for i, child_title in enumerate(title):
        child_def: dict = {
            "title": child_title,
            "type": child_type,
            "order": i,
        }

        # Add sequential dependencies
        if sequential and created_ids:
            child_def["depends_on"] = [created_ids[-1]]

        children_defs.append(child_def)

        # Generate ID for next iteration's dependency
        child_id = Task.generate_id(child_title)
        created_ids.append(child_id)

    # Create children
    children = storage.decompose_task(task_id, children_defs)

    click.echo(f"\nDecomposed: {parent.title}")
    click.echo("-" * 40)

    for child in children:
        dep_info = ""
        if child.depends_on:
            dep_info = f" (depends on: {child.depends_on[0][:20]}...)"
        click.echo(f"  [{child.order}] {child.title} [{child.type.value}]{dep_info}")


@cli.command()
@click.argument("task_id")
@click.argument("child_ids", nargs=-1)
def reorder(task_id: str, child_ids: tuple[str, ...]) -> None:
    """Reorder children of a task.

    Specify child IDs in desired order.

    Examples:
        task reorder 20260112-parent 20260112-child2 20260112-child1 20260112-child3
    """
    storage = get_storage()
    index = get_index()

    parent = index.get_task(task_id)
    if not parent:
        click.echo(f"Task not found: {task_id}", err=True)
        sys.exit(1)

    if not child_ids:
        click.echo("No child IDs provided.", err=True)
        sys.exit(1)

    # Verify all children belong to parent
    current_children = {c.id for c in index.get_children(task_id)}
    for child_id in child_ids:
        if child_id not in current_children:
            click.echo(f"Not a child of {task_id}: {child_id}", err=True)
            sys.exit(1)

    # Update order
    for new_order, child_id in enumerate(child_ids):
        task = storage.get_task(child_id)
        if task:
            task.order = new_order
            storage.save_task(task)
            click.echo(f"  [{new_order}] {task.title}")

    click.echo(f"\nReordered {len(child_ids)} children")


# Index Commands


@cli.group()
def index() -> None:
    """Index management commands."""
    pass


@index.command("rebuild")
def index_rebuild() -> None:
    """Rebuild task index from files.

    Scans all project directories for task files and rebuilds index.json.

    Examples:
        task index rebuild
    """
    click.echo("Rebuilding task index...")

    task_index = TaskIndex()
    task_index.rebuild()

    stats = task_index.stats()
    click.echo("\nIndex rebuilt successfully:")
    click.echo(f"  Total tasks:  {stats['total']}")
    click.echo(f"  Ready:        {stats['ready']}")
    click.echo(f"  Blocked:      {stats['blocked']}")
    click.echo(f"  Roots:        {stats['roots']}")
    click.echo(f"  Projects:     {stats['projects']}")
    click.echo(f"  Index path:   {task_index.index_path}")


@index.command("stats")
def index_stats() -> None:
    """Show index statistics.

    Displays task counts by status and type.

    Examples:
        task index stats
    """
    task_index = get_index()
    stats = task_index.stats()

    click.echo("\nTask Index Statistics")
    click.echo("=" * 40)
    click.echo(f"Generated: {stats['generated']}")
    click.echo(f"Version:   {stats['version']}")
    click.echo()

    click.echo("Counts:")
    click.echo(f"  Total:    {stats['total']}")
    click.echo(f"  Ready:    {stats['ready']}")
    click.echo(f"  Blocked:  {stats['blocked']}")
    click.echo(f"  Roots:    {stats['roots']}")
    click.echo(f"  Projects: {stats['projects']}")

    if stats.get("by_status"):
        click.echo("\nBy Status:")
        for status, count in sorted(stats["by_status"].items()):
            click.echo(f"  {status}: {count}")

    if stats.get("by_type"):
        click.echo("\nBy Type:")
        for task_type, count in sorted(stats["by_type"].items()):
            click.echo(f"  {task_type}: {count}")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
