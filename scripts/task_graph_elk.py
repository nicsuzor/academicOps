#!/usr/bin/env python3
"""Generate styled task graph using ELK (Eclipse Layout Kernel) via elkjs.

Produces force-directed or layered layouts with proper orthogonal edge routing.
Requires: npm install elkjs (in ~ or project root)

Layouts:
  - stress (default): Force-directed stress minimization
  - force: Force-directed (spring-electric model)
  - layered: Hierarchical layered layout (like Graphviz dot)

Edge routing:
  - ORTHOGONAL (default): Manhattan-style right-angle edges
  - POLYLINE: Straight-line segments with bends
  - SPLINES: Bezier curves

Usage:
    python3 task_graph_elk.py INPUT.json [-o OUTPUT] [--layout stress] [--edge-routing ORTHOGONAL]

Examples:
    python3 task_graph_elk.py tasks.json -o task-map --filter reachable
    python3 task_graph_elk.py tasks.json -o task-map --layout stress --edge-routing ORTHOGONAL
    python3 task_graph_elk.py tasks.json -o task-map --layout layered --edge-routing SPLINES
"""

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

# Add scripts dir for task_graph imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from task_graph import (
    ASSIGNEE_COLORS,
    ASSIGNEE_DEFAULT,
    EDGE_STYLES,
    INCOMPLETE_STATUSES,
    PRIORITY_BORDERS,
    STATUS_COLORS,
    STRUCTURAL_STYLE,
    TYPE_SHAPES,
    classify_edge,
    extract_assignee,
    extract_ego_subgraph,
    filter_completed_smart,
    filter_reachable,
    filter_rollup,
    generate_attention_map,
)

# ELK shape to SVG element mapping
ELK_SHAPES = {
    "ellipse": "ellipse",
    "box3d": "rect",
    "octagon": "polygon",
    "box": "rect",
    "note": "rect",
    "diamond": "polygon",
    "hexagon": "polygon",
    "tab": "rect",
    "plaintext": "rect",
    "circle": "ellipse",
    "cds": "polygon",
    "component": "rect",
}


def find_elkjs():
    """Find elkjs installation."""
    candidates = [
        Path.home() / "node_modules" / "elkjs",
        REPO_ROOT / "node_modules" / "elkjs",
        SCRIPT_DIR / "node_modules" / "elkjs",
    ]
    for p in candidates:
        if (p / "lib" / "elk-api.js").exists():
            return p
    return None


def build_elk_graph(
    nodes: list[dict],
    edges: list[dict],
    structural_ids: set[str],
    include_orphans: bool = False,
) -> tuple[dict, dict]:
    """Build ELK JSON graph and a styling metadata dict.

    Returns (elk_graph, style_map) where style_map[node_id] = {fill, stroke, strokeWidth, shape, ...}
    """
    node_by_id = {n["id"]: n for n in nodes}

    # Filter to connected nodes unless include_orphans
    if not include_orphans:
        connected = set()
        for e in edges:
            connected.add(e["source"])
            connected.add(e["target"])
        nodes = [n for n in nodes if n["id"] in connected]
        node_by_id = {n["id"]: n for n in nodes}

    node_ids = set(node_by_id.keys())
    style_map = {}

    elk_children = []
    for node_data in nodes:
        nid = node_data["id"]

        node_type = node_data.get("node_type") or "task"
        status = (node_data.get("status") or "inbox").lower()
        priority = node_data.get("priority", 2)
        if not isinstance(priority, int):
            priority = 2
        file_path = node_data.get("path", "")
        dw = node_data.get("downstream_weight", 0)

        # Label
        label = node_data.get("label", nid)[:50]
        if dw > 0:
            label += f" [{dw:.1f}]"

        # Size: scale with label length and downstream weight
        base_w = max(60, min(len(label) * 7, 200))
        base_h = 30
        scale = 1.0 + min(dw * 0.1, 0.8)
        w = base_w * scale
        h = base_h * scale

        # Shape
        if nid in structural_ids:
            dot_shape = STRUCTURAL_STYLE["shape"]
        else:
            dot_shape = TYPE_SHAPES.get(node_type, "box")

        # Fill color
        if nid in structural_ids:
            fill_hex = STRUCTURAL_STYLE["fillcolor"]
        else:
            fill_hex = STATUS_COLORS.get(status, "#ffffff")

        # Border color
        is_incomplete = status in INCOMPLETE_STATUSES
        if is_incomplete and file_path:
            assignee = extract_assignee(file_path)
            if assignee:
                pen_hex = ASSIGNEE_COLORS.get(assignee, ASSIGNEE_DEFAULT)
                pw = 3.0
            else:
                pen_hex = PRIORITY_BORDERS.get(priority, "#6c757d")
                pw = 3.0 if priority <= 1 else 1.0
        else:
            pen_hex = PRIORITY_BORDERS.get(priority, "#6c757d")
            pw = 3.0 if priority <= 1 else 1.0

        if dw > 0:
            pw = max(pw, min(1 + math.sqrt(dw), 5))

        # Structural nodes get dashed border
        stroke_dash = "8,4" if nid in structural_ids else ""

        style_map[nid] = {
            "fill": fill_hex,
            "stroke": pen_hex,
            "strokeWidth": pw,
            "shape": dot_shape,
            "strokeDash": stroke_dash,
            "label": label,
            "w": w,
            "h": h,
        }

        elk_children.append({
            "id": nid,
            "width": w,
            "height": h,
            "labels": [{"text": label}],
        })

    elk_edges = []
    edge_styles = {}
    for i, edge_data in enumerate(edges):
        src, tgt = edge_data["source"], edge_data["target"]
        if src not in node_ids or tgt not in node_ids:
            continue

        eid = f"e{i}"
        edge_type = edge_data.get("type") or classify_edge(src, tgt, node_by_id)
        style = EDGE_STYLES.get(edge_type, EDGE_STYLES["link"])

        elk_edges.append({
            "id": eid,
            "sources": [src],
            "targets": [tgt],
        })

        edge_styles[eid] = {
            "color": style["color"],
            "width": float(style.get("penwidth", "1")),
            "dash": "4,4" if style.get("style") == "dashed" else
                    "2,2" if style.get("style") == "dotted" else "",
        }

    elk_graph = {
        "id": "root",
        "children": elk_children,
        "edges": elk_edges,
    }

    return elk_graph, style_map, edge_styles


