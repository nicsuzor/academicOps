#!/usr/bin/env python3
"""Generate styled task graph using graph-tool + Cairo/Graphviz rendering.

Produces denser, better-routed graphs than the DOT-only task_graph.py.
Uses graph-tool's sfdp_layout for node positioning and either:
  - graphviz_draw(splines=True) for SVG with bezier edge routing (default)
  - graph_draw() for Cairo-rendered PDF/PNG (--cairo flag)

Requires: brew install graph-tool  (uses python@3.14)

Usage:
    /opt/homebrew/opt/python@3.14/bin/python3.14 task_graph_gt.py INPUT.json [-o OUTPUT]

Examples:
    python3.14 task_graph_gt.py tasks.json -o task-map --filter reachable
    python3.14 task_graph_gt.py tasks.json -o task-map --cairo  # PDF output
    python3.14 task_graph_gt.py tasks.json --ego mynode --depth 3
"""

import argparse
import json
import math
import sys
from pathlib import Path

# Add graph-tool site-packages from brew
_GT_SP = Path("/opt/homebrew/opt/graph-tool/libexec/lib/python3.14/site-packages")
if _GT_SP.exists():
    sys.path.insert(0, str(_GT_SP))

try:
    from graph_tool import Graph
    from graph_tool.draw import (
        graph_draw,
        graphviz_draw,
        sfdp_layout,
    )
except ImportError:
    print(
        "Error: graph-tool not available.\n"
        "Install: brew install graph-tool\n"
        "Run with: /opt/homebrew/opt/python@3.14/bin/python3.14",
        file=sys.stderr,
    )
    sys.exit(1)

# Add aops-core to path for imports from existing task_graph
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

# graph-tool shape mapping (DOT shapes -> graph-tool Cairo shapes)
GT_SHAPE_MAP = {
    "ellipse": "circle",
    "box3d": "double_square",
    "octagon": "octagon",
    "box": "square",
    "note": "pentagon",
    "diamond": "triangle",
    "hexagon": "hexagon",
    "tab": "heptagon",
    "plaintext": "none",
    "circle": "circle",
    "cds": "octagon",
    "component": "heptagon",
}

# Edge dash patterns for Cairo rendering
EDGE_DASH = {
    "parent": [],  # solid
    "depends_on": [],  # solid (bold)
    "soft_depends_on": [6.0, 3.0],  # dashed
    "link": [2.0, 2.0],  # dotted
    "wikilink": [2.0, 2.0],  # dotted
}


def hex_to_rgba(hex_str: str, alpha: float = 1.0) -> list[float]:
    """Convert hex color to RGBA list [0..1]."""
    h = hex_str.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return [r, g, b, alpha]


