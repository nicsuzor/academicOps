#!/usr/bin/env python3
"""Generate task visualization from bd issues with force-directed layout.

Queries bd for issues, computes layout using networkx,
and outputs a valid excalidraw JSON file.

Usage:
    python task_viz_bd.py output.excalidraw [--include-closed] [--prefix PREFIX]

Examples:
    python task_viz_bd.py tasks.excalidraw
    python task_viz_bd.py tasks.excalidraw --include-closed
    python task_viz_bd.py tasks.excalidraw --prefix ns-
"""

import argparse
import json
import subprocess
import sys
import time
from typing import Any

import networkx as nx

# Priority colors (P0-P3)
PRIORITY_COLORS = {
    0: {"bg": "#f8d7da", "stroke": "#721c24"},  # P0 - red (critical)
    1: {"bg": "#ffe5d0", "stroke": "#fd7e14"},  # P1 - orange (high)
    2: {"bg": "#fff3cd", "stroke": "#856404"},  # P2 - yellow (medium)
    3: {"bg": "#e9ecef", "stroke": "#6c757d"},  # P3 - gray (low)
}

# Issue type colors
TYPE_COLORS = {
    "epic": {"bg": "#d4edda", "stroke": "#28a745"},  # green
    "task": {"bg": "#cce5ff", "stroke": "#004085"},  # blue
    "bug": {"bg": "#f8d7da", "stroke": "#721c24"},  # red
    "molecule": {"bg": "#e2d5f1", "stroke": "#6f42c1"},  # purple
}

# Status styling
STATUS_OPACITY = {
    "open": 100,
    "in_progress": 100,
    "blocked": 60,
    "closed": 40,
}


