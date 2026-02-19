#!/usr/bin/env python3
"""Task CLI - Command line interface for tasks-v2.

Provides command-line access to the task storage system with rich TUI formatting.
Includes hierarchical tree view and colorized status display.

Usage:
    task list [--status STATUS] [--project PROJECT]
    task tree [--project PROJECT] [--all]
    task create TITLE [--project PROJECT] [--type TYPE]
    task show TASK_ID
    task complete TASK_ID
    task ready CALLER [--project PROJECT]
"""

import fcntl
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from lib.task_index import TaskIndex, TaskIndexEntry  # noqa: E402
from lib.task_model import TaskStatus, TaskType  # noqa: E402
from lib.task_storage import TaskStorage  # noqa: E402

console = Console()

# Status icons and colors
STATUS_STYLE = {
    "inbox": ("📥", "dim"),
    "active": ("▶", "green bold"),
    "blocked": ("🔒", "red"),
    "waiting": ("⏳", "yellow"),
    "done": ("✓", "dim strike"),
    "cancelled": ("✗", "dim strike"),
}

# Type icons
TYPE_ICON = {
    "goal": "🎯",
    "project": "📁",
    "epic": "📌",
    "task": "📋",
    "action": "⚡",
    "bug": "🐛",
    "feature": "✨",
    "learn": "📖",
}

# Priority styling
PRIORITY_STYLE = {
    0: ("P0", "red bold"),  # Critical
    1: ("P1", "yellow bold"),  # High
    2: ("P2", "white"),  # Normal
    3: ("P3", "dim"),  # Low
    4: ("P4", "dim italic"),  # Someday
}


def get_storage() -> TaskStorage:
    """Get task storage instance."""
    return TaskStorage()


def get_index() -> TaskIndex:
    """Get task index instance, always rebuilding for freshness."""
    index = TaskIndex()
    # Always rebuild - fast-indexer is quick enough
    if not index.rebuild_fast():
        index.rebuild()
    return index


def format_status(status: str) -> Text:
    """Format status with icon and color."""
    icon, style = STATUS_STYLE.get(status, ("?", "white"))
    return Text(f"{icon} {status}", style=style)


def format_priority(priority: int) -> Text:
    """Format priority with color."""
    label, style = PRIORITY_STYLE.get(priority, ("P?", "white"))
    return Text(label, style=style)


def format_type(task_type: str) -> str:
    """Format type with icon."""
    icon = TYPE_ICON.get(task_type, "•")
    return f"{icon}"


def build_task_tree(
    index: TaskIndex,
    entry: TaskIndexEntry,
    tree: Tree,
    show_done: bool = False,
) -> None:
    """Recursively build tree structure for a task and its children."""
    children = index.get_children(entry.id)

    # Sort by status (active first), then priority, then order
    status_order = {
        "active": 0,
        "inbox": 1,
        "waiting": 2,
        "blocked": 3,
        "done": 4,
        "cancelled": 5,
    }
    children.sort(key=lambda e: (status_order.get(e.status, 9), e.priority, e.order))

    for child in children:
        # Skip done/cancelled unless showing all
        if not show_done and child.status in ("done", "cancelled"):
            continue

        # Build child label
        icon, style = STATUS_STYLE.get(child.status, ("•", "white"))
        type_icon = TYPE_ICON.get(child.type, "•")
        pri_label, pri_style = PRIORITY_STYLE.get(child.priority, ("P?", "white"))

        label = Text()
        label.append(f"[{child.id}] ", style="dim")
        label.append(f"{icon} ", style=style)
        label.append(f"{type_icon} ", style="dim")
        label.append(
            child.title,
            style=style if child.status in ("done", "cancelled") else "white",
        )
        label.append("  ", style="dim")
        label.append(pri_label, style=pri_style)

        if child.assignee:
            label.append(f"  @{child.assignee}", style="cyan dim")

        # Create subtree
        subtree = tree.add(label)

        # Recurse for children
        build_task_tree(index, child, subtree, show_done)


@click.group()
def main():
    """Task management CLI with rich TUI formatting."""
    pass


