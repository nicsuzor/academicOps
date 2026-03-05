#!/usr/bin/env python3
"""Generate SFDP layout for the task graph with Manhattan edge routing.

Reads graph.json (from ``aops graph``), converts to DOT, runs graphviz
``sfdp`` for scalable force-directed placement, parses output positions,
and writes a per-layout JSON file (``graph-sfdp.json``) compatible with
the overwhelm dashboard's layout system.

SFDP handles hundreds of thousands of nodes efficiently.
Manhattan edge routing is done client-side by the D3 renderer (not by
graphviz ortho splines, which are too slow at scale).

Usage:
    python task_graph_sfdp.py [INPUT] [-o OUTPUT]

Examples:
    python task_graph_sfdp.py graph.json -o graph-sfdp.json
    python task_graph_sfdp.py  # reads from $AOPS_SESSIONS/graph.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_STATUS_COLORS = {
    "done": "#dcfce7",
    "completed": "#dcfce7",
    "cancelled": "#f1f5f9",
    "active": "#dbeafe",
    "in_progress": "#c7d2fe",
    "blocked": "#fee2e2",
    "waiting": "#fef9c3",
    "inbox": "#f1f5f9",
    "todo": "#f1f5f9",
    "review": "#f3e8ff",
    "decomposing": "#e0f2fe",
    "dormant": "#f1f5f9",
}

_EDGE_COLORS = {
    "parent": "#3b82f6",
    "depends_on": "#ef4444",
}
_EDGE_DEFAULT_COLOR = "#94a3b8"

_TYPE_WEIGHT = {
    "goal": 8.0,
    "project": 5.0,
    "epic": 3.0,
    "task": 1.0,
    "feature": 2.0,
    "bug": 1.0,
    "action": 0.8,
    "learn": 0.6,
    "knowledge": 0.6,
    "note": 0.4,
    "daily": 0.3,
    "person": 1.0,
    "context": 0.4,
    "template": 0.3,
}


def _escape_dot(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def graph_to_dot(graph: dict) -> str:
    """Convert graph.json to DOT format for sfdp layout."""
    lines = [
        "graph G {",
        "    overlap=prism;",
        "    overlap_scaling=-4;",
        "    K=0.6;",
        "    repulsiveforce=1.8;",
        '    sep="+8";',
        '    node [shape=box, style=filled, fontsize=8, margin="0.04,0.02"];',
    ]

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_ids = {n["id"] for n in nodes}

    for node in nodes:
        nid = node["id"]
        label = node.get("label", nid)
        if len(label) > 40:
            label = label[:37] + "..."
        status = (node.get("status") or "inbox").lower()
        node_type = node.get("node_type") or "task"
        fill = _STATUS_COLORS.get(status, "#e9ecef")
        weight = _TYPE_WEIGHT.get(node_type, 1.0)
        w = 0.8 + weight * 0.15
        h = 0.3 + weight * 0.05

        lines.append(
            f'    "{nid}" [label="{_escape_dot(label)}", '
            f'fillcolor="{fill}", width={w:.2f}, height={h:.2f}, '
            f"fixedsize=true];"
        )

    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src not in node_ids or tgt not in node_ids:
            continue
        etype = edge.get("type", "link")
        color = _EDGE_COLORS.get(etype, _EDGE_DEFAULT_COLOR)
        weight = 5.0 if etype == "parent" else 2.0 if etype == "depends_on" else 0.5
        lines.append(f'    "{src}" -- "{tgt}" [color="{color}", weight={weight:.1f}];')

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SFDP execution and position parsing
# ---------------------------------------------------------------------------

# Matches multi-line node blocks: nodeId [attr1=..., \n attr2=..., \n pos="x,y"];
_NODE_BLOCK_RE = re.compile(
    r"""(?:^|\n)\s+(?:"([^"]+)"|(\S+?))\s+\[([^\]]*)\]""",
    re.DOTALL,
)
_POS_ATTR_RE = re.compile(r'pos="([^"]+)"')


