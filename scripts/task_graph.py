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

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

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
    # Task types
    "goal": "ellipse",
    "project": "box3d",
    "epic": "octagon",  # Milestone grouping
    "task": "box",
    "action": "note",
    "bug": "diamond",  # Defect to fix
    "feature": "hexagon",  # New functionality
    "learn": "tab",  # Observational tracking
    # PKB cross-type nodes (#563)
    "daily": "plaintext",
    "knowledge": "note",
    "person": "circle",
    "context": "cds",
    "template": "component",
    "note": "box",  # Default
}

EDGE_STYLES = {
    "parent": {"color": "#0d6efd", "style": "solid", "penwidth": "3"},  # blue - hierarchy
    "depends_on": {"color": "#dc3545", "style": "bold", "penwidth": "2"},  # red - blocking
    "soft_depends_on": {
        "color": "#6c757d",
        "style": "dashed",
        "penwidth": "1.5",
    },  # gray - advisory
    "link": {"color": "#adb5bd", "style": "dotted", "penwidth": "1"},  # light gray - generic
    "wikilink": {"color": "#adb5bd", "style": "dotted", "penwidth": "1"},
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


def filter_reachable(nodes: list[dict], edges: list[dict]) -> tuple[list[dict], set[str]]:
    """Filter to nodes reachable from unfinished leaf tasks.

    A "leaf" is an unfinished node with no unfinished children. This catches:
    - Actionable tasks (active, no children)
    - Stale mid-level tasks (active but not decomposed into subtasks)
    - Projects needing breakdown (active with only completed children)

    From each leaf, walks upstream through parent, depends_on, and soft_depends_on
    edges to show the full hierarchy and blocker chain.

    Returns:
        (filtered_nodes, structural_ids) where structural_ids are completed nodes
        kept because they are ancestors of leaves (displayed differently).
    """
    done_statuses = {"done", "completed", "cancelled"}

    # Build lookups
    node_by_id = {n["id"]: n for n in nodes}
    unfinished_ids = {n["id"] for n in nodes if n.get("status", "").lower() not in done_statuses}

    # Build parent→children mapping
    children_of: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for node in nodes:
        parent_id = node.get("parent")
        if parent_id and parent_id in children_of:
            children_of[parent_id].append(node["id"])

    # Identify leaves: unfinished work-item nodes with no unfinished children.
    # Only nodes with an explicit status AND a work-item node_type can seed the BFS.
    # This prevents contacts/notes/references (which have no status and are childless)
    # from being treated as actionable leaves and flooding the graph.
    _LEAF_TYPES = {"task", "project", "epic", "bug", "feature", "review"}
    leaf_ids: set[str] = set()
    for node_id in unfinished_ids:
        node = node_by_id[node_id]
        if not node.get("status"):
            continue
        if node.get("node_type") not in _LEAF_TYPES:
            continue
        unfinished_children = [c for c in children_of.get(node_id, []) if c in unfinished_ids]
        if not unfinished_children:
            leaf_ids.add(node_id)

    # Build upstream adjacency: for each node, what can we reach by walking
    # "up" through parent, depends_on, and soft_depends_on edges?
    upstream_of: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    for node in nodes:
        nid = node["id"]
        # Parent edge (child → parent)
        parent_id = node.get("parent")
        if parent_id and parent_id in node_by_id:
            upstream_of[nid].add(parent_id)
        # Hard dependencies (task → blocker)
        for dep_id in node.get("depends_on") or []:
            if dep_id in node_by_id:
                upstream_of[nid].add(dep_id)
        # Soft dependencies (task → advisory dep)
        for dep_id in node.get("soft_depends_on") or []:
            if dep_id in node_by_id:
                upstream_of[nid].add(dep_id)

    # Walk upstream from all leaves (BFS)
    reachable: set[str] = set(leaf_ids)
    frontier = set(leaf_ids)
    while frontier:
        next_frontier: set[str] = set()
        for nid in frontier:
            for upstream_id in upstream_of.get(nid, set()):
                if upstream_id not in reachable:
                    reachable.add(upstream_id)
                    next_frontier.add(upstream_id)
        frontier = next_frontier

    # Classify: structural = completed/cancelled nodes kept for context
    keep_ids = reachable
    structural_ids = keep_ids - unfinished_ids

    filtered_nodes = [n for n in nodes if n["id"] in keep_ids]
    return filtered_nodes, structural_ids


def classify_edge(source_id: str, target_id: str, node_by_id: dict) -> str:
    """Determine edge type from node relationships."""
    source = node_by_id.get(source_id, {})
    if source.get("parent") == target_id:
        return "parent"
    if target_id in (source.get("depends_on") or []):
        return "depends_on"
    if target_id in (source.get("soft_depends_on") or []):
        return "soft_depends_on"
    return "link"


def _build_legend_table(stats: dict) -> str:
    """Build an HTML table label for the legend node.

    Uses Graphviz HTML-like label syntax to create a compact, boxed legend
    that works with all layout engines (including sfdp, neato, fdp).
    """
    rows = []

    rows.append(
        '<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4"'
        ' COLOR="#dee2e6" BGCOLOR="#f8f9fa">'
    )

    # Title
    rows.append(
        '<TR><TD COLSPAN="4" ALIGN="CENTER">'
        '<B><FONT POINT-SIZE="14" COLOR="#495057">Legend</FONT></B>'
        "</TD></TR>"
    )

    # Task Types (include PKB cross-types #563)
    rows.append('<TR><TD COLSPAN="4" BGCOLOR="#e9ecef"><B>Node Types</B></TD></TR>')
    type_items = [
        ("Goal", "ellipse"),
        ("Project", "box3d"),
        ("Epic", "octagon"),
        ("Task", "box"),
        ("Action", "note"),
        ("Bug", "diamond"),
        ("Feature", "hexagon"),
        ("Learn", "tab"),
        ("Daily", "plaintext"),
        ("Knowledge", "note"),
        ("Person", "circle"),
    ]
    for i in range(0, len(type_items), 4):
        chunk = type_items[i : i + 4]
        cells = "".join(
            f'<TD BGCOLOR="#cce5ff" BORDER="1">{name} ({shape})</TD>' for name, shape in chunk
        )
        rows.append(f"<TR>{cells}</TR>")

    # Status
    rows.append('<TR><TD COLSPAN="4" BGCOLOR="#e9ecef"><B>Status</B></TD></TR>')
    status_items = [
        ("Active", "#cce5ff"),
        ("Done", "#d4edda"),
        ("Structural", "#c3e6cb"),
        ("Blocked", "#f8d7da"),
    ]
    cells = "".join(f'<TD BGCOLOR="{color}" BORDER="1">{name}</TD>' for name, color in status_items)
    rows.append(f"<TR>{cells}</TR>")
    rows.append('<TR><TD BGCOLOR="#fff3cd" BORDER="1">Waiting</TD><TD COLSPAN="3"></TD></TR>')

    # Assignee
    rows.append('<TR><TD COLSPAN="4" BGCOLOR="#e9ecef"><B>Assignee (border color)</B></TD></TR>')
    assignee_items = [
        ("@bot", "#17a2b8"),
        ("@nic", "#6f42c1"),
        ("@worker", "#fd7e14"),
    ]
    cells = "".join(f'<TD BORDER="1" COLOR="{color}">{name}</TD>' for name, color in assignee_items)
    cells += "<TD></TD>"
    rows.append(f"<TR>{cells}</TR>")

    # Downstream Weight
    rows.append('<TR><TD COLSPAN="4" BGCOLOR="#e9ecef"><B>Downstream Weight</B></TD></TR>')
    rows.append(
        "<TR>"
        '<TD COLSPAN="2">\u2696 N.N = impact score</TD>'
        '<TD COLSPAN="2">Double border = stakeholder</TD>'
        "</TR>"
    )

    # Edge Types
    rows.append('<TR><TD COLSPAN="4" BGCOLOR="#e9ecef"><B>Edge Types</B></TD></TR>')
    rows.append(
        "<TR>"
        '<TD><FONT COLOR="#0d6efd"><B>&#x2501;&#x2501;</B></FONT> parent</TD>'
        '<TD><FONT COLOR="#dc3545"><B>&#x2500;&#x2500;</B></FONT> depends_on</TD>'
        '<TD><FONT COLOR="#6c757d">- - -</FONT> soft_depends_on</TD>'
        '<TD><FONT COLOR="#adb5bd">. . .</FONT> link</TD>'
        "</TR>"
    )

    # Statistics
    if stats:
        total_nodes = stats.get("total_nodes", 0)
        total_edges = stats.get("total_edges", 0)
        rows.append('<TR><TD COLSPAN="4" BGCOLOR="#e9ecef"><B>Statistics</B></TD></TR>')
        rows.append(
            f'<TR><TD COLSPAN="2">Nodes: {total_nodes}</TD>'
            f'<TD COLSPAN="2">Edges: {total_edges}</TD></TR>'
        )

        by_type = stats.get("by_type", {})
        if by_type:
            parts = [f"{v} {k}" for k, v in sorted(by_type.items(), key=lambda x: -x[1])[:5]]
            rows.append(
                f'<TR><TD COLSPAN="4"><FONT POINT-SIZE="10">{", ".join(parts)}</FONT></TD></TR>'
            )

        by_status = stats.get("by_status", {})
        if by_status:
            parts = [f"{v} {k}" for k, v in sorted(by_status.items(), key=lambda x: -x[1])[:5]]
            rows.append(
                f'<TR><TD COLSPAN="4"><FONT POINT-SIZE="10">{", ".join(parts)}</FONT></TD></TR>'
            )

    rows.append("</TABLE>")
    return "\n".join(rows)


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
        "    splines=spline;",
        "    overlap=scalexy;",
        '    node [style=filled, fontname="Helvetica"];',
        '    edge [color="#6c757d"];',
    ]

    # Legend as a single HTML-table node (works with all layout engines)
    legend_html = _build_legend_table(stats)
    lines.extend(
        [
            "",
            "    // Legend",
            f"    legend [shape=plaintext margin=0 label=<{legend_html}>];",
            "",
        ]
    )

    # Add nodes
    for node in nodes:
        node_id = node["id"]
        node_type = node.get("node_type") or "task"
        status = node.get("status") or "inbox"
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

        # Downstream weight visualization
        dw = node.get("downstream_weight", 0)
        stakeholder = node.get("stakeholder_exposure", False)
        extra_attrs = ""

        if dw > 0:
            # Append weight to label
            label = f"{label}\\n\u2696 {dw:.1f}"
            # Sqrt scaling for better visual separation across the 1-10 range
            import math

            sqrt_dw = math.sqrt(dw)
            scale_w = min(1.2 + sqrt_dw * 0.7, 4.0)
            scale_h = min(0.8 + sqrt_dw * 0.3, 2.0)
            extra_attrs += f" width={scale_w:.2f} height={scale_h:.2f} fixedsize=false"
            # Graduated font size
            if dw >= 6.0:
                extra_attrs += " fontsize=16"
            elif dw >= 3.0:
                extra_attrs += " fontsize=13"
            # Thicken border proportional to weight (visual "heft")
            penwidth = max(penwidth, min(1 + sqrt_dw, 5))

        if stakeholder:
            # Double border for stakeholder exposure
            extra_attrs += " peripheries=2"

        lines.append(
            f'    "{node_id}" ['
            f'label="{label}" '
            f"shape={shape} "
            f'style="{style}" '
            f'fillcolor="{fillcolor}" '
            f'color="{pencolor}" '
            f"penwidth={penwidth}"
            f"{extra_attrs}"
            f"];"
        )

    lines.append("")

    # Add edges (only for nodes in our filtered set)
    node_ids = {n["id"] for n in nodes}
    for edge in edges:
        if edge["source"] in node_ids and edge["target"] in node_ids:
            # Prefer edge type from indexer JSON, fallback to classification
            edge_type = edge.get("type") or classify_edge(
                edge["source"], edge["target"], node_by_id
            )
            style = EDGE_STYLES.get(edge_type, EDGE_STYLES["link"])

            style_attrs = [
                f'color="{style["color"]}"',
                f'style="{style["style"]}"',
            ]
            if "penwidth" in style:
                style_attrs.append(f"penwidth={style['penwidth']}")

            lines.append(f'    "{edge["source"]}" -> "{edge["target"]}" [{" ".join(style_attrs)}];')

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

    layout_opts: dict[str, list[str]] = {
        "sfdp": [],
        "neato": [],
        "fdp": [],
        "dot": [],
        "circo": [],
        "twopi": [],
    }

    _FALLBACKS: dict[str, str] = {"sfdp": "fdp"}

    _FORCE_DIRECTED = {"fdp", "sfdp", "neato"}

    def _try_layout(eng: str) -> bool:
        try:
            if eng in _FORCE_DIRECTED:
                # Two-step: position nodes with the layout engine, then route
                # edges separately with neato -n.
                # Pass -Gsplines=line to sfdp/fdp so it only positions nodes
                # and doesn't attempt (and fall back from) spline routing itself.
                r1 = subprocess.run(
                    [eng, "-Txdot", "-Gsplines=line"] + [dot_path],
                    check=True,
                    capture_output=True,
                )
                # neato -n keeps positions, routes edges with full spline support.
                subprocess.run(
                    ["neato", "-n", "-Tsvg", "-Gsplines=spline", "-o", svg_path],
                    input=r1.stdout,
                    check=True,
                    capture_output=True,
                )
            else:
                cmd = [eng, "-Tsvg"] + layout_opts.get(eng, []) + [dot_path, "-o", svg_path]
                subprocess.run(cmd, check=True, capture_output=True)
            return True
        except FileNotFoundError:
            print(f"  Warning: {eng} not found, skipping SVG generation")
            return False
        except subprocess.CalledProcessError as e:
            print(f"  Warning: {eng} failed: {e.stderr.decode().strip()}")
            return False

    success = _try_layout(layout)
    if not success and layout in _FALLBACKS:
        fallback = _FALLBACKS[layout]
        print(f"  Retrying with {fallback}...")
        success = _try_layout(fallback)
    if success:
        print(f"  Written {svg_path}")

    if not keep_dot and Path(dot_path).exists():
        Path(dot_path).unlink()
    elif keep_dot:
        print(f"  Written {dot_path}")

    return success