@main.command(name="list")
@click.option("--status", "-s", help="Filter by status (inbox, active, done, etc.)")
@click.option("--project", "-p", help="Filter by project")
@click.option("--type", "-t", "task_type", help="Filter by type (goal, project, task, action)")
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    help="Show all tasks (including done/cancelled)",
)
@click.option("--plain", is_flag=True, help="Plain output without formatting")
def list_tasks(
    status: str | None,
    project: str | None,
    task_type: str | None,
    show_all: bool,
    plain: bool,
):
    """List tasks with optional filters.

    By default, hides done and cancelled tasks. Use --all to show them.
    """
    storage = get_storage()

    # Convert string filters to enums
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError as e:
            console.print(f"[red]Invalid status: {status}[/red]")
            console.print(f"Valid values: {', '.join(s.value for s in TaskStatus)}")
            raise SystemExit(1) from e

    type_filter = None
    if task_type:
        try:
            type_filter = TaskType(task_type)
        except ValueError as e:
            console.print(f"[red]Invalid type: {task_type}[/red]")
            console.print(f"Valid values: {', '.join(t.value for t in TaskType)}")
            raise SystemExit(1) from e

    tasks = storage.list_tasks(project=project, status=status_filter, type=type_filter)

    # Filter out done/cancelled unless showing all or specifically asked for that status
    if not show_all and not status:
        tasks = [t for t in tasks if t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)]

    if not tasks:
        console.print("[dim]No tasks found.[/dim]")
        return

    if plain:
        # Plain output for scripting
        for task in tasks:
            status_str = task.status.value[:4].upper()
            project_str = f"[{task.project}]" if task.project else "[inbox]"
            click.echo(f"{task.id}  {status_str}  {project_str}  {task.title}")
        return

    # Rich table output
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("", width=2)  # Status icon
    table.add_column("", width=2)  # Type icon
    table.add_column("Pri", width=3)
    table.add_column("Project", style="cyan", width=12)
    table.add_column("Title")

    for task in tasks:
        icon, style = STATUS_STYLE.get(task.status.value, ("?", "white"))
        type_icon = TYPE_ICON.get(task.type.value, "•")
        pri_label, pri_style = PRIORITY_STYLE.get(task.priority, ("P?", "white"))

        title_style = style if task.status.value in ("done", "cancelled") else "white"

        table.add_row(
            task.id,
            Text(icon, style=style),
            Text(type_icon, style="dim"),
            Text(pri_label, style=pri_style),
            task.project or "inbox",
            Text(task.title, style=title_style),
        )

    console.print(table)
    console.print(f"\n[dim]{len(tasks)} task(s)[/dim]")


@main.command()
@click.option("--project", "-p", help="Filter by project")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show completed tasks too")
@click.option("--roots-only", "-r", is_flag=True, help="Only show root-level tasks (no full tree)")
@click.option(
    "--goals", "-g", is_flag=True, help="Show full goal-rooted tree instead of project level"
)
def tree(project: str | None, show_all: bool, roots_only: bool, goals: bool):
    """Show tasks in hierarchical tree view.

    Displays the task hierarchy with visual tree structure.
    By default hides completed tasks - use --all to show them.
    """
    index = get_index()

    # Get display roots: default to top-level projects, --goals shows goal-rooted tree
    if goals:
        roots = index.get_roots()
    else:
        # Show projects whose parent is null or a root-level goal (no parent)
        root_goal_ids = {
            t.id for t in index._tasks.values() if t.type == "goal" and t.parent is None
        }
        roots = [
            t
            for t in index._tasks.values()
            if t.type == "project" and (t.parent is None or t.parent in root_goal_ids)
        ]

    # Filter by project if specified
    if project:
        roots = [r for r in roots if r.project == project]

    # Filter out done/cancelled roots unless showing all
    if not show_all:
        roots = [r for r in roots if r.status not in ("done", "cancelled")]

    if not roots:
        console.print("[dim]No tasks found.[/dim]")
        return

    # Sort roots by project, then priority, then order
    roots.sort(key=lambda e: (e.project or "", e.priority, e.order))

    # Group by project
    current_project = None

    for root in roots:
        # Print project header if changed
        if root.project != current_project:
            current_project = root.project
            proj_name = current_project or "inbox"
            console.print()
            console.print(f"[bold cyan]═══ {proj_name} ═══[/bold cyan]")

        # Build root label
        icon, style = STATUS_STYLE.get(root.status, ("•", "white"))
        type_icon = TYPE_ICON.get(root.type, "•")
        pri_label, pri_style = PRIORITY_STYLE.get(root.priority, ("P?", "white"))

        label = Text()
        label.append(f"[{root.id}] ", style="dim")
        label.append(f"{icon} ", style=style)
        label.append(f"{type_icon} ", style="dim")
        label.append(root.title, style="bold" if root.type in ("goal", "project") else "white")
        label.append("  ", style="dim")
        label.append(pri_label, style=pri_style)

        if root.assignee:
            label.append(f"  @{root.assignee}", style="cyan dim")

        if roots_only:
            # Just print the root without tree structure
            console.print(f"  {label}")
        else:
            # Create tree and add children
            tree_view = Tree(label)
            build_task_tree(index, root, tree_view, show_done=show_all)
            console.print(tree_view)

    # Print summary
    stats = index.stats()
    console.print()
    console.print(
        f"[dim]{stats['total']} total · {stats['ready']} ready · {stats['blocked']} blocked[/dim]"
    )


