#!/usr/bin/env python3
import click
import os
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
@click.option("--no-push", is_flag=True, help="Skip pushing to remote")
@click.option("--nuke", "do_nuke", is_flag=True, help="Also remove the worktree after finishing")
def finish(no_push, do_nuke):
    """Mark current task as ready for merge.

    Must be run from within a polecat worktree.
    Pushes branch and sets task status to 'review'.
    """
    import subprocess

    manager = PolecatManager()
    cwd = Path.cwd()

    # Detect if we're in a polecat worktree
    if not cwd.is_relative_to(manager.polecats_dir):
        print(f"Error: Not in a polecat worktree. Expected path under {manager.polecats_dir}", file=sys.stderr)
        sys.exit(1)

    # Extract task ID from directory name
    task_id = cwd.relative_to(manager.polecats_dir).parts[0]
    task = manager.storage.get_task(task_id)

    if not task:
        print(f"Error: Task {task_id} not found in task database", file=sys.stderr)
        sys.exit(1)

    print(f"Finishing task: {task.title} ({task_id})")

    # Check for uncommitted changes
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  Warning: Uncommitted changes detected:")
        print(result.stdout)
        if not click.confirm("Continue anyway?"):
            sys.exit(1)

    # Push to origin
    if not no_push:
        branch_name = f"polecat/{task_id}"
        print(f"Pushing {branch_name} to origin...")
        try:
            subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error pushing to origin: {e}", file=sys.stderr)
            sys.exit(1)

    # Update task status to review
    try:
        from lib.task_model import TaskStatus
        task.status = TaskStatus.REVIEW
        manager.storage.save_task(task)
        print(f"✅ Task marked as 'review' (ready for merge)")
    except ImportError:
        print("Warning: Could not update task status (lib.task_model not available)")

    # Optionally nuke
    if do_nuke:
        print("Nuking worktree...")
        os.chdir(Path.home())  # Move out of worktree before nuking
        manager.nuke_worktree(task_id)
        print(f"Worktree removed")
    else:
        print(f"\nTo clean up later: polecat nuke {task_id}")

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

@main.command()
def merge():
    """Scan for tasks in REVIEW status and merge them to main.

    This runs the Refinery: finds all tasks marked 'review',
    squash-merges their polecat branches, runs tests, and
    marks them 'done' on success.
    """
    # Import here to avoid circular dependency
    sys.path.insert(0, str(Path(__file__).parent.parent / "refinery"))
    from engineer import Engineer

    eng = Engineer()
    eng.scan_and_merge()

if __name__ == "__main__":
    main()
