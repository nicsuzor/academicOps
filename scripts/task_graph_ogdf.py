#!/usr/bin/env python3
"""Generate styled task graph using OGDF (Open Graph Drawing Framework).

Produces hierarchical or force-directed layouts with OGDF's edge routing.
Requires: uv pip install 'ogdf-python[quickstart]'

Layouts:
  - fmmm (default): Fast multipole force-directed
  - sugiyama: Hierarchical layered layout (best for DAGs)
  - fmme: Fast multipole multilevel embedder

Usage:
    uv run python3 task_graph_ogdf.py INPUT.json [-o OUTPUT]

Examples:
    uv run python3 task_graph_ogdf.py tasks.json -o task-map --filter reachable
    uv run python3 task_graph_ogdf.py tasks.json -o task-map --layout sugiyama
"""

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from ogdf_python import cppinclude, ogdf  # type: ignore

    cppinclude("ogdf/fileformats/GraphIO.h")
    cppinclude("ogdf/energybased/FMMMLayout.h")
    cppinclude("ogdf/energybased/FastMultipoleMultilevelEmbedder.h")
    cppinclude("ogdf/layered/SugiyamaLayout.h")
    cppinclude("ogdf/layered/MedianHeuristic.h")
    cppinclude("ogdf/layered/OptimalHierarchyLayout.h")
    cppinclude("ogdf/layered/OptimalRanking.h")
    # Orthogonal layout pipeline
    cppinclude("ogdf/planarity/PlanarizationLayout.h")
    cppinclude("ogdf/planarity/PlanarizationGridLayout.h")
    cppinclude("ogdf/orthogonal/OrthoLayout.h")
    cppinclude("ogdf/planarity/SubgraphPlanarizer.h")
    cppinclude("ogdf/planarity/PlanarSubgraphFast.h")
    cppinclude("ogdf/planarity/VariableEmbeddingInserter.h")
    cppinclude("ogdf/planarity/EmbedderMinDepthMaxFaceLayers.h")
except ImportError:
    print(
        "Error: ogdf-python not available.\nInstall: uv pip install 'ogdf-python[quickstart]'",
        file=sys.stderr,
    )
    sys.exit(1)

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

# OGDF shape mapping
OGDF_SHAPE_MAP = {
    "ellipse": ogdf.Shape.Ellipse,
    "box3d": ogdf.Shape.RoundedRect,
    "octagon": ogdf.Shape.Octagon,
    "box": ogdf.Shape.Rect,
    "note": ogdf.Shape.Rect,
    "diamond": ogdf.Shape.Rhomb,
    "hexagon": ogdf.Shape.Hexagon,
    "tab": ogdf.Shape.Rect,
    "plaintext": ogdf.Shape.Rect,
    "circle": ogdf.Shape.Ellipse,
    "cds": ogdf.Shape.Octagon,
    "component": ogdf.Shape.Rect,
}


def hex_to_ogdf_color(hex_str: str) -> ogdf.Color:
    """Convert hex color string to ogdf.Color."""
    h = hex_str.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return ogdf.Color(r, g, b)


