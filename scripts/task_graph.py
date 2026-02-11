#!/usr/bin/env python3
"""Generate styled DOT graph from fast-indexer JSON output.

Reads JSON from fast-indexer and applies color coding based on
status, priority, and type. Generates SVG using Graphviz sfdp.

By default, generates two SVG variants:
  - {output}.svg         : Smart-filtered (active work focus)
  - {output}-rollup.svg  : Pruned tree (unfinished nodes + structural ancestors)

Usage:
    python task_graph.py INPUT.json [-o OUTPUT] [--single]

Examples:
    fast-indexer ./data -o graph -f json -t task,project,goal
    python task_graph.py graph.json -o task-map          # Generates 2 SVGs
    python task_graph.py graph.json -o task-map --single  # Single output only
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Color schemes
ASSIGNEE_COLORS = {
    "bot": "#17a2b8",  # cyan/teal - AI agent
    "claude": "#17a2b8",  # same as bot
    "worker": "#fd7e14",  # orange - background worker
    "nic": "#6f42c1",  # purple - human
}
ASSIGNEE_DEFAULT = "#6c757d"  # gray for unassigned

STATUS_COLORS = {
    "done": "#d4edda",  # green
    "completed": "#d4edda",
    "cancelled": "#e9ecef",  # gray
    "active": "#cce5ff",  # blue
    "in_progress": "#cce5ff",
    "blocked": "#f8d7da",  # red
    "waiting": "#fff3cd",  # yellow
    "inbox": "#ffffff",  # white
    "todo": "#ffffff",  # white
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
    "epic": "octagon",  # Milestone grouping
    "task": "box",
    "action": "note",
    "bug": "diamond",  # Defect to fix
    "feature": "hexagon",  # New functionality
    "learn": "tab",  # Observational tracking
}

EDGE_STYLES = {
    "parent": {"color": "#6c757d", "style": "solid"},  # gray - hierarchy
    "depends_on": {"color": "#dc3545", "style": "bold"},  # red - blocking
    "soft_depends_on": {"color": "#17a2b8", "style": "dashed"},  # teal - advisory
    "wikilink": {"color": "#adb5bd", "style": "dotted"},  # light gray - generic
}

# Structural completed nodes (completed parents with active children)
STRUCTURAL_STYLE = {
    "shape": "box3d",
    "fillcolor": "#c3e6cb",  # muted green
    "style": "filled,dashed",
}

# Statuses considered incomplete (assignee coloring applies)
INCOMPLETE_STATUSES = {
    "inbox",
    "active",
    "in_progress",
    "blocked",
    "waiting",
    "todo",
    "pending",
}


def extract_assignee(file_path: str) -> str | None:
    """Extract assignee from markdown frontmatter."""
    try:
        path = Path(file_path)
        if not path.exists():
            return None
        content = path.read_text(errors="ignore")[:2000]  # Only read start
        if not content.startswith("---"):
            return None
        # Find end of frontmatter
        end = content.find("\n---", 3)
        if end == -1:
            return None
        frontmatter = content[3:end]
        match = re.search(r"^assignee:\s*(.+)$", frontmatter, re.MULTILINE)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None


def filter_completed_smart(nodes: list[dict], edges: list[dict]) -> tuple[list[dict], set[str]]:
    """Filter completed tasks, keeping structural parents with active descendants.

    Returns:
        (filtered_nodes, structural_ids) where structural_ids are completed nodes
        kept because they have active descendants (displayed differently).
    """
    done_statuses = {"done", "completed"}

    # Build node lookup and identify completed nodes
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


def filter_rollup(nodes: list[dict], edges: list[dict]) -> tuple[list[dict], set[str]]:
    """Filter to show only unfinished nodes and ancestors with unfinished descendants.

    This creates a "rollup" view showing the pruned tree of incomplete work.
    Completed leaf nodes are removed, but completed structural nodes (those with
    incomplete descendants) are preserved to maintain hierarchy context.

    Returns:
        (filtered_nodes, structural_ids) where structural_ids are completed nodes
        kept because they have unfinished descendants (displayed differently).
    """
    done_statuses = {"done", "completed"}

    # Build lookups
    node_by_id = {n["id"]: n for n in nodes}
    unfinished_ids = {n["id"] for n in nodes if n.get("status", "").lower() not in done_statuses}

    # Build parent→children mapping from node.parent field
    # (more reliable than parsing edges since nodes directly declare their parent)
    children_of: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for node in nodes:
        parent_id = node.get("parent")
        if parent_id and parent_id in children_of:
            children_of[parent_id].append(node["id"])

    # Memoized check: does this node have any unfinished descendant?
    memo: dict[str, bool] = {}

    def has_unfinished_descendant(node_id: str, visited: set[str]) -> bool:
        """Check if node has any unfinished node in its subtree (children, grandchildren, etc.)."""
        if node_id in memo:
            return memo[node_id]
        if node_id in visited:  # Cycle detection
            return False
        visited.add(node_id)

        for child_id in children_of.get(node_id, []):
            if child_id in unfinished_ids:
                memo[node_id] = True
                return True
            if has_unfinished_descendant(child_id, visited):
                memo[node_id] = True
                return True

        memo[node_id] = False
        return False

    # Determine which nodes to keep
    keep_ids: set[str] = set()
    structural_ids: set[str] = set()

    for node_id in node_by_id:
        if node_id in unfinished_ids:
            # Always keep unfinished nodes
            keep_ids.add(node_id)
        elif has_unfinished_descendant(node_id, set()):
            # Keep finished nodes that have unfinished descendants (structural)
            keep_ids.add(node_id)
            structural_ids.add(node_id)
        # Otherwise: finished node with no unfinished descendants → prune

    filtered_nodes = [n for n in nodes if n["id"] in keep_ids]
    return filtered_nodes, structural_ids


def classify_edge(source_id: str, target_id: str, node_by_id: dict) -> str:
    """Determine edge type from node relationships."""
    source = node_by_id.get(source_id, {})
    if source.get("parent") == target_id:
        return "parent"
    if target_id in source.get("depends_on", []):
        return "depends_on"
    if target_id in source.get("soft_depends_on", []):
        return "soft_depends_on"
    return "wikilink"


def generate_dot(
    nodes: list[dict],
    edges: list[dict],
    include_orphans: bool = False,
    structural_ids: set[str] | None = None,
    stats: dict | None = None,
) -> str:
    """Generate DOT format graph with styling.

    Args:
        structural_ids: Set of node IDs that are completed but kept for structure.
                       These get box3d shape with dashed style.
        stats: Optional dict with graph statistics to display in legend.
               Expected keys: total_nodes, total_edges, by_type, by_status
    """
    structural_ids = structural_ids or set()
    stats = stats or {}

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
        '    node [style=filled, fontname="Helvetica"];',
        '    edge [color="#6c757d"];',
        "",
        "    // Legend Container",
        "    subgraph cluster_legend_container {",
        '        label="Legend & Statistics";',
        '        style="filled,solid";',
        '        fillcolor="#f8f9fa";',
        '        color="#dee2e6";',
        '        fontsize=14;',
        "",
        "        // Legend - Task Types",
        "        subgraph cluster_legend_types {",
        '            label="Task Types";',
        "            style=dashed;",
        '            legend_goal [label="Goal" shape=ellipse fillcolor="#cce5ff"];',
        '            legend_project [label="Project" shape=box3d fillcolor="#cce5ff"];',
        '            legend_epic [label="Epic" shape=octagon fillcolor="#cce5ff"];',
        '            legend_task [label="Task" shape=box fillcolor="#cce5ff"];',
        '            legend_action [label="Action" shape=note fillcolor="#cce5ff"];',
        '            legend_bug [label="Bug" shape=diamond fillcolor="#cce5ff"];',
        '            legend_feature [label="Feature" shape=hexagon fillcolor="#cce5ff"];',
        '            legend_learn [label="Learn" shape=tab fillcolor="#cce5ff"];',
        "        }",
        "",
        "        // Legend - Status",
        "        subgraph cluster_legend_status {",
        '            label="Status";',
        "            style=dashed;",
        '            legend_active [label="Active" shape=box fillcolor="#cce5ff"];',
        '            legend_done [label="Done" shape=box fillcolor="#d4edda"];',
        '            legend_structural [label="Done (structural)" shape=box3d style="filled,dashed" fillcolor="#c3e6cb"];',
        '            legend_blocked [label="Blocked" shape=box fillcolor="#f8d7da"];',
        '            legend_waiting [label="Waiting" shape=box fillcolor="#fff3cd"];',
        "        }",
        "",
        "        // Legend - Assignee",
        "        subgraph cluster_legend_assignee {",
        '            label="Assignee";',
        "            style=dashed;",
        '            legend_bot [label="@bot" shape=box fillcolor="#ffffff" color="#17a2b8" penwidth=3];',
        '            legend_nic [label="@nic" shape=box fillcolor="#ffffff" color="#6f42c1" penwidth=3];',
        '            legend_worker [label="@worker" shape=box fillcolor="#ffffff" color="#fd7e14" penwidth=3];',
        "        }",
        "",
        "        // Legend - Edge Types",
        "        subgraph cluster_legend_edges {",
        '            label="Edge Types";',
        "            style=dashed;",
        '            legend_e1 [label="" shape=point width=0.1];',
        '            legend_e2 [label="" shape=point width=0.1];',
        '            legend_e3 [label="" shape=point width=0.1];',
        '            legend_e4 [label="" shape=point width=0.1];',
        '            legend_e5 [label="" shape=point width=0.1];',
        '            legend_e6 [label="" shape=point width=0.1];',
        '            legend_e1 -> legend_e2 [label="parent" color="#6c757d" style=solid];',
        '            legend_e3 -> legend_e4 [label="depends_on" color="#dc3545" style=bold];',
        '            legend_e5 -> legend_e6 [label="soft_depends" color="#17a2b8" style=dashed];',
        "        }",
    ]

    # Add statistics subgraph if stats provided
    if stats:
        total_nodes = stats.get("total_nodes", 0)
        total_edges = stats.get("total_edges", 0)
        by_type = stats.get("by_type", {})
        by_status = stats.get("by_status", {})

        # Build type breakdown string
        type_parts = [f"{v} {k}" for k, v in sorted(by_type.items(), key=lambda x: -x[1])]
        type_str = ", ".join(type_parts[:5])  # Top 5 types
        if len(type_parts) > 5:
            type_str += f", +{len(type_parts) - 5} more"

        # Build status breakdown string
        status_parts = [f"{v} {k}" for k, v in sorted(by_status.items(), key=lambda x: -x[1])]
        status_str = ", ".join(status_parts[:5])  # Top 5 statuses
        if len(status_parts) > 5:
            status_str += f", +{len(status_parts) - 5} more"

        stats_label = (
            f"Graph Statistics\\n"
            f"─────────────────\\n"
            f"Nodes: {total_nodes}\\n"
            f"Edges: {total_edges}\\n"
            f"─────────────────\\n"
            f"By Type:\\n{type_str}\\n"
            f"─────────────────\\n"
            f"By Status:\\n{status_str}"
        )

        lines.extend(
            [
                "        // Statistics",
                "        subgraph cluster_stats {",
                '            label="";',
                "            style=filled;",
                '            fillcolor="#f8f9fa";',
                f'            stats_box [label="{stats_label}" shape=note fillcolor="#ffffff" fontsize=10];',
                "        }",
                "",
            ]
        )

    # Close the legend container
    lines.append("    }")
    lines.append("")

    # Add nodes
    for node in nodes:
        node_id = node["id"]
        node_type = node.get("node_type", "task")
        status = node.get("status", "inbox")
        priority = node.get("priority", 2)
        file_path = node.get("path", "")

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

        # For incomplete tasks, use assignee color for border; otherwise priority color
        is_incomplete = status.lower() in INCOMPLETE_STATUSES
        if is_incomplete and file_path:
            assignee = extract_assignee(file_path)
            if assignee:
                pencolor = ASSIGNEE_COLORS.get(assignee, ASSIGNEE_DEFAULT)
                penwidth = 3  # Thick border for assigned tasks
            else:
                pencolor = PRIORITY_BORDERS.get(priority, "#6c757d")
                penwidth = 3 if priority <= 1 else 1
        else:
            pencolor = PRIORITY_BORDERS.get(priority, "#6c757d")
            penwidth = 3 if priority <= 1 else 1

        label = node.get("label", node["id"])[:50].replace('"', '\\"')

        lines.append(
            f'    "{node_id}" ['
            f'label="{label}" '
            f"shape={shape} "
            f'style="{style}" '
            f'fillcolor="{fillcolor}" '
            f'color="{pencolor}" '
            f"penwidth={penwidth}"
            f"];"
        )

    lines.append("")

    # Add edges (only for nodes in our filtered set)
    node_ids = {n["id"] for n in nodes}
    for edge in edges:
        if edge["source"] in node_ids and edge["target"] in node_ids:
            edge_type = classify_edge(edge["source"], edge["target"], node_by_id)
            style = EDGE_STYLES.get(edge_type, EDGE_STYLES["wikilink"])
            lines.append(
                f'    "{edge["source"]}" -> "{edge["target"]}" '
                f'[color="{style["color"]}" style="{style["style"]}"];'
            )

    lines.append("}")
    return "\n".join(lines)


def generate_svg(dot_content: str, output_base: str, layout: str, keep_dot: bool = False) -> bool:
    """Generate SVG from DOT content using Graphviz.

    Args:
        dot_content: The DOT format graph content
        output_base: Base path for output (without extension)
        layout: Graphviz layout engine to use
        keep_dot: If True, keep the .dot file; otherwise delete after SVG generation

    Returns:
        True if SVG was successfully generated
    """
    dot_path = f"{output_base}.dot"
    svg_path = f"{output_base}.svg"

    Path(dot_path).write_text(dot_content)

    layout_opts = {
        "sfdp": ["-Goverlap=prism", "-Gsplines=true"],
        "neato": ["-Goverlap=prism", "-Gsplines=true"],
        "fdp": ["-Goverlap=prism", "-Gsplines=true"],
        "dot": [],
        "circo": [],
        "twopi": [],
    }

    try:
        cmd = [layout, "-Tsvg"] + layout_opts.get(layout, []) + [dot_path, "-o", svg_path]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  Written {svg_path}")
        success = True
    except FileNotFoundError:
        print(f"  Warning: {layout} not found, skipping SVG generation")
        success = False
    except subprocess.CalledProcessError as e:
        print(f"  Warning: {layout} failed: {e.stderr.decode()}")
        success = False

    if not keep_dot and Path(dot_path).exists():
        Path(dot_path).unlink()
    elif keep_dot:
        print(f"  Written {dot_path}")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Generate styled task graph from fast-indexer JSON"
    )
    parser.add_argument("input", help="Input JSON file from fast-indexer")
    parser.add_argument("-o", "--output", default="tasks", help="Output base name")
    parser.add_argument("--include-orphans", action="store_true", help="Include unconnected nodes")
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="Disable smart filtering (show all tasks including completed)",
    )
    parser.add_argument(
        "--layout",
        default="sfdp",
        choices=["dot", "neato", "sfdp", "fdp", "circo", "twopi"],
        help="Graphviz layout engine (default: sfdp)",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Generate only single output (default generates multiple variants)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    # Load JSON
    with open(input_path) as f:
        data = json.load(f)

    all_nodes = data["nodes"]
    all_edges = data["edges"]

    print(f"Loaded {len(all_nodes)} nodes, {len(all_edges)} edges from {input_path}")

    # Define variants to generate
    # Each variant: (suffix, filter_type, include_orphans, description)
    # filter_type: "smart" = active work focus, "rollup" = pruned tree, None = no filter
    if args.single:
        # Single mode: respect --no-filter and --include-orphans flags
        variants = [
            (
                "",
                None if args.no_filter else "smart",
                args.include_orphans,
                "single output",
            ),
        ]
    else:
        # Multi mode (default): generate both variants
        variants = [
            ("", "smart", False, "smart-filtered (active work)"),
            (
                "-rollup",
                "rollup",
                False,
                "pruned tree (unfinished + structural ancestors)",
            ),
        ]

    for suffix, filter_type, include_orphans, description in variants:
        output_base = f"{args.output}{suffix}"
        print(f"\nGenerating {output_base}.svg: {description}")

        # Start with fresh copy of all nodes
        nodes = list(all_nodes)
        edges = list(all_edges)

        # Apply filter based on type
        structural_ids = set()
        original_count = len(nodes)
        if filter_type == "smart":
            nodes, structural_ids = filter_completed_smart(nodes, edges)
        elif filter_type == "rollup":
            nodes, structural_ids = filter_rollup(nodes, edges)
        # filter_type == None means no filtering

        excluded_count = original_count - len(nodes)
        if excluded_count > 0 or structural_ids:
            print(
                f"  Filtered: {excluded_count} nodes removed, {len(structural_ids)} structural kept"
            )

        # Count by type and status for this variant
        # Note: Some linked nodes (non-tasks) may lack status/type fields
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for n in nodes:
            t = n.get("node_type") or "unknown"
            s = n.get("status") or "unknown"
            by_type[t] = by_type.get(t, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1
        print(f"  Types: {by_type}")
        print(f"  Status: {by_status}")

        # Build stats dict for legend
        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "by_type": by_type,
            "by_status": by_status,
        }

        # Generate DOT and SVG
        dot_content = generate_dot(nodes, edges, include_orphans, structural_ids, stats)
        # Keep .dot file only for primary output (no suffix)
        generate_svg(dot_content, output_base, args.layout, keep_dot=(suffix == ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
