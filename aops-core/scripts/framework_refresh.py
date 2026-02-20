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

    failed_steps: list[str] = []

    # 1. Core Task Index
    print("Regenerating task index...")
    if not run_fast_indexer(data_root, data_root / "tasks" / "index", format="json"):
        failed_steps.append("task index")

    # 2. Dashboard Graphs
    print("Regenerating knowledge graphs...")
    if not run_fast_indexer(data_root, data_root / "outputs" / "graph", format="json"):
        failed_steps.append("knowledge graph")
    if not run_fast_indexer(data_root, data_root / "outputs" / "knowledge-graph", format="json"):
        failed_steps.append("knowledge-graph (alt)")

    # 3. Styled Task Map for Dashboard
    print("Rendering styled task map...")
    filtered_json = Path("/tmp/tasks-filtered.json")
    if not run_fast_indexer(
        data_root, Path("/tmp/tasks-filtered"), format="json", filter_types="task,project,goal"
    ):
        failed_steps.append("filtered task index")

    if filtered_json.exists():
        if not render_task_map(filtered_json, data_root / "outputs" / "task-map"):
            failed_steps.append("task map render")

    # 4. Sync to Memory
    print("Syncing to memory server...")
    aops_root = Path(os.environ.get("AOPS", "."))
    sync_script = aops_root / "scripts" / "sync_brain_to_memory.py"
    if sync_script.exists():
        import subprocess

        result = subprocess.run(["uv", "run", "python", str(sync_script)], check=False)
        if result.returncode != 0:
            failed_steps.append("memory sync")

    # 5. Update timestamp
    update_refresh_timestamp(data_root)

    if failed_steps:
        print(f"\n✗ Framework refresh completed with failures: {', '.join(failed_steps)}")
        sys.exit(1)

    print("\n✓ Framework refresh complete.")


if __name__ == "__main__":
    main()
