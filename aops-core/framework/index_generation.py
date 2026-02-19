#!/usr/bin/env python3
"""Core logic for framework index generation."""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_fast_indexer(
    data_root: Path, output_path: Path, format: str = "json", filter_types: str = None
):
    """Invoke the fast-indexer Rust binary."""
    aops_root = Path(os.environ.get("AOPS", "."))
    binary_path = aops_root / "scripts" / "bin" / "fast-indexer"

    if not binary_path.exists():
        logger.error(f"fast-indexer binary not found at {binary_path}")
        return False

    cmd = [str(binary_path), str(data_root), "-o", str(output_path), "-f", format]
    if filter_types:
        cmd.extend(["-t", filter_types])

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"fast-indexer completed: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"fast-indexer failed: {e.stderr}")
        return False


def update_refresh_timestamp(data_root: Path):
    """Update the .last_refresh file."""
    timestamp_path = data_root / "tasks" / ".last_refresh"
    timestamp_path.parent.mkdir(parents=True, exist_ok=True)
    from datetime import UTC, datetime

    timestamp_path.write_text(datetime.now(UTC).isoformat() + "Z")
