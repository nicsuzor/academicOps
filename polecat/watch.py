#!/usr/bin/env python3
"""Polecat watch command: monitor swarm activity and send desktop notifications."""

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
from polecat.observability import metrics


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


@click.command()
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
    from datetime import timedelta

    _use_legacy = False
    try:
        from lib.task_model import TaskStatus

        _use_legacy = True
    except ImportError:
        pass

    manager = PolecatManager(home_dir=ctx.obj.get("home"), verbose=ctx.obj.get("verbose", False))

    # Track seen PRs and last activity time
    seen_merge_ready = set()
    seen_review = set()
    last_activity = datetime.now().astimezone()

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

    def _list(status, proj=project):
        if manager.storage is not None and _use_legacy:
            return manager.storage.list_tasks(
                status=getattr(TaskStatus, status.upper()), project=proj
            )
        from polecat.pkb_bridge import list_tasks as pkb_list_tasks

        return pkb_list_tasks(status=status, project=proj)

    def _ready(proj=project):
        if manager.storage is not None and _use_legacy:
            return manager.storage.get_ready_tasks(project=proj)
        from polecat.pkb_bridge import get_ready_tasks as pkb_ready

        return pkb_ready(project=proj)

    # Initial scan to populate seen sets (don't alert on startup)
    try:
        merge_ready_tasks = _list("merge_ready")
        for task in merge_ready_tasks:
            seen_merge_ready.add(task.id)

        review_tasks = _list("review")
        for task in review_tasks:
            seen_review.add(task.id)

        print(f"Initial state: {len(seen_merge_ready)} merge_ready, {len(seen_review)} review")
    except Exception as e:
        print(f"Warning: Initial scan failed: {e}")

    while not stop_requested:
        try:
            now = datetime.now().astimezone()

            # Check for new merge_ready tasks (new PRs filed)
            merge_ready_tasks = _list("merge_ready")
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
            review_tasks = _list("review")
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
            _list("done")
            # We don't track done tasks, but finding new ones means progress
            # This is a simplification - in production you'd track these too

            # Check for in_progress tasks (active work)
            in_progress = _list("in_progress")
            if in_progress:
                # Check if any were modified recently
                for task in in_progress:
                    task_mod = task.modified
                    if task_mod and task_mod.tzinfo is None:
                        task_mod = task_mod.replace(tzinfo=UTC)
                    if task_mod and task_mod > last_activity:
                        last_activity = task_mod

            # Get leaf-ready tasks (actually pullable work)
            leaf_ready = _ready()

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

            # Status line (leaf-ready is the primary queue metric).
            # Metric label uses the canonical PKB status `in_progress` (per
            # aops-core/skills/remember/references/TAXONOMY.md) rather than
            # the legacy "active" label.
            ready_count = len(leaf_ready)
            in_progress_count = len(in_progress)
            merge_ready_count = len(merge_ready_tasks)
            review_count = len(review_tasks)
            timestamp = now.strftime("%H:%M:%S")
            print(
                f"[{timestamp}] ready={ready_count} in_progress={in_progress_count} merge_ready={merge_ready_count} review={review_count}"
            )

            # Record periodic metrics for dashboard
            metrics.record_queue_depth("ready", count=ready_count, project=project)
            metrics.record_queue_depth("in_progress", count=in_progress_count, project=project)
            metrics.record_queue_depth("merge_ready", count=merge_ready_count, project=project)
            metrics.record_queue_depth("review", count=review_count, project=project)

        except Exception as e:
            print(f"Error during poll: {e}")

        # Sleep in small chunks to allow interrupt
        for _ in range(interval):
            if stop_requested:
                break
            time.sleep(1)

    print("Watch stopped.")
