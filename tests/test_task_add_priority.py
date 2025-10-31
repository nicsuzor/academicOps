#!/usr/bin/env python3
"""Integration tests for task_add.py priority validation.

Tests verify that both numeric ('0', '1', '2') and prefixed ('P0', 'P1', 'P2')
priority formats are accepted.

Relates to GitHub issue #173.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


def test_task_add_accepts_numeric_priority():
    """Verify task_add.py accepts numeric priority format (0, 1, 2)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange
        script = Path(__file__).parent.parent / "scripts" / "task_add.py"
        result_file = Path(tmpdir) / "data" / "tasks" / "inbox"

        # Act - Create task with numeric priority
        result = subprocess.run(
            [
                "python3", str(script),
                "--title", "Test task with numeric priority",
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
        assert output["title"] == "Test task with numeric priority"


def test_task_add_accepts_p0_priority_format():
    """Verify task_add.py accepts P0 priority format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange
        script = Path(__file__).parent.parent / "scripts" / "task_add.py"

        # Act - Create task with P0 priority
        result = subprocess.run(
            [
                "python3", str(script),
                "--title", "Test task with P0 priority",
                "--priority", "P0",
                "--project", "test"
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        # Assert
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify JSON output contains correct priority (normalized to 0)
        output = json.loads(result.stdout)
        assert output["priority"] == 0
        assert output["title"] == "Test task with P0 priority"


def test_task_add_accepts_p1_priority_format():
    """Verify task_add.py accepts P1 priority format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange
        script = Path(__file__).parent.parent / "scripts" / "task_add.py"

        # Act - Create task with P1 priority
        result = subprocess.run(
            [
                "python3", str(script),
                "--title", "Test task with P1 priority",
                "--priority", "P1",
                "--project", "test"
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        # Assert
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify JSON output contains correct priority (normalized to 1)
        output = json.loads(result.stdout)
        assert output["priority"] == 1
        assert output["title"] == "Test task with P1 priority"


def test_task_add_accepts_p2_priority_format():
    """Verify task_add.py accepts P2 priority format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange
        script = Path(__file__).parent.parent / "scripts" / "task_add.py"

        # Act - Create task with P2 priority
        result = subprocess.run(
            [
                "python3", str(script),
                "--title", "Test task with P2 priority",
                "--priority", "P2",
                "--project", "test"
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        # Assert
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify JSON output contains correct priority (normalized to 2)
        output = json.loads(result.stdout)
        assert output["priority"] == 2
        assert output["title"] == "Test task with P2 priority"


def test_task_add_rejects_invalid_priority_with_clear_error():
    """Verify task_add.py rejects invalid priority with helpful error message."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Arrange
        script = Path(__file__).parent.parent / "scripts" / "task_add.py"

        # Act - Try invalid priority
        result = subprocess.run(
            [
                "python3", str(script),
                "--title", "Test task",
                "--priority", "invalid",
                "--project", "test"
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        # Assert - Should fail with clear error
        assert result.returncode != 0
        assert "priority" in result.stderr.lower()
        # Error should mention valid formats
        assert any(hint in result.stderr.lower() for hint in ["p0", "p1", "p2", "0", "1", "2", "valid"])


def test_task_add_help_documents_priority_formats():
    """Verify --help output clearly documents priority format options."""
    script = Path(__file__).parent.parent / "scripts" / "task_add.py"

    # Act
    result = subprocess.run(
        ["python3", str(script), "--help"],
        capture_output=True,
        text=True
    )

    # Assert
    assert result.returncode == 0
    # Help text should mention both formats
    help_text = result.stdout.lower()
    assert "priority" in help_text
    # Should document that both P0/P1/P2 and 0/1/2 are valid
    assert any(format_hint in help_text for format_hint in ["p0", "p1", "p2", "0/1/2"])