@main.command()
@click.argument("title")
@click.option("--project", "-p", help="Assign to project")
@click.option(
    "--type",
    "-t",
    "task_type",
    default="task",
    help="Task type (goal, project, epic, task, action)",
)
@click.option("--parent", help="Parent task ID for hierarchy")
@click.option("--priority", type=int, default=2, help="Priority 0-4 (0=critical, 4=someday)")
@click.option("--assignee", "-a", help="Assign to actor (human/agent)")
@click.option("--complexity", "-c", help="Task complexity")
@click.option("--tags", help="Comma-separated tags")
@click.option("--body", help="Markdown body content")
@click.option("--depends-on", help="Comma-separated dependency IDs")
@click.option("--soft-depends-on", help="Comma-separated soft dependency IDs")
def create(
    title: str,
    project: str | None,
    task_type: str,
    parent: str | None,
    priority: int,
    assignee: str | None,
    complexity: str | None,
    tags: str | None,
    body: str | None,
    depends_on: str | None,
    soft_depends_on: str | None,
):
    """Create a new task."""
    storage = get_storage()

    try:
        type_enum = TaskType(task_type)
    except ValueError as e:
        console.print(f"[red]Invalid type: {task_type}[/red]")
        console.print(f"Valid values: {', '.join(t.value for t in TaskType)}")
        raise SystemExit(1) from e

    # Parse complexity
    task_complexity = None
    if complexity:
        try:
            from lib.task_model import TaskComplexity

            task_complexity = TaskComplexity(complexity)
        except ValueError as e:
            console.print(f"[red]Invalid complexity: {complexity}[/red]")
            raise SystemExit(1) from e

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Parse dependencies
    dep_list = [d.strip() for d in depends_on.split(",")] if depends_on else []
    soft_dep_list = [d.strip() for d in soft_depends_on.split(",")] if soft_depends_on else []

    # P#62: Inherit project from parent if not explicitly specified
    effective_project = project
    if parent and not project:
        parent_task = storage.get_task(parent)
        if parent_task and parent_task.project:
            effective_project = parent_task.project

    task = storage.create_task(
        title=title,
        project=effective_project,
        type=type_enum,
        parent=parent,
        priority=priority,
        assignee=assignee,
        complexity=task_complexity,
        tags=tag_list,
        body=body or "",
        depends_on=dep_list,
        soft_depends_on=soft_dep_list,
    )

    path = storage.save_task(task)

    type_icon = TYPE_ICON.get(task_type, "•")
    console.print(f"[green]✓[/green] Created {type_icon} [bold]{task.title}[/bold]")
    console.print(f"  [dim]ID: {task.id}[/dim]")
    console.print(f"  [dim]Path: {path}[/dim]")


