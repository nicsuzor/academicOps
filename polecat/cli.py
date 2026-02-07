#!/usr/bin/env python3
import click
import os
import sys
from pathlib import Path
from manager import PolecatManager
from validation import TaskIDValidationError, validate_task_id_or_raise




def is_interactive() -> bool:
    """Check if we're running in an interactive terminal."""
    return sys.stdin.isatty()


@click.group()
@click.option(
    "--home",
    envvar="POLECAT_HOME",
    type=click.Path(path_type=Path),
    help="Polecat home directory (default: ~/.aops, or POLECAT_HOME env var)",
)
@click.pass_context
def main(ctx, home):
    """Polecat: Ephemeral worker management system."""
    ctx.ensure_object(dict)
    ctx.obj["home"] = home


@main.command()
@click.option("--project", "-p", help="Initialize only this project (default: all)")
@click.pass_context
def init(ctx, project):
    """Initialize bare mirror repos in <home>/polecat/.repos/

    Creates bare clones of all registered projects for isolated worktree spawning.
    Run this once before using polecat, or when adding new projects.

    Examples:
        polecat init              # Initialize all projects
        polecat init -p aops      # Initialize only aops
        polecat --home /custom/path init  # Use custom home directory
    """
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

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
        print("\n✓ All mirrors ready")


@main.command()
@click.pass_context
def sync(ctx):
    """Fetch latest from origin for all mirror repos.

    Updates existing bare mirrors with latest branches from origin.
    Use before spawning polecats to ensure they have recent code.

    Examples:
        polecat sync
    """
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    print(f"Syncing mirrors in {manager.repos_dir}...")
    results = manager.sync_all_mirrors()
    successes = sum(1 for v in results.values() if v)
    print(f"\n✓ Synced {successes}/{len(results)} mirrors")


