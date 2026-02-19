#!/usr/bin/env python3
"""Logic for rendering task and knowledge graphs."""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def render_task_map(input_json: Path, output_base: Path, layout: str = "sfdp"):
    """Render a styled SVG task map using task_graph.py."""
    aops_root = Path(os.environ.get("AOPS", "."))
    script_path = aops_root / "scripts" / "task_graph.py"

    if not script_path.exists():
        logger.error(f"task_graph.py not found at {script_path}")
        return False

    cmd = [
        "uv",
        "run",
        "python",
        str(script_path),
        str(input_json),
        "-o",
        str(output_base),
        "--layout",
        layout,
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"task_graph.py completed: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"task_graph.py failed: {e.stderr}")
        return False
