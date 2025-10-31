#!/usr/bin/env python3
"""Integration tests for skills/scribe/scripts/task_add.py priority validation.

Tests verify that both numeric ('0', '1', '2') and prefixed ('P0', 'P1', 'P2')
priority formats are accepted in the scribe version.

Relates to GitHub issue #173.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


def test_scribe_task_add_accepts_numeric_priority():
    """Verify scribe task_add.py accepts numeric priority format (0, 1, 2)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange
        script = Path(__file__).parent.parent / "skills" / "scribe" / "scripts" / "task_add.py"
        result_file = Path(tmpdir) / "data" / "tasks" / "inbox"

        # Act - Create task with numeric priority
        result = subprocess.run(
            [
                "python3", str(script),
                "--title", "Test scribe task with numeric priority",
                "--priority", "1",
                "--project", "test"
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        # Assert
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify JSON output contains correct priority
        output = json.loads(result.stdout)
        assert output["priority"] == 1
        assert output["title"] == "Test scribe task with numeric priority"


def test_scribe_task_add_accepts_p_format():
    """Verify scribe task_add.py accepts P0/P1/P2 priority formats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange
        script = Path(__file__).parent.parent / "skills" / "scribe" / "scripts" / "task_add.py"

        # Test all P-format priorities
        for p_format, expected_value in [("P0", 0), ("P1", 1), ("P2", 2), ("P3", 3)]:
            # Act
            result = subprocess.run(
                [
                    "python3", str(script),
                    "--title", f"Test task with {p_format}",
                    "--priority", p_format,
                    "--project", "test"
                ],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            # Assert
            assert result.returncode == 0, f"Script failed for {p_format}: {result.stderr}"

            # Verify JSON output
            output = json.loads(result.stdout)
            assert output["priority"] == expected_value, f"Expected {expected_value} for {p_format}"
