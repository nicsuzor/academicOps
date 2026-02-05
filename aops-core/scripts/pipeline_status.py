#!/usr/bin/env python3
"""Display session insights pipeline status and health.

A simple CLI dashboard for monitoring pipeline health.

Usage:
    pipeline_status.py [--json]

Options:
    --json    Output raw JSON instead of formatted display
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add aops-core to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.pipeline_metrics import (
    check_alerts,
    format_alerts,
    load_pipeline_metrics,
)


def format_timestamp(ts: str | None) -> str:
    """Format ISO timestamp to human-readable."""
    if not ts:
        return "Never"
    try:
        dt = datetime.fromisoformat(ts)
        now = datetime.now(timezone.utc)
        delta = now - dt
        if delta.total_seconds() < 60:
            return "Just now"
        if delta.total_seconds() < 3600:
            mins = int(delta.total_seconds() / 60)
            return f"{mins}m ago"
        if delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"{hours}h ago"
        days = int(delta.total_seconds() / 86400)
        return f"{days}d ago"
    except ValueError:
        return ts


def format_status_icon(status: str) -> str:
    """Get icon for health status."""
    icons = {
        "healthy": "✅",
        "warning": "⚠️",
        "degraded": "🟠",
        "critical": "🚨",
        "unknown": "❓",
    }
    return icons.get(status, "❓")


def display_dashboard(metrics: dict) -> None:
    """Display formatted dashboard."""
    print("=" * 60)
    print("   SESSION INSIGHTS PIPELINE STATUS")
    print("=" * 60)
    print()

    # Health summary
    health = metrics["health"]
    status = health["status"]
    icon = format_status_icon(status)
    print(f"  Status: {icon} {status.upper()}")
    print(f"  Last Success: {format_timestamp(health['last_successful_run'])}")
    print(f"  Consecutive Failures: {health['consecutive_failures']}")
    print(f"  24h Uptime: {health['uptime_24h']:.0%}")
    print()

    # Cumulative stats
    cumulative = metrics["cumulative"]
    print("-" * 60)
    print("  CUMULATIVE STATISTICS")
    print("-" * 60)
    print(f"  Total Runs: {cumulative['total_runs']}")
    print(
        f"  Success Rate: {cumulative['total_success']}/{cumulative['total_runs']} ",
        end="",
    )
    if cumulative["total_runs"] > 0:
        rate = cumulative["total_success"] / cumulative["total_runs"]
        print(f"({rate:.0%})")
    else:
        print("(N/A)")
    print(f"  Sessions Processed: {cumulative['total_sessions_processed']}")
    print(f"  Sessions Failed: {cumulative['total_sessions_failed']}")
    print(f"  Avg Task Match Rate: {cumulative['avg_task_match_rate']:.0%}")
    print(f"  Avg Run Duration: {cumulative['avg_run_duration_ms']}ms")
    print()

    # Quality metrics
    print("-" * 60)
    print("  QUALITY METRICS")
    print("-" * 60)
    print(f"  Validation Errors: {cumulative['total_validation_errors']}")
    print(f"  Malformed JSON: {cumulative['total_malformed_json']}")
    print()

    # Current/last run
    current_run = metrics["current_run"]
    if current_run:
        print("-" * 60)
        print("  LAST RUN")
        print("-" * 60)
        print(f"  Timestamp: {format_timestamp(current_run['run_timestamp'])}")
        print(f"  Status: {current_run['run_status']}")
        print(f"  Trigger: {current_run['run_trigger']}")
        print(f"  Duration: {current_run['run_duration_ms']}ms")
        print(
            f"  Sessions: {current_run['sessions_processed']} processed, {current_run['sessions_failed']} failed"
        )
        if (
            current_run["sessions_with_task_match"]
            + current_run["sessions_no_task_match"]
            > 0
        ):
            total = (
                current_run["sessions_with_task_match"]
                + current_run["sessions_no_task_match"]
            )
            rate = current_run["sessions_with_task_match"] / total
            print(
                f"  Task Match: {current_run['sessions_with_task_match']}/{total} ({rate:.0%})"
            )
        print()

    # Alerts
    alerts = check_alerts(metrics)
    if alerts:
        print("-" * 60)
        print("  ALERTS")
        print("-" * 60)
        print(format_alerts(alerts))
        print()

    print("=" * 60)
    print(f"  Last Updated: {format_timestamp(metrics['last_updated'])}")
    print("=" * 60)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Display session insights pipeline status"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted display",
    )
    args = parser.parse_args()

    metrics = load_pipeline_metrics()

    if metrics is None:
        if args.json:
            print(json.dumps({"error": "No metrics file found", "status": "unknown"}))
        else:
            print("No pipeline metrics found.")
            print("Run the session insights pipeline to generate metrics.")
        return 1

    if args.json:
        # Add computed alerts to JSON output
        metrics["alerts"] = check_alerts(metrics)
        print(json.dumps(metrics, indent=2))
    else:
        display_dashboard(metrics)

    return 0


if __name__ == "__main__":
    sys.exit(main())
