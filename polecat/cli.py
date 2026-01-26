#!/usr/bin/env python3
import click
import sys
from pathlib import Path
from manager import PolecatManager

@click.group()
def main():
    """Polecat: Ephemeral worker management system."""
    pass

@main.command()
@click.option("--project", "-p", help="Project to claim tasks from")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
def start(project, caller):
    """Claim next ready task and spawn a worktree."""
    manager = PolecatManager()
    
    print(f"Looking for ready tasks{' in project ' + project if project else ''}...")
    task = manager.claim_next_task(caller, project)
    
    if not task:
        print("No ready tasks found.")
        sys.exit(0)
        
    print(f"Claimed task: {task.title} ({task.id})")
    
    try:
        worktree_path = manager.setup_worktree(task)
        print(f"\nSuccess! Worktree ready at:\n{worktree_path}")
        print(f"\nTo start working:\ncd {worktree_path}")
    except Exception as e:
        print(f"\nError setting up worktree: {e}")
        sys.exit(1)

@main.command()
@click.argument("task_id")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
def checkout(task_id, caller):
    """Checkout a specific task by ID and create its worktree.

    Use with shell integration for automatic cd:
        cd $(polecat checkout TASK_ID)

    Or add to your shell rc:
        pc() { cd "$(polecat checkout "$@")" 2>/dev/null || polecat checkout "$@"; }
    """
    manager = PolecatManager()

    task = manager.storage.get_task(task_id)
    if not task:
        print(f"Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    # Claim the task if not already in progress
    try:
        from lib.task_model import TaskStatus
        if task.status == TaskStatus.ACTIVE:
            task.status = TaskStatus.IN_PROGRESS
            task.assignee = caller
            manager.storage.save_task(task)
            print(f"Claimed: {task.title}", file=sys.stderr)
    except ImportError:
        pass

    try:
        worktree_path = manager.setup_worktree(task)
        # Output just the path for shell integration (cd $(polecat checkout ...))
        print(worktree_path)
    except Exception as e:
        print(f"Error setting up worktree: {e}", file=sys.stderr)
        sys.exit(1)

@main.command()
@click.argument("task_id")
def nuke(task_id):
    """Destroy a polecat (remove worktree and branch)."""
    manager = PolecatManager()
    manager.nuke_worktree(task_id)
    print(f"Nuked polecat {task_id}")

@main.command()
def list():
    """List active polecats."""
    manager = PolecatManager()
    if not manager.polecats_dir.exists():
        print("No polecats directory found.")
        return

    found = False
    for item in manager.polecats_dir.iterdir():
        if item.is_dir():
            print(f"{item.name} -> {item}")
            found = True
            
    if not found:
        print("No active polecats.")

if __name__ == "__main__":
    main()
