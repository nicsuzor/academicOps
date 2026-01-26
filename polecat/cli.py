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

    # Update task status to review (clear assignee so merge can pick it up)
    try:
        from lib.task_model import TaskStatus
        task.status = TaskStatus.REVIEW
        task.assignee = None
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
    from engineer import Engineer

    eng = Engineer()
    eng.scan_and_merge()

@main.command()
@click.option("--project", "-p", help="Project to claim tasks from")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.option("--task-id", "-t", help="Specific task ID to run (skips claim)")
@click.option("--no-finish", is_flag=True, help="Don't auto-finish after agent exits")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--interactive", "-i", is_flag=True, help="Run in interactive mode (not headless)")
def run(project, caller, task_id, no_finish, gemini, interactive):
    """Run a full polecat cycle: claim → work → finish.

    Claims a task, spawns a worktree, runs claude with the task context,
    and marks as ready for merge when the agent exits.

    Examples:
        polecat run -p aops           # Run next ready task from aops project
        polecat run -t task-123       # Run specific task
        polecat run --no-finish       # Don't auto-finish (manual review)
    """
    import subprocess

    manager = PolecatManager()

    # Step 1: Get/claim task
    if task_id:
        task = manager.storage.get_task(task_id)
        if not task:
            print(f"Task not found: {task_id}", file=sys.stderr)
            sys.exit(1)
        # Claim if not already in progress
        try:
            from lib.task_model import TaskStatus
            if task.status == TaskStatus.ACTIVE:
                task.status = TaskStatus.IN_PROGRESS
                task.assignee = caller
                manager.storage.save_task(task)
        except ImportError:
            pass
    else:
        print(f"Looking for ready tasks{' in project ' + project if project else ''}...")
        task = manager.claim_next_task(caller, project)
        if not task:
            print("No ready tasks found.")
            sys.exit(0)

    print(f"🎯 Task: {task.title} ({task.id})")

    # Step 2: Setup worktree
    try:
        worktree_path = manager.setup_worktree(task)
        print(f"📁 Worktree: {worktree_path}")
    except Exception as e:
        print(f"Error setting up worktree: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 3: Build prompt from task
    prompt = f"/pull {task.id}"

    # Step 4: Run agent in the worktree with proper plugin dirs
    # Choose CLI tool based on --gemini flag
    cli_tool = "gemini" if gemini else "claude"
    mode = "interactive" if interactive else "headless"
    print(f"\n🤖 Starting {cli_tool} agent ({mode})...")
    print("-" * 50)

    # Build command
    cmd = [cli_tool]

    # Add headless flags only if not interactive
    if not interactive:
        cmd.append("--dangerously-skip-permissions")

    cmd.extend([
        "--permission-mode", "plan",
        "--setting-sources=user",
        "--plugin-dir", str(worktree_path / "aops-core"),
        "--plugin-dir", str(worktree_path / "aops-tools"),
        "-p", prompt,
    ])

    try:
        result = subprocess.run(
            cmd,
            cwd=worktree_path,
        )
        exit_code = result.returncode
    except FileNotFoundError:
        print(f"Error: '{cli_tool}' command not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Agent interrupted by user")
        exit_code = 130

    print("-" * 50)

    # Step 5: Finish (push and mark as review)
    if no_finish:
        print(f"\n📝 Skipping auto-finish. To finish manually:")
        print(f"   cd {worktree_path}")
        print(f"   polecat finish")
    elif exit_code == 0:
        print(f"\n✅ Agent completed successfully. Finishing...")
        os.chdir(worktree_path)

        # Push
        branch_name = f"polecat/{task.id}"
        try:
            subprocess.run(["git", "push", "-u", "origin", branch_name], check=True, cwd=worktree_path)
        except subprocess.CalledProcessError:
            print("⚠️  Push failed - you may need to commit changes first")
            sys.exit(1)

        # Mark as review (clear assignee so merge can pick it up)
        try:
            from lib.task_model import TaskStatus
            task = manager.storage.get_task(task.id)  # Refresh
            task.status = TaskStatus.REVIEW
            task.assignee = None
            manager.storage.save_task(task)
            print(f"✅ Task marked as 'review' (ready for merge)")
        except ImportError:
            print("Warning: Could not update task status")

        print(f"\n🏭 To merge: polecat merge")
    else:
        print(f"\n⚠️  Agent exited with code {exit_code}. Not auto-finishing.")
        print(f"   To finish manually: cd {worktree_path} && polecat finish")

if __name__ == "__main__":
    main()
