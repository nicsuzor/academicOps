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
@click.option("--project", "-p", help="Initialize only this project (default: all)")
def init(project):
    """Initialize bare mirror repos in ~/.aops/polecat/.repos/

    Creates bare clones of all registered projects for isolated worktree spawning.
    Run this once before using polecat, or when adding new projects.

    Examples:
        polecat init              # Initialize all projects
        polecat init -p aops      # Initialize only aops
    """
    manager = PolecatManager()

    if project:
        try:
            path = manager.ensure_repo_mirror(project)
            print(f"✓ {project} -> {path}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Failed to initialize {project}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Initializing mirrors in {manager.repos_dir}...")
        results = manager.init_all_mirrors()
        failures = [p for p, path in results.items() if path is None]
        if failures:
            print(f"\n⚠️  Failed: {', '.join(failures)}")
            sys.exit(1)
        print(f"\n✓ All mirrors ready")


@main.command()
def sync():
    """Fetch latest from origin for all mirror repos.

    Updates existing bare mirrors with latest branches from origin.
    Use before spawning polecats to ensure they have recent code.

    Examples:
        polecat sync
    """
    manager = PolecatManager()
    print(f"Syncing mirrors in {manager.repos_dir}...")
    results = manager.sync_all_mirrors()
    successes = sum(1 for v in results.values() if v)
    print(f"\n✓ Synced {successes}/{len(results)} mirrors")


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
@click.option(
    "--nuke", "do_nuke", is_flag=True, help="Also remove the worktree after finishing"
)
def finish(no_push, do_nuke):
    """Mark current task as ready for merge.

    Must be run from within a polecat worktree.
    Pushes branch and sets task status to 'merge_ready'.
    """
    import subprocess

    manager = PolecatManager()
    cwd = Path.cwd()

    # Detect if we're in a polecat worktree
    if not cwd.is_relative_to(manager.polecats_dir):
        print(
            f"Error: Not in a polecat worktree. Expected path under {manager.polecats_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Extract task ID from directory name
    task_id = cwd.relative_to(manager.polecats_dir).parts[0]
    task = manager.storage.get_task(task_id)

    if not task:
        print(f"Error: Task {task_id} not found in task database", file=sys.stderr)
        sys.exit(1)

    print(f"Finishing task: {task.title} ({task_id})")

    # --- SAFEGUARD 1: Dirty Exit Protection ---
    # Check for uncommitted changes
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    )
    if result.stdout.strip():
        print("⚠️  Warning: Uncommitted changes detected.")
        # Automatically commit changes if they are simple
        print("  🧹 Automatically staging and committing changes...")
        try:
            subprocess.run(["git", "add", "-u"], check=True)  # Stage modified/deleted
            subprocess.run(
                ["git", "add", "."], check=True
            )  # Stage new files (careful!)
            subprocess.run(
                ["git", "commit", "-m", "chore: saving uncommitted agent work"],
                check=True,
            )
            print("  ✅ Changes saved.")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to auto-commit: {e}")
            if not click.confirm("Continue without saving? (Risk of data loss)"):
                sys.exit(1)

    # --- SAFEGUARD 2: Repo-Nuke Protection ---
    # Check if we are unexpectedly rewriting the whole repo
    # This prevents the "orphan branch" issue where an agent commits 1000+ files as new
    try:
        # Get shortstat diff against origin/main to see scale of changes
        diff_res = subprocess.run(
            ["git", "diff", "--shortstat", "origin/main", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Output format: " 10 files changed, 100 insertions(+), 50 deletions(-)"
        if diff_res.returncode == 0 and diff_res.stdout.strip():
            parts = diff_res.stdout.strip().split(",")
            files_changed_str = parts[0].strip().split(" ")[0]
            if files_changed_str.isdigit():
                files_changed = int(files_changed_str)
                if files_changed > 50:
                    print(
                        f"\n🚨 SAFEGUARD ACTIVATE: Large changeset detected ({files_changed} files)."
                    )
                    print("   This looks like a 'repo nuke' or orphan branch issue.")
                    print(
                        "   Run 'git reset --soft FETCH_HEAD' to recover if this is accidental."
                    )
                    if not click.confirm("Are you SURE you want to push this?"):
                        sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not run repo checking safeguards: {e}")

    # Push to origin
    if not no_push:
        branch_name = f"polecat/{task_id}"

        # --- SAFEGUARD 3: Main-Push Blockade ---
        if branch_name == "main" or branch_name == "master":
            print("🚨 SAFEGUARD: Refusing to push 'main' branch via polecat.")
            sys.exit(1)

        print(f"Pushing {branch_name} to origin...")
        try:
            # Explicitly push local branch to remote branch of same name
            # This avoids issues where tracking upstream is set to main
            subprocess.run(
                ["git", "push", "-u", "origin", f"{branch_name}:{branch_name}"],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error pushing to origin: {e}", file=sys.stderr)
            sys.exit(1)

    # Update task status to merge_ready
    try:
        from lib.task_model import TaskStatus

        task.status = TaskStatus.MERGE_READY
        manager.storage.save_task(task)
        print(f"✅ Task marked as 'merge_ready'")
    except ImportError:
        print("Warning: Could not update task status (lib.task_model not available)")

    # Optionally nuke
    if do_nuke:
        print("Nuking worktree...")
        os.chdir(Path.home())  # Move out of worktree before nuking
        manager.nuke_worktree(task_id, force=False)
        print(f"Worktree removed")
    else:
        print(f"\nTo clean up later: polecat nuke {task_id}")


@main.command()
@click.argument("task_id")
@click.option("--force", "-f", is_flag=True, help="Delete even if work is not merged")
def nuke(task_id, force):
    """Destroy a polecat (remove worktree and branch)."""
    manager = PolecatManager()
    try:
        manager.nuke_worktree(task_id, force=force)
        print(f"Nuked polecat {task_id}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


@main.command("list")
def list_polecats():
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
@click.option(
    "--project", "-p", multiple=True, help="Project(s) to work on (default: all)"
)
@click.option("--name", "-n", help="Crew name (randomly generated if not specified)")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--resume", "-r", help="Resume existing crew worker by name")
def crew(project, name, gemini, resume):
    """Start an interactive crew session.

    Crew workers are persistent, named agents for interactive collaboration.
    Unlike polecats (autonomous, task-scoped), crew workers:
    - Have randomly generated names (famous queer women of color)
    - Persist across sessions
    - Can work on multiple tasks
    - Are not bound to a single task (but edits require task binding via hooks)

    Examples:
        polecat crew                      # New crew with ALL projects
        polecat crew -p aops              # New crew for aops only
        polecat crew -p aops -p buttermilk  # New crew for specific projects
        polecat crew -r audre             # Resume crew worker "audre"
    """
    import subprocess

    manager = PolecatManager()

    # Determine which projects to use
    if project:
        projects = list(project)
    else:
        # Default to all projects
        projects = list(manager.projects.keys())

    # Determine crew name
    if resume:
        crew_name = resume
        if crew_name not in manager.list_crew():
            print(
                f"Error: No crew worker named '{crew_name}'. Active: {manager.list_crew()}",
                file=sys.stderr,
            )
            sys.exit(1)
    elif name:
        crew_name = name
    else:
        crew_name = manager.generate_crew_name()

    print(f"🧑‍🤝‍🧑 Crew worker: {crew_name}")

    # Setup worktrees for all projects
    worktree_paths = {}
    try:
        for proj in projects:
            worktree_path = manager.setup_crew_worktree(crew_name, proj)
            worktree_paths[proj] = worktree_path
            print(f"📁 {proj}: {worktree_path}")
    except Exception as e:
        print(f"Error setting up worktree: {e}", file=sys.stderr)
        sys.exit(1)

    # Crew root is the parent of all project worktrees
    crew_root = manager.crew_dir / crew_name

    # Run agent in interactive mode (no task binding - hooks will enforce when needed)
    cli_tool = "gemini" if gemini else "claude"
    print(f"\n🤝 Starting {cli_tool} crew session...")
    print(f"   Crew: {crew_name}")
    print(f"   Projects: {', '.join(projects)}")
    print(f"   Working dir: {crew_root}")
    print("-" * 50)

    if gemini:
        cmd = ["gemini"]
    else:
        aops_dir = os.environ.get("AOPS")
        if not aops_dir:
            print("Error: $AOPS environment variable not set", file=sys.stderr)
            sys.exit(1)
        cmd = [
            "claude",
            "--permission-mode=plan",
            "--dangerously-skip-permissions",
            "--setting-sources=user",
            "--plugin-dir",
            str(Path(aops_dir) / "aops-core"),
            "--plugin-dir",
            str(Path(aops_dir) / "aops-tools"),
        ]

    try:
        subprocess.run(cmd, cwd=crew_root)
    except FileNotFoundError:
        print(f"Error: '{cli_tool}' command not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Session interrupted")

    print("-" * 50)
    print(f"\n📋 Crew '{crew_name}' session ended.")
    print(f"   Worktrees preserved at: {crew_root}")
    print(f"   To resume: polecat crew -r {crew_name}")
    print(f"   To nuke:   polecat nuke-crew {crew_name}")


@main.command("nuke-crew")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Delete even if work is not merged")
def nuke_crew(name, force):
    """Remove a crew worker and their worktrees."""
    manager = PolecatManager()
    try:
        manager.nuke_crew(name, force=force)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


@main.command("list-crew")
def list_crew():
    """List active crew workers."""
    manager = PolecatManager()
    crew = manager.list_crew()
    if not crew:
        print("No active crew workers.")
        return
    print("Active crew workers:")
    for name in crew:
        crew_path = manager.crew_dir / name
        projects = [d.name for d in crew_path.iterdir() if d.is_dir()]
        print(f"  {name}: {', '.join(projects)}")


@main.command()
@click.option("--project", "-p", help="Project for the collaboration")
@click.option("--title", "-t", help="Brief title for the collaboration task")
@click.option(
    "--caller",
    "-c",
    default="nic",
    help="Identity for the collaboration (default: nic)",
)
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option("--no-finish", is_flag=True, hidden=True, help="(Deprecated, no-op)")
def colab(project, title, caller, gemini, no_finish):
    """[DEPRECATED] Use 'polecat crew' instead.

    Creates a new task, spawns a worktree, and starts an interactive
    agent session for human-bot pairing. Agents should call `polecat finish` when ready.

    Examples:
        polecat colab -p aops -t "Debug failing tests"
        polecat colab -t "Refactor login flow"
    """
    print("⚠️  'colab' is deprecated. Use 'polecat crew' instead.")
    print("   polecat crew -p aops")
    print("")
    import subprocess
    from datetime import datetime

    manager = PolecatManager()

    # Generate title if not provided
    if not title:
        title = f"session-{datetime.now().astimezone().strftime('%H%M')}"

    # Create a new task for tracking using storage.create_task (handles ID generation)
    try:
        from lib.task_model import TaskStatus, TaskType

        task = manager.storage.create_task(
            title=f"Collaborate: {title}",
            type=TaskType.TASK,
            status=TaskStatus.IN_PROGRESS,
            project=project or "aops",
            assignee=caller,
        )
        manager.storage.save_task(task)
        print(f"📋 Created task: {task.title} ({task.id})")
    except ImportError as e:
        print(f"Error: Could not create task - {e}", file=sys.stderr)
        sys.exit(1)

    # Setup worktree
    try:
        worktree_path = manager.setup_worktree(task)
        print(f"📁 Worktree: {worktree_path}")
    except Exception as e:
        print(f"Error setting up worktree: {e}", file=sys.stderr)
        sys.exit(1)

    # Build prompt - just reference the task
    prompt = f"/pull {task.id}"

    # Run agent in interactive mode
    cli_tool = "gemini" if gemini else "claude"
    print(f"\n🤝 Starting {cli_tool} collaboration session...")
    print("-" * 50)

    if gemini:
        cmd = ["gemini", "-i", prompt]
    else:
        aops_dir = os.environ.get("AOPS")
        if not aops_dir:
            print("Error: $AOPS environment variable not set", file=sys.stderr)
            sys.exit(1)
        cmd = [
            "claude",
            "--permission-mode",
            "plan",
            "--setting-sources=user",
            "--plugin-dir",
            str(Path(aops_dir) / "aops-core"),
            "--plugin-dir",
            str(Path(aops_dir) / "aops-tools"),
            prompt,
        ]

    try:
        result = subprocess.run(cmd, cwd=worktree_path)
        exit_code = result.returncode
    except FileNotFoundError:
        print(f"Error: '{cli_tool}' command not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Session interrupted by user")
        exit_code = 130

    print("-" * 50)

    # Report status - agents should call `polecat finish` themselves
    if exit_code == 0:
        print(f"\n✅ Collaboration completed.")
    else:
        print(f"\n⚠️  Session exited with code {exit_code}.")
    print(f"\n📝 When ready to merge, run `polecat finish` from the worktree.")
    print(f"   Worktree: {worktree_path}")


@main.command()
@click.option("--project", "-p", help="Project to claim tasks from")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.option("--task-id", "-t", help="Specific task ID to run (skips claim)")
@click.option("--no-finish", is_flag=True, hidden=True, help="(Deprecated, no-op)")
@click.option("--gemini", "-g", is_flag=True, help="Use Gemini CLI instead of Claude")
@click.option(
    "--interactive", "-i", is_flag=True, help="Run in interactive mode (not headless)"
)
@click.option(
    "--no-auto-finish",
    is_flag=True,
    help="Skip automatic 'polecat finish' on successful completion",
)
@click.pass_context
def run(ctx, project, caller, task_id, no_finish, gemini, interactive, no_auto_finish):
    """Run a polecat cycle: claim → setup → work → finish.

    Claims a task, spawns a worktree, and runs claude with the task context.
    On successful completion (exit code 0), automatically runs `polecat finish`.

    Examples:
        polecat run -p aops              # Run next ready task from aops project
        polecat run -t task-123          # Run specific task
        polecat run -p aops --no-auto-finish  # Skip auto-finish on success
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
        print(
            f"Looking for ready tasks{' in project ' + project if project else ''}..."
        )
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

    # Step 4: Run agent in the worktree
    # Choose CLI tool based on --gemini flag
    cli_tool = "gemini" if gemini else "claude"
    mode = "interactive" if interactive else "headless"
    print(f"\n🤖 Starting {cli_tool} agent ({mode})...")
    print("-" * 50)

    # Build command - gemini and claude have different CLI interfaces
    if gemini:
        # Gemini CLI
        cmd = ["gemini"]
        if interactive:
            # -i starts interactive mode with initial prompt
            cmd.extend(["-i", prompt])
        else:
            # Headless mode with auto-approve
            cmd.extend(["--approval-mode", "yolo", "-p", prompt])
    else:
        # Claude CLI
        aops_dir = os.environ.get("AOPS")
        if not aops_dir:
            print("Error: $AOPS environment variable not set", file=sys.stderr)
            sys.exit(1)
        cmd = ["claude"]
        if not interactive:
            cmd.append("--dangerously-skip-permissions")
        cmd.extend(
            [
                "--permission-mode",
                "plan",
                "--setting-sources=user",
                "--plugin-dir",
                str(Path(aops_dir) / "aops-core"),
                "--plugin-dir",
                str(Path(aops_dir) / "aops-tools"),
            ]
        )
        if interactive:
            # Interactive: just append the prompt as positional arg
            cmd.append(prompt)
        else:
            # Headless: use -p for print mode
            cmd.extend(["-p", prompt])

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

    # Step 5: Auto-finish on success (unless disabled)
    if exit_code == 0:
        print(f"\n✅ Agent completed successfully.")
        if not no_auto_finish:
            print(f"🔄 Running auto-finish...")
            # Change to worktree directory and invoke finish directly
            original_cwd = os.getcwd()
            try:
                os.chdir(worktree_path)
                ctx.invoke(finish, no_push=False, do_nuke=False)
                print(f"✅ Auto-finish completed.")
            except SystemExit as e:
                if e.code != 0:
                    print(f"⚠️  Auto-finish failed.")
                    print(
                        f"   You can retry manually: cd {worktree_path} && polecat finish"
                    )
            except Exception as e:
                print(f"⚠️  Auto-finish failed: {e}")
                print(
                    f"   You can retry manually: cd {worktree_path} && polecat finish"
                )
            finally:
                os.chdir(original_cwd)
        else:
            print(f"📝 Auto-finish disabled. Run `polecat finish` when ready.")
            print(f"   Worktree: {worktree_path}")
    else:
        print(f"\n⚠️  Agent exited with code {exit_code}. Skipping auto-finish.")
        print(f"   Worktree: {worktree_path}")
        print(f"   To finish manually: cd {worktree_path} && polecat finish")


@main.command()
@click.option("--claude", "-c", default=0, help="Number of Claude workers")
@click.option("--gemini", "-g", default=0, help="Number of Gemini workers")
@click.option("--project", "-p", help="Project to focus on (default: all)")
@click.option("--dry-run", is_flag=True, help="Simulate execution")
def swarm(claude, gemini, project, dry_run):
    """Run a swarm of parallel Polecat workers.

    Spawns N claude and M gemini workers, managing CPU affinity.
    Restarting workers on success, stopping on failure.
    """
    try:
        from swarm import run_swarm
    except ImportError:
        # Fallback for when running as script in same dir
        try:
            from .swarm import run_swarm
        except ImportError:
            # Last ditch for direct execution
            try:
                import swarm as swarm_module

                run_swarm = swarm_module.run_swarm
            except ImportError:
                print("Error: Could not import swarm module.", file=sys.stderr)
                sys.exit(1)

    run_swarm(claude, gemini, project, dry_run)


if __name__ == "__main__":
    main()
