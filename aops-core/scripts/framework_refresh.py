#!/usr/bin/env python3
"""Entry point for framework-refresh skill."""

import os
import sys
from pathlib import Path

# Add aops-core to path for framework imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE = SCRIPT_DIR if SCRIPT_DIR.name == "aops-core" else SCRIPT_DIR.parent
sys.path.insert(0, str(AOPS_CORE))

from framework.graph_rendering import render_task_map
from framework.index_generation import run_fast_indexer, update_refresh_timestamp


def main():
    data_root_str = os.environ.get("ACA_DATA")
    if not data_root_str:
        print("Error: ACA_DATA environment variable not set.")
        sys.exit(1)

    data_root = Path(data_root_str)

    print("=== Refreshing Framework Indices ===")

    # 1. Core Task Index
    print("Regenerating task index...")
    run_fast_indexer(data_root, data_root / "tasks" / "index", format="json")

    # 2. Dashboard Graphs
    print("Regenerating knowledge graphs...")
    run_fast_indexer(data_root, data_root / "outputs" / "graph", format="json")
    run_fast_indexer(data_root, data_root / "outputs" / "knowledge-graph", format="json")

    # 3. Styled Task Map for Dashboard
    print("Rendering styled task map...")
    filtered_json = Path("/tmp/tasks-filtered.json")
    run_fast_indexer(
        data_root, Path("/tmp/tasks-filtered"), format="json", filter_types="task,project,goal"
    )

    if filtered_json.exists():
        render_task_map(filtered_json, data_root / "outputs" / "task-map")

    # 4. Sync to Memory
    print("Syncing to memory server...")
    aops_root = Path(os.environ.get("AOPS", "."))
    sync_script = aops_root / "scripts" / "sync_brain_to_memory.py"
    if sync_script.exists():
        import subprocess

        subprocess.run(["uv", "run", "python", str(sync_script)], check=False)

    # 5. Update timestamp
    update_refresh_timestamp(data_root)

    print("\n✓ Framework refresh complete.")


if __name__ == "__main__":
    main()
