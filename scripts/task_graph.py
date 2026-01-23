#!/usr/bin/env python3
"""Generate styled DOT graph from fast-indexer JSON output.

Reads JSON from fast-indexer and applies color coding based on
status, priority, and type. Generates SVG using Graphviz sfdp.

Usage:
    python task_graph.py INPUT.json [-o OUTPUT]

Examples:
    fast-indexer ./data -o graph -f json -t task,project,goal
    python task_graph.py graph.json -o tasks
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Color schemes
STATUS_COLORS = {
    "done": "#d4edda",      # green
    "completed": "#d4edda",
    "cancelled": "#e9ecef", # gray
    "active": "#cce5ff",    # blue
    "in_progress": "#cce5ff",
    "blocked": "#f8d7da",   # red
    "waiting": "#fff3cd",   # yellow
    "inbox": "#ffffff",     # white
    "todo": "#ffffff",      # white
}

PRIORITY_BORDERS = {
    0: "#dc3545",  # P0 - red (critical)
    1: "#fd7e14",  # P1 - orange (high)
    2: "#6c757d",  # P2 - gray (medium)
    3: "#adb5bd",  # P3 - light gray (low)
    4: "#dee2e6",  # P4 - very light (someday)
}

TYPE_SHAPES = {
    "goal": "ellipse",
    "project": "box3d",
    "task": "box",
    "action": "note",
}

# Structural completed nodes (completed parents with active children)
STRUCTURAL_STYLE = {
    "shape": "box3d",
    "fillcolor": "#c3e6cb",  # muted green
    "style": "filled,dashed",
}


def filter_completed_smart(nodes: list[dict], edges: list[dict]) -> tuple[list[dict], set[str]]:
    """Filter completed tasks, keeping structural parents with active descendants.

    Returns:
        (filtered_nodes, structural_ids) where structural_ids are completed nodes
        kept because they have active descendants (displayed differently).
    """
    done_statuses = {"done", "completed"}

    # Build node lookup and identify completed nodes
    node_by_id = {n["id"]: n for n in nodes}
    completed_ids = {n["id"] for n in nodes if n.get("status", "").lower() in done_statuses}
    active_ids = {n["id"] for n in nodes if n.get("status", "").lower() not in done_statuses}

    # Build adjacency: for each node, find its neighbors (bidirectional for wikilinks)
    neighbors = {n["id"]: set() for n in nodes}
    for e in edges:
        src, tgt = e["source"], e["target"]
        if src in neighbors and tgt in neighbors:
            neighbors[src].add(tgt)
            neighbors[tgt].add(src)

    # Find completed nodes that have a path to any active node
    # (these are "structural" - they connect active parts of the graph)
    structural_ids = set()

    def has_active_neighbor(node_id: str, visited: set) -> bool:
        """Check if node has any active node reachable through the graph."""
        if node_id in visited:
            return False
        visited.add(node_id)

        for neighbor in neighbors.get(node_id, []):
            if neighbor in active_ids:
                return True
            if neighbor in completed_ids and neighbor not in visited:
                if has_active_neighbor(neighbor, visited):
                    return True
        return False

    for node_id in completed_ids:
        if has_active_neighbor(node_id, set()):
            structural_ids.add(node_id)

    # Keep: all active nodes + structural completed nodes
    keep_ids = active_ids | structural_ids
    filtered_nodes = [n for n in nodes if n["id"] in keep_ids]

    return filtered_nodes, structural_ids


def generate_dot(nodes: list[dict], edges: list[dict], include_orphans: bool = False,
                 structural_ids: set[str] | None = None) -> str:
    """Generate DOT format graph with styling.

    Args:
        structural_ids: Set of node IDs that are completed but kept for structure.
                       These get box3d shape with dashed style.
    """
    structural_ids = structural_ids or set()

    # Build node lookup by id
    node_by_id = {n["id"]: n for n in nodes}

    # Filter to connected nodes only (unless include_orphans)
    if not include_orphans:
        connected = set()
        for edge in edges:
            connected.add(edge["source"])
            connected.add(edge["target"])
        nodes = [n for n in nodes if n["id"] in connected]

    lines = [
        "digraph TaskGraph {",
        "    rankdir=TB;",
        "    node [style=filled, fontname=\"Helvetica\"];",
        "    edge [color=\"#6c757d\"];",
        "",
        "    // Legend",
        "    subgraph cluster_legend {",
        "        label=\"Legend\";",
        "        style=dashed;",
        "        legend_goal [label=\"Goal\" shape=ellipse fillcolor=\"#cce5ff\"];",
        "        legend_project [label=\"Project\" shape=box3d fillcolor=\"#cce5ff\"];",
        "        legend_task [label=\"Task\" shape=box fillcolor=\"#cce5ff\"];",
        "        legend_done [label=\"Done\" shape=box fillcolor=\"#d4edda\"];",
        "        legend_structural [label=\"Done (structural)\" shape=box3d style=\"filled,dashed\" fillcolor=\"#c3e6cb\"];",
        "        legend_blocked [label=\"Blocked\" shape=box fillcolor=\"#f8d7da\"];",
        "    }",
        "",
    ]

    # Add nodes
    for node in nodes:
        node_id = node["id"]
        node_type = node.get("node_type", "task")
        status = node.get("status", "inbox")
        priority = node.get("priority", 2)

        # Check if this is a structural completed node
        if node_id in structural_ids:
            shape = STRUCTURAL_STYLE["shape"]
            fillcolor = STRUCTURAL_STYLE["fillcolor"]
            style = STRUCTURAL_STYLE["style"]
        else:
            shape = TYPE_SHAPES.get(node_type, "box")
            fillcolor = STATUS_COLORS.get(status, "#ffffff")
            style = "filled"

        priority = priority if isinstance(priority, int) else 2
        pencolor = PRIORITY_BORDERS.get(priority, "#6c757d")
        penwidth = 3 if priority <= 1 else 1

        label = node.get("label", node["id"])[:50].replace('"', '\\"')

        lines.append(
            f'    "{node_id}" ['
            f'label="{label}" '
            f'shape={shape} '
            f'style="{style}" '
            f'fillcolor="{fillcolor}" '
            f'color="{pencolor}" '
            f'penwidth={penwidth}'
            f'];'
        )

    lines.append("")

    # Add edges (only for nodes in our filtered set)
    node_ids = {n["id"] for n in nodes}
    for edge in edges:
        if edge["source"] in node_ids and edge["target"] in node_ids:
            lines.append(f'    "{edge["source"]}" -> "{edge["target"]}";')

    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate styled task graph from fast-indexer JSON")
    parser.add_argument("input", help="Input JSON file from fast-indexer")
    parser.add_argument("-o", "--output", default="tasks", help="Output base name")
    parser.add_argument("--include-orphans", action="store_true", help="Include unconnected nodes")
    parser.add_argument("--exclude-done", action="store_true", help="Exclude all tasks with status done/completed")
    parser.add_argument("--smart-filter", action="store_true",
                        help="Smart filter: remove completed leaves but keep completed parents with active children (shown as box3d)")
    parser.add_argument("--layout", default="sfdp", choices=["dot", "neato", "sfdp", "fdp", "circo", "twopi"],
                        help="Graphviz layout engine (default: sfdp)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    # Load JSON
    with open(input_path) as f:
        data = json.load(f)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    print(f"Loaded {len(nodes)} nodes, {len(edges)} edges from {input_path}")

    # Filter completed tasks
    structural_ids = set()
    if args.smart_filter:
        # Smart filter: keep completed parents with active children
        original_count = len(nodes)
        nodes, structural_ids = filter_completed_smart(nodes, edges)
        excluded_leaves = original_count - len(nodes)
        if excluded_leaves > 0 or structural_ids:
            print(f"  Smart filter: excluded {excluded_leaves} completed leaves, kept {len(structural_ids)} structural")
    elif args.exclude_done:
        # Simple filter: remove all completed
        done_statuses = {"done", "completed"}
        original_count = len(nodes)
        nodes = [n for n in nodes if n.get("status", "").lower() not in done_statuses]
        excluded = original_count - len(nodes)
        if excluded > 0:
            print(f"  Excluded {excluded} done/completed tasks")

    # Count by type and status
    by_type = {}
    by_status = {}
    for n in nodes:
        t = n.get("node_type", "unknown")
        s = n.get("status", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_status[s] = by_status.get(s, 0) + 1
    print(f"  Types: {by_type}")
    print(f"  Status: {by_status}")

    # Generate DOT
    dot_content = generate_dot(nodes, edges, args.include_orphans, structural_ids)
    dot_path = f"{args.output}.dot"
    Path(dot_path).write_text(dot_content)
    print(f"  Written {dot_path}")

    # Generate SVG
    svg_path = f"{args.output}.svg"
    layout_opts = {
        "sfdp": ["-Goverlap=prism", "-Gsplines=true"],
        "neato": ["-Goverlap=prism", "-Gsplines=true"],
        "fdp": ["-Goverlap=prism", "-Gsplines=true"],
        "dot": [],
        "circo": [],
        "twopi": [],
    }
    try:
        cmd = [args.layout, "-Tsvg"] + layout_opts.get(args.layout, []) + [dot_path, "-o", svg_path]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  Written {svg_path}")
    except FileNotFoundError:
        print(f"  Warning: {args.layout} not found, skipping SVG generation")
    except subprocess.CalledProcessError as e:
        print(f"  Warning: {args.layout} failed: {e.stderr.decode()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