@main.command()
@click.option("--project", "-p", help="Project to claim tasks from")
@click.option("--caller", "-c", default="polecat", help="Identity claiming the task")
@click.pass_context
def start(ctx, project, caller):
    """Claim next ready task and spawn a worktree."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

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
@click.pass_context
def checkout(ctx, task_id, caller):
    """Checkout a specific task by ID and create its worktree.

    Use with shell integration for automatic cd:
        cd $(polecat checkout TASK_ID)

    Or add to your shell rc:
        pc() { cd "$(polecat checkout "$@")" 2>/dev/null || polecat checkout "$@"; }
    """
    # Validate task ID before any operations
    try:
        validate_task_id_or_raise(task_id)
    except TaskIDValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

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


def _attempt_auto_merge(task, manager):
    """Attempt to auto-merge a task after it's marked merge_ready.

    This is a hook called from the finish command. It attempts to merge
    immediately if conditions are right, otherwise leaves the task for
    manual merge via 'polecat merge'.

    Args:
        task: Task object that was just marked merge_ready
        manager: PolecatManager instance
    """
    try:
        from engineer import Engineer
        from lib.task_model import TaskStatus

        # Check if any blocking dependencies are not done
        if task.depends_on:
            for dep_id in task.depends_on:
                dep_task = manager.storage.get_task(dep_id)
                if dep_task and dep_task.status != TaskStatus.DONE:
                    print(f"  ⏸ Auto-merge skipped: dependency {dep_id} not done")
                    return

        print("  🔄 Attempting auto-merge...")
        eng = Engineer()

        # Process just this task (not a full scan)
        try:
            eng.process_merge(task)
            print("  ✅ Auto-merge succeeded!")
        except Exception as e:
            # Merge failed - kickback to review
            print(f"  ⚠ Auto-merge failed: {e}")
            eng.handle_failure(task, str(e))
            print("  Task moved to 'review' - engineer (bot) will attempt to fix")

    except ImportError as e:
        print(f"  ⚠ Auto-merge skipped: {e}")
    except Exception as e:
        print(f"  ⚠ Auto-merge error: {e}")


@main.command()
@click.option("--no-push", is_flag=True, help="Skip pushing to remote")
@click.option(
    "--nuke", "do_nuke", is_flag=True, help="Also remove the worktree after finishing"
)
@click.pass_context
def finish(ctx, no_push, do_nuke):
    """Mark current task as ready for merge.

    Must be run from within a polecat worktree.
    Pushes branch and sets task status to 'merge_ready'.
    """
    import subprocess

    manager = PolecatManager(home_dir=ctx.obj.get("home"))
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
            if not is_interactive():
                print("  🚫 Non-interactive mode: refusing to continue without saving.")
                sys.exit(1)
            if not click.confirm("Continue without saving? (Risk of data loss)"):
                sys.exit(1)

    # --- NO-CHANGES DETECTION ---
    # If the agent made no changes, skip the entire test/merge pipeline
    try:
        # First, fetch to ensure we have latest origin/main
        subprocess.run(
            ["git", "fetch", "origin", "main"],
            capture_output=True,
            check=False,
        )
        # Check if there are any commits on this branch vs origin/main
        diff_check = subprocess.run(
            ["git", "diff", "--quiet", "origin/main", "HEAD"],
            capture_output=True,
            check=False,
        )
        # git diff --quiet returns 0 if no changes, 1 if changes exist
        if diff_check.returncode == 0:
            print("📭 No changes detected. Skipping test/merge pipeline.")
            # Mark task as done directly
            try:
                from lib.task_model import TaskStatus

                task.status = TaskStatus.DONE
                manager.storage.save_task(task)
                print("✅ Task marked as 'done' (no changes to merge)")
            except ImportError:
                print(
                    "Warning: Could not update task status (lib.task_model not available)"
                )

            # Optionally nuke
            if do_nuke:
                print("Nuking worktree...")
                os.chdir(Path.home())  # Move out of worktree before nuking
                manager.nuke_worktree(task_id, force=False)
                print("Worktree removed")
            else:
                print(f"\nTo clean up later: polecat nuke {task_id}")
            return  # Exit early, skip rest of finish flow

    except Exception as e:
        print(f"Warning: Could not check for changes: {e}")
        # Continue with normal flow if check fails

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
                    if not is_interactive():
                        print(
                            "   🚫 Non-interactive mode: refusing to push large changeset without confirmation."
                        )
                        print(
                            "   Re-run interactively or manually push if this is intentional."
                        )
                        sys.exit(1)
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

        # --- REBASE BEFORE PUSH ---
        # Fetch and rebase onto latest main to prevent orphan commits and merge conflicts
        print("🔄 Syncing with latest main before push...")
        try:
            # Fetch latest from origin
            subprocess.run(
                ["git", "fetch", "origin", "main"],
                check=True,
                capture_output=True,
            )

            # Check if we need to rebase (are we behind origin/main?)
            merge_base = subprocess.run(
                ["git", "merge-base", "HEAD", "origin/main"],
                capture_output=True,
                text=True,
                check=True,
            )
            origin_main = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                capture_output=True,
                text=True,
                check=True,
            )

            if merge_base.stdout.strip() != origin_main.stdout.strip():
                # We're behind, need to rebase
                print("  📥 Branch is behind origin/main, rebasing...")
                rebase_result = subprocess.run(
                    ["git", "rebase", "origin/main"],
                    capture_output=True,
                    text=True,
                )
                if rebase_result.returncode != 0:
                    # Rebase failed - abort and report
                    subprocess.run(["git", "rebase", "--abort"], check=False)
                    print("  ❌ Rebase failed due to conflicts.", file=sys.stderr)
                    print(f"  {rebase_result.stderr}", file=sys.stderr)
                    print("  Task will be marked for review.", file=sys.stderr)
                    # Don't exit - let it fall through to mark as review
                    try:
                        from lib.task_model import TaskStatus

                        task.status = TaskStatus.REVIEW
                        task.body += "\n\n## ⚠️ Rebase Failed\nConflicts detected during rebase onto main.\n"
                        manager.storage.save_task(task)
                    except ImportError:
                        pass
                    sys.exit(1)
                print("  ✅ Rebase successful")
            else:
                print("  ✅ Already up-to-date with main")

        except subprocess.CalledProcessError as e:
            print(f"  ⚠️ Sync failed: {e}", file=sys.stderr)
            # Continue anyway - the push might still work

        print(f"Pushing {branch_name} to origin...")
        try:
            # Use --force-with-lease for safe force push after rebase
            # This is safe because we just rebased and no one else should be pushing to this branch
            subprocess.run(
                ["git", "push", "--force-with-lease", "-u", "origin", f"{branch_name}:{branch_name}"],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error pushing to origin: {e}", file=sys.stderr)
            sys.exit(1)

    # --- GitHub PR Integration ---
    try:
        # Import locally to avoid potential circular dependencies
        try:
            from github import generate_pr_body, check_gh_installed
        except ImportError:
            # Fallback if running as module
            from .github import generate_pr_body, check_gh_installed

        if check_gh_installed():
            print("  🐙 GitHub CLI detected. Updating Pull Request...")
            pr_body = generate_pr_body(task)

            # Create a temp file for the body to handle multiline content safely
            import tempfile
            import json

            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                f.write(pr_body)
                body_file = f.name

            try:
                # Check if PR exists
                pr_check = subprocess.run(
                    [
                        "gh",
                        "pr",
                        "list",
                        "--head",
                        branch_name,
                        "--json",
                        "number",
                        "--state",
                        "open",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                prs = []
                if pr_check.returncode == 0 and pr_check.stdout.strip():
                    try:
                        prs = json.loads(pr_check.stdout)
                    except json.JSONDecodeError:
                        pass

                if prs:
                    # Update existing PR
                    pr_number = prs[0]["number"]
                    subprocess.run(
                        ["gh", "pr", "edit", str(pr_number), "--body-file", body_file],
                        check=True,
                        capture_output=True,
                    )
                    print(f"  ✅ Updated PR #{pr_number}")
                else:
                    # Create new PR
                    subprocess.run(
                        [
                            "gh",
                            "pr",
                            "create",
                            "--title",
                            task.title,
                            "--body-file",
                            body_file,
                            "--head",
                            branch_name,
                            "--base",
                            "main",
                        ],
                        check=True,
                        capture_output=True,
                    )
                    print("  ✅ Created new PR")

            except subprocess.CalledProcessError as e:
                # Don't fail the whole finish command if PR creation fails
                err_msg = e.stderr.decode().strip() if e.stderr else str(e)
                print(f"  ⚠️  Failed to manage PR: {err_msg}")
            except Exception as e:
                print(f"  ⚠️  Error in PR integration: {e}")
            finally:
                if os.path.exists(body_file):
                    os.unlink(body_file)

    except ImportError:
        print("  ⚠️  Could not import github module for PR integration.")
    except Exception as e:
        print(f"  ⚠️  Unexpected error in PR integration: {e}")

    # Update task status to merge_ready
    try:
        from lib.task_model import TaskStatus

        task.status = TaskStatus.MERGE_READY
        manager.storage.save_task(task)
        print("✅ Task marked as 'merge_ready'")

        # Auto-merge hook: attempt to merge immediately if no blockers
        _attempt_auto_merge(task, manager)

    except ImportError:
        print("Warning: Could not update task status (lib.task_model not available)")

    # Optionally nuke
    if do_nuke:
        print("Nuking worktree...")
        os.chdir(Path.home())  # Move out of worktree before nuking
        manager.nuke_worktree(task_id, force=False)
        print("Worktree removed")
    else:
        print(f"\nTo clean up later: polecat nuke {task_id}")


@main.command()
@click.argument("task_id")
@click.option("--force", "-f", is_flag=True, help="Delete even if work is not merged")
@click.pass_context
def nuke(ctx, task_id, force):
    """Destroy a polecat (remove worktree and branch)."""
    # Validate task ID before any operations
    try:
        validate_task_id_or_raise(task_id)
    except TaskIDValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    try:
        manager.nuke_worktree(task_id, force=force)
        print(f"Nuked polecat {task_id}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


@main.command("list")
@click.pass_context
def list_polecats(ctx):
    """List active polecats."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    if not manager.polecats_dir.exists():
        print("No polecats directory found.")
        return

    # Directories to exclude from listing (system dirs)
    exclude = {".repos", "crew"}

    found = False
    for item in manager.polecats_dir.iterdir():
        if item.is_dir() and not item.name.startswith(".") and item.name not in exclude:
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
@click.pass_context
def crew(ctx, project, name, gemini, resume):
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

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

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
        cmd = ["gemini", "--approval-mode", "yolo"]
    else:
        # Get aops-core plugin directory
        # aops_root = get_aops_root()
        # plugin_dir_core = aops_root / "aops-core"
        cmd = [
            "claude",
            "--permission-mode=plan",
            "--dangerously-skip-permissions",
            "--setting-sources=user",
            # "--plugin-dir",
            # plugin_dir_core,
        ]

    # Set session type environment variable for hooks to detect
    env = os.environ.copy()
    env["POLECAT_SESSION_TYPE"] = "crew"

    try:
        subprocess.run(cmd, cwd=crew_root, env=env)
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
@click.pass_context
def nuke_crew(ctx, name, force):
    """Remove a crew worker and their worktrees."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    try:
        manager.nuke_crew(name, force=force)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


@main.command("list-crew")
@click.pass_context
def list_crew(ctx):
    """List active crew workers."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))
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

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Step 1: Get/claim task
    if task_id:
        # Validate task ID before any operations
        try:
            validate_task_id_or_raise(task_id)
        except TaskIDValidationError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

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
        cmd = [
            "gemini",
            "--approval-mode",
            "yolo",
        ]
        # Note: Gemini CLI doesn't support --session-id; it uses --resume for session management
        # For now, each polecat run starts a fresh session

        if interactive:
            # -i starts interactive mode with initial prompt
            cmd.extend(["-i", prompt])
        else:
            # Headless mode with auto-approve
            cmd.extend(["-p", prompt])
    else:
        # Claude CLI
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--setting-sources=user",
        ]

        if interactive:
            # Interactive: just append the prompt as positional arg
            cmd.append(prompt)
        else:
            # Headless: use -p for print mode
            cmd.extend(["-p", prompt])

    # Set session type environment variable for hooks to detect
    env = os.environ.copy()
    env["POLECAT_SESSION_TYPE"] = "polecat"

    try:
        if interactive:
            # In interactive mode, we MUST NOT capture output or it will hang
            # and we want the user to see/interact with the CLI
            result = subprocess.run(
                cmd,
                cwd=worktree_path,
                env=env,
            )
            exit_code = result.returncode
            # No transcript to analyze in interactive mode (currently)
        else:
            result = subprocess.run(
                cmd,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                env=env,
            )
            exit_code = result.returncode
            # Display agent output after run
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            # Analyze the transcript for failures
            if hasattr(manager, "analyze_transcript"):
                manager.analyze_transcript(task, result.stdout, result.stderr)

    except FileNotFoundError:
        print(f"Error: '{cli_tool}' command not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Agent interrupted by user")
        exit_code = 130

    print("-" * 50)

    # Step 5: Auto-finish on success (unless disabled)
    if exit_code == 0:
        print("\n✅ Agent completed successfully.")
        if not no_auto_finish:
            print("🔄 Running auto-finish...")
            # Change to worktree directory and invoke finish directly
            original_cwd = os.getcwd()
            try:
                os.chdir(worktree_path)
                ctx.invoke(finish, no_push=False, do_nuke=False)
                print("✅ Auto-finish completed.")
            except SystemExit as e:
                if e.code != 0:
                    print("⚠️  Auto-finish failed.")
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
            print("📝 Auto-finish disabled. Run `polecat finish` when ready.")
            print(f"   Worktree: {worktree_path}")
    else:
        print(f"\n⚠️  Agent exited with code {exit_code}. Skipping auto-finish.")
        print(f"   Worktree: {worktree_path}")
        print(f"   To finish manually: cd {worktree_path} && polecat finish")


