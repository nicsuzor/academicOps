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
