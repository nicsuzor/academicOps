#!/usr/bin/env -S uv run python
"""
Audit all tasks in the PKB for consistency between ID, type, project, and filename.

Criteria:
1. ID prefix must match type (epic-, task-, bug-, learn-, target-)
2. Filename stem must match ID exactly.
"""

import sys
from pathlib import Path


def get_graph():
    # We use uvx to run the MCP tool if possible, but easier to just use the
    # environment's provided PKB_MCP_URL or assume we are running where we can call pkb_bridge

    # For this script, we'll try to find the polecat bridge
    repo_root = Path(__file__).parent.parent.resolve()
    sys.path.append(str(repo_root / "polecat"))

    try:
        from pkb_bridge import _get_client

        client = _get_client()
        return client.call_tool("graph_json", {})
    except ImportError:
        print("Error: Could not import polecat.pkb_bridge")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching graph: {e}")
        sys.exit(1)


def audit_tasks():
    graph_data = get_graph()
    if not graph_data or not isinstance(graph_data, dict):
        print("No graph data returned.")
        return

    nodes = graph_data.get("nodes", [])
    print(f"Auditing {len(nodes)} nodes...")

    mismatches = []

    TYPE_PREFIXES = {
        "epic": "epic",
        "task": "task",
        "learn": "learn",
        "target": "target",
        "goal": "target",
        "bug": "task",
    }

    for node in nodes:
        node = node or {}
        node_id = node.get("id")
        node_type = node.get("node_type") or node.get("type")
        path = node.get("path")

        if not node_id or not node_type:
            continue

        # Ignore nodes that are not tasks/epics/etc. (e.g. memories might have different rules)
        # But create_task usually creates things with these types.

        # 1. Check ID prefix vs Type
        prefix = node_id.split("-")[0] if "-" in node_id else node_id

        type_mismatch = False
        expected_type = ""
        if prefix in TYPE_PREFIXES:
            expected_type = TYPE_PREFIXES[prefix]
            if prefix == "bug":
                if node_type != "task":
                    type_mismatch = True
            elif node_type != expected_type:
                type_mismatch = True

        # 2. Check Filename stem vs ID
        filename_mismatch = False
        stem = ""
        if path:
            stem = Path(path).stem
            if stem != node_id:
                filename_mismatch = True

        if type_mismatch or filename_mismatch:
            reasons = []
            if type_mismatch:
                reasons.append(
                    f"Type mismatch: prefix '{prefix}-' suggests '{expected_type}', got '{node_type}'"
                )
            if filename_mismatch:
                reasons.append(f"Filename mismatch: stem '{stem}' != ID '{node_id}'")

            mismatches.append({"id": node_id, "type": node_type, "path": path, "reasons": reasons})

    print(f"Found {len(mismatches)} mismatches.")
    for m in mismatches[:20]:  # Show first 20
        print(f"\nID: {m['id']} (Type: {m['type']})")
        print(f"Path: {m['path']}")
        for r in m["reasons"]:
            print(f"  - {r}")

    if len(mismatches) > 20:
        print(f"\n... and {len(mismatches) - 20} more.")


if __name__ == "__main__":
    audit_tasks()