def run_elk_layout(elk_graph: dict, layout_options: dict) -> dict:
    """Run ELK layout via Node.js subprocess."""
    elk_path = find_elkjs()
    if not elk_path:
        print("Error: elkjs not found. Install: npm install elkjs", file=sys.stderr)
        sys.exit(1)

    elk_graph["layoutOptions"] = layout_options

    # Write ELK runner script
    runner_js = f"""
const ELK = require('{elk_path}/lib/elk.bundled.js');
const elk = new ELK();

const graph = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf-8'));

elk.layout(graph)
    .then(result => {{
        process.stdout.write(JSON.stringify(result));
    }})
    .catch(err => {{
        process.stderr.write('ELK error: ' + err.message + '\\n');
        process.exit(1);
    }});
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as jf:
        jf.write(runner_js)
        js_path = jf.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as gf:
        json.dump(elk_graph, gf)
        graph_path = gf.name

    try:
        result = subprocess.run(
            ["node", js_path, graph_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"ELK layout failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        return json.loads(result.stdout)
    finally:
        Path(js_path).unlink(missing_ok=True)
        Path(graph_path).unlink(missing_ok=True)


def render_svg(
    layout: dict,
    style_map: dict,
    edge_styles: dict,
    output_path: str,
):
    """Render ELK layout result to SVG."""
    svg_path = f"{output_path}.svg"

    # Get bounds
    graph_w = layout.get("width", 800)
    graph_h = layout.get("height", 600)
    margin = 20
    vb_w = graph_w + 2 * margin
    vb_h = graph_h + 2 * margin

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                 f'viewBox="0 0 {vb_w:.0f} {vb_h:.0f}" '
                 f'width="{vb_w:.0f}" height="{vb_h:.0f}">')
    lines.append('<style>')
    lines.append('  text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 10px; fill: #333; }')
    lines.append('  .edge-label { font-size: 8px; fill: #666; }')
    lines.append('</style>')
    lines.append(f'<g transform="translate({margin},{margin})">')

    # Draw edges first (behind nodes)
    for edge in layout.get("edges", []):
        eid = edge["id"]
        es = edge_styles.get(eid, {"color": "#adb5bd", "width": 1, "dash": ""})

        sections = edge.get("sections", [])
        for section in sections:
            start = section.get("startPoint", {})
            end = section.get("endPoint", {})
            bends = section.get("bendPoints", [])

            # Build path
            points = [start] + bends + [end]
            d_parts = [f'M {points[0]["x"]:.1f} {points[0]["y"]:.1f}']
            for pt in points[1:]:
                d_parts.append(f'L {pt["x"]:.1f} {pt["y"]:.1f}')

            dash_attr = f' stroke-dasharray="{es["dash"]}"' if es["dash"] else ""
            lines.append(
                f'  <path d="{" ".join(d_parts)}" '
                f'fill="none" stroke="{es["color"]}" '
                f'stroke-width="{es["width"]:.1f}"{dash_attr} />'
            )

            # Arrowhead at end
            if len(points) >= 2:
                p1 = points[-2]
                p2 = points[-1]
                dx = p2["x"] - p1["x"]
                dy = p2["y"] - p1["y"]
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    dx /= length
                    dy /= length
                    arrow_size = 6
                    ax = p2["x"]
                    ay = p2["y"]
                    # Two points for arrowhead
                    lx = ax - arrow_size * dx + arrow_size * 0.4 * dy
                    ly = ay - arrow_size * dy - arrow_size * 0.4 * dx
                    rx = ax - arrow_size * dx - arrow_size * 0.4 * dy
                    ry = ay - arrow_size * dy + arrow_size * 0.4 * dx
                    lines.append(
                        f'  <polygon points="{ax:.1f},{ay:.1f} {lx:.1f},{ly:.1f} {rx:.1f},{ry:.1f}" '
                        f'fill="{es["color"]}" />'
                    )

    # Draw nodes
    for child in layout.get("children", []):
        nid = child["id"]
        x = child.get("x", 0)
        y = child.get("y", 0)
        w = child.get("width", 60)
        h = child.get("height", 30)
        st = style_map.get(nid, {})

        fill = st.get("fill", "#ffffff")
        stroke = st.get("stroke", "#6c757d")
        sw = st.get("strokeWidth", 1)
        dash = st.get("strokeDash", "")
        label = st.get("label", nid)
        shape = st.get("shape", "box")

        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""

        if shape in ("ellipse", "circle"):
            cx = x + w / 2
            cy = y + h / 2
            lines.append(
                f'  <ellipse cx="{cx:.1f}" cy="{cy:.1f}" '
                f'rx="{w/2:.1f}" ry="{h/2:.1f}" '
                f'fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw:.1f}"{dash_attr} />'
            )
        elif shape == "diamond":
            cx = x + w / 2
            cy = y + h / 2
            pts = f"{cx:.1f},{y:.1f} {x+w:.1f},{cy:.1f} {cx:.1f},{y+h:.1f} {x:.1f},{cy:.1f}"
            lines.append(
                f'  <polygon points="{pts}" '
                f'fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw:.1f}"{dash_attr} />'
            )
        elif shape == "hexagon":
            dx = w * 0.15
            pts = (f"{x+dx:.1f},{y:.1f} {x+w-dx:.1f},{y:.1f} {x+w:.1f},{y+h/2:.1f} "
                   f"{x+w-dx:.1f},{y+h:.1f} {x+dx:.1f},{y+h:.1f} {x:.1f},{y+h/2:.1f}")
            lines.append(
                f'  <polygon points="{pts}" '
                f'fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw:.1f}"{dash_attr} />'
            )
        elif shape == "octagon":
            d = min(w, h) * 0.2
            pts = (f"{x+d:.1f},{y:.1f} {x+w-d:.1f},{y:.1f} {x+w:.1f},{y+d:.1f} "
                   f"{x+w:.1f},{y+h-d:.1f} {x+w-d:.1f},{y+h:.1f} {x+d:.1f},{y+h:.1f} "
                   f"{x:.1f},{y+h-d:.1f} {x:.1f},{y+d:.1f}")
            lines.append(
                f'  <polygon points="{pts}" '
                f'fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw:.1f}"{dash_attr} />'
            )
        else:
            # Default: rect with rounded corners
            rx = 3 if shape == "box3d" else 0
            lines.append(
                f'  <rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                f'fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw:.1f}"{dash_attr} />'
            )

        # Label text (centered in node)
        tx = x + w / 2
        ty = y + h / 2
        # Truncate label for display
        display_label = label[:40] + "..." if len(label) > 40 else label
        # Escape XML entities
        display_label = (display_label
                         .replace("&", "&amp;")
                         .replace("<", "&lt;")
                         .replace(">", "&gt;")
                         .replace('"', "&quot;"))
        lines.append(
            f'  <text x="{tx:.1f}" y="{ty:.1f}" '
            f'text-anchor="middle" dominant-baseline="central">'
            f'{display_label}</text>'
        )

    lines.append('</g>')
    lines.append('</svg>')

    with open(svg_path, "w") as f:
        f.write("\n".join(lines))

    print(f"  Written {svg_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate styled task graph using ELK (elkjs)"
    )
    parser.add_argument("input", help="Input JSON file from fast-indexer")
    parser.add_argument("-o", "--output", default="tasks", help="Output base name")
    parser.add_argument("--include-orphans", action="store_true")
    parser.add_argument(
        "--filter",
        choices=["smart", "rollup", "reachable", "none"],
        default="reachable",
        help="Filter type (default: reachable)",
    )
    parser.add_argument(
        "--layout",
        default="stress",
        choices=["stress", "force", "layered"],
        help="ELK layout algorithm (default: stress)",
    )
    parser.add_argument(
        "--edge-routing",
        default="ORTHOGONAL",
        choices=["ORTHOGONAL", "POLYLINE", "SPLINES", "UNDEFINED"],
        help="Edge routing strategy (default: ORTHOGONAL)",
    )
    parser.add_argument(
        "--spacing",
        type=float,
        default=20.0,
        help="Node-to-node spacing (default: 20)",
    )
    parser.add_argument("--ego", metavar="ID", help="Ego-subgraph center node")
    parser.add_argument("--depth", type=int, default=2, help="Ego depth (default: 2)")
    parser.add_argument("--attention-map", action="store_true")
    parser.add_argument("--attention-top", type=int, default=20)

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        return 1

    with open(input_path) as f:
        data = json.load(f)

    all_nodes = [n for n in data["nodes"] if n.get("status", "").lower() != "cancelled"]
    node_ids = {n["id"] for n in all_nodes}
    all_edges = [e for e in data["edges"] if e["source"] in node_ids and e["target"] in node_ids]
    print(f"Loaded {len(all_nodes)} nodes, {len(all_edges)} edges from {input_path}")

    # Ego subgraph
    if args.ego:
        all_nodes, all_edges = extract_ego_subgraph(all_nodes, all_edges, args.ego, args.depth)
        if not all_nodes:
            return 1
        print(f"Ego subgraph: {len(all_nodes)} nodes (center={args.ego}, depth={args.depth})")

    # Attention map
    if args.attention_map:
        flagged_nodes, flagged_edges, gap_data = generate_attention_map(
            all_nodes, all_edges, top_n=args.attention_top
        )
        if not gap_data:
            print("No attention-needed nodes found")
            return 0
        print(f"Attention map: {len(gap_data)} flagged, {len(flagged_nodes)} total")
        all_nodes, all_edges = flagged_nodes, flagged_edges

    # Apply filter
    structural_ids: set[str] = set()
    original = len(all_nodes)
    if args.filter == "smart":
        all_nodes, structural_ids = filter_completed_smart(all_nodes, all_edges)
    elif args.filter == "rollup":
        all_nodes, structural_ids = filter_rollup(all_nodes, all_edges)
    elif args.filter == "reachable":
        all_nodes, structural_ids = filter_reachable(all_nodes, all_edges)

    excluded = original - len(all_nodes)
    if excluded or structural_ids:
        print(f"  Filtered: {excluded} removed, {len(structural_ids)} structural kept")

    # Build ELK graph
    elk_graph, style_map, edge_styles = build_elk_graph(
        all_nodes, all_edges, structural_ids, args.include_orphans
    )

    num_nodes = len(elk_graph["children"])
    num_edges = len(elk_graph["edges"])
    print(f"  Graph: {num_nodes} nodes, {num_edges} edges")

    if num_nodes == 0:
        print("No nodes to render")
        return 0

    # ELK layout options
    layout_options = {
        "elk.algorithm": args.layout,
        "elk.edgeRouting": args.edge_routing,
        "elk.spacing.nodeNode": str(args.spacing),
    }

    # Algorithm-specific options
    if args.layout == "stress":
        layout_options["elk.stress.desiredEdgeLength"] = "80"
    elif args.layout == "force":
        layout_options["elk.force.temperature"] = "0.001"
        layout_options["elk.force.iterations"] = "300"
    elif args.layout == "layered":
        layout_options["elk.layered.spacing.nodeNodeBetweenLayers"] = "30"
        layout_options["elk.direction"] = "DOWN"

    print(f"  Layout: ELK {args.layout} + {args.edge_routing} ({num_nodes} nodes)")

    # Run ELK
    result = run_elk_layout(elk_graph, layout_options)

    # Render SVG
    render_svg(result, style_map, edge_styles, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