def run_sfdp(dot_input: str, *, timeout: int = 300) -> str:
    """Run sfdp on DOT input, return DOT output with positions.

    splines=ortho is NOT used because ortho routing is extremely expensive
    at scale (4k+ nodes causes timeouts). Manhattan edge routing is
    handled client-side by the D3 renderer instead.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
        f.write(dot_input)
        f.flush()
        input_path = f.name

    try:
        result = subprocess.run(
            [
                "sfdp",
                "-Goverlap=prism",
                "-Goverlap_scaling=-4",
                "-Gsep=+8",
                "-GK=0.6",
                "-Grepulsiveforce=1.8",
                input_path,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            print(f"sfdp stderr: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        return result.stdout
    finally:
        Path(input_path).unlink(missing_ok=True)


def parse_positions(dot_output: str) -> dict[str, tuple[float, float]]:
    """Parse node positions from sfdp DOT output.

    Handles multi-line node attribute blocks and both quoted/unquoted IDs.
    """
    positions = {}
    for match in _NODE_BLOCK_RE.finditer(dot_output):
        nid = match.group(1) or match.group(2)
        attrs = match.group(3)
        pos_match = _POS_ATTR_RE.search(attrs)
        if not pos_match:
            continue
        coords = pos_match.group(1).rstrip("!")
        parts = coords.split(",")
        if len(parts) >= 2:
            try:
                x, y = float(parts[0]), float(parts[1])
                positions[nid] = (x, y)
            except ValueError:
                continue
    return positions


def normalize_positions(
    positions: dict[str, tuple[float, float]],
    target_range: float = 1000.0,
    padding: float = 20.0,
) -> dict[str, tuple[float, float]]:
    """Normalize positions to [padding, target_range - padding] range."""
    if not positions:
        return {}

    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    range_x = max_x - min_x or 1.0
    range_y = max_y - min_y or 1.0

    usable = target_range - 2 * padding
    scale = usable / max(range_x, range_y)

    result = {}
    for nid, (x, y) in positions.items():
        nx = padding + (x - min_x) * scale
        ny = padding + (y - min_y) * scale
        result[nid] = (round(nx, 2), round(ny, 2))
    return result


def build_layout_json(graph: dict, positions: dict[str, tuple[float, float]]) -> dict:
    """Build per-layout JSON with sfdp positions on nodes."""
    nodes_out = []
    for node in graph.get("nodes", []):
        nid = node["id"]
        out = {**node}
        if nid in positions:
            out["x"] = positions[nid][0]
            out["y"] = positions[nid][1]
        else:
            out["x"] = None
            out["y"] = None
        nodes_out.append(out)

    return {
        "nodes": nodes_out,
        "edges": graph.get("edges", []),
        "ready": graph.get("ready", []),
        "blocked": graph.get("blocked", []),
        "by_project": graph.get("by_project", {}),
        "roots": graph.get("roots", []),
        "layout_metadata": graph.get("layout_metadata", {}),
    }


def build_positioned_dot(graph: dict, positions: dict[str, tuple[float, float]]) -> str:
    """Build a DOT file with precomputed positions for neato -n rendering."""
    lines = [
        "graph G {",
        "    splines=ortho;",
        "    overlap=false;",
        '    node [shape=box, style=filled, fontsize=8, margin="0.04,0.02"];',
    ]

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_ids = {n["id"] for n in nodes}

    for node in nodes:
        nid = node["id"]
        if nid not in positions:
            continue
        label = node.get("label", nid)
        if len(label) > 40:
            label = label[:37] + "..."
        status = (node.get("status") or "inbox").lower()
        fill = _STATUS_COLORS.get(status, "#e9ecef")
        x, y = positions[nid]
        lines.append(
            f'    "{nid}" [label="{_escape_dot(label)}", fillcolor="{fill}", pos="{x},{y}!"];'
        )

    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src not in node_ids or tgt not in node_ids:
            continue
        if src not in positions or tgt not in positions:
            continue
        etype = edge.get("type", "link")
        color = _EDGE_COLORS.get(etype, _EDGE_DEFAULT_COLOR)
        lines.append(f'    "{src}" -- "{tgt}" [color="{color}"];')

    lines.append("}")
    return "\n".join(lines)


def main():
    sessions = os.environ.get(
        "AOPS_SESSIONS",
        os.path.join(os.environ.get("POLECAT_HOME", os.path.expanduser("~/.aops")), "sessions"),
    )
    default_input = os.path.join(sessions, "graph.json")

    parser = argparse.ArgumentParser(description="Generate SFDP layout for task graph")
    parser.add_argument("input", nargs="?", default=default_input, help="Input graph.json")
    parser.add_argument("-o", "--output", default=None, help="Output JSON path")
    parser.add_argument("--dot-output", default=None, help="Output positioned DOT path")
    parser.add_argument("--timeout", type=int, default=300, help="sfdp timeout in seconds")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / "graph-sfdp.json"

    if args.dot_output:
        dot_output_path = Path(args.dot_output)
    else:
        dot_output_path = input_path.parent / "graph-sfdp.dot"

    print(f"Reading {input_path} ...", file=sys.stderr)
    graph = json.loads(input_path.read_text())
    n_nodes = len(graph.get("nodes", []))
    n_edges = len(graph.get("edges", []))
    print(f"  {n_nodes} nodes, {n_edges} edges", file=sys.stderr)

    print("Generating DOT ...", file=sys.stderr)
    dot_input = graph_to_dot(graph)

    print(f"Running sfdp (timeout={args.timeout}s) ...", file=sys.stderr)
    dot_result = run_sfdp(dot_input, timeout=args.timeout)

    positions = parse_positions(dot_result)
    print(f"  Parsed {len(positions)} positions", file=sys.stderr)

    if not positions:
        print("Error: sfdp produced no positions", file=sys.stderr)
        sys.exit(1)

    positions = normalize_positions(positions)

    layout_json = build_layout_json(graph, positions)
    output_path.write_text(json.dumps(layout_json, separators=(",", ":")))
    print(f"Wrote {output_path} ({output_path.stat().st_size / 1024:.0f} KB)", file=sys.stderr)

    dot_positioned = build_positioned_dot(graph, positions)
    dot_output_path.write_text(dot_positioned)
    print(f"Wrote {dot_output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