def query_bd_issues(include_closed: bool = False, prefix: str | None = None) -> list[dict]:
    """Query bd for issues."""
    cmd = ["bd", "list", "--json", "--limit", "0"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        issues = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running bd: {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing bd JSON: {e}", file=sys.stderr)
        return []

    # Filter out closed issues unless requested
    if not include_closed:
        issues = [i for i in issues if i.get("status") != "closed"]

    # Filter by prefix if specified
    if prefix:
        issues = [i for i in issues if i["id"].startswith(prefix)]

    return issues


def get_issue_details(issue_id: str) -> dict | None:
    """Get detailed info for a single issue (includes parent)."""
    cmd = ["bd", "show", issue_id, "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        issues = json.loads(result.stdout)
        return issues[0] if issues else None
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def discover_issues_with_parents(
    include_closed: bool = False, prefix: str | None = None
) -> list[dict[str, Any]]:
    """Get all issues with parent information."""
    issues = query_bd_issues(include_closed, prefix)

    # Get parent info for each issue
    enriched = []
    for issue in issues:
        # Get detailed info to find parent
        details = get_issue_details(issue["id"])
        parent = details.get("parent") if details else None

        enriched.append({
            "id": issue["id"],
            "title": issue["title"][:60],  # Truncate long titles
            "priority": issue.get("priority", 2),
            "status": issue.get("status", "open"),
            "issue_type": issue.get("issue_type", "task"),
            "labels": issue.get("labels", []),
            "parent": parent,
        })

    return enriched


def build_graph(issues: list[dict]) -> nx.DiGraph:
    """Build directed graph from issues."""
    G = nx.DiGraph()

    # Create nodes
    for issue in issues:
        G.add_node(
            issue["id"],
            title=issue["title"],
            priority=issue["priority"],
            status=issue["status"],
            issue_type=issue["issue_type"],
            labels=issue["labels"],
        )

    # Create edges (child -> parent)
    issue_ids = {i["id"] for i in issues}
    for issue in issues:
        if issue["parent"] and issue["parent"] in issue_ids:
            G.add_edge(issue["id"], issue["parent"], weight=5.0)

    return G


def compute_layout(G: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Compute force-directed layout."""
    if len(G.nodes()) == 0:
        return {}

    # Use spring layout with parameters tuned for task hierarchies
    pos = nx.spring_layout(
        G.to_undirected(),  # Spring layout works on undirected
        k=2.0,  # Ideal distance between nodes
        iterations=300,
        scale=3500,
        seed=42,
        weight="weight",
    )

    # Normalize to positive coords with margin
    if pos:
        min_x = min(p[0] for p in pos.values())
        min_y = min(p[1] for p in pos.values())
        pos = {n: (x - min_x + 150, y - min_y + 150) for n, (x, y) in pos.items()}

    return pos


def node_size(issue_type: str, title: str) -> tuple[int, int, int]:
    """Get node dimensions and font size based on type."""
    if issue_type == "epic":
        font = 28
        min_w, h = 280, 80
    elif issue_type == "molecule":
        font = 20
        min_w, h = 200, 60
    else:  # task, bug
        font = 14
        min_w, h = 160, 45

    # Width based on text length
    text_w = len(title) * font * 0.5
    return max(min_w, int(text_w) + 40), h, font


def get_colors(issue: dict) -> tuple[str, str]:
    """Get background and stroke colors for an issue."""
    # Epics use type color, others use priority color
    if issue["issue_type"] in ("epic", "molecule"):
        colors = TYPE_COLORS.get(issue["issue_type"], TYPE_COLORS["task"])
    else:
        colors = PRIORITY_COLORS.get(issue["priority"], PRIORITY_COLORS[2])
    return colors["bg"], colors["stroke"]


def make_excalidraw_element(
    elem_id: str,
    issue_type: str,
    x: float,
    y: float,
    width: int,
    height: int,
    bg_color: str,
    stroke_color: str,
    opacity: int,
) -> dict:
    """Create excalidraw rectangle/ellipse element."""
    seed = hash(elem_id) % 2000000000
    return {
        "id": elem_id,
        "type": "ellipse" if issue_type == "epic" else "rectangle",
        "x": int(x),
        "y": int(y),
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": stroke_color,
        "backgroundColor": bg_color,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": opacity,
        "groupIds": [],
        "roundness": {"type": 3} if issue_type != "epic" else {"type": 2},
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": [{"id": f"text-{elem_id}", "type": "text"}],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }


def make_text_element(
    container_id: str,
    text: str,
    x: float,
    y: float,
    width: int,
    height: int,
    font_size: int,
) -> dict:
    """Create text element bound to container."""
    seed = hash(f"text-{container_id}") % 2000000000
    return {
        "id": f"text-{container_id}",
        "type": "text",
        "x": int(x) + 10,
        "y": int(y) + height // 2 - font_size // 2,
        "width": width - 20,
        "height": font_size + 10,
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
        "text": text,
        "fontSize": font_size,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "baseline": font_size,
        "containerId": container_id,
        "originalText": text,
        "lineHeight": 1.25,
        "autoResize": True,
    }


def make_arrow(
    source_id: str,
    target_id: str,
    positions: dict,
    sizes: dict,
) -> dict:
    """Create arrow from child to parent."""
    sx, sy = positions[source_id]
    tx, ty = positions[target_id]
    sw, sh = sizes[source_id][:2]
    tw, th = sizes[target_id][:2]

    seed = hash(f"arrow-{source_id}-{target_id}") % 2000000000

    return {
        "id": f"arrow-{source_id}-{target_id}",
        "type": "arrow",
        "x": int(sx + sw / 2),
        "y": int(sy + sh / 2),
        "width": int(tx - sx),
        "height": int(ty - sy),
        "angle": 0,
        "strokeColor": "#868e96",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 60,
        "groupIds": [],
        "roundness": {"type": 2},
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
        "points": [[0, 0], [int(tx - sx), int(ty - sy)]],
        "lastCommittedPoint": None,
        "startBinding": {"elementId": source_id, "focus": 0, "gap": 5},
        "endBinding": {"elementId": target_id, "focus": 0, "gap": 5},
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }


def make_legend(x: int, y: int) -> list[dict]:
    """Create a legend explaining colors."""
    elements = []
    legend_items = [
        ("P0 Critical", PRIORITY_COLORS[0]),
        ("P1 High", PRIORITY_COLORS[1]),
        ("P2 Medium", PRIORITY_COLORS[2]),
        ("P3 Low", PRIORITY_COLORS[3]),
        ("Epic", TYPE_COLORS["epic"]),
    ]

    for i, (label, colors) in enumerate(legend_items):
        item_y = y + i * 35
        box_id = f"legend-box-{i}"

        # Small color box
        elements.append({
            "id": box_id,
            "type": "rectangle",
            "x": x,
            "y": item_y,
            "width": 20,
            "height": 20,
            "strokeColor": colors["stroke"],
            "backgroundColor": colors["bg"],
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "angle": 0,
            "groupIds": [],
            "roundness": {"type": 3},
            "seed": hash(box_id) % 2000000000,
            "version": 1,
            "versionNonce": hash(box_id) % 2000000000,
            "isDeleted": False,
            "boundElements": None,
            "updated": int(time.time() * 1000),
            "link": None,
            "locked": False,
        })

        # Label text
        elements.append({
            "id": f"legend-text-{i}",
            "type": "text",
            "x": x + 30,
            "y": item_y + 2,
            "width": 100,
            "height": 20,
            "text": label,
            "fontSize": 14,
            "fontFamily": 1,
            "textAlign": "left",
            "verticalAlign": "top",
            "strokeColor": "#1e1e1e",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "angle": 0,
            "groupIds": [],
            "roundness": None,
            "seed": hash(f"legend-text-{i}") % 2000000000,
            "version": 1,
            "versionNonce": hash(f"legend-text-{i}") % 2000000000,
            "isDeleted": False,
            "boundElements": None,
            "updated": int(time.time() * 1000),
            "link": None,
            "locked": False,
            "containerId": None,
            "originalText": label,
            "lineHeight": 1.25,
            "baseline": 12,
        })

    return elements


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate task visualization from bd issues"
    )
    parser.add_argument("output", help="Output excalidraw file path")
    parser.add_argument(
        "--include-closed",
        action="store_true",
        help="Include closed issues (excluded by default)",
    )
    parser.add_argument(
        "--prefix",
        help="Filter issues by ID prefix (e.g., 'ns-', 'aops-')",
    )
    args = parser.parse_args()

    # Discover issues
    print("Querying bd issues...")
    issues = discover_issues_with_parents(args.include_closed, args.prefix)
    print(f"  Found {len(issues)} issues")

    if not issues:
        print("No issues found. Nothing to visualize.")
        return 1

    # Count by type
    type_counts = {}
    for i in issues:
        t = i["issue_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  Types: {type_counts}")

    # Count parent relationships
    parent_count = sum(1 for i in issues if i["parent"])
    print(f"  Parent relationships: {parent_count}")

    # Build and layout graph
    print("Computing layout...")
    G = build_graph(issues)
    positions = compute_layout(G)

    # Generate excalidraw elements
    print("Generating excalidraw...")
    elements = []
    sizes = {}

    # Create issue lookup
    issue_lookup = {i["id"]: i for i in issues}

    # Add nodes and text
    for node_id in G.nodes():
        issue = issue_lookup[node_id]
        x, y = positions.get(node_id, (0, 0))
        w, h, font = node_size(issue["issue_type"], issue["title"])
        sizes[node_id] = (w, h, font)

        bg_color, stroke_color = get_colors(issue)
        opacity = STATUS_OPACITY.get(issue["status"], 100)

        # Collect arrow bindings
        arrow_bindings = []
        for source, target in G.edges():
            if source == node_id or target == node_id:
                arrow_bindings.append({
                    "id": f"arrow-{source}-{target}",
                    "type": "arrow",
                })

        # Create box
        box = make_excalidraw_element(
            node_id, issue["issue_type"], x, y, w, h, bg_color, stroke_color, opacity
        )
        box["boundElements"] = [{"id": f"text-{node_id}", "type": "text"}] + arrow_bindings
        elements.append(box)

        # Create text
        elements.append(make_text_element(node_id, issue["title"], x, y, w, h, font))

    # Add arrows
    for source, target in G.edges():
        if source in positions and target in positions:
            elements.append(make_arrow(source, target, positions, sizes))

    # Add timestamp
    max_x = max(p[0] for p in positions.values()) if positions else 1000
    ts_text = f"Generated: {time.strftime('%Y-%m-%d @ %H:%M')}"
    elements.append({
        "id": "timestamp",
        "type": "text",
        "x": int(max_x) + 200,
        "y": 50,
        "width": 250,
        "height": 30,
        "text": ts_text,
        "fontSize": 16,
        "fontFamily": 1,
        "textAlign": "right",
        "verticalAlign": "top",
        "strokeColor": "#868e96",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "groupIds": [],
        "roundness": None,
        "seed": 12345,
        "version": 1,
        "versionNonce": 12345,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
        "containerId": None,
        "originalText": ts_text,
        "lineHeight": 1.25,
        "baseline": 14,
    })

    # Add legend
    elements.extend(make_legend(int(max_x) + 200, 100))

    # Build final document
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "gridSize": 20,
            "gridStep": 5,
            "gridModeEnabled": False,
            "viewBackgroundColor": "#ffffff",
        },
        "files": {},
    }

    # Write output
    with open(args.output, "w") as f:
        json.dump(doc, f, indent=2)

    print(f"  Written to {args.output}")
    print(f"  {len(elements)} elements, canvas ~{int(max_x)}px wide")

    return 0


if __name__ == "__main__":
    sys.exit(main())
