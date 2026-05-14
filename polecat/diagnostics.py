#!/usr/bin/env python3
"""Polecat diagnostics commands: analyze and reset-stalled."""

import sys
from datetime import UTC, datetime
from pathlib import Path

# Add aops-core to path for lib imports (mirrors polecat/cli.py)
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT / "aops-core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "aops-core"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import click

from polecat.manager import PolecatManager
from polecat.validation import TaskIDValidationError, validate_task_id_or_raise


@click.command()
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

    # Validate task ID
    try:
        validate_task_id_or_raise(task_id)
    except TaskIDValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Load task
    if manager.storage is not None:
        task = manager.storage.get_task(task_id)
    else:
        from polecat.pkb_bridge import get_task as pkb_get_task

        task = pkb_get_task(task_id)
    if not task:
        print(f"❌ Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Analyzing task: {task_id}")
    print("=" * 60)

    # --- Section 1: Task Metadata ---
    print("\n📋 TASK METADATA")
    print(f"   Title:    {task.title}")
    print(f"   Status:   {task.status}")
    print(f"   Assignee: {task.assignee or '(none)'}")
    print(f"   Project:  {task.project or 'aops'}")
    print(f"   Priority: P{task.priority}")

    # Calculate staleness
    if task.modified:
        now = datetime.now().astimezone()
        modified = task.modified
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=UTC)
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
    try:
        from lib.paths import find_polecat_transcript

        transcript_path = find_polecat_transcript(task_id)
    except ImportError:
        transcript_path = manager.home_dir / "transcripts" / f"{task_id}.jsonl"

    if not transcript_path.exists():
        print(f"   (No transcript found at {transcript_path})")
        print("   💡 Transcript capture may not be enabled yet")
    else:
        import json

        try:
            # Read last N lines
            with open(transcript_path) as f:
                lines = f.readlines()

            if not lines:
                print("   (Transcript file is empty)")
            else:
                print(
                    f"   Showing last {min(transcript_lines, len(lines))} of {len(lines)} entries:"
                )
                print()
                for line in lines[-transcript_lines:]:
                    try:
                        entry = json.loads(line)
                        # Format depends on transcript structure
                        if "type" in entry:
                            print(
                                f"   [{entry.get('type', '?')}] {entry.get('message', entry.get('content', str(entry)[:80]))}"
                            )
                        else:
                            print(f"   {str(entry)[:100]}")
                    except json.JSONDecodeError:
                        print(f"   {line.strip()[:100]}")
        except Exception as e:
            print(f"   ❌ Failed to read transcript: {e}")

    # --- Section 4: Suggested Remediation ---
    print("\n💡 SUGGESTED ACTIONS")

    status_str = task.status or ""

    if status_str == "in_progress":
        if not worktree_path.exists():
            print("   1. Task claimed but no worktree - may have crashed during setup")
            print(
                f"      → Reset: polecat reset-stalled --hours 0 --project {task.project or 'aops'}"
            )
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


@click.command("reset-stalled")
@click.option("--project", "-p", help="Filter by project")
@click.option("--hours", default=4.0, help="Hours since last modification (default: 4)")
@click.option("--dry-run", is_flag=True, help="Show what would be reset without changing")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt (required in non-interactive mode)",
)
@click.pass_context
def reset_stalled(ctx, project, hours, dry_run, force):
    """Reset stalled in_progress tasks back to active.

    Finds tasks that have been in_progress for > N hours and resets them.
    Useful for cleaning up after crashed/abandoned agents.
    """
    from datetime import timedelta

    _TaskIndex = None
    try:
        from lib.task_index import TaskIndex as _TaskIndex
    except ImportError:
        pass

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    # Calculate cutoff time
    cutoff = datetime.now().astimezone() - timedelta(hours=hours)

    print(f"Checking for tasks stalled since {cutoff.isoformat()}...")

    # List tasks
    if manager.storage is not None:
        try:
            from lib.task_model import TaskStatus

            candidates = manager.storage.list_tasks(status=TaskStatus.IN_PROGRESS, project=project)
        except ImportError:
            candidates = []
    else:
        from polecat.pkb_bridge import list_tasks as pkb_list_tasks

        candidates = pkb_list_tasks(status="in_progress", project=project)

    stalled = []
    pr_locked = []
    for task in candidates:
        # Ensure timezone awareness
        task_mod = task.modified
        if task_mod is None:
            continue
        if task_mod.tzinfo is None:
            task_mod = task_mod.replace(tzinfo=UTC)

        if task_mod < cutoff:
            # Never reset tasks that have an open PR — they are locked by prior work.
            if task.pr_url or task.pr:
                pr_locked.append(task)
            else:
                stalled.append(task)

    if pr_locked:
        print(f"Skipping {len(pr_locked)} PR-locked tasks (have open PR — will not reset):")
        for t in pr_locked:
            pr_ref = t.pr_url or f"#{t.pr}"
            print(f"  [{t.id}] {t.title} (PR: {pr_ref})")

    if not stalled:
        print("No stalled tasks found.")
        return

    print(f"Found {len(stalled)} stalled tasks (modified > {hours}h ago):")
    for t in stalled:
        print(f"  [{t.id}] {t.title} (modified: {t.modified.isoformat()})")

    if dry_run:
        print("\nDry run: no changes made.")
        return

    if not force:
        print(f"\nError: This will reset {len(stalled)} tasks. Use --force to confirm.")
        sys.exit(1)

    reset_count = 0
    for task in stalled:
        try:
            task.status = "queued"
            task.assignee = None
            if manager.storage is not None:
                try:
                    from lib.task_model import TaskStatus

                    _status_attr = getattr(
                        TaskStatus, "QUEUED", getattr(TaskStatus, "ACTIVE", None)
                    )
                    if _status_attr is not None:
                        task.status = _status_attr.value
                except (ImportError, AttributeError):
                    pass
                manager.storage.save_task(task)
            else:
                from polecat.pkb_bridge import save_task as pkb_save

                pkb_save(task)
            reset_count += 1
        except Exception as e:
            print(f"Failed to reset {task.id}: {e}", file=sys.stderr)

    # Rebuild index (only relevant for legacy TaskIndex)
    if reset_count > 0 and _TaskIndex is not None and manager.storage is not None:
        try:
            data_root = manager.storage.data_root
            index = _TaskIndex(data_root)
            index.rebuild_fast()
            print("Index rebuilt.")
        except Exception as e:
            print(f"Warning: Failed to rebuild index: {e}", file=sys.stderr)

    print(f"\n✅ Reset {reset_count} tasks.")
