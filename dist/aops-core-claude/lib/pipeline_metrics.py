"""Pipeline metrics collection for session insights.

Provides unified metrics collection and persistence for monitoring
the session insights generation pipeline.

Usage:
    from lib.pipeline_metrics import PipelineMetrics

    metrics = PipelineMetrics()
    metrics.start_run(trigger="skill")

    # During processing
    metrics.record_session_scanned()
    metrics.record_session_processed()
    metrics.record_validation_error("Missing required field")

    # At end
    metrics.end_run(status="success")
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

RunStatus = Literal["success", "partial", "failure"]
RunTrigger = Literal["manual", "skill", "hook", "batch"]


def get_metrics_dir() -> Path:
    """Get metrics directory.

    Returns ~/writing/sessions/summaries/.metrics/

    Returns:
        Path to metrics directory
    """
    metrics_dir = Path.home() / "writing" / "sessions" / "summaries" / ".metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    return metrics_dir


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON file using temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path_str = tempfile.mkstemp(
        suffix=".json", prefix="metrics-", dir=str(path.parent)
    )
    temp_path = Path(temp_path_str)
    fd_closed = False

    try:
        os.write(fd, json.dumps(data, indent=2).encode())
        os.close(fd)
        fd_closed = True
        temp_path.rename(path)
    except Exception:
        if not fd_closed:
            os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise


class PipelineMetrics:
    """Collect and persist pipeline metrics for session insights."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._metrics_dir = get_metrics_dir()
        self._metrics_file = self._metrics_dir / "pipeline-metrics.json"
        self._runs_file = self._metrics_dir / "runs.jsonl"

        # Current run state
        self._run_start: datetime | None = None
        self._run_trigger: RunTrigger = "manual"

        # Processing counters
        self._sessions_scanned = 0
        self._sessions_pending = 0
        self._sessions_processed = 0
        self._sessions_failed = 0
        self._sessions_skipped = 0

        # Quality counters
        self._validation_errors = 0
        self._malformed_json = 0
        self._empty_responses = 0
        self._coercions_applied = 0

        # Task sync counters
        self._sessions_with_task_match = 0
        self._sessions_no_task_match = 0
        self._accomplishments_synced = 0

        # Error tracking
        self._errors: list[str] = []

    def start_run(self, trigger: RunTrigger = "manual") -> None:
        """Start a new pipeline run.

        Args:
            trigger: What triggered the run
        """
        self._run_start = datetime.now(timezone.utc)
        self._run_trigger = trigger

        # Reset counters
        self._sessions_scanned = 0
        self._sessions_pending = 0
        self._sessions_processed = 0
        self._sessions_failed = 0
        self._sessions_skipped = 0
        self._validation_errors = 0
        self._malformed_json = 0
        self._empty_responses = 0
        self._coercions_applied = 0
        self._sessions_with_task_match = 0
        self._sessions_no_task_match = 0
        self._accomplishments_synced = 0
        self._errors = []

    def record_session_scanned(self, count: int = 1) -> None:
        """Record sessions scanned for pending."""
        self._sessions_scanned += count

    def record_session_pending(self, count: int = 1) -> None:
        """Record sessions found needing processing."""
        self._sessions_pending += count

    def record_session_processed(self) -> None:
        """Record a successfully processed session."""
        self._sessions_processed += 1

    def record_session_failed(self, error: str | None = None) -> None:
        """Record a failed session processing."""
        self._sessions_failed += 1
        if error:
            self._errors.append(error)

    def record_session_skipped(self) -> None:
        """Record a skipped session."""
        self._sessions_skipped += 1

    def record_validation_error(self, error: str | None = None) -> None:
        """Record a schema validation error."""
        self._validation_errors += 1
        if error:
            self._errors.append(f"Validation: {error}")

    def record_malformed_json(self, error: str | None = None) -> None:
        """Record a malformed JSON response."""
        self._malformed_json += 1
        if error:
            self._errors.append(f"JSON: {error}")

    def record_empty_response(self) -> None:
        """Record an empty LLM response."""
        self._empty_responses += 1

    def record_coercion(self, field: str | None = None) -> None:
        """Record a type coercion applied."""
        self._coercions_applied += 1

    def record_task_match(self, accomplishments_count: int = 0) -> None:
        """Record a session matched to a task."""
        self._sessions_with_task_match += 1
        self._accomplishments_synced += accomplishments_count

    def record_no_task_match(self) -> None:
        """Record a session with no task match."""
        self._sessions_no_task_match += 1

    def _calculate_task_match_rate(self) -> float:
        """Calculate task match rate."""
        total = self._sessions_with_task_match + self._sessions_no_task_match
        if total == 0:
            return 0.0
        return self._sessions_with_task_match / total

    def _determine_status(self) -> RunStatus:
        """Determine overall run status."""
        if self._sessions_failed > 0 and self._sessions_processed == 0:
            return "failure"
        if self._sessions_failed > 0:
            return "partial"
        return "success"

    def end_run(self, status: RunStatus | None = None, error: str | None = None) -> dict[str, Any]:
        """End the current run and persist metrics.

        Args:
            status: Override auto-determined status
            error: Error message if run failed

        Returns:
            Current run metrics dict
        """
        if self._run_start is None:
            self._run_start = datetime.now(timezone.utc)

        run_end = datetime.now(timezone.utc)
        run_duration_ms = int((run_end - self._run_start).total_seconds() * 1000)

        final_status = status or self._determine_status()

        # Build current run record
        current_run = {
            "run_timestamp": self._run_start.isoformat(),
            "run_duration_ms": run_duration_ms,
            "run_status": final_status,
            "run_error": error or (self._errors[0] if self._errors else None),
            "run_trigger": self._run_trigger,
            "sessions_scanned": self._sessions_scanned,
            "sessions_pending": self._sessions_pending,
            "sessions_processed": self._sessions_processed,
            "sessions_failed": self._sessions_failed,
            "sessions_skipped": self._sessions_skipped,
            "validation_errors": self._validation_errors,
            "malformed_json": self._malformed_json,
            "empty_responses": self._empty_responses,
            "coercions_applied": self._coercions_applied,
            "sessions_with_task_match": self._sessions_with_task_match,
            "sessions_no_task_match": self._sessions_no_task_match,
            "accomplishments_synced": self._accomplishments_synced,
        }

        # Load existing metrics or initialize
        metrics = self._load_or_init_metrics()

        # Update cumulative
        metrics["cumulative"]["total_runs"] += 1
        if final_status == "success":
            metrics["cumulative"]["total_success"] += 1
        else:
            metrics["cumulative"]["total_failures"] += 1
        metrics["cumulative"]["total_sessions_processed"] += self._sessions_processed
        metrics["cumulative"]["total_sessions_failed"] += self._sessions_failed
        metrics["cumulative"]["total_validation_errors"] += self._validation_errors
        metrics["cumulative"]["total_malformed_json"] += self._malformed_json

        # Update rolling averages
        n = metrics["cumulative"]["total_runs"]
        old_avg_rate = metrics["cumulative"]["avg_task_match_rate"]
        new_rate = self._calculate_task_match_rate()
        metrics["cumulative"]["avg_task_match_rate"] = (
            (old_avg_rate * (n - 1) + new_rate) / n if n > 0 else new_rate
        )

        old_avg_duration = metrics["cumulative"]["avg_run_duration_ms"]
        metrics["cumulative"]["avg_run_duration_ms"] = int(
            (old_avg_duration * (n - 1) + run_duration_ms) / n if n > 0 else run_duration_ms
        )

        # Update health
        if final_status == "success":
            metrics["health"]["last_successful_run"] = self._run_start.isoformat()
            metrics["health"]["consecutive_failures"] = 0
        else:
            metrics["health"]["consecutive_failures"] += 1

        # Calculate health status
        metrics["health"]["status"] = self._calculate_health_status(metrics["health"])

        # Set current run
        metrics["current_run"] = current_run
        metrics["last_updated"] = run_end.isoformat()

        # Persist
        _atomic_write_json(self._metrics_file, metrics)
        self._append_run_log(current_run)

        return current_run

    def _load_or_init_metrics(self) -> dict[str, Any]:
        """Load existing metrics file or initialize."""
        if self._metrics_file.exists():
            try:
                with open(self._metrics_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                # Log the error but continue with fresh metrics
                print(f"Warning: Could not load metrics file, initializing fresh: {e}")

        # Initialize with empty structure
        return {
            "$schema": "session-insights-metrics-schema/v1",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "current_run": None,
            "cumulative": {
                "total_runs": 0,
                "total_success": 0,
                "total_failures": 0,
                "total_sessions_processed": 0,
                "total_sessions_failed": 0,
                "total_validation_errors": 0,
                "total_malformed_json": 0,
                "avg_task_match_rate": 0.0,
                "avg_run_duration_ms": 0,
            },
            "health": {
                "last_successful_run": None,
                "consecutive_failures": 0,
                "uptime_24h": 1.0,
                "status": "unknown",
            },
        }

    def _calculate_health_status(self, health: dict[str, Any]) -> str:
        """Calculate health status from metrics."""
        consecutive = health["consecutive_failures"]
        if consecutive >= 5:
            return "critical"
        if consecutive >= 3:
            return "degraded"
        if consecutive > 0:
            return "warning"
        return "healthy"

    def _append_run_log(self, run: dict[str, Any]) -> None:
        """Append run record to JSONL log."""
        # Compact record for log
        log_entry = {
            "run_timestamp": run["run_timestamp"],
            "run_duration_ms": run["run_duration_ms"],
            "run_status": run["run_status"],
            "run_trigger": run["run_trigger"],
            "sessions_processed": run["sessions_processed"],
            "sessions_failed": run["sessions_failed"],
            "validation_errors": run["validation_errors"],
            "task_match_rate": self._calculate_task_match_rate(),
        }

        with open(self._runs_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_current_metrics(self) -> dict[str, Any]:
        """Get current in-memory metrics snapshot."""
        return {
            "sessions_scanned": self._sessions_scanned,
            "sessions_pending": self._sessions_pending,
            "sessions_processed": self._sessions_processed,
            "sessions_failed": self._sessions_failed,
            "sessions_skipped": self._sessions_skipped,
            "validation_errors": self._validation_errors,
            "malformed_json": self._malformed_json,
            "empty_responses": self._empty_responses,
            "coercions_applied": self._coercions_applied,
            "sessions_with_task_match": self._sessions_with_task_match,
            "sessions_no_task_match": self._sessions_no_task_match,
            "accomplishments_synced": self._accomplishments_synced,
            "task_match_rate": self._calculate_task_match_rate(),
            "errors": self._errors,
        }


# Singleton for easy import
_metrics_instance: PipelineMetrics | None = None


def get_metrics() -> PipelineMetrics:
    """Get or create singleton metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PipelineMetrics()
    return _metrics_instance


def load_pipeline_metrics() -> dict[str, Any] | None:
    """Load persisted pipeline metrics.

    Returns:
        Metrics dict or None if not found
    """
    metrics_file = get_metrics_dir() / "pipeline-metrics.json"
    if metrics_file.exists():
        try:
            with open(metrics_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load metrics file: {e}")
            return None
    return None


# Alert threshold definitions
# See specs/session-insights-metrics-schema.md for documentation
ALERT_THRESHOLDS = {
    "consecutive_failures": {
        "warning": 3,
        "critical": 5,
    },
    "uptime_24h": {
        "warning": 0.8,  # Below this is warning
        "critical": 0.5,  # Below this is critical
    },
    "task_match_rate": {
        "warning": 0.5,  # Below this is warning
    },
    "hours_since_success": {
        "warning": 24,
        "critical": 48,
    },
}


AlertSeverity = Literal["info", "warning", "critical"]


def check_alerts(metrics: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Check metrics against alert thresholds.

    Args:
        metrics: Metrics dict to check, or None to load from file

    Returns:
        List of alert dicts with keys: condition, threshold, actual, severity, message
    """
    if metrics is None:
        metrics = load_pipeline_metrics()
    if metrics is None:
        return []

    alerts: list[dict[str, Any]] = []
    health = metrics["health"]
    current_run = metrics["current_run"]

    # Check consecutive failures
    consecutive = health["consecutive_failures"]
    if consecutive >= ALERT_THRESHOLDS["consecutive_failures"]["critical"]:
        alerts.append({
            "condition": "consecutive_failures",
            "threshold": ALERT_THRESHOLDS["consecutive_failures"]["critical"],
            "actual": consecutive,
            "severity": "critical",
            "message": f"Pipeline has failed {consecutive} times consecutively",
        })
    elif consecutive >= ALERT_THRESHOLDS["consecutive_failures"]["warning"]:
        alerts.append({
            "condition": "consecutive_failures",
            "threshold": ALERT_THRESHOLDS["consecutive_failures"]["warning"],
            "actual": consecutive,
            "severity": "warning",
            "message": f"Pipeline has failed {consecutive} times consecutively",
        })

    # Check uptime
    uptime = health["uptime_24h"]
    if uptime < ALERT_THRESHOLDS["uptime_24h"]["critical"]:
        alerts.append({
            "condition": "uptime_24h",
            "threshold": ALERT_THRESHOLDS["uptime_24h"]["critical"],
            "actual": uptime,
            "severity": "critical",
            "message": f"24h uptime is {uptime:.0%}, below critical threshold",
        })
    elif uptime < ALERT_THRESHOLDS["uptime_24h"]["warning"]:
        alerts.append({
            "condition": "uptime_24h",
            "threshold": ALERT_THRESHOLDS["uptime_24h"]["warning"],
            "actual": uptime,
            "severity": "warning",
            "message": f"24h uptime is {uptime:.0%}, below warning threshold",
        })

    # Check hours since last success
    last_success = health["last_successful_run"]
    if last_success:
        last_success_dt = datetime.fromisoformat(last_success)
        hours_since = (datetime.now(timezone.utc) - last_success_dt).total_seconds() / 3600
        if hours_since >= ALERT_THRESHOLDS["hours_since_success"]["critical"]:
            alerts.append({
                "condition": "hours_since_success",
                "threshold": ALERT_THRESHOLDS["hours_since_success"]["critical"],
                "actual": hours_since,
                "severity": "critical",
                "message": f"No successful run in {hours_since:.1f} hours",
            })
        elif hours_since >= ALERT_THRESHOLDS["hours_since_success"]["warning"]:
            alerts.append({
                "condition": "hours_since_success",
                "threshold": ALERT_THRESHOLDS["hours_since_success"]["warning"],
                "actual": hours_since,
                "severity": "warning",
                "message": f"No successful run in {hours_since:.1f} hours",
            })

    # Check task match rate (from current run if available)
    if current_run:
        total_matched = current_run["sessions_with_task_match"]
        total_unmatched = current_run["sessions_no_task_match"]
        total = total_matched + total_unmatched
        if total > 0:
            match_rate = total_matched / total
            if match_rate < ALERT_THRESHOLDS["task_match_rate"]["warning"]:
                alerts.append({
                    "condition": "task_match_rate",
                    "threshold": ALERT_THRESHOLDS["task_match_rate"]["warning"],
                    "actual": match_rate,
                    "severity": "warning",
                    "message": f"Task match rate is {match_rate:.0%}, below threshold",
                })

        # Check for validation errors (info level)
        if current_run["validation_errors"] > 0:
            alerts.append({
                "condition": "validation_errors",
                "threshold": 0,
                "actual": current_run["validation_errors"],
                "severity": "info",
                "message": f"{current_run['validation_errors']} validation errors in last run",
            })

        # Check for malformed JSON (warning level)
        if current_run["malformed_json"] > 0:
            alerts.append({
                "condition": "malformed_json",
                "threshold": 0,
                "actual": current_run["malformed_json"],
                "severity": "warning",
                "message": f"{current_run['malformed_json']} malformed JSON responses in last run",
            })

    return alerts


def format_alerts(alerts: list[dict[str, Any]]) -> str:
    """Format alerts for human-readable output.

    Args:
        alerts: List of alert dicts from check_alerts()

    Returns:
        Formatted string with alerts
    """
    if not alerts:
        return "No alerts - pipeline healthy"

    severity_icons = {
        "info": "ℹ️",
        "warning": "⚠️",
        "critical": "🚨",
    }

    lines = []
    for alert in sorted(alerts, key=lambda a: {"critical": 0, "warning": 1, "info": 2}[a["severity"]]):
        icon = severity_icons[alert["severity"]]
        lines.append(f"{icon} [{alert['severity'].upper()}] {alert['message']}")

    return "\n".join(lines)