@main.command()
@click.argument("task_id")
def show(task_id: str):
    """Show task details."""
    storage = get_storage()
    index = get_index()

    task = storage.get_task(task_id)
    if task is None:
        console.print(f"[red]Task not found: {task_id}[/red]")
        raise SystemExit(1)

    # Header with status and type
    icon, style = STATUS_STYLE.get(task.status.value, ("?", "white"))
    type_icon = TYPE_ICON.get(task.type.value, "•")
    pri_label, pri_style = PRIORITY_STYLE.get(task.priority, ("P?", "white"))

    header = Text()
    header.append(f"{icon} ", style=style)
    header.append(f"{type_icon} ", style="dim")
    header.append(task.title, style="bold")

    console.print(Panel(header, border_style="dim"))

    # Details table
    details = Table(show_header=False, box=None, padding=(0, 2))
    details.add_column("Field", style="dim")
    details.add_column("Value")

    details.add_row("ID", task.id)
    details.add_row("Type", task.type.value)
    details.add_row("Status", Text(f"{icon} {task.status.value}", style=style))
    details.add_row("Priority", Text(pri_label, style=pri_style))
    details.add_row("Project", task.project or "[dim]inbox[/dim]")

    if task.parent:
        parent_entry = index.get_task(task.parent)
        parent_label = f"{task.parent}"
        if parent_entry:
            parent_label += f" ({parent_entry.title})"
        details.add_row("Parent", parent_label)

    if task.depends_on:
        details.add_row("Depends on", ", ".join(task.depends_on))

    if task.soft_depends_on:
        details.add_row("Soft depends on", ", ".join(task.soft_depends_on))

    if task.tags:
        details.add_row("Tags", ", ".join(task.tags))

    if task.assignee:
        details.add_row("Assignee", f"@{task.assignee}")

    if task.complexity:
        details.add_row("Complexity", task.complexity.value)

    if task.due:
        details.add_row("Due", task.due.isoformat())

    details.add_row("Created", task.created.strftime("%Y-%m-%d %H:%M"))
    details.add_row("Modified", task.modified.strftime("%Y-%m-%d %H:%M"))

    console.print(details)

    # Show children if any
    entry = index.get_task(task_id)
    if entry and entry.children:
        console.print()
        console.print("[bold]Children:[/bold]")
        children = index.get_children(task_id)
        for child in children:
            c_icon, c_style = STATUS_STYLE.get(child.status, ("•", "white"))
            console.print(f"  {c_icon} {child.title} [dim]({child.id})[/dim]", style=c_style)

    # Body content
    if task.body:
        console.print()
        console.print("[bold]Notes:[/bold]")
        console.print(task.body)


@main.command()
@click.argument("task_id")
def complete(task_id: str):
    """Mark a task as completed."""
    storage = get_storage()

    task = storage.get_task(task_id)
    if task is None:
        console.print(f"[red]Task not found: {task_id}[/red]")
        raise SystemExit(1)

    task.status = TaskStatus.DONE
    storage.save_task(task, update_body=False)
    console.print(f"[green]✓[/green] Completed: [strike]{task.title}[/strike]")


@main.command()
@click.argument("task_id")
@click.argument("titles", nargs=-1)
def decompose(task_id: str, titles: list[str]):
    """Decompose a task into subtasks."""
    storage = get_storage()

    if not titles:
        console.print("[red]Please provide at least one subtask title.[/red]")
        raise SystemExit(1)

    children = [{"title": t} for t in titles]
    try:
        created = storage.decompose_task(task_id, children)
        console.print(
            f"[green]✓[/green] Decomposed [bold]{task_id}[/bold] into {len(created)} subtasks:"
        )
        for child in created:
            console.print(f"  [dim]• {child.id}[/dim] {child.title}")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from e


