#!/usr/bin/env python3
"""Polecat summary command: generate a summary of swarm work over a time period."""

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
    except ValueError as e:
        raise ValueError(f"Invalid duration value: {value_str}") from e

    multipliers = {
        "m": 60,  # minutes
        "h": 3600,  # hours
        "d": 86400,  # days
    }

    if unit not in multipliers:
        raise ValueError(f"Unknown duration unit: {unit}. Use m, h, or d")

    return int(value * multipliers[unit])


@click.command()
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
    import json
    import subprocess
    from datetime import timedelta

    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    def _list(status, proj=project):
        if manager.storage is not None:
            try:
                from lib.task_model import TaskStatus

                return manager.storage.list_tasks(
                    status=getattr(TaskStatus, status.upper()), project=proj
                )
            except ImportError:
                pass
        from polecat.pkb_bridge import list_tasks as pkb_list_tasks

        return pkb_list_tasks(status=status, project=proj)

    def _ready(proj=project):
        if manager.storage is not None:
            try:
                from lib.task_model import TaskStatus  # noqa: F401, F811

                return manager.storage.get_ready_tasks(project=proj)
            except ImportError:
                pass
        from polecat.pkb_bridge import get_ready_tasks as pkb_ready

        return pkb_ready(project=proj)

    # Parse the duration
    try:
        seconds = parse_duration(since)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    cutoff = datetime.now().astimezone() - timedelta(seconds=seconds)
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
                        merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
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
        all_done = _list("done")

        for task in all_done:
            task_mod = task.modified
            if task_mod is None:
                continue
            # Handle both date and datetime objects
            if hasattr(task_mod, "tzinfo"):
                # It's a datetime
                if task_mod.tzinfo is None:
                    task_mod = task_mod.replace(tzinfo=UTC)
            else:
                # It's a date - convert to datetime at midnight UTC
                task_mod = datetime.combine(task_mod, datetime.min.time(), tzinfo=UTC)

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
        ready_tasks = _ready()
        in_progress = _list("in_progress")
        blocked = _list("blocked")
        review = _list("review")
        merge_ready = _list("merge_ready")

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
        active_polecats = [
            d.name
            for d in manager.polecats_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
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
