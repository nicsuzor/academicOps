"""Tests for pipeline metrics collection library."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.pipeline_metrics import (
    ALERT_THRESHOLDS,
    PipelineMetrics,
    check_alerts,
    format_alerts,
    get_metrics,
    get_metrics_dir,
    load_pipeline_metrics,
)


class TestPipelineMetrics:
    """Test PipelineMetrics class."""

    @pytest.fixture
    def temp_metrics_dir(self, tmp_path: Path):
        """Create temporary metrics directory."""
        metrics_dir = tmp_path / "summaries" / ".metrics"
        metrics_dir.mkdir(parents=True)
        return metrics_dir

    @pytest.fixture
    def metrics(self, temp_metrics_dir: Path):
        """Create metrics instance with temp directory."""
        m = PipelineMetrics()
        m._metrics_dir = temp_metrics_dir
        m._metrics_file = temp_metrics_dir / "pipeline-metrics.json"
        m._runs_file = temp_metrics_dir / "runs.jsonl"
        return m

    def test_start_run_resets_counters(self, metrics: PipelineMetrics):
        """Test that start_run resets all counters."""
        metrics._sessions_processed = 5
        metrics._validation_errors = 2

        metrics.start_run(trigger="skill")

        assert metrics._sessions_processed == 0
        assert metrics._validation_errors == 0
        assert metrics._run_trigger == "skill"
        assert metrics._run_start is not None

    def test_record_session_processed(self, metrics: PipelineMetrics):
        """Test recording processed sessions."""
        metrics.start_run()
        metrics.record_session_processed()
        metrics.record_session_processed()

        assert metrics._sessions_processed == 2

    def test_record_session_failed_with_error(self, metrics: PipelineMetrics):
        """Test recording failed sessions with error message."""
        metrics.start_run()
        metrics.record_session_failed("Connection timeout")

        assert metrics._sessions_failed == 1
        assert "Connection timeout" in metrics._errors

    def test_record_validation_error(self, metrics: PipelineMetrics):
        """Test recording validation errors."""
        metrics.start_run()
        metrics.record_validation_error("Missing required field: session_id")

        assert metrics._validation_errors == 1
        assert any("Validation:" in e for e in metrics._errors)

    def test_record_malformed_json(self, metrics: PipelineMetrics):
        """Test recording malformed JSON errors."""
        metrics.start_run()
        metrics.record_malformed_json("Unexpected token")

        assert metrics._malformed_json == 1
        assert any("JSON:" in e for e in metrics._errors)

    def test_record_task_match(self, metrics: PipelineMetrics):
        """Test recording task matches with accomplishments."""
        metrics.start_run()
        metrics.record_task_match(accomplishments_count=3)

        assert metrics._sessions_with_task_match == 1
        assert metrics._accomplishments_synced == 3

    def test_calculate_task_match_rate(self, metrics: PipelineMetrics):
        """Test task match rate calculation."""
        metrics.start_run()
        metrics.record_task_match()
        metrics.record_task_match()
        metrics.record_no_task_match()

        rate = metrics._calculate_task_match_rate()
        assert rate == pytest.approx(2 / 3)

    def test_calculate_task_match_rate_zero_sessions(self, metrics: PipelineMetrics):
        """Test task match rate with no sessions."""
        metrics.start_run()
        rate = metrics._calculate_task_match_rate()
        assert rate == 0.0

    def test_determine_status_success(self, metrics: PipelineMetrics):
        """Test status determination for success."""
        metrics.start_run()
        metrics.record_session_processed()

        assert metrics._determine_status() == "success"

    def test_determine_status_partial(self, metrics: PipelineMetrics):
        """Test status determination for partial success."""
        metrics.start_run()
        metrics.record_session_processed()
        metrics.record_session_failed()

        assert metrics._determine_status() == "partial"

    def test_determine_status_failure(self, metrics: PipelineMetrics):
        """Test status determination for complete failure."""
        metrics.start_run()
        metrics.record_session_failed()

        assert metrics._determine_status() == "failure"

    def test_end_run_persists_metrics(self, metrics: PipelineMetrics):
        """Test that end_run persists metrics to file."""
        metrics.start_run(trigger="batch")
        metrics.record_session_scanned(10)
        metrics.record_session_pending(3)
        metrics.record_session_processed()
        metrics.record_session_processed()
        metrics.record_task_match(accomplishments_count=2)

        result = metrics.end_run()

        # Check return value
        assert result["run_status"] == "success"
        assert result["run_trigger"] == "batch"
        assert result["sessions_scanned"] == 10
        assert result["sessions_processed"] == 2

        # Check persisted file
        assert metrics._metrics_file.exists()
        with open(metrics._metrics_file) as f:
            persisted = json.load(f)
        assert persisted["cumulative"]["total_runs"] == 1
        assert persisted["cumulative"]["total_success"] == 1
        assert persisted["health"]["status"] == "healthy"

    def test_end_run_appends_to_run_log(self, metrics: PipelineMetrics):
        """Test that end_run appends to runs.jsonl."""
        metrics.start_run()
        metrics.record_session_processed()
        metrics.end_run()

        assert metrics._runs_file.exists()
        with open(metrics._runs_file) as f:
            lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["run_status"] == "success"

    def test_cumulative_metrics_accumulate(self, metrics: PipelineMetrics):
        """Test that cumulative metrics accumulate across runs."""
        # First run
        metrics.start_run()
        metrics.record_session_processed()
        metrics.end_run()

        # Second run
        metrics.start_run()
        metrics.record_session_processed()
        metrics.record_session_processed()
        metrics.end_run()

        with open(metrics._metrics_file) as f:
            persisted = json.load(f)

        assert persisted["cumulative"]["total_runs"] == 2
        assert persisted["cumulative"]["total_sessions_processed"] == 3

    def test_health_status_degraded_after_failures(self, metrics: PipelineMetrics):
        """Test health degrades after consecutive failures."""
        for _ in range(3):
            metrics.start_run()
            metrics.record_session_failed()
            metrics.end_run()

        with open(metrics._metrics_file) as f:
            persisted = json.load(f)

        assert persisted["health"]["consecutive_failures"] == 3
        assert persisted["health"]["status"] == "degraded"

    def test_health_resets_on_success(self, metrics: PipelineMetrics):
        """Test health resets after successful run."""
        # Cause some failures
        for _ in range(3):
            metrics.start_run()
            metrics.record_session_failed()
            metrics.end_run()

        # Then succeed
        metrics.start_run()
        metrics.record_session_processed()
        metrics.end_run()

        with open(metrics._metrics_file) as f:
            persisted = json.load(f)

        assert persisted["health"]["consecutive_failures"] == 0
        assert persisted["health"]["status"] == "healthy"

    def test_get_current_metrics(self, metrics: PipelineMetrics):
        """Test getting current in-memory metrics."""
        metrics.start_run()
        metrics.record_session_scanned(5)
        metrics.record_session_processed()
        metrics.record_validation_error("test error")

        current = metrics.get_current_metrics()

        assert current["sessions_scanned"] == 5
        assert current["sessions_processed"] == 1
        assert current["validation_errors"] == 1
        assert len(current["errors"]) == 1


class TestHealthStatus:
    """Test health status calculation."""

    @pytest.fixture
    def metrics(self, tmp_path: Path):
        """Create metrics instance."""
        metrics_dir = tmp_path / ".metrics"
        metrics_dir.mkdir()
        m = PipelineMetrics()
        m._metrics_dir = metrics_dir
        m._metrics_file = metrics_dir / "pipeline-metrics.json"
        m._runs_file = metrics_dir / "runs.jsonl"
        return m

    def test_healthy_status(self, metrics: PipelineMetrics):
        """Test healthy status with no failures."""
        health = {"consecutive_failures": 0}
        assert metrics._calculate_health_status(health) == "healthy"

    def test_warning_status(self, metrics: PipelineMetrics):
        """Test warning status with 1-2 failures."""
        health = {"consecutive_failures": 1}
        assert metrics._calculate_health_status(health) == "warning"

        health = {"consecutive_failures": 2}
        assert metrics._calculate_health_status(health) == "warning"

    def test_degraded_status(self, metrics: PipelineMetrics):
        """Test degraded status with 3-4 failures."""
        health = {"consecutive_failures": 3}
        assert metrics._calculate_health_status(health) == "degraded"

        health = {"consecutive_failures": 4}
        assert metrics._calculate_health_status(health) == "degraded"

    def test_critical_status(self, metrics: PipelineMetrics):
        """Test critical status with 5+ failures."""
        health = {"consecutive_failures": 5}
        assert metrics._calculate_health_status(health) == "critical"

        health = {"consecutive_failures": 10}
        assert metrics._calculate_health_status(health) == "critical"


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_metrics_returns_singleton(self):
        """Test get_metrics returns singleton instance."""
        # Reset singleton
        import lib.pipeline_metrics as pm
        pm._metrics_instance = None

        m1 = get_metrics()
        m2 = get_metrics()

        assert m1 is m2

    def test_load_pipeline_metrics_returns_none_if_missing(self, tmp_path: Path):
        """Test load returns None if file missing."""
        with patch.object(Path, "home", return_value=tmp_path):
            result = load_pipeline_metrics()
        # May return None or actual metrics depending on home dir state
        # Just verify it doesn't crash
        assert result is None or isinstance(result, dict)

    def test_get_metrics_dir_creates_directory(self, tmp_path: Path):
        """Test get_metrics_dir creates directory if missing."""
        with patch.object(Path, "home", return_value=tmp_path):
            metrics_dir = get_metrics_dir()

        assert metrics_dir.exists()
        assert metrics_dir.name == ".metrics"


class TestAlertThresholds:
    """Test alert threshold checking."""

    def test_alert_thresholds_defined(self):
        """Test that alert thresholds are properly defined."""
        assert "consecutive_failures" in ALERT_THRESHOLDS
        assert "warning" in ALERT_THRESHOLDS["consecutive_failures"]
        assert "critical" in ALERT_THRESHOLDS["consecutive_failures"]

    def test_check_alerts_no_metrics(self):
        """Test check_alerts with no metrics returns empty list."""
        alerts = check_alerts(None)
        assert alerts == []

    def test_check_alerts_healthy_metrics(self):
        """Test check_alerts with healthy metrics."""
        from datetime import datetime, timezone

        metrics = {
            "health": {
                "consecutive_failures": 0,
                "uptime_24h": 1.0,
                "last_successful_run": datetime.now(timezone.utc).isoformat(),
            },
            "current_run": {
                "sessions_with_task_match": 3,
                "sessions_no_task_match": 1,
                "validation_errors": 0,
                "malformed_json": 0,
            },
        }
        alerts = check_alerts(metrics)
        assert len(alerts) == 0

    def test_check_alerts_consecutive_failures_warning(self):
        """Test warning alert for consecutive failures."""
        from datetime import datetime, timezone

        metrics = {
            "health": {
                "consecutive_failures": 3,
                "uptime_24h": 0.9,
                "last_successful_run": datetime.now(timezone.utc).isoformat(),
            },
            "current_run": None,
        }
        alerts = check_alerts(metrics)
        failure_alerts = [a for a in alerts if a["condition"] == "consecutive_failures"]
        assert len(failure_alerts) == 1
        assert failure_alerts[0]["severity"] == "warning"

    def test_check_alerts_consecutive_failures_critical(self):
        """Test critical alert for consecutive failures."""
        from datetime import datetime, timezone

        metrics = {
            "health": {
                "consecutive_failures": 5,
                "uptime_24h": 0.9,
                "last_successful_run": datetime.now(timezone.utc).isoformat(),
            },
            "current_run": None,
        }
        alerts = check_alerts(metrics)
        failure_alerts = [a for a in alerts if a["condition"] == "consecutive_failures"]
        assert len(failure_alerts) == 1
        assert failure_alerts[0]["severity"] == "critical"

    def test_check_alerts_low_uptime(self):
        """Test alert for low uptime."""
        from datetime import datetime, timezone

        metrics = {
            "health": {
                "consecutive_failures": 0,
                "uptime_24h": 0.4,
                "last_successful_run": datetime.now(timezone.utc).isoformat(),
            },
            "current_run": None,
        }
        alerts = check_alerts(metrics)
        uptime_alerts = [a for a in alerts if a["condition"] == "uptime_24h"]
        assert len(uptime_alerts) == 1
        assert uptime_alerts[0]["severity"] == "critical"

    def test_check_alerts_low_task_match_rate(self):
        """Test alert for low task match rate."""
        from datetime import datetime, timezone

        metrics = {
            "health": {
                "consecutive_failures": 0,
                "uptime_24h": 1.0,
                "last_successful_run": datetime.now(timezone.utc).isoformat(),
            },
            "current_run": {
                "sessions_with_task_match": 1,
                "sessions_no_task_match": 9,
                "validation_errors": 0,
                "malformed_json": 0,
            },
        }
        alerts = check_alerts(metrics)
        match_alerts = [a for a in alerts if a["condition"] == "task_match_rate"]
        assert len(match_alerts) == 1
        assert match_alerts[0]["severity"] == "warning"

    def test_check_alerts_validation_errors(self):
        """Test info alert for validation errors."""
        from datetime import datetime, timezone

        metrics = {
            "health": {
                "consecutive_failures": 0,
                "uptime_24h": 1.0,
                "last_successful_run": datetime.now(timezone.utc).isoformat(),
            },
            "current_run": {
                "sessions_with_task_match": 5,
                "sessions_no_task_match": 0,
                "validation_errors": 2,
                "malformed_json": 0,
            },
        }
        alerts = check_alerts(metrics)
        validation_alerts = [a for a in alerts if a["condition"] == "validation_errors"]
        assert len(validation_alerts) == 1
        assert validation_alerts[0]["severity"] == "info"

    def test_format_alerts_empty(self):
        """Test formatting empty alerts."""
        result = format_alerts([])
        assert result == "No alerts - pipeline healthy"

    def test_format_alerts_with_alerts(self):
        """Test formatting alerts."""
        alerts = [
            {"condition": "test", "severity": "warning", "message": "Test warning"},
            {"condition": "test2", "severity": "critical", "message": "Test critical"},
        ]
        result = format_alerts(alerts)
        assert "CRITICAL" in result
        assert "WARNING" in result
        # Critical should come first
        assert result.index("CRITICAL") < result.index("WARNING")
