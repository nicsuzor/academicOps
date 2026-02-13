import io
import sys
from contextlib import redirect_stderr

from polecat.observability import PolecatMetrics


def test_metrics_emit_format():
    metrics = PolecatMetrics()
    f = io.StringIO()
    with redirect_stderr(f):
        metrics._emit("test_metric", key="value", count=1)

    output = f.getvalue().strip()
    assert "[POLECAT_METRIC]" in output
    assert "type=test_metric" in output
    assert "key=value" in output
    assert "count=1" in output
    assert "timestamp=" in output


def test_time_operation():
    metrics = PolecatMetrics()
    f = io.StringIO()
    with redirect_stderr(f):
        with metrics.time_operation("test_op", project="foo"):
            pass

    output = f.getvalue().strip()
    assert "type=test_op_latency" in output
    assert "project=foo" in output
    assert "success=True" in output
    assert "duration_ms=" in output


def test_record_lock_wait():
    metrics = PolecatMetrics()
    f = io.StringIO()
    with redirect_stderr(f):
        metrics.record_lock_wait("my_lock", 100.5, acquired=True)

    output = f.getvalue().strip()
    assert "type=lock_contention" in output
    assert "lock_name=my_lock" in output
    assert "wait_time_ms=100.50" in output


if __name__ == "__main__":
    try:
        test_metrics_emit_format()
        test_time_operation()
        test_record_lock_wait()
        print("All observability tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