def build_graph(
    nodes: list[dict],
    edges: list[dict],
    structural_ids: set[str],
    include_orphans: bool = False,
) -> tuple:
    """Build graph-tool Graph with visual property maps.

    Returns (graph, props_dict, node_count) where props_dict contains
    all vertex/edge property maps needed for rendering.
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

    g = Graph(directed=True)

    # Vertex property maps
    v_label = g.new_vertex_property("string")
    v_shape = g.new_vertex_property("string")
    v_fill = g.new_vertex_property("vector<double>")
    v_border = g.new_vertex_property("vector<double>")
    v_pen_width = g.new_vertex_property("double")
    v_size = g.new_vertex_property("double")
    v_font_size = g.new_vertex_property("double")
    v_halo = g.new_vertex_property("bool")
    v_halo_color = g.new_vertex_property("vector<double>")
    v_halo_size = g.new_vertex_property("double")
    v_text_color = g.new_vertex_property("vector<double>")

    # Edge property maps
    e_color = g.new_edge_property("vector<double>")
    e_pen_width = g.new_edge_property("double")
    e_dash = g.new_edge_property("vector<double>")
    e_marker = g.new_edge_property("string")

    # For graphviz_draw: string-based DOT attribute props
    v_dot_shape = g.new_vertex_property("string")
    v_dot_fillcolor = g.new_vertex_property("string")
    v_dot_color = g.new_vertex_property("string")
    v_dot_style = g.new_vertex_property("string")
    v_dot_penwidth = g.new_vertex_property("string")
    v_dot_fontsize = g.new_vertex_property("string")
    v_dot_peripheries = g.new_vertex_property("string")
    e_dot_color = g.new_edge_property("string")
    e_dot_style = g.new_edge_property("string")
    e_dot_penwidth = g.new_edge_property("string")

    # Build vertices
    id_to_vertex: dict[str, int] = {}
    for node in nodes:
        v = g.add_vertex()
        nid = node["id"]
        id_to_vertex[nid] = int(v)

        node_type = node.get("node_type") or "task"
        status = (node.get("status") or "inbox").lower()
        priority = node.get("priority", 2)
        if not isinstance(priority, int):
            priority = 2
        file_path = node.get("path", "")
        dw = node.get("downstream_weight", 0)
        stakeholder = node.get("stakeholder_exposure", False)

        # Label
        label = node.get("label", nid)[:50]
        if dw > 0:
            label += f"\n\u2696 {dw:.1f}"
        v_label[v] = label

        # Shape
        if nid in structural_ids:
            dot_shape = STRUCTURAL_STYLE["shape"]
            gt_shape = GT_SHAPE_MAP.get(dot_shape, "square")
        else:
            dot_shape = TYPE_SHAPES.get(node_type, "box")
            gt_shape = GT_SHAPE_MAP.get(dot_shape, "square")

        if stakeholder:
            # Double border for stakeholder exposure
            if gt_shape in (
                "square",
                "circle",
                "hexagon",
                "octagon",
                "pentagon",
                "triangle",
                "heptagon",
            ):
                gt_shape = f"double_{gt_shape}"
            v_dot_peripheries[v] = "2"
        else:
            v_dot_peripheries[v] = "1"

        v_shape[v] = gt_shape
        v_dot_shape[v] = dot_shape

        # Fill color
        if nid in structural_ids:
            fill_hex = STRUCTURAL_STYLE["fillcolor"]
            style_str = STRUCTURAL_STYLE["style"]
        else:
            fill_hex = STATUS_COLORS.get(status, "#ffffff")
            style_str = "filled"

        v_fill[v] = hex_to_rgba(fill_hex)
        v_dot_fillcolor[v] = fill_hex
        v_dot_style[v] = style_str

        # Border color (assignee or priority)
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

        # Downstream weight thickens border
        if dw > 0:
            pw = max(pw, min(1 + math.sqrt(dw), 5))

        v_border[v] = hex_to_rgba(pen_hex)
        v_pen_width[v] = pw
        v_dot_color[v] = pen_hex
        v_dot_penwidth[v] = str(pw)

        # Size: compact nodes for dense layout
        base_size = 12.0
        v_size[v] = base_size + min(dw * 2, 12)

        # Font size: small for density
        if dw >= 6.0:
            v_font_size[v] = 8.0
        elif dw >= 3.0:
            v_font_size[v] = 7.0
        else:
            v_font_size[v] = 6.0

        v_dot_fontsize[v] = str(v_font_size[v])

        # Text color
        v_text_color[v] = [0.15, 0.15, 0.15, 1.0]

        # Halo for high-priority or blocked items
        if status == "blocked" or priority == 0:
            v_halo[v] = True
            v_halo_color[v] = hex_to_rgba("#dc3545", 0.25)
            v_halo_size[v] = 1.4
        else:
            v_halo[v] = False
            v_halo_color[v] = [0, 0, 0, 0]
            v_halo_size[v] = 1.0

    # Build edges
    node_ids = set(id_to_vertex.keys())
    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src not in node_ids or tgt not in node_ids:
            continue

        e = g.add_edge(id_to_vertex[src], id_to_vertex[tgt])

        edge_type = edge.get("type") or classify_edge(src, tgt, node_by_id)
        style = EDGE_STYLES.get(edge_type, EDGE_STYLES["link"])

        e_color[e] = hex_to_rgba(style["color"], 0.85)
        e_pen_width[e] = float(style.get("penwidth", "1"))
        e_dash[e] = EDGE_DASH.get(edge_type, [])
        e_marker[e] = "arrow" if edge_type in ("parent", "depends_on") else "none"

        e_dot_color[e] = style["color"]
        e_dot_style[e] = style["style"]
        e_dot_penwidth[e] = style.get("penwidth", "1")

    props = {
        # Cairo props
        "v_label": v_label,
        "v_shape": v_shape,
        "v_fill": v_fill,
        "v_border": v_border,
        "v_pen_width": v_pen_width,
        "v_size": v_size,
        "v_font_size": v_font_size,
        "v_halo": v_halo,
        "v_halo_color": v_halo_color,
        "v_halo_size": v_halo_size,
        "v_text_color": v_text_color,
        "e_color": e_color,
        "e_pen_width": e_pen_width,
        "e_dash": e_dash,
        "e_marker": e_marker,
        # DOT props (for graphviz_draw)
        "v_dot_shape": v_dot_shape,
        "v_dot_fillcolor": v_dot_fillcolor,
        "v_dot_color": v_dot_color,
        "v_dot_style": v_dot_style,
        "v_dot_penwidth": v_dot_penwidth,
        "v_dot_fontsize": v_dot_fontsize,
        "v_dot_peripheries": v_dot_peripheries,
        "e_dot_color": e_dot_color,
        "e_dot_style": e_dot_style,
        "e_dot_penwidth": e_dot_penwidth,
    }

    return g, props, len(nodes)


def compute_layout(
    g: Graph,
    num_nodes: int,
    layout_hint: str = "sfdp",
    dense: bool = True,
    K_override: float | None = None,
    C_override: float | None = None,
):
    """Compute node positions using graph-tool layout algorithms.

    Args:
        dense: If True, use tighter spacing for dense, compact graphs.
        K_override: Override optimal edge length for sfdp.
        C_override: Override repulsive force for sfdp.
    """
    if num_nodes == 0:
        return g.new_vertex_property("vector<double>")

    if layout_hint == "fr" or (layout_hint == "auto" and num_nodes < 150):
        from graph_tool.draw import fruchterman_reingold_layout

        print(f"  Layout: fruchterman_reingold ({num_nodes} nodes)")
        return fruchterman_reingold_layout(g, n_iter=500)

    if layout_hint == "radial":
        from graph_tool.draw import radial_tree_layout

        print(f"  Layout: radial_tree ({num_nodes} nodes)")
        return radial_tree_layout(g, g.vertex(0))

    # sfdp: K controls optimal edge length (smaller = denser)
    # C controls repulsive force (smaller = nodes pack tighter)
    if dense:
        K, C = 0.3, 0.1  # very tight packing
    else:
        K, C = 2.0, 0.4

    if K_override is not None:
        K = K_override
    if C_override is not None:
        C = C_override

    print(f"  Layout: sfdp multilevel ({num_nodes} nodes, K={K}, C={C})")
    return sfdp_layout(
        g,
        K=K,
        C=C,
        p=2.0,
        theta=0.4,
        max_iter=1000,
        multilevel=True,
        coarse_method="hybrid",
    )


def render_graphviz(
    g,
    pos,
    props,
    output_path: str,
    layout_engine: str = "sfdp",
    splines_mode: str = "true",
    sep: str = "+2",
    overlap: str = "true",
):
    """Render with graphviz_draw: graph-tool positions + Graphviz spline routing.

    Uses pinned positions from sfdp_layout with Graphviz's spline edge router
    for bezier curves that route tightly around nodes.
    """
    svg_path = f"{output_path}.svg"
    print(
        f"  Rendering: graphviz_draw -> {svg_path} (splines={splines_mode}, sep={sep}, overlap={overlap})"
    )

    # Scale canvas based on node count - larger for more nodes
    n = g.num_vertices()
    dim = max(40, min(int(math.sqrt(n) * 4), 100))

    # graphviz_draw only accepts splines=True/False natively.
    # Non-standard modes (ortho, curved, polyline) must go through gprops.
    use_splines_param = splines_mode in ("true", "false")
    splines_bool = splines_mode == "true" if use_splines_param else False

    gprops = {
        "outputorder": "edgesfirst",  # draw edges behind nodes
        "concentrate": "false",  # don't merge edges
    }
    if not use_splines_param:
        gprops["splines"] = splines_mode

    graphviz_draw(
        g,
        pos=pos,
        size=(dim, dim),
        layout=layout_engine,
        pin=True,
        splines=splines_bool,
        overlap=overlap,
        sep=sep,
        vprops={
            "shape": props["v_dot_shape"],
            "style": props["v_dot_style"],
            "fillcolor": props["v_dot_fillcolor"],
            "color": props["v_dot_color"],
            "penwidth": props["v_dot_penwidth"],
            "fontsize": props["v_dot_fontsize"],
            "peripheries": props["v_dot_peripheries"],
            "label": props["v_label"],
        },
        eprops={
            "color": props["e_dot_color"],
            "style": props["e_dot_style"],
            "penwidth": props["e_dot_penwidth"],
        },
        gprops=gprops,
        output=svg_path,
        fork=False,
    )
    print(f"  Written {svg_path}")


def render_cairo(g, pos, props, output_path: str, fmt: str = "svg"):
    """Render with graph_draw: pure Cairo output - dense, anti-aliased."""
    out_file = f"{output_path}.{fmt}"
    print(f"  Rendering: Cairo graph_draw -> {out_file}")

    n = g.num_vertices()
    # High-res canvas for dense graphs
    dim = max(3000, min(int(math.sqrt(n) * 250), 8000))

    # Make edges semi-transparent so overlapping edges create depth
    e_color_alpha = g.new_edge_property("vector<double>")
    for e in g.edges():
        c = list(props["e_color"][e])
        c[3] = 0.4  # semi-transparent edges
        e_color_alpha[e] = c

    graph_draw(
        g,
        pos=pos,
        output_size=(dim, dim),
        output=out_file,
        fmt=fmt,
        vertex_shape=props["v_shape"],
        vertex_fill_color=props["v_fill"],
        vertex_color=props["v_border"],
        vertex_pen_width=props["v_pen_width"],
        vertex_size=props["v_size"],
        vertex_text=props["v_label"],
        vertex_font_size=props["v_font_size"],
        vertex_text_color=props["v_text_color"],
        vertex_halo=props["v_halo"],
        vertex_halo_color=props["v_halo_color"],
        vertex_halo_size=props["v_halo_size"],
        vertex_text_position=0,  # center text
        edge_color=e_color_alpha,
        edge_pen_width=props["e_pen_width"],
        edge_dash_style=props["e_dash"],
        edge_marker_size=6,
        bg_color=[1, 1, 1, 1],
        fit_view=0.95,
        adjust_aspect=False,
    )
    print(f"  Written {out_file}")


def render_manhattan(g, pos, props, output_path: str):
    """Render with sfdp positions and Manhattan (orthogonal) edge routing.

    Uses L-shaped or Z-shaped paths so edges follow axis-aligned segments,
    routing around node bounding boxes.
    """
    svg_path = f"{output_path}.svg"
    print(f"  Rendering: Manhattan edge routing -> {svg_path}")

    n = g.num_vertices()

    # Extract positions and compute bounds
    # node_data = []  # [(x, y, w, h, fill_hex, stroke_hex, stroke_width, stroke_dash, shape, label)]
    xs, ys = [], []
    for v in g.vertices():
        x, y = pos[v]
        xs.append(x)
        ys.append(y)

    if not xs:
        print("  No nodes to render")
        return

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x or 1
    span_y = max_y - min_y or 1

    # Scale to a reasonable canvas size
    canvas_w = max(2000, min(int(math.sqrt(n) * 250), 8000))
    canvas_h = int(canvas_w * span_y / span_x) if span_x > 0 else canvas_w
    margin = 80

    def scale_x(x):
        return margin + (x - min_x) / span_x * (canvas_w - 2 * margin)

    def scale_y(y):
        return margin + (y - min_y) / span_y * (canvas_h - 2 * margin)

    # Build node rectangles for collision detection
    node_rects = {}  # vertex_index -> (cx, cy, w, h)
    for v in g.vertices():
        vi = int(v)
        x, y = pos[v]
        cx, cy = scale_x(x), scale_y(y)
        label = props["v_label"][v]
        # Width based on label length, height fixed
        w = max(40, min(len(label.split("\n")[0]) * 6.5 + 12, 180))
        h = 24 + 12 * (label.count("\n"))
        node_rects[vi] = (cx, cy, w, h)

    def rect_contains(rect, px, py, pad=2):
        """Check if point is inside a rectangle (with padding)."""
        cx, cy, w, h = rect
        return (
            cx - w / 2 - pad <= px <= cx + w / 2 + pad
            and cy - h / 2 - pad <= py <= cy + h / 2 + pad
        )

    def manhattan_route(src_rect, tgt_rect):
        """Route an edge from src to tgt using orthogonal segments.

        Returns a list of (x, y) points forming the path.
        Uses an L-shape (one bend) or Z-shape (two bends) depending on
        relative position.
        """
        sx, sy, sw, sh = src_rect
        tx, ty, tw, th = tgt_rect

        # Determine exit/entry sides based on relative position
        dx = tx - sx
        dy = ty - sy

        # Clearance around nodes
        pad = 6

        if abs(dx) > abs(dy):
            # Primarily horizontal relationship
            if dx > 0:
                # Source is left of target
                start_x = sx + sw / 2 + pad
                end_x = tx - tw / 2 - pad
            else:
                start_x = sx - sw / 2 - pad
                end_x = tx + tw / 2 + pad
            start_y = sy
            end_y = ty

            if abs(dy) < sh / 2 + th / 2 + pad:
                # Close vertically - use Z-shape with horizontal offset
                mid_x = (start_x + end_x) / 2
                return [(start_x, start_y), (mid_x, start_y), (mid_x, end_y), (end_x, end_y)]
            else:
                # L-shape
                return [(start_x, start_y), (end_x, start_y), (end_x, end_y)]
        else:
            # Primarily vertical relationship
            if dy > 0:
                start_y = sy + sh / 2 + pad
                end_y = ty - th / 2 - pad
            else:
                start_y = sy - sh / 2 - pad
                end_y = ty + th / 2 + pad
            start_x = sx
            end_x = tx

            if abs(dx) < sw / 2 + tw / 2 + pad:
                # Close horizontally - use Z-shape with vertical offset
                mid_y = (start_y + end_y) / 2
                return [(start_x, start_y), (start_x, mid_y), (end_x, mid_y), (end_x, end_y)]
            else:
                # L-shape
                return [(start_x, start_y), (start_x, end_y), (end_x, end_y)]

    # Build SVG
    lines = []
    vb_w = canvas_w + 2 * margin
    vb_h = canvas_h + 2 * margin
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {vb_w:.0f} {vb_h:.0f}" '
        f'width="{vb_w:.0f}" height="{vb_h:.0f}">'
    )
    lines.append("<style>")
    lines.append(
        '  text { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 9px; fill: #333; }'
    )
    lines.append("</style>")

    # Edges
    for e in g.edges():
        si, ti = int(e.source()), int(e.target())
        if si not in node_rects or ti not in node_rects:
            continue

        src_r = node_rects[si]
        tgt_r = node_rects[ti]
        points = manhattan_route(src_r, tgt_r)

        # Edge color (from RGBA to hex)
        ec = props["e_color"][e]
        r, g_c, b = int(ec[0] * 255), int(ec[1] * 255), int(ec[2] * 255)
        alpha = ec[3] if len(ec) > 3 else 0.6
        color = f"rgb({r},{g_c},{b})"
        pw = props["e_pen_width"][e]

        # Dash
        dash_vals = list(props["e_dash"][e])
        dash_attr = (
            f' stroke-dasharray="{",".join(str(int(d)) for d in dash_vals)}"' if dash_vals else ""
        )

        # Path
        d = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
        for pt in points[1:]:
            d += f" L {pt[0]:.1f} {pt[1]:.1f}"

        lines.append(
            f'  <path d="{d}" fill="none" stroke="{color}" '
            f'stroke-width="{pw:.1f}" opacity="{alpha:.2f}"{dash_attr} />'
        )

        # Arrowhead
        if len(points) >= 2:
            p1, p2 = points[-2], points[-1]
            ddx = p2[0] - p1[0]
            ddy = p2[1] - p1[1]
            length = math.sqrt(ddx * ddx + ddy * ddy)
            if length > 0:
                ddx /= length
                ddy /= length
                a = 5
                ax, ay = p2
                lx = ax - a * ddx + a * 0.35 * ddy
                ly = ay - a * ddy - a * 0.35 * ddx
                rx = ax - a * ddx - a * 0.35 * ddy
                ry = ay - a * ddy + a * 0.35 * ddx
                lines.append(
                    f'  <polygon points="{ax:.1f},{ay:.1f} {lx:.1f},{ly:.1f} {rx:.1f},{ry:.1f}" '
                    f'fill="{color}" opacity="{alpha:.2f}" />'
                )

    # Nodes
    for v in g.vertices():
        vi = int(v)
        cx, cy, w, h = node_rects[vi]

        # Fill color
        fc = props["v_fill"][v]
        fill = f"rgb({int(fc[0] * 255)},{int(fc[1] * 255)},{int(fc[2] * 255)})"

        # Border color
        bc = props["v_border"][v]
        stroke = f"rgb({int(bc[0] * 255)},{int(bc[1] * 255)},{int(bc[2] * 255)})"
        sw = props["v_pen_width"][v]

        # Shape
        shape = props["v_shape"][v]
        dash = ' stroke-dasharray="6,3"' if "dashed" in props["v_dot_style"][v] else ""

        x1 = cx - w / 2
        y1 = cy - h / 2

        if shape in ("circle", "double_circle"):
            lines.append(
                f'  <ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w / 2:.1f}" ry="{h / 2:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.1f}"{dash} />'
            )
        else:
            rx = 3 if "3d" in props["v_dot_shape"][v] else 0
            lines.append(
                f'  <rect x="{x1:.1f}" y="{y1:.1f}" width="{w:.1f}" height="{h:.1f}" '
                f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw:.1f}"{dash} />'
            )

        # Label
        label = props["v_label"][v].split("\n")[0][:40]
        label = (
            label.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        lines.append(
            f'  <text x="{cx:.1f}" y="{cy:.1f}" '
            f'text-anchor="middle" dominant-baseline="central">{label}</text>'
        )

    lines.append("</svg>")

    with open(svg_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Written {svg_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate styled task graph using graph-tool")
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
        default="sfdp",
        choices=["sfdp", "fr", "radial", "auto"],
        help="Layout algorithm (default: sfdp)",
    )
    parser.add_argument(
        "--graphviz",
        action="store_true",
        help="Use Graphviz renderer (looks like original) instead of Cairo",
    )
    parser.add_argument(
        "--manhattan",
        action="store_true",
        help="Use Manhattan (orthogonal) edge routing with sfdp positions",
    )
    parser.add_argument(
        "--fmt",
        default="svg",
        choices=["svg", "pdf", "png"],
        help="Output format (default: svg)",
    )
    parser.add_argument(
        "--sparse",
        action="store_true",
        help="Use sparser layout (default is dense with tight edge routing)",
    )
    parser.add_argument(
        "--splines",
        default="true",
        choices=["true", "curved", "ortho", "polyline", "line", "false"],
        help="Edge routing mode for --graphviz (default: true)",
    )
    parser.add_argument(
        "--sep", default="+4", help="Node separation for edge routing (default: +4)"
    )
    parser.add_argument(
        "--overlap",
        default="prism",
        help="Overlap removal: true/false/scale/prism/compress (default: prism)",
    )
    parser.add_argument(
        "--K", type=float, default=None, help="sfdp optimal edge length (overrides dense/sparse)"
    )
    parser.add_argument(
        "--C", type=float, default=None, help="sfdp repulsive force (overrides dense/sparse)"
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

    # Build graph
    g, props, node_count = build_graph(all_nodes, all_edges, structural_ids, args.include_orphans)
    print(f"  Graph: {g.num_vertices()} vertices, {g.num_edges()} edges")

    if g.num_vertices() == 0:
        print("No nodes to render")
        return 0

    # Layout
    layout_hint = args.layout
    if args.ego and layout_hint == "sfdp":
        layout_hint = "auto"  # auto-select for ego subgraphs
    pos = compute_layout(
        g,
        node_count,
        layout_hint,
        dense=not args.sparse,
        K_override=args.K,
        C_override=args.C,
    )

    # Render: Cairo is default (dense, anti-aliased), --graphviz for old style
    if args.manhattan:
        render_manhattan(g, pos, props, args.output)
    elif args.graphviz:
        render_graphviz(
            g,
            pos,
            props,
            args.output,
            splines_mode=args.splines,
            sep=args.sep,
            overlap=args.overlap,
        )
    else:
        render_cairo(g, pos, props, args.output, args.fmt)

    return 0


if __name__ == "__main__":
    sys.exit(main())