@main.command()
@click.argument("task_id")
@click.option("--status", "-s", help="New status")
@click.option("--title", "-t", help="New title")
@click.option("--priority", "-P", type=int, help="New priority (0-4)")
@click.option("--project", "-p", help="Move to project")
@click.option("--assignee", "-a", help="New assignee")
@click.option("--complexity", "-c", help="New complexity")
@click.option("--parent", help="New parent ID")
@click.option("--tags", help="Comma-separated tags")
@click.option("--type", "task_type", help="New task type")
@click.option("--due", help="New due date (ISO)")
@click.option("--order", type=int, help="New sibling order")
@click.option("--depends-on", help="Comma-separated dependency IDs")
@click.option("--soft-depends-on", help="Comma-separated soft dependency IDs")
@click.option("--effort", help="New effort estimate")
@click.option("--context", help="New context")
@click.option("--body", help="New body content (append by default)")
@click.option("--replace-body", is_flag=True, help="Replace body instead of appending")
def update(
    task_id: str,
    status: str | None,
    title: str | None,
    priority: int | None,
    project: str | None,
    assignee: str | None,
    complexity: str | None,
    parent: str | None,
    tags: str | None,
    task_type: str | None,
    due: str | None,
    order: int | None,
    depends_on: str | None,
    soft_depends_on: str | None,
    effort: str | None,
    context: str | None,
    body: str | None,
    replace_body: bool,
):
    """Update a task."""
    storage = get_storage()

    task = storage.get_task(task_id)
    if task is None:
        console.print(f"[red]Task not found: {task_id}[/red]")
        raise SystemExit(1)

    changes = []

    if status:
        try:
            task.status = TaskStatus(status)
            changes.append(f"status → {status}")
        except ValueError as e:
            console.print(f"[red]Invalid status: {status}[/red]")
            raise SystemExit(1) from e

    if title:
        task.title = title
        changes.append(f"title → {title}")

    if priority is not None:
        task.priority = priority
        changes.append(f"priority → P{priority}")

    if project is not None:
        task.project = project if project else None
        changes.append(f"project → {project or 'inbox'}")

    if assignee is not None:
        task.assignee = assignee if assignee else None
        changes.append(f"assignee → {assignee or 'unassigned'}")

    if complexity is not None:
        if complexity == "":
            task.complexity = None
            changes.append("complexity → cleared")
        else:
            try:
                from lib.task_model import TaskComplexity

                task.complexity = TaskComplexity(complexity)
                changes.append(f"complexity → {complexity}")
            except ValueError as e:
                console.print(f"[red]Invalid complexity: {complexity}[/red]")
                raise SystemExit(1) from e

    if parent is not None:
        task.parent = parent if parent else None
        changes.append(f"parent → {parent or 'none'}")

    if tags is not None:
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        task.tags = tag_list
        changes.append(f"tags → {tags or 'none'}")

    if task_type is not None:
        try:
            task.type = TaskType(task_type)
            changes.append(f"type → {task_type}")
        except ValueError as e:
            console.print(f"[red]Invalid type: {task_type}[/red]")
            raise SystemExit(1) from e

    if due is not None:
        if due == "":
            task.due = None
            changes.append("due → cleared")
        else:
            try:
                from datetime import datetime

                task.due = datetime.fromisoformat(due.replace("Z", "+00:00"))
                changes.append(f"due → {due}")
            except ValueError as e:
                console.print(f"[red]Invalid due date format: {due}[/red]")
                raise SystemExit(1) from e

    if order is not None:
        task.order = order
        changes.append(f"order → {order}")

    if depends_on is not None:
        dep_list = [d.strip() for d in depends_on.split(",")] if depends_on else []
        task.depends_on = dep_list
        changes.append(f"depends_on → {depends_on or 'none'}")

    if soft_depends_on is not None:
        soft_dep_list = [d.strip() for d in soft_depends_on.split(",")] if soft_depends_on else []
        task.soft_depends_on = soft_dep_list
        changes.append(f"soft_depends_on → {soft_depends_on or 'none'}")

    if effort is not None:
        task.effort = effort if effort else None
        changes.append(f"effort → {effort or 'cleared'}")

    if context is not None:
        task.context = context if context else None
        changes.append(f"context → {context or 'cleared'}")

    if body is not None:
        if replace_body or not task.body:
            task.body = body
        else:
            task.body = task.body + "\n\n" + body
        changes.append("body updated")

    storage.save_task(task, update_body=True if body else False)

    console.print(f"[green]✓[/green] Updated [bold]{task.id}[/bold]")
    for change in changes:
        console.print(f"  [dim]{change}[/dim]")


