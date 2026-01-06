"""Test task index freshness.

Verifies that index.json is regenerated within acceptable time window.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest


class TestTaskIndexFreshness:
    """Test that task index stays fresh."""

    def test_index_exists_and_is_fresh(self) -> None:
        """Verify index.json exists and was modified within 10 minutes.

        This test requires:
        - $ACA_DATA to be set
        - regenerate_task_index.py to run periodically (cron or manual)

        The 10-minute threshold allows for:
        - 5-minute cron interval
        - Processing time buffer
        """
        aca_data = os.environ.get("ACA_DATA")
        if not aca_data:
            pytest.skip("ACA_DATA environment variable not set")

        index_path = Path(aca_data) / "tasks" / "index.json"

        # Index must exist
        assert index_path.exists(), (
            f"Task index not found: {index_path}\n"
            f"Run: uv run python scripts/regenerate_task_index.py"
        )

        # Index must be fresh (modified within 10 minutes)
        max_age_seconds = 600  # 10 minutes
        mtime = index_path.stat().st_mtime
        age_seconds = time.time() - mtime

        assert age_seconds < max_age_seconds, (
            f"Task index is stale: {age_seconds:.0f} seconds old "
            f"(max: {max_age_seconds} seconds)\n"
            f"Run: uv run python scripts/regenerate_task_index.py"
        )