@main.command()
@click.argument("task_id")
@click.option("--transcript-lines", "-n", default=20, help="Number of transcript lines to show")
@click.pass_context
def analyze(ctx, task_id, transcript_lines):
    """Diagnose a stalled or failed task.

    Shows task metadata, worktree status, transcript tail, and suggested
    remediation actions for tasks that are stuck in_progress.

    Examples:
        polecat analyze aops-abc12345     # Full diagnostic
        polecat analyze aops-abc12345 -n 50  # Show more transcript
    """
    from datetime import datetime, timezone

    # Validate task ID
    try:
        validate_task_id_or_raise(task_id)
    except TaskIDValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Load task
    task = manager.storage.get_task(task_id)
    if not task:
        print(f"❌ Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Analyzing task: {task_id}")
    print("=" * 60)

    # --- Section 1: Task Metadata ---
    print("\n📋 TASK METADATA")
    print(f"   Title:    {task.title}")
    print(f"   Status:   {task.status.value if hasattr(task.status, 'value') else task.status}")
    print(f"   Assignee: {task.assignee or '(none)'}")
    print(f"   Project:  {task.project or 'aops'}")
    print(f"   Priority: P{task.priority}")

    # Calculate staleness
    if task.modified:
        now = datetime.now(timezone.utc)
        modified = task.modified
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=timezone.utc)
        age = now - modified
        hours = age.total_seconds() / 3600
        print(f"   Modified: {modified.isoformat()} ({hours:.1f}h ago)")

        # Flag staleness
        if hours > 4:
            print(f"   ⚠️  STALE: No activity for {hours:.1f} hours")

    # --- Section 2: Worktree Status ---
    print("\n📁 WORKTREE STATUS")
    worktree_path = manager.polecats_dir / task_id

    if not worktree_path.exists():
        print(f"   ❌ Worktree not found at {worktree_path}")
        print("   💡 Suggestion: Task may not have been started, or worktree was nuked")
    else:
        print(f"   ✓ Worktree exists at {worktree_path}")

        # Check git status
        import subprocess
        git_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if git_status.returncode == 0:
            if git_status.stdout.strip():
                changes = git_status.stdout.strip().split("\n")
                print(f"   ⚠️  Uncommitted changes ({len(changes)} files):")
                for line in changes[:5]:
                    print(f"      {line}")
                if len(changes) > 5:
                    print(f"      ... and {len(changes) - 5} more")
            else:
                print("   ✓ Working tree clean")
        else:
            print(f"   ❌ Git status failed: {git_status.stderr.strip()}")

        # Check branch and commits
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if branch_result.returncode == 0:
            branch = branch_result.stdout.strip()
            print(f"   Branch: {branch}")

            # Check commits ahead of main
            commits_result = subprocess.run(
                ["git", "log", "--oneline", "origin/main..HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if commits_result.returncode == 0 and commits_result.stdout.strip():
                commits = commits_result.stdout.strip().split("\n")
                print(f"   Commits ahead of main ({len(commits)}):")
                for commit in commits[:3]:
                    print(f"      {commit}")
                if len(commits) > 3:
                    print(f"      ... and {len(commits) - 3} more")
            else:
                print("   No commits ahead of main")

    # --- Section 3: Transcript (if available) ---
    print("\n📜 TRANSCRIPT")
    transcript_path = manager.home_dir / "transcripts" / f"{task_id}.jsonl"

    if not transcript_path.exists():
        print(f"   (No transcript found at {transcript_path})")
        print("   💡 Transcript capture may not be enabled yet")
    else:
        import json
        try:
            # Read last N lines
            with open(transcript_path, "r") as f:
                lines = f.readlines()

            if not lines:
                print("   (Transcript file is empty)")
            else:
                print(f"   Showing last {min(transcript_lines, len(lines))} of {len(lines)} entries:")
                print()
                for line in lines[-transcript_lines:]:
                    try:
                        entry = json.loads(line)
                        # Format depends on transcript structure
                        if "type" in entry:
                            print(f"   [{entry.get('type', '?')}] {entry.get('message', entry.get('content', str(entry)[:80]))}")
                        else:
                            print(f"   {str(entry)[:100]}")
                    except json.JSONDecodeError:
                        print(f"   {line.strip()[:100]}")
        except Exception as e:
            print(f"   ❌ Failed to read transcript: {e}")

    # --- Section 4: Suggested Remediation ---
    print("\n💡 SUGGESTED ACTIONS")

    status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)

    if status_str == "in_progress":
        if not worktree_path.exists():
            print("   1. Task claimed but no worktree - may have crashed during setup")
            print(f"      → Reset: polecat reset-stalled --hours 0 --project {task.project or 'aops'}")
            print("      → Or retry: polecat run -t {task_id}")
        elif hours > 4:
            print("   1. Task appears stalled (no activity > 4h)")
            print("      → Check if agent is still running")
            print("      → Reset if abandoned: polecat reset-stalled")
            print(f"      → Or manually finish: cd {worktree_path} && polecat finish")
        else:
            print("   1. Task is in progress and appears active")
            print("      → Wait for agent to complete, or check logs")
    elif status_str == "merge_ready":
        print("   1. Task ready to merge")
        print("      → Run: polecat merge")
    elif status_str == "review":
        print("   1. Task needs human review before merging")
        print(f"      → Review changes: cd {worktree_path}")
        print("      → Then set status to merge_ready or fix issues")
    elif status_str == "blocked":
        print("   1. Task is blocked")
        print("      → Check task body for blocker details")
        if task.depends_on:
            print(f"      → Depends on: {', '.join(task.depends_on)}")
    elif status_str == "done":
        print("   1. Task is already complete ✓")
        if worktree_path.exists():
            print(f"      → Consider cleanup: polecat nuke {task_id}")
    else:
        print(f"   Status is '{status_str}' - no specific suggestions")

    print()


@main.command("reset-stalled")
@click.option("--project", "-p", help="Filter by project")
@click.option("--hours", default=4.0, help="Hours since last modification (default: 4)")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be reset without changing"
)
@click.pass_context
def reset_stalled(ctx, project, hours, dry_run):
    """Reset stalled in_progress tasks back to active.

    Finds tasks that have been in_progress for > N hours and resets them.
    Useful for cleaning up after crashed/abandoned agents.
    """
    from datetime import datetime, timedelta, timezone

    try:
        from lib.task_model import TaskStatus
        from lib.task_index import TaskIndex
    except ImportError:
        print(
            "Error: Could not import task libraries. Ensure aops-core is available.",
            file=sys.stderr,
        )
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Calculate cutoff time
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    print(f"Checking for tasks stalled since {cutoff.isoformat()}...")

    # List tasks
    candidates = manager.storage.list_tasks(
        status=TaskStatus.IN_PROGRESS, project=project
    )

    stalled = []
    for task in candidates:
        # Ensure timezone awareness
        task_mod = task.modified
        if task_mod.tzinfo is None:
            task_mod = task_mod.replace(tzinfo=timezone.utc)

        if task_mod < cutoff:
            stalled.append(task)

    if not stalled:
        print("No stalled tasks found.")
        return

    print(f"Found {len(stalled)} stalled tasks (modified > {hours}h ago):")
    for t in stalled:
        print(f"  [{t.id}] {t.title} (modified: {t.modified.isoformat()})")

    if dry_run:
        print("\nDry run: no changes made.")
        return

    if not click.confirm(f"\nReset these {len(stalled)} tasks to ACTIVE?"):
        print("Aborted.")
        return

    reset_count = 0
    for task in stalled:
        try:
            task.status = TaskStatus.ACTIVE
            task.assignee = None
            manager.storage.save_task(task)
            reset_count += 1
        except Exception as e:
            print(f"Failed to reset {task.id}: {e}", file=sys.stderr)

    # Rebuild index
    if reset_count > 0:
        try:
            # Try to get data root from storage or use default
            data_root = manager.storage.data_root
            index = TaskIndex(data_root)
            index.rebuild_fast()
            print("Index rebuilt.")
        except Exception as e:
            print(f"Warning: Failed to rebuild index: {e}", file=sys.stderr)

    print(f"\n✅ Reset {reset_count} tasks.")


