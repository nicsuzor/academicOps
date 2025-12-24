"""
Prompt router compliance measurement tests.

These tests measure how often agents comply with skill invocation suggestions
from the prompt router hook. They don't assert strict pass/fail criteria -
instead they report metrics and warn if compliance drops significantly.

Run with:
    uv run pytest tests/test_router_compliance.py -v -s

Markers:
    @pytest.mark.metrics - Observability tests that report metrics
    @pytest.mark.slow - Requires analyzing session transcripts
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Path to the measurement script
MEASURE_SCRIPT = Path(__file__).parent.parent / "scripts" / "measure_router_compliance.py"

# Baseline from 2025-11-28 measurement
BASELINE_COMPLIANCE_RATE = 3.2  # percent
WARN_THRESHOLD = 1.0  # Warn if compliance drops below this


@pytest.mark.metrics
@pytest.mark.slow
def test_router_compliance_measurement():
    """Run compliance measurement and report results.

    This test always passes but prints metrics for review.
    Use --capture=no (-s) to see output.
    """
    assert MEASURE_SCRIPT.exists(), f"Measurement script not found: {MEASURE_SCRIPT}"

    result = subprocess.run(
        [sys.executable, str(MEASURE_SCRIPT), "--all"],
        capture_output=True,
        text=True,
        cwd=MEASURE_SCRIPT.parent.parent,
        env={"PYTHONPATH": str(MEASURE_SCRIPT.parent.parent)},
    )

    print("\n" + "=" * 60)
    print("ROUTER COMPLIANCE MEASUREMENT")
    print("=" * 60)
    print(result.stdout)

    if result.stderr:
        print("STDERR:", result.stderr)

    # Extract compliance rate from output
    compliance_rate = None
    for line in result.stdout.split("\n"):
        if "Compliance Rate:" in line:
            try:
                compliance_rate = float(line.split(":")[1].strip().rstrip("%"))
            except (ValueError, IndexError):
                pass

    if compliance_rate is not None:
        print(f"\nCurrent compliance: {compliance_rate:.1f}%")
        print(f"Baseline (2025-11-28): {BASELINE_COMPLIANCE_RATE}%")

        if compliance_rate < WARN_THRESHOLD:
            print(f"⚠️  WARNING: Compliance below {WARN_THRESHOLD}% threshold")
        elif compliance_rate > BASELINE_COMPLIANCE_RATE:
            print(f"✓ Improvement over baseline: +{compliance_rate - BASELINE_COMPLIANCE_RATE:.1f}%")


@pytest.mark.metrics
def test_router_compliance_today():
    """Quick measurement of today's compliance only."""
    if not MEASURE_SCRIPT.exists():
        pytest.skip(f"Measurement script not found: {MEASURE_SCRIPT}")

    result = subprocess.run(
        [sys.executable, str(MEASURE_SCRIPT)],  # No --all flag = today only
        capture_output=True,
        text=True,
        cwd=MEASURE_SCRIPT.parent.parent,
        env={"PYTHONPATH": str(MEASURE_SCRIPT.parent.parent)},
    )

    print("\n" + result.stdout)


@pytest.mark.metrics
def test_hook_logs_exist():
    """Verify hook logging infrastructure is working."""
    # Hook logs go to ~/.claude/projects/<project>/*-hooks.jsonl
    projects_dir = Path.home() / ".claude" / "projects"

    assert projects_dir.exists(), f"Claude projects directory missing: {projects_dir}"

    hook_logs = list(projects_dir.rglob("*-hooks.jsonl"))
    assert len(hook_logs) > 0, "No hook logs found - hooks may not be firing"

    print(f"\n✓ Found {len(hook_logs)} hook log files")
    print(f"  Most recent: {sorted(hook_logs, key=lambda f: f.stat().st_mtime)[-1]}")