@main.command()
@click.option("--project", "-p", default="", help="Filter by project (empty for all)")
@click.option(
    "--claim",
    "-c",
    "caller",
    default=None,
    help="Claim the highest-priority task as CALLER (e.g., 'human' or 'polecat')",
)
@click.option("--limit", "-n", default=20, help="Number of tasks to show (default: 20)")
def ready(project: str, caller: str | None, limit: int):
    """Show ready tasks ordered by priority, or claim one.

    Without --claim: Lists up to 20 ready tasks (leaf + no blockers)
    in priority order (P0 first) without claiming any.

    With --claim CALLER: Claims the highest-priority ready task by
    setting status to "in_progress" and assignee to CALLER. Uses file
    locking to prevent race conditions.

    Examples:
        task ready                      # List top 20 ready tasks
        task ready -n 10                # List top 10 ready tasks
        task ready --claim human        # Claim highest-priority task as 'human'
        task ready -p aops --claim polecat  # Claim from 'aops' project as 'polecat'
    """
    storage = get_storage()
    tasks = storage.get_ready_tasks(project=project or None)

    if not tasks:
        console.print(
            f"[dim]No ready tasks available{' in project ' + project if project else ''}[/dim]"
        )
        return

    # If not claiming, just list tasks
    if caller is None:
        # Show table of ready tasks
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("#", width=3, justify="right")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("", width=2)  # Type icon
        table.add_column("Pri", width=3)
        table.add_column("Project", style="cyan", width=12)
        table.add_column("Assignee", style="dim", width=8)
        table.add_column("Title")

        for i, task in enumerate(tasks[:limit], 1):
            type_icon = TYPE_ICON.get(task.type.value, "•")
            pri_label, pri_style = PRIORITY_STYLE.get(task.priority, ("P?", "white"))
            assignee = f"@{task.assignee}" if task.assignee else ""

            table.add_row(
                str(i),
                task.id,
                Text(type_icon, style="dim"),
                Text(pri_label, style=pri_style),
                task.project or "inbox",
                assignee,
                task.title,
            )

        console.print(table)
        console.print(
            f"\n[dim]{len(tasks)} ready task(s) total, showing top {min(limit, len(tasks))}[/dim]"
        )
        console.print("[dim]Use --claim CALLER to claim the highest-priority task[/dim]")
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

                    if fresh_task.status != TaskStatus.ACTIVE:
                        continue
                    if fresh_task.assignee and fresh_task.assignee != caller:
                        continue

                    # Claim it - set to in_progress
                    fresh_task.status = TaskStatus.IN_PROGRESS
                    fresh_task.assignee = caller
                    storage.save_task(fresh_task, update_body=False)

                    # Rich output
                    type_icon = TYPE_ICON.get(fresh_task.type.value, "•")
                    pri_label, pri_style = PRIORITY_STYLE.get(fresh_task.priority, ("P?", "white"))
                    proj = fresh_task.project or "inbox"

                    console.print(
                        f"[green]▶[/green] Claimed: {type_icon} [bold]{fresh_task.title}[/bold]"
                    )
                    console.print(f"  [dim]ID: {fresh_task.id}[/dim]")
                    console.print(f"  [cyan]{proj}[/cyan]  ", end="")
                    console.print(Text(pri_label, style=pri_style), end="")
                    console.print(f"  [dim]@{caller}[/dim]")
                    return

                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

        except Exception as e:
            console.print(f"[yellow]Warning: Failed to claim {task.id}: {e}[/yellow]")
            continue
        finally:
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass

    console.print("[dim]No tasks available to claim (all locked or already assigned)[/dim]")


@main.command()
def stats():
    """Show task statistics."""
    index = get_index()
    s = index.stats()

    console.print()
    console.print("[bold]Task Statistics[/bold]")
    console.print()

    # Summary
    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column("Metric", style="dim")
    summary.add_column("Count", justify="right")

    summary.add_row("Total tasks", str(s["total"]))
    summary.add_row("Ready", Text(str(s["ready"]), style="green"))
    summary.add_row("Blocked", Text(str(s["blocked"]), style="red"))
    summary.add_row("Root tasks", str(s["roots"]))
    summary.add_row("Projects", str(s["projects"]))

    console.print(summary)

    # By status
    console.print()
    console.print("[bold]By Status:[/bold]")
    for status, count in sorted(s["by_status"].items()):
        icon, style = STATUS_STYLE.get(status, ("•", "white"))
        console.print(f"  {icon} {status}: {count}", style=style)

    # By type
    console.print()
    console.print("[bold]By Type:[/bold]")
    for task_type, count in sorted(s["by_type"].items()):
        icon = TYPE_ICON.get(task_type, "•")
        console.print(f"  {icon} {task_type}: {count}")


@main.command()
@click.option("--force", "-f", is_flag=True, help="Force rebuild even if index is fresh")
def reindex(force: bool):
    """Rebuild the task index."""
    index = TaskIndex()

    console.print("[dim]Rebuilding index...[/dim]")

    # Try fast indexer first
    if index.rebuild_fast():
        console.print("[green]✓[/green] Rebuilt index using fast-indexer")
    else:
        index.rebuild()
        console.print("[green]✓[/green] Rebuilt index using Python")

    s = index.stats()
    console.print(f"  [dim]{s['total']} tasks indexed[/dim]")


