"""Regression test for the aops-crew Docker image.

Issue #520: Gemini CLI called ``pgrep`` inside the container, but the
base image was missing ``procps``. This caused stderr spam like
``/bin/sh: 1: pgrep: not found`` during polecat task runs.

This test verifies that ``pgrep`` is available on $PATH in the built
``aops-crew`` image. It skips cleanly when Docker or the image is
unavailable (local dev machines without the image built).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests.conftest import _docker_available  # noqa: E402


def _image_built() -> bool:
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", "aops-crew"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.integration
def test_procps_available() -> None:
    """``pgrep`` must resolve inside the aops-crew image (issue #520)."""
    if not _docker_available():
        pytest.skip("Docker not available or aops-crew image not built")
    if not _image_built():
        pytest.skip("aops-crew image not built locally")

    result = subprocess.run(
        ["docker", "run", "--rm", "aops-crew", "which", "pgrep"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"`which pgrep` failed in aops-crew image "
        f"(exit={result.returncode}, stderr={result.stderr!r}). "
        "procps is likely missing from the Dockerfile apt-get install block."
    )
    assert "/pgrep" in result.stdout, (
        f"pgrep not found on PATH in aops-crew image; stdout={result.stdout!r}"
    )