def extract_ego_subgraph(
    nodes: list[dict], edges: list[dict], center_id: str, depth: int = 2
) -> tuple[list[dict], list[dict]]:
    """Extract ego-subgraph around a center node (#563).

    Includes all nodes within `depth` hops via ANY edge type,
    traversing edges bidirectionally.

    Args:
        nodes: All nodes from graph.json.
        edges: All edges from graph.json.
        center_id: Node ID to center on. Also tries resolution via label/filename.
        depth: Maximum hop distance from center.

    Returns:
        (filtered_nodes, filtered_edges) containing only the subgraph.
    """
    node_by_id = {n["id"]: n for n in nodes}

    # Try to resolve center_id if not a direct ID
    if center_id not in node_by_id:
        # Try label match (case-insensitive)
        for n in nodes:
            if n.get("label", "").lower() == center_id.lower():
                center_id = n["id"]
                break
        # Try filename stem match
        if center_id not in node_by_id:
            for n in nodes:
                stem = Path(n.get("path", "")).stem
                if stem.lower() == center_id.lower():
                    center_id = n["id"]
                    break

    if center_id not in node_by_id:
        print(f"Error: Cannot find node '{center_id}' in graph", file=sys.stderr)
        return [], []

    # Build undirected adjacency for BFS
    adjacency: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    for e in edges:
        src, tgt = e["source"], e["target"]
        if src in adjacency and tgt in adjacency:
            adjacency[src].add(tgt)
            adjacency[tgt].add(src)

    # BFS from center
    visited = {center_id}
    frontier = {center_id}
    for _ in range(depth):
        next_frontier = set()
        for nid in frontier:
            for neighbor in adjacency.get(nid, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier

    filtered_nodes = [n for n in nodes if n["id"] in visited]
    filtered_edges = [e for e in edges if e["source"] in visited and e["target"] in visited]

    return filtered_nodes, filtered_edges


def generate_attention_map(
    nodes: list[dict], edges: list[dict], top_n: int = 20
) -> tuple[list[dict], list[dict], list[dict]]:
    """Generate attention map: nodes where importance >> connectivity (#564).

    Computes importance (priority weight + downstream_weight) and connectivity
    (degree in the graph) for each node, then flags nodes with high gap scores.

    Args:
        nodes: All nodes from graph.json.
        edges: All edges from graph.json.
        top_n: Number of top attention-needed nodes to return.

    Returns:
        (flagged_nodes, flagged_edges, gap_data) where:
        - flagged_nodes: Subgraph of attention-needed nodes + their nearest neighbors
        - flagged_edges: Edges within the subgraph
        - gap_data: List of dicts with node info and gap scores
    """
    # Build degree map (undirected)
    degree: dict[str, int] = {n["id"]: 0 for n in nodes}
    for e in edges:
        src, tgt = e["source"], e["target"]
        if src in degree:
            degree[src] += 1
        if tgt in degree:
            degree[tgt] += 1

    # Priority weight mapping
    priority_weights = {0: 5.0, 1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}

    # Compute gap scores
    gap_data = []
    for node in nodes:
        nid = node["id"]
        # Skip done/cancelled
        status = (node.get("status") or "").lower()
        if status in ("done", "cancelled", "completed"):
            continue

        priority = node.get("priority")
        if priority is None:
            priority_weight = 0.5
        else:
            priority_weight = priority_weights.get(priority, 0.5)

        downstream = node.get("downstream_weight", 0.0)
        importance = priority_weight + downstream

        connectivity = degree.get(nid, 0)

        # Gap: high importance relative to connectivity
        if connectivity == 0:
            gap_score = importance
        else:
            gap_score = importance / (1 + connectivity)

        if gap_score > 0.5:  # Threshold for inclusion
            gap_data.append(
                {
                    "id": nid,
                    "label": node.get("label", ""),
                    "node_type": node.get("node_type") or "note",
                    "status": node.get("status"),
                    "priority": priority,
                    "importance": round(importance, 2),
                    "connectivity": connectivity,
                    "gap_score": round(gap_score, 2),
                }
            )

    # Sort by gap score
    gap_data.sort(key=lambda x: x["gap_score"], reverse=True)
    gap_data = gap_data[:top_n]

    # Build subgraph: flagged nodes + their direct neighbors
    flagged_ids = {g["id"] for g in gap_data}
    # Add nearest neighbors
    adjacency: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    for e in edges:
        src, tgt = e["source"], e["target"]
        if src in adjacency and tgt in adjacency:
            adjacency[src].add(tgt)
            adjacency[tgt].add(src)

    neighbor_ids = set()
    for fid in flagged_ids:
        for neighbor in adjacency.get(fid, set()):
            neighbor_ids.add(neighbor)

    subgraph_ids = flagged_ids | neighbor_ids
    flagged_nodes = [n for n in nodes if n["id"] in subgraph_ids]
    flagged_edges = [
        e for e in edges if e["source"] in subgraph_ids and e["target"] in subgraph_ids
    ]

    return flagged_nodes, flagged_edges, gap_data


def generate_attention_dot(
    nodes: list[dict],
    edges: list[dict],
    gap_data: list[dict],
) -> str:
    """Generate DOT format graph for attention map (#564).

    Flagged nodes (high gap score) get red borders with gap annotation.
    Neighbor nodes get normal styling.
    """
    flagged_ids = {g["id"] for g in gap_data}
    gap_by_id = {g["id"]: g for g in gap_data}

    lines = [
        "digraph AttentionMap {",
        "    rankdir=TB;",
        '    node [style=filled, fontname="Helvetica"];',
        '    edge [color="#6c757d"];',
        '    label="Attention Map: Under-connected Important Nodes";',
        "    labelloc=t;",
        "    fontsize=18;",
        "",
    ]

    for node in nodes:
        nid = node["id"]
        node_type = node.get("node_type") or "task"
        status = node.get("status") or "inbox"
        shape = TYPE_SHAPES.get(node_type, "box")
        fillcolor = STATUS_COLORS.get(status, "#ffffff")
        label = node.get("label", nid)[:50].replace('"', '\\"')

        if nid in flagged_ids:
            gap = gap_by_id[nid]
            label += f"\\n\u26a0 gap={gap['gap_score']}"
            pencolor = "#dc3545"  # Red border for attention
            penwidth = 3
            style = "filled,bold"
        else:
            pencolor = "#adb5bd"
            penwidth = 1
            style = "filled"

        lines.append(
            f'    "{nid}" ['
            f'label="{label}" '
            f"shape={shape} "
            f'style="{style}" '
            f'fillcolor="{fillcolor}" '
            f'color="{pencolor}" '
            f"penwidth={penwidth}"
            f"];"
        )

    lines.append("")

    node_ids = {n["id"] for n in nodes}
    for edge in edges:
        if edge["source"] in node_ids and edge["target"] in node_ids:
            edge_type = edge.get("type", "link")
            edge_style = EDGE_STYLES.get(edge_type, EDGE_STYLES["link"])
            style_attrs = [
                f'color="{edge_style["color"]}"',
                f'style="{edge_style["style"]}"',
            ]
            if "penwidth" in edge_style:
                style_attrs.append(f"penwidth={edge_style['penwidth']}")
            lines.append(f'    "{edge["source"]}" -> "{edge["target"]}" [{" ".join(style_attrs)}];')

    lines.append("}")
    return "\n".join(lines)


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
        default="fdp",
        choices=["dot", "neato", "sfdp", "fdp", "circo", "twopi"],
        help="Graphviz layout engine (default: sfdp)",
    )
    parser.add_argument(
        "--filter",
        choices=["smart", "rollup", "reachable", "none"],
        default=None,
        help="Filter type: smart (active work focus), rollup (unfinished + ancestors), reachable (upstream from active leaves), none",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Generate only single output (default generates multiple variants)",
    )
    # Ego-subgraph extraction (#563)
    parser.add_argument(
        "--ego",
        metavar="ID",
        help="Extract ego-subgraph centered on this node (ID, label, or filename)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Ego-subgraph depth in hops (default: 2, use with --ego)",
    )
    # Attention map (#564)
    parser.add_argument(
        "--attention-map",
        action="store_true",
        help="Generate attention map: under-connected important nodes",
    )
    parser.add_argument(
        "--attention-top",
        type=int,
        default=20,
        help="Number of top attention nodes (default: 20, use with --attention-map)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    # Load JSON
    with open(input_path) as f:
        data = json.load(f)

    all_nodes = [n for n in data["nodes"] if n.get("status", "").lower() != "cancelled"]
    node_ids = {n["id"] for n in all_nodes}
    all_edges = [e for e in data["edges"] if e["source"] in node_ids and e["target"] in node_ids]

    print(
        f"Loaded {len(all_nodes)} nodes (excluding cancelled), "
        f"{len(all_edges)} edges from {input_path}"
    )

    # Ego-subgraph extraction (#563)
    if args.ego:
        all_nodes, all_edges = extract_ego_subgraph(all_nodes, all_edges, args.ego, args.depth)
        if not all_nodes:
            return 1
        node_ids = {n["id"] for n in all_nodes}
        print(
            f"Ego subgraph: {len(all_nodes)} nodes, {len(all_edges)} edges "
            f"(center={args.ego}, depth={args.depth})"
        )

    # Attention map (#564)
    if args.attention_map:
        flagged_nodes, flagged_edges, gap_data = generate_attention_map(
            all_nodes, all_edges, top_n=args.attention_top
        )

        if not gap_data:
            print("No attention-needed nodes found")
            return 0

        print(
            f"\nAttention map: {len(gap_data)} flagged nodes, {len(flagged_nodes)} total in subgraph"
        )
        for g in gap_data[:10]:
            print(
                f"  {g['label'][:40]:<40} gap={g['gap_score']:.1f}  "
                f"importance={g['importance']:.1f}  connectivity={g['connectivity']}"
            )

        dot_content = generate_attention_dot(flagged_nodes, flagged_edges, gap_data)
        output_base = f"{args.output}-attention"
        generate_svg(dot_content, output_base, args.layout, keep_dot=True)
        return 0

    # Define variants to generate
    # Each variant: (suffix, filter_type, include_orphans, description)
    # filter_type: "smart" = active work focus, "rollup" = pruned tree, None = no filter
    if args.filter:
        # Explicit filter: single output with no suffix
        ft = None if args.filter == "none" else args.filter
        desc = {
            "smart": "smart-filtered (active work)",
            "rollup": "rollup (unfinished + structural ancestors)",
            "reachable": "reachable from active leaves",
            "none": "unfiltered",
        }
        variants = [("", ft, args.include_orphans, desc.get(args.filter, "filtered"))]
    elif args.single:
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
        elif filter_type == "reachable":
            nodes, structural_ids = filter_reachable(nodes, edges)
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