@main.command(name="dedup")
@click.option("--delete", "-d", is_flag=True, help="Delete duplicates (keeps newest or done)")
@click.option("--plain", is_flag=True, help="Plain output for scripting")
def find_duplicates(delete: bool, plain: bool):
    """Find and optionally remove duplicate tasks.

    Identifies tasks with identical frontmatter IDs (data corruption) or
    identical titles. When --delete is used, keeps the task that is 'done'
    (if any), otherwise keeps the newest.
    """
    storage = get_storage()
    # Note: Don't call get_index() here - it would fail on duplicates
    # (fast-indexer refuses to run with duplicate IDs)

    # Group tasks by title AND by ID (for detecting frontmatter ID collisions)
    from collections import defaultdict

    by_title: dict[str, list] = defaultdict(list)
    by_id: dict[str, list] = defaultdict(list)

    for task in storage._iter_all_tasks():
        by_title[task.title].append(task)
        by_id[task.id].append(task)

    # Find title duplicates (same title, different files)
    title_duplicates = {title: tasks for title, tasks in by_title.items() if len(tasks) > 1}

    # Find ID duplicates (same frontmatter id in different files) - MORE SERIOUS
    id_duplicates = {task_id: tasks for task_id, tasks in by_id.items() if len(tasks) > 1}

    # Merge: ID duplicates take precedence (use "ID: {id}" as key to distinguish)
    duplicates: dict[str, list] = {}

    # Add ID duplicates first
    for task_id, tasks in id_duplicates.items():
        duplicates[f"ID: {task_id}"] = tasks

    # Add title duplicates that aren't already covered by ID duplicates
    covered_tasks = set()
    for tasks in id_duplicates.values():
        for t in tasks:
            covered_tasks.add(id(t))

    for title, tasks in title_duplicates.items():
        remaining = [t for t in tasks if id(t) not in covered_tasks]
        if len(remaining) > 1:
            duplicates[title] = remaining

    if not duplicates:
        console.print("[green]✓[/green] No duplicate tasks found.")
        return

    id_dup_count = sum(1 for k in duplicates.keys() if k.startswith("ID: "))
    title_dup_count = len(duplicates) - id_dup_count
    total_dups = sum(len(tasks) - 1 for tasks in duplicates.values())

    msg_parts = []
    if id_dup_count:
        msg_parts.append(f"{id_dup_count} ID duplicate(s)")
    if title_dup_count:
        msg_parts.append(f"{title_dup_count} title duplicate(s)")
    console.print(
        f"[yellow]Found {' and '.join(msg_parts)} ({total_dups} files to remove)[/yellow]"
    )
    console.print()

    to_delete = []

    for title, tasks in sorted(duplicates.items()):
        # Sort: done status first, then by modified date (newest first)
        tasks.sort(
            key=lambda t: (
                0 if t.status.value == "done" else 1,
                -t.modified.timestamp(),
            )
        )

        keep = tasks[0]
        remove = tasks[1:]
        to_delete.extend(remove)

        if plain:
            for t in remove:
                click.echo(t.id)
        else:
            console.print(f"[bold]{title}[/bold]")
            icon, style = STATUS_STYLE.get(keep.status.value, ("•", "white"))
            console.print(f"  [green]keep[/green]  {icon} {keep.id} ({keep.status.value})")
            for t in remove:
                icon, style = STATUS_STYLE.get(t.status.value, ("•", "white"))
                console.print(f"  [red]dup[/red]   {icon} {t.id} ({t.status.value})")
            console.print()

    if delete and to_delete:
        console.print(f"[bold red]Deleting {len(to_delete)} duplicate(s)...[/bold red]")
        deleted_count = 0
        for task in to_delete:
            if storage.delete_task(task.id):
                deleted_count += 1
                if not plain:
                    console.print(f"  [red]✗[/red] Deleted {task.id}")

        # Rebuild index
        index = TaskIndex()
        if index.rebuild_fast():
            pass
        else:
            index.rebuild()

        console.print(f"[green]✓[/green] Deleted {deleted_count} duplicate(s)")
    elif not delete and to_delete:
        console.print(f"[dim]Use --delete to remove {len(to_delete)} duplicate(s)[/dim]")


if __name__ == "__main__":
    main()