def build_graph(
    nodes: list[dict],
    edges: list[dict],
    structural_ids: set[str],
    include_orphans: bool = False,
) -> tuple:
    """Build OGDF Graph with GraphAttributes.

    Returns (G, GA, node_map, structural_node_ids_in_graph)
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

    G = ogdf.Graph()
    GA = ogdf.GraphAttributes(
        G,
        ogdf.GraphAttributes.nodeGraphics
        | ogdf.GraphAttributes.edgeGraphics
        | ogdf.GraphAttributes.nodeLabel
        | ogdf.GraphAttributes.nodeStyle
        | ogdf.GraphAttributes.edgeStyle
        | ogdf.GraphAttributes.edgeArrow,
    )

    # Track OGDF node objects by ID
    id_to_node = {}
    structural_ogdf_nodes = set()

    for node_data in nodes:
        nid = node_data["id"]
        n = G.newNode()
        id_to_node[nid] = n

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
        GA.label[n] = label

        # Size: scale with label length and downstream weight
        base_w = max(60, min(len(label) * 7, 200))
        base_h = 30
        scale = 1.0 + min(dw * 0.1, 0.8)
        GA.width[n] = base_w * scale
        GA.height[n] = base_h * scale

        # Shape
        if nid in structural_ids:
            dot_shape = STRUCTURAL_STYLE["shape"]
            structural_ogdf_nodes.add(n.index())
        else:
            dot_shape = TYPE_SHAPES.get(node_type, "box")
        GA.shape[n] = OGDF_SHAPE_MAP.get(dot_shape, ogdf.Shape.Rect)

        # Fill color
        if nid in structural_ids:
            fill_hex = STRUCTURAL_STYLE["fillcolor"]
        else:
            fill_hex = STATUS_COLORS.get(status, "#ffffff")
        GA.fillColor[n] = hex_to_ogdf_color(fill_hex)

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

        GA.strokeColor[n] = hex_to_ogdf_color(pen_hex)
        GA.strokeWidth[n] = pw

    # Build edges
    node_ids = set(id_to_node.keys())
    for edge_data in edges:
        src, tgt = edge_data["source"], edge_data["target"]
        if src not in node_ids or tgt not in node_ids:
            continue

        e = G.newEdge(id_to_node[src], id_to_node[tgt])

        edge_type = edge_data.get("type") or classify_edge(src, tgt, node_by_id)
        style = EDGE_STYLES.get(edge_type, EDGE_STYLES["link"])

        GA.strokeColor[e] = hex_to_ogdf_color(style["color"])
        GA.strokeWidth[e] = float(style.get("penwidth", "1"))

        # Arrow style
        if edge_type in ("parent", "depends_on"):
            GA.arrowType[e] = ogdf.EdgeArrow.Last
        else:
            GA.arrowType[e] = ogdf.EdgeArrow.Last

    return G, GA, id_to_node, structural_ogdf_nodes, len(nodes)


def apply_layout(G, GA, layout_name: str, num_nodes: int):
    """Apply OGDF layout algorithm."""
    if layout_name == "ortho":
        print(f"  Layout: PlanarizationLayout + OrthoLayout ({num_nodes} nodes)")
        pl = ogdf.PlanarizationLayout()

        # Crossing minimization
        crossMin = ogdf.SubgraphPlanarizer()
        ps = ogdf.PlanarSubgraphFast[int]()
        ps.runs(100)
        ves = ogdf.VariableEmbeddingInserter()
        ves.removeReinsert(ogdf.RemoveReinsertType.All)
        crossMin.setSubgraph(ps)
        crossMin.setInserter(ves)
        ps.__python_owns__ = False
        ves.__python_owns__ = False
        crossMin.__python_owns__ = False
        pl.setCrossMin(crossMin)

        # Embedder
        emb = ogdf.EmbedderMinDepthMaxFaceLayers()
        emb.__python_owns__ = False
        pl.setEmbedder(emb)

        # Orthogonal layout module
        ol = ogdf.OrthoLayout()
        ol.separation(20.0)
        ol.cOverhang(0.4)
        ol.__python_owns__ = False
        pl.setPlanarLayouter(ol)

        pl.call(GA)

    elif layout_name == "ortho-grid":
        print(f"  Layout: PlanarizationGridLayout ({num_nodes} nodes)")
        pgl = ogdf.PlanarizationGridLayout()
        pgl.pageRatio(1.0)
        pgl.call(GA)

    elif layout_name == "sugiyama":
        print(f"  Layout: Sugiyama hierarchical ({num_nodes} nodes)")
        sl = ogdf.SugiyamaLayout()
        sl.call(GA)
    elif layout_name == "fmme":
        print(f"  Layout: FastMultipoleMultilevelEmbedder ({num_nodes} nodes)")
        fmme = ogdf.FastMultipoleMultilevelEmbedder()
        fmme.call(GA)
    else:
        # Default: FMMMLayout
        print(f"  Layout: FMMM force-directed ({num_nodes} nodes)")
        fmmm = ogdf.FMMMLayout()
        fmmm.useHighLevelOptions(True)
        fmmm.unitEdgeLength(50.0)
        fmmm.newInitialPlacement(True)
        fmmm.qualityVersusSpeed(ogdf.FMMMOptions.QualityVsSpeed.GorgeousAndEfficient)
        fmmm.call(GA)


def postprocess_svg(svg_path: str, structural_node_indices: set[int]):
    """Post-process SVG to add dashed borders for structural nodes."""
    if not structural_node_indices:
        return

    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        # OGDF SVG uses node indices in element IDs
        # ns = {"svg": "http://www.w3.org/2000/svg"}

        for elem in root.iter():
            node_id = elem.get("id", "")
            # OGDF typically generates IDs like "node0", "node1", etc.
            if node_id.startswith("node"):
                try:
                    idx = int(node_id[4:])
                    if idx in structural_node_indices:
                        # Add dashed stroke to the shape element
                        for child in elem:
                            if child.tag.endswith(("rect", "ellipse", "polygon")):
                                child.set("stroke-dasharray", "8,4")
                except (ValueError, IndexError):
                    pass

        tree.write(svg_path, xml_declaration=True, encoding="unicode")
    except Exception as e:
        print(f"  Warning: SVG post-processing failed: {e}")


def render_svg(GA, output_path: str, structural_nodes: set[int]):
    """Render graph to SVG."""
    svg_path = f"{output_path}.svg"
    print(f"  Rendering: OGDF -> {svg_path}")

    ogdf.GraphIO.drawSVG(GA, svg_path)
    postprocess_svg(svg_path, structural_nodes)

    print(f"  Written {svg_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate styled task graph using OGDF")
    parser.add_argument("input", help="Input JSON file from aops graph")
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
        default="fmmm",
        choices=["fmmm", "sugiyama", "fmme", "ortho", "ortho-grid"],
        help="OGDF layout algorithm (default: fmmm)",
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
    G, GA, id_to_node, structural_ogdf_nodes, node_count = build_graph(
        all_nodes, all_edges, structural_ids, args.include_orphans
    )
    print(f"  Graph: {G.numberOfNodes()} nodes, {G.numberOfEdges()} edges")

    if G.numberOfNodes() == 0:
        print("No nodes to render")
        return 0

    # Layout
    apply_layout(G, GA, args.layout, node_count)

    # Render
    render_svg(GA, args.output, structural_ogdf_nodes)

    return 0


if __name__ == "__main__":
    sys.exit(main())
