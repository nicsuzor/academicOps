#!/usr/bin/env python3
"""Generate SFDP layout for the task graph with Manhattan edge routing.

Reads graph.dot (from ``aops graph -f dot``) directly, strips precomputed
positions, converts digraph to undirected graph, runs graphviz ``sfdp``
for scalable force-directed placement, then merges positions into
graph.json to produce ``graph-sfdp.json`` for the dashboard.

SFDP handles hundreds of thousands of nodes efficiently.
Manhattan edge routing is done client-side by the D3 renderer (not by
graphviz ortho splines, which are too slow at scale).

Usage:
    python task_graph_sfdp.py [SESSIONS_DIR]

Examples:
    python task_graph_sfdp.py                    # uses $AOPS_SESSIONS
    python task_graph_sfdp.py /path/to/sessions  # explicit dir
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

# ---------------------------------------------------------------------------
# DOT preparation (strip positions, convert to undirected for sfdp)
# ---------------------------------------------------------------------------

_POS_ATTR_RE = re.compile(r',?\s*pos="[^"]*"')

# Matches -> as a DOT edge operator at the start of a line (after a node ID).
# Anchoring to line-start prevents matching -> inside quoted attribute values
# such as label="A -> B", which appear later on the line after '['.
_EDGE_ARROW_RE = re.compile(r'^(\s*(?:"[^"]*"|\w[\w.\-:]*))\s*->\s*', re.MULTILINE)


def prepare_dot_for_sfdp(dot_text: str) -> str:
    """Prepare server-generated DOT for sfdp consumption.

    - Converts ``digraph`` to ``graph`` (sfdp needs undirected)
    - Converts ``->`` edge operators to ``--`` (line-anchored to avoid corrupting labels)
    - Strips precomputed ``pos="x,y!"`` attributes
    - Adds sfdp-tuned graph attributes
    """
    out = dot_text
    # Convert directed to undirected
    out = re.sub(r"^digraph\b", "graph", out, count=1)
    # Replace edge operators only (not -> inside quoted label values)
    out = _EDGE_ARROW_RE.sub(r"\1 -- ", out)
    # Strip pinned positions
    out = _POS_ATTR_RE.sub("", out)
    # Inject sfdp layout parameters after the opening brace
    # Dense packing: very small K pulls clusters tight, overlap=compress
    # squeezes remaining gaps, low sep allows near-touching nodes.
    sfdp_attrs = (
        "\n    overlap=compress;"
        "\n    K=0.15;"
        "\n    repulsiveforce=0.8;"
        "\n    beautify=true;"
        '\n    sep="+1";'
    )
    out = out.replace("{", "{" + sfdp_attrs, 1)
    return out


# ---------------------------------------------------------------------------
# SFDP execution and position parsing
# ---------------------------------------------------------------------------

# Matches multi-line node blocks: nodeId [attr1=...,\n attr2=...,\n pos="x,y"];
_NODE_BLOCK_RE = re.compile(
    r"""(?:^|\n)\s+(?:"([^"]+)"|(\S+?))\s+\[([^\]]*)\]""",
    re.DOTALL,
)
_POS_OUT_RE = re.compile(r'pos="([^"]+)"')


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
            ["sfdp", input_path],
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
        pos_match = _POS_OUT_RE.search(attrs)
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
    padding: float = 50.0,
) -> dict[str, tuple[float, float]]:
    """Normalize positions to [padding, target_range - padding] range.

    Uses percentile-based bounds (2nd-98th) to avoid outliers stretching
    the layout, which keeps the dense core compact.
    """
    if not positions:
        return {}

    xs = sorted(p[0] for p in positions.values())
    ys = sorted(p[1] for p in positions.values())

    # Percentile bounds to ignore outliers
    lo = int(len(xs) * 0.02)
    hi = int(len(xs) * 0.98)
    min_x, max_x = xs[lo], xs[hi]
    min_y, max_y = ys[lo], ys[hi]

    range_x = max_x - min_x or 1.0
    range_y = max_y - min_y or 1.0

    usable = target_range - 2 * padding
    scale = usable / max(range_x, range_y)

    result = {}
    for nid, (x, y) in positions.items():
        nx = padding + (x - min_x) * scale
        ny = padding + (y - min_y) * scale
        # Clamp outliers to bounds
        nx = max(padding * 0.5, min(target_range - padding * 0.5, nx))
        ny = max(padding * 0.5, min(target_range - padding * 0.5, ny))
        result[nid] = (round(nx, 2), round(ny, 2))
    return result


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------


