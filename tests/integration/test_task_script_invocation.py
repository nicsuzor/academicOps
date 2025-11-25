"""Integration tests for task script invocation with uv context.

Tests that task scripts can be invoked via subprocess with proper
PYTHONPATH and uv context, ensuring yaml and other dependencies
are accessible.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def aops_root() -> Path:
    """Return Path to aOps framework root.

    Returns:
        Path: Absolute path to /home/nic/src/aOps
    """
    return Path("/home/nic/src/aOps")


def test_task_ops_import_with_uv_context(aops_root: Path) -> None:
    """Test that task_ops can be imported with proper uv context.

    Verifies that the yaml import fix works correctly:
    - Importing task_ops with PYTHONPATH set works
    - yaml module is accessible when invoked via uv run
    - This is the CORRECT pattern that should PASS

    Args:
        aops_root: Path to aOps framework root

    Raises:
        AssertionError: If import fails or returns non-zero exit code
    """
    # Arrange: Prepare invocation with proper uv context (WITH PYTHONPATH)
    cmd = [
        "uv",
        "run",
        "python",
        "-c",
        "from skills.tasks import task_ops; print('SUCCESS')",
    ]

    env = {
        "PYTHONPATH": str(aops_root),
    }

    # Act: Invoke python with uv context
    result = subprocess.run(
        cmd,
        cwd=str(aops_root),
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        timeout=30,
    )

    # Assert: Import succeeds
    assert (
        result.returncode == 0
    ), f"Import failed with exit code {result.returncode}.\nStdout: {result.stdout}\nStderr: {result.stderr}"

    # Assert: SUCCESS printed
    assert (
        "SUCCESS" in result.stdout
    ), f"Expected SUCCESS in stdout, got: {result.stdout}"

    # Assert: No ModuleNotFoundError in output
    assert (
        "ModuleNotFoundError" not in result.stderr
    ), f"ModuleNotFoundError found in stderr: {result.stderr}"