def _send_notification(title: str, message: str, urgency: str = "normal"):
    """Send a desktop notification via notify-send if available.

    Args:
        title: Notification title
        message: Notification body
        urgency: low, normal, or critical
    """
    import shutil

    print(f"[{urgency.upper()}] {title}: {message}")

    if shutil.which("notify-send"):
        try:
            import subprocess

            subprocess.run(
                ["notify-send", "-u", urgency, title, message],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass


@main.command()
@click.option(
    "--interval",
    "-i",
    default=300,
    help="Polling interval in seconds (default: 300 = 5 min)",
)
@click.option(
    "--stall-threshold",
    "-s",
    default=30,
    help="Minutes without progress before stall alert (default: 30)",
)
@click.option("--project", "-p", help="Project to monitor (default: all)")
@click.pass_context
def watch(ctx, interval, stall_threshold, project):
    """Monitor swarm activity and send desktop notifications.

    Runs as a background process that:
    - Polls for new PRs and merge_ready tasks
    - Sends notification when a new PR is filed
    - Alerts if swarm stalls (no progress in threshold minutes)

    Examples:
        polecat watch              # Default: poll every 5min, stall at 30min
        polecat watch -i 60        # Poll every 60 seconds
        polecat watch -s 60        # Alert after 60min of no progress
        polecat watch &            # Run in background
    """
    import signal
    import time
    from datetime import datetime, timedelta, timezone

    try:
        from lib.task_model import TaskStatus
    except ImportError:
        print("Error: Could not import task libraries.", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Track seen PRs and last activity time
    seen_merge_ready = set()
    seen_review = set()
    last_activity = datetime.now(timezone.utc)

    # Graceful shutdown
    stop_requested = False

    def handle_signal(signum, frame):
        nonlocal stop_requested
        print("\nShutting down watch...")
        stop_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print("Starting polecat watch...")
    print(f"  Polling interval: {interval}s")
    print(f"  Stall threshold: {stall_threshold}min")
    print(f"  Project filter: {project or 'all'}")
    print("  Press Ctrl+C to stop.\n")

    # Initial scan to populate seen sets (don't alert on startup)
    try:
        merge_ready_tasks = manager.storage.list_tasks(
            status=TaskStatus.MERGE_READY, project=project
        )
        for task in merge_ready_tasks:
            seen_merge_ready.add(task.id)

        review_tasks = manager.storage.list_tasks(
            status=TaskStatus.REVIEW, project=project
        )
        for task in review_tasks:
            seen_review.add(task.id)

        print(f"Initial state: {len(seen_merge_ready)} merge_ready, {len(seen_review)} review")
    except Exception as e:
        print(f"Warning: Initial scan failed: {e}")

    while not stop_requested:
        try:
            now = datetime.now(timezone.utc)

            # Check for new merge_ready tasks (new PRs filed)
            merge_ready_tasks = manager.storage.list_tasks(
                status=TaskStatus.MERGE_READY, project=project
            )
            for task in merge_ready_tasks:
                if task.id not in seen_merge_ready:
                    seen_merge_ready.add(task.id)
                    last_activity = now
                    _send_notification(
                        "PR Filed",
                        f"{task.id}: {task.title}",
                        urgency="normal",
                    )

            # Check for new review tasks (merge failures)
            review_tasks = manager.storage.list_tasks(
                status=TaskStatus.REVIEW, project=project
            )
            for task in review_tasks:
                if task.id not in seen_review:
                    seen_review.add(task.id)
                    last_activity = now
                    _send_notification(
                        "Review Needed",
                        f"{task.id}: {task.title}",
                        urgency="critical",
                    )

            # Check for completed tasks (mark as activity)
            manager.storage.list_tasks(
                status=TaskStatus.DONE, project=project
            )
            # We don't track done tasks, but finding new ones means progress
            # This is a simplification - in production you'd track these too

            # Check for in_progress tasks (active work)
            in_progress = manager.storage.list_tasks(
                status=TaskStatus.IN_PROGRESS, project=project
            )
            if in_progress:
                # Check if any were modified recently
                for task in in_progress:
                    task_mod = task.modified
                    if task_mod.tzinfo is None:
                        task_mod = task_mod.replace(tzinfo=timezone.utc)
                    if task_mod > last_activity:
                        last_activity = task_mod

            # Check for stall
            stall_cutoff = now - timedelta(minutes=stall_threshold)
            if last_activity < stall_cutoff:
                minutes_stalled = int((now - last_activity).total_seconds() / 60)
                _send_notification(
                    "Swarm Stalled",
                    f"No progress in {minutes_stalled} minutes",
                    urgency="critical",
                )
                # Reset to avoid spamming alerts
                last_activity = now

            # Status line
            active_count = len(in_progress)
            ready_count = len(merge_ready_tasks)
            review_count = len(review_tasks)
            timestamp = now.strftime("%H:%M:%S")
            print(
                f"[{timestamp}] active={active_count} merge_ready={ready_count} review={review_count}"
            )

        except Exception as e:
            print(f"Error during poll: {e}")

        # Sleep in small chunks to allow interrupt
        for _ in range(interval):
            if stop_requested:
                break
            time.sleep(1)

    print("Watch stopped.")


@main.command()
@click.option("--claude", "-c", default=0, help="Number of Claude workers")
@click.option("--gemini", "-g", default=0, help="Number of Gemini workers")
@click.option("--project", "-p", help="Project to focus on (default: all)")
@click.option(
    "--caller", default="polecat", help="Identity claiming the tasks (default: bot)"
)
@click.option("--dry-run", is_flag=True, help="Simulate execution")
@click.pass_context
def swarm(ctx, claude, gemini, project, caller, dry_run):
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

    home = ctx.obj.get("home")
    run_swarm(claude, gemini, project, caller, dry_run, str(home) if home else None)


def parse_duration(duration_str: str) -> int:
    """Parse a duration string like '8h', '1d', '30m' into seconds.

    Args:
        duration_str: Duration string with suffix h (hours), d (days), or m (minutes)

    Returns:
        Duration in seconds

    Raises:
        ValueError: If format is invalid
    """
    if not duration_str:
        raise ValueError("Duration string cannot be empty")

    duration_str = duration_str.strip().lower()

    # Handle numeric-only input (default to hours)
    if duration_str.isdigit():
        return int(duration_str) * 3600

    if len(duration_str) < 2:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value_str = duration_str[:-1]
    unit = duration_str[-1]

    try:
        value = float(value_str)
    except ValueError:
        raise ValueError(f"Invalid duration value: {value_str}")

    multipliers = {
        "m": 60,  # minutes
        "h": 3600,  # hours
        "d": 86400,  # days
    }

    if unit not in multipliers:
        raise ValueError(f"Unknown duration unit: {unit}. Use m, h, or d")

    return int(value * multipliers[unit])


@main.command()
@click.option(
    "--since",
    "-s",
    default="8h",
    help="Time period to summarize (e.g., 8h, 1d, 30m). Default: 8h",
)
@click.option("--project", "-p", help="Filter by project (default: all)")
@click.pass_context
def summary(ctx, since, project):
    """Generate a summary of polecat swarm work.

    Shows merged PRs, completed tasks, and queue changes for the specified
    time period. Output is markdown suitable for daily notes.

    Examples:
        polecat summary                # Last 8 hours
        polecat summary --since 1d     # Last day
        polecat summary -s 4h -p aops  # Last 4 hours, aops only
    """
    import subprocess
    import json
    from datetime import datetime, timedelta, timezone

    try:
        from lib.task_model import TaskStatus
    except ImportError:
        print(
            "Error: Could not import task libraries. Ensure aops-core is available.",
            file=sys.stderr,
        )
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Parse the duration
    try:
        seconds = parse_duration(since)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    # Format duration for display
    if seconds >= 86400:
        duration_display = f"{seconds // 86400} day(s)"
    elif seconds >= 3600:
        duration_display = f"{seconds // 3600} hour(s)"
    else:
        duration_display = f"{seconds // 60} minute(s)"

    print(f"## Polecat Swarm Summary (last {duration_display})")
    print()

    # --- Merged PRs ---
    print("### PRs Merged")
    print()

    merged_prs = []
    try:
        # Query GitHub for merged PRs
        # gh pr list --state merged returns PRs merged, filtered by date
        gh_cmd = [
            "gh",
            "pr",
            "list",
            "--state",
            "merged",
            "--search",
            f"merged:>{cutoff_iso[:10]}",  # Date only for search
            "--json",
            "number,title,mergedAt,headRefName",
            "--limit",
            "100",
        ]

        result = subprocess.run(gh_cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0 and result.stdout.strip():
            all_prs = json.loads(result.stdout)

            # Filter by actual merged time (gh search is date-only)
            for pr in all_prs:
                merged_at = pr.get("mergedAt", "")
                if merged_at:
                    # Parse ISO timestamp
                    try:
                        merged_dt = datetime.fromisoformat(
                            merged_at.replace("Z", "+00:00")
                        )
                        if merged_dt >= cutoff:
                            # Filter by project if specified
                            if project:
                                # Check if branch matches project pattern
                                branch = pr.get("headRefName", "")
                                if not branch.startswith("polecat/"):
                                    continue
                            merged_prs.append(pr)
                    except (ValueError, TypeError):
                        pass

            if merged_prs:
                print(f"**{len(merged_prs)} PRs merged**")
                print()
                for pr in merged_prs[:20]:  # Limit display
                    print(f"- #{pr['number']}: {pr['title']}")
                if len(merged_prs) > 20:
                    print(f"- ... and {len(merged_prs) - 20} more")
            else:
                print("No PRs merged in this period.")
        else:
            print("(Could not query GitHub - gh CLI not available or not authenticated)")

    except FileNotFoundError:
        print("(GitHub CLI not installed)")
    except Exception as e:
        print(f"(GitHub query failed: {e})")

    print()

    # --- Completed Tasks ---
    print("### Tasks Completed")
    print()

    completed_tasks = []
    try:
        # Get all done tasks and filter by modified time
        all_done = manager.storage.list_tasks(status=TaskStatus.DONE, project=project)

        for task in all_done:
            task_mod = task.modified
            # Handle both date and datetime objects
            if hasattr(task_mod, "tzinfo"):
                # It's a datetime
                if task_mod.tzinfo is None:
                    task_mod = task_mod.replace(tzinfo=timezone.utc)
            else:
                # It's a date - convert to datetime at midnight UTC
                task_mod = datetime.combine(task_mod, datetime.min.time(), tzinfo=timezone.utc)

            if task_mod >= cutoff:
                completed_tasks.append(task)

        if completed_tasks:
            print(f"**{len(completed_tasks)} tasks completed**")
            print()
            for task in completed_tasks[:20]:
                print(f"- [{task.id}] {task.title}")
            if len(completed_tasks) > 20:
                print(f"- ... and {len(completed_tasks) - 20} more")
        else:
            print("No tasks completed in this period.")

    except Exception as e:
        print(f"(Task query failed: {e})")

    print()

    # --- Queue Status ---
    print("### Queue Status")
    print()

    try:
        # Count tasks by status
        ready_tasks = manager.storage.get_ready_tasks(project=project)
        in_progress = manager.storage.list_tasks(
            status=TaskStatus.IN_PROGRESS, project=project
        )
        blocked = manager.storage.list_tasks(status=TaskStatus.BLOCKED, project=project)
        review = manager.storage.list_tasks(status=TaskStatus.REVIEW, project=project)
        merge_ready = manager.storage.list_tasks(
            status=TaskStatus.MERGE_READY, project=project
        )

        print(f"- **Ready**: {len(ready_tasks)} tasks")
        print(f"- **In Progress**: {len(in_progress)} tasks")
        print(f"- **Blocked**: {len(blocked)} tasks")
        print(f"- **Review**: {len(review)} tasks")
        print(f"- **Merge Ready**: {len(merge_ready)} tasks")
        print(f"- **Completed** (this period): {len(completed_tasks)} tasks")

    except Exception as e:
        print(f"(Queue status query failed: {e})")

    print()

    # --- Active Workers ---
    print("### Active Workers")
    print()

    try:
        # Count active polecats (worktrees)
        exclude = {".repos", "crew", ".git"}
        active_polecats = [
            d.name
            for d in manager.polecats_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in exclude
        ]

        # Count crew workers
        crew_workers = manager.list_crew()

        if active_polecats:
            print(f"- **Polecats**: {len(active_polecats)} active worktrees")
        else:
            print("- **Polecats**: None active")

        if crew_workers:
            print(f"- **Crew**: {len(crew_workers)} workers ({', '.join(crew_workers)})")
        else:
            print("- **Crew**: None active")

    except Exception as e:
        print(f"(Worker status query failed: {e})")

    print()


if __name__ == "__main__":
    main()