def build_layout_json(graph: dict, positions: dict[str, tuple[float, float]]) -> dict:
    """Build per-layout JSON with sfdp positions on nodes.

    Nodes that sfdp failed to position receive a fallback position at the
    centroid of all positioned nodes, preventing null x/y values from
    producing NaN in SVG paths in the D3 renderer.
    """
    # Fallback for unpositioned nodes: centroid of the positioned set
    if positions:
        cx = round(sum(p[0] for p in positions.values()) / len(positions), 2)
        cy = round(sum(p[1] for p in positions.values()) / len(positions), 2)
    else:
        cx, cy = 500.0, 500.0

    nodes_out = []
    for node in graph.get("nodes", []):
        nid = node["id"]
        out = {**node}
        if nid in positions:
            out["x"] = positions[nid][0]
            out["y"] = positions[nid][1]
        else:
            out["x"] = cx
            out["y"] = cy
        nodes_out.append(out)

    return {**graph, "nodes": nodes_out}


def build_positioned_dot(sfdp_output: str) -> str:
    """Build a DOT file with sfdp positions for neato -n SVG rendering.

    Uses splines=line for straight-line edges in the static SVG. Ortho
    routing is avoided here for the same reason it is avoided in sfdp:
    it is O(n^2+) and causes timeouts at 4k+ nodes. The live D3 view
    handles Manhattan routing client-side.
    """
    # Insert splines=line after the opening brace for static SVG rendering
    out = sfdp_output.replace("{", "{\n    splines=line;", 1)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    sessions_default = os.environ.get(
        "AOPS_SESSIONS",
        os.path.join(os.environ.get("POLECAT_HOME", os.path.expanduser("~/.aops")), "sessions"),
    )

    parser = argparse.ArgumentParser(description="Generate SFDP layout for task graph")
    parser.add_argument(
        "sessions_dir",
        nargs="?",
        default=sessions_default,
        help="Sessions directory containing graph.json and graph.dot",
    )
    parser.add_argument("--timeout", type=int, default=300, help="sfdp timeout in seconds")
    args = parser.parse_args()

    sessions = Path(args.sessions_dir)
    dot_path = sessions / "graph.dot"
    json_path = sessions / "graph.json"
    output_json = sessions / "graph-sfdp.json"
    output_dot = sessions / "graph-sfdp.dot"

    if not dot_path.exists():
        print(f"Error: {dot_path} not found", file=sys.stderr)
        sys.exit(1)
    if not json_path.exists():
        print(f"Error: {json_path} not found", file=sys.stderr)
        sys.exit(1)

    # Read server-generated DOT
    print(f"Reading {dot_path} ...", file=sys.stderr)
    dot_text = dot_path.read_text()
    line_count = dot_text.count("\n")
    print(f"  {line_count} lines", file=sys.stderr)

    # Prepare for sfdp (strip positions, convert to undirected)
    print("Preparing DOT for sfdp ...", file=sys.stderr)
    sfdp_input = prepare_dot_for_sfdp(dot_text)

    # Run sfdp
    print(f"Running sfdp (timeout={args.timeout}s) ...", file=sys.stderr)
    sfdp_output = run_sfdp(sfdp_input, timeout=args.timeout)

    positions = parse_positions(sfdp_output)
    print(f"  Parsed {len(positions)} positions", file=sys.stderr)

    if not positions:
        print("Error: sfdp produced no positions", file=sys.stderr)
        sys.exit(1)

    positions = normalize_positions(positions)

    # Read graph.json for full node metadata
    print(f"Reading {json_path} for metadata ...", file=sys.stderr)
    graph = json.loads(json_path.read_text())

    # Write per-layout JSON
    layout_json = build_layout_json(graph, positions)
    output_json.write_text(json.dumps(layout_json, separators=(",", ":")))
    print(f"Wrote {output_json} ({output_json.stat().st_size / 1024:.0f} KB)", file=sys.stderr)

    # Write positioned DOT for SVG rendering
    positioned_dot = build_positioned_dot(sfdp_output)
    output_dot.write_text(positioned_dot)
    print(f"Wrote {output_dot}", file=sys.stderr)


if __name__ == "__main__":
    main()
