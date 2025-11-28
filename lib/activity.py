#!/usr/bin/env python3
"""
Activity logging for aOps framework.

Provides simple JSONL-based activity logging to track framework operations:
- All logs written to $ACA_DATA/logs/activity.jsonl
- One JSON object per line (JSONL format)
- ISO 8601 timestamps
- Automatic directory creation
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lib.paths import get_logs_dir


def log_activity(action: str, session: str = "session") -> None:
    """
    Log an activity to the framework activity log.

    Writes a single JSONL entry to $ACA_DATA/logs/activity.jsonl with:
    - timestamp: ISO 8601 format with timezone
    - session: Session identifier
    - action: Description of what happened

    Creates the logs directory if it doesn't exist (fail-fast if ACA_DATA not set).

    Args:
        action: Description of the activity being logged
        session: Session identifier (default: "session")

    Raises:
        RuntimeError: If ACA_DATA environment variable not set (propagated from get_logs_dir)
    """
    # Get logs directory (fails fast if ACA_DATA not set)
    logs_dir = get_logs_dir()

    # Create logs directory if missing
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Build log entry
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session": session,
        "action": action,
    }

    # Append to activity log
    activity_log = logs_dir / "activity.jsonl"
    with activity_log.open("a") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()
