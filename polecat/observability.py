#!/usr/bin/env python3
"""
Polecat Observability: Structured metrics for sync latency, lock contention, and queue depth.

Emits structured log lines in a format suitable for log aggregation and analysis.
All metrics are prefixed with [POLECAT_METRIC] for easy filtering.

Usage:
    from observability import metrics

    # Time an operation
    with metrics.time_operation("sync", project="aops"):
        do_sync()

    # Record lock contention
    metrics.record_lock_wait("worktree_creation", wait_time_ms=150.5)

    # Record queue depth
    metrics.record_queue_depth("merge_ready", count=5)
"""

import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional


class PolecatMetrics:
    """Structured metrics emitter for polecat operations."""

    PREFIX = "[POLECAT_METRIC]"

    def _emit(self, metric_type: str, **fields):
        """Emit a structured metric line to stderr.

        Format: [POLECAT_METRIC] type=<type> timestamp=<iso> key1=value1 key2=value2
        """
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        parts = [f"{self.PREFIX} type={metric_type}", f"timestamp={timestamp}"]
        for key, value in fields.items():
            if value is not None:
                # Quote strings with spaces, escape quotes
                if isinstance(value, str) and (" " in value or '"' in value):
                    value = f'"{value.replace(chr(34), chr(92) + chr(34))}"'
                parts.append(f"{key}={value}")
        print(" ".join(parts), file=sys.stderr)

    @contextmanager
    def time_operation(
        self, operation: str, project: Optional[str] = None, **extra_fields
    ):
        """Context manager to time an operation and emit latency metric.

        Args:
            operation: Name of the operation (e.g., "sync", "fetch", "merge")
            project: Optional project slug
            **extra_fields: Additional fields to include in the metric

        Yields:
            A dict that can be updated with additional fields during the operation

        Example:
            with metrics.time_operation("sync", project="aops") as ctx:
                result = do_sync()
                ctx["commits_fetched"] = 5
        """
        context = {}
        start_time = time.perf_counter()
        try:
            yield context
            success = True
        except Exception:
            success = False
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._emit(
                f"{operation}_latency",
                duration_ms=f"{elapsed_ms:.2f}",
                success=success,
                project=project,
                **extra_fields,
                **context,
            )

    def record_lock_wait(
        self,
        lock_name: str,
        wait_time_ms: float,
        acquired: bool = True,
        caller: Optional[str] = None,
    ):
        """Record time spent waiting for a lock.

        Args:
            lock_name: Identifier for the lock (e.g., "worktree_creation", "task_claim")
            wait_time_ms: Time spent waiting in milliseconds
            acquired: Whether the lock was successfully acquired
            caller: Optional identifier for who was waiting
        """
        self._emit(
            "lock_contention",
            lock_name=lock_name,
            wait_time_ms=f"{wait_time_ms:.2f}",
            acquired=acquired,
            caller=caller,
        )

    def record_queue_depth(
        self, queue_name: str, count: int, project: Optional[str] = None
    ):
        """Record the depth of a queue.

        Args:
            queue_name: Name of the queue (e.g., "merge_ready", "active", "review")
            count: Number of items in the queue
            project: Optional project filter used
        """
        self._emit("queue_depth", queue_name=queue_name, count=count, project=project)

    def record_lock_timeout(
        self, lock_name: str, timeout_seconds: float, caller: Optional[str] = None
    ):
        """Record when a lock acquisition times out.

        Args:
            lock_name: Identifier for the lock
            timeout_seconds: How long we waited before timing out
            caller: Optional identifier for who timed out
        """
        self._emit(
            "lock_timeout",
            lock_name=lock_name,
            timeout_seconds=f"{timeout_seconds:.2f}",
            caller=caller,
        )

    def record_merge_attempt(
        self,
        task_id: str,
        success: bool,
        duration_ms: float,
        failure_reason: Optional[str] = None,
    ):
        """Record a merge attempt with outcome.

        Args:
            task_id: ID of the task being merged
            success: Whether the merge succeeded
            duration_ms: Time taken for the merge attempt
            failure_reason: If failed, why (e.g., "conflicts", "tests_failed")
        """
        self._emit(
            "merge_attempt",
            task_id=task_id,
            success=success,
            duration_ms=f"{duration_ms:.2f}",
            failure_reason=failure_reason,
        )


# Global metrics instance
metrics = PolecatMetrics()
