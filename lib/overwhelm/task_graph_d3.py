"""D3 force-directed graph for the overwhelm dashboard.

Renders a rich manhattan-routed force graph using graph.json data from
`aops graph`. Features weight-based visual dominance, shaped nodes per type,
differentiated edges (S-curves for parent, manhattan routing for deps,
dashed for refs), legend, detail panel, and hover highlighting.
"""

import math
import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants (mirrored from scripts/task_graph_d3.py to avoid cross-path import)
# ---------------------------------------------------------------------------

EDGE_FORCE = {
    "parent": {"strength": 1.0, "distance": 40},
    "depends_on": {"strength": 0.15, "distance": 200},
    "ref": {"strength": 0.02, "distance": 300},
}

# Global force simulation parameters — all tunables in one place.
# Passed to JS via graphData.forceConfig so nothing is hardcoded in index.html.
FORCE_CONFIG = {
    "chargeDistanceMax": 100,  # Stop repelling beyond this distance (px)
    "collisionPadding": 2,  # Extra px around each node for collision avoidance
    "collisionStrength": 0.4,  # How aggressively collisions are enforced (0-1)
    "collisionIterations": 3,  # Solver iterations per tick (more = stabler but slower)
    "clusterStrength": 0.25,  # Pull toward project centroid (0 = off, 1 = very strong)
    "defaultCharge": -200,  # Fallback repulsion if node type not in TYPE_CHARGE
    "defaultLinkDistance": 150,  # Fallback link distance if not set per-edge
    "defaultLinkStrength": 0.1,  # Fallback link strength if not set per-edge
    "orphanRadius": 0.45,  # Fraction of viewport to push orphans toward (0-1)
    "orphanStrength": 0.3,  # How strongly orphans are pushed to periphery (0-1)
}

TYPE_CHARGE = {
    "goal": -500,
    "project": -350,
    "epic": -250,
    "task": -150,
    "action": -100,
    "bug": -150,
    "feature": -180,
    "learn": -100,
    "daily": -70,
    "knowledge": -100,
    "person": -100,
    "context": -70,
    "template": -60,
    "note": -70,
}

TYPE_BASE_SCALE = {
    "goal": 1.5,
    "project": 1.25,
    "epic": 1.1,
    "task": 1.0,
    "action": 0.85,
    "bug": 1.0,
    "feature": 1.05,
    "learn": 0.85,
    "daily": 0.7,
    "knowledge": 0.8,
    "person": 0.9,
    "context": 0.75,
    "template": 0.7,
    "note": 0.8,
}

TYPE_SHAPE = {
    "goal": "pill",
    "project": "rounded",
    "epic": "hexagon",
    "task": "rect",
    "action": "rect",
    "bug": "rect",
    "feature": "rounded",
    "learn": "rect",
    "daily": "rect",
    "knowledge": "rect",
    "person": "pill",
}

STATUS_FILLS = {
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

STATUS_TEXT = {
    "done": "#166534",
    "completed": "#166534",
    "cancelled": "#94a3b8",
    "active": "#1e3a5f",
    "in_progress": "#312e81",
    "blocked": "#991b1b",
    "waiting": "#854d0e",
    "inbox": "#475569",
    "todo": "#475569",
    "review": "#6b21a8",
    "decomposing": "#0369a1",
    "dormant": "#94a3b8",
}

TYPE_BADGE = {
    "goal": "GOAL",
    "project": "PROJECT",
    "epic": "EPIC",
    "task": "",
    "action": "ACTION",
    "bug": "BUG",
    "feature": "FEATURE",
    "learn": "LEARN",
}

ASSIGNEE_COLORS = {
    "bot": "#17a2b8",
    "claude": "#17a2b8",
    "worker": "#fd7e14",
    "nic": "#6f42c1",
}
ASSIGNEE_DEFAULT = "#6c757d"

PRIORITY_BORDERS = {
    0: "#dc3545",
    1: "#fd7e14",
    2: "#6c757d",
    3: "#adb5bd",
    4: "#dee2e6",
}

INCOMPLETE_STATUSES = {
    "inbox",
    "active",
    "in_progress",
    "blocked",
    "waiting",
    "todo",
    "pending",
}

_MUTED_FILL = "#e8eaed"
_MUTED_TEXT = "#9ca3af"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _estimate_text_width(text: str, font_size: int) -> float:
    return len(text) * font_size * 0.56


def _wrap_text(label: str, font_size: int, max_width: float) -> list[str]:
    if _estimate_text_width(label, font_size) <= max_width:
        return [label]
    chars_per_line = max(10, int(max_width / (font_size * 0.56)))
    lines: list[str] = []
    current = ""
    for word in label.split():
        test = f"{current} {word}".strip()
        if len(test) > chars_per_line and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines[:3]


def _extract_assignee(file_path: str) -> str | None:
    try:
        path = Path(file_path)
        if not path.exists():
            return None
        content = path.read_text(errors="ignore")[:2000]
        if not content.startswith("---"):
            return None
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


def _classify_edge(source_id: str, target_id: str, node_by_id: dict) -> str:
    source = node_by_id.get(source_id, {})
    if source.get("parent") == target_id:
        return "parent"
    if target_id in (source.get("depends_on") or []):
        return "depends_on"
    if target_id in (source.get("soft_depends_on") or []):
        return "soft_depends_on"
    return "link"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _interpolate_color(color_a: str, color_b: str, t: float) -> str:
    """Interpolate between two hex colors. t=0 gives color_a, t=1 gives color_b."""
    t = max(0.0, min(1.0, t))
    ra, ga, ba = _hex_to_rgb(color_a)
    rb, gb, bb = _hex_to_rgb(color_b)
    r = round(ra + (rb - ra) * t)
    g = round(ga + (gb - ga) * t)
    b = round(ba + (bb - ba) * t)
    return _rgb_to_hex(r, g, b)


# ---------------------------------------------------------------------------
# Rich graph data preparation (from graph.json)
# ---------------------------------------------------------------------------


def prepare_embedded_graph_data(
    graph: dict,
    structural_ids: set[str] | None = None,
) -> dict:
    """Transform graph.json into rich D3-compatible format with visual encoding.

    Args:
        graph: Raw graph.json dict with "nodes" and "edges" keys.
        structural_ids: Optional set of node IDs that are structural (completed
            parents kept for context). These get muted styling.

    Returns:
        Dict with "nodes" and "links" ready for the embedded D3 renderer.
    """
    if structural_ids is None:
        structural_ids = set()

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    node_by_id = {n["id"]: n for n in nodes}
    node_ids = {n["id"] for n in nodes}
    valid_edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]
    max_depth = max((n.get("depth", 0) for n in nodes), default=0)

    weights = [n.get("downstream_weight", 0) for n in nodes]
    max_weight = max(weights) if weights else 1
    if max_weight == 0:
        max_weight = 1

    target_weight = {n["id"]: n.get("downstream_weight", 0) for n in nodes}

    d3_nodes = []
    for node in nodes:
        nid = node["id"]
        node_type = node.get("node_type") or "task"
        status = (node.get("status") or "inbox").lower()
        priority = node.get("priority", 2)
        if not isinstance(priority, int):
            priority = 2
        dw = node.get("downstream_weight", 0)
        stakeholder = node.get("stakeholder_exposure", False)
        depth = node.get("depth", 0)
        is_structural = nid in structural_ids

        # Prioritize title over label for human-readable names
        label = node.get("title") or node.get("label") or nid
        if len(label) > 60:
            label = label[:57] + "..."

        # Extract modification time for recency heatmap
        modified = node.get("modified")
        if not modified and node.get("path"):
            try:
                # Fallback to filesystem mtime if path exists and modified not in graph.json
                p = Path(os.environ.get("ACA_DATA", "")) / node["path"]
                if p.exists():
                    modified = p.stat().st_mtime
            except Exception:
                pass

        type_scale = TYPE_BASE_SCALE.get(node_type, 1.0)
        if status in ("done", "completed", "cancelled"):
            type_scale *= 0.6  # Shrink completed tasks
        weight_factor = 1 + math.log1p(dw) * 0.3 if dw > 0 else 1.0
        scale = type_scale * weight_factor

        base_font = 10
        font_size = max(8, min(16, round(base_font * scale)))

        max_text_w = 160 * scale
        lines = _wrap_text(label, font_size, max_text_w)
        line_widths = [_estimate_text_width(line, font_size) for line in lines]
        text_w = max(line_widths) if line_widths else 40

        pad_x = 16 * type_scale
        pad_y = 10 * type_scale
        node_w = max(text_w + pad_x * 2, 55 * type_scale)
        node_h = max(len(lines) * (font_size + 4) + pad_y * 2, 30 * type_scale)

        # Weight-driven color intensity
        weight_norm = min(math.log1p(dw) / math.log1p(max_weight), 1.0) if max_weight > 0 else 0
        base_fill = STATUS_FILLS.get(status, "#f1f5f9")
        if is_structural:
            fill = "#e2e8f0"
            text_col = "#94a3b8"
        else:
            desaturation = max(0.0, 0.4 - weight_norm * 0.4)
            fill = _interpolate_color(base_fill, _MUTED_FILL, desaturation)
            base_text = STATUS_TEXT.get(status, "#475569")
            text_col = _interpolate_color(base_text, _MUTED_TEXT, desaturation)

        opacity = 1.0
        if not is_structural and dw == 0:
            has_edges = any(e["source"] == nid or e["target"] == nid for e in valid_edges)
            if not has_edges:
                opacity = 0.5

        is_incomplete = status in INCOMPLETE_STATUSES
        border_color = PRIORITY_BORDERS.get(priority, "#cbd5e1")
        assignee = node.get("assignee")
        if is_incomplete and not assignee:
            file_path = node.get("path", "")
            if file_path:
                assignee = _extract_assignee(file_path)
        if assignee and is_incomplete:
            border_color = ASSIGNEE_COLORS.get(assignee, ASSIGNEE_DEFAULT)

        border_width = 1.5 + min(math.log1p(dw) * 0.5, 2.5)
        if priority <= 1 and is_incomplete:
            border_width = max(border_width, 3)

        shape = TYPE_SHAPE.get(node_type, "rect")
        badge = TYPE_BADGE.get(node_type, "")

        d3_nodes.append(
            {
                "id": nid,
                "label": label,
                "lines": lines,
                "type": node_type,
                "shape": shape,
                "status": status,
                "priority": priority,
                "depth": depth,
                "maxDepth": max_depth,
                "w": round(node_w, 1),
                "h": round(node_h, 1),
                "fontSize": font_size,
                "fill": fill,
                "textColor": text_col,
                "borderColor": border_color,
                "borderWidth": round(border_width, 1),
                "stakeholder": stakeholder,
                "structural": is_structural,
                "dw": round(dw, 1),
                "modified": modified,
                "badge": badge,
                "charge": TYPE_CHARGE.get(node_type, -100),
                "parent": node.get("parent"),
                "project": node.get("project"),
                "assignee": assignee or node.get("assignee"),
                "opacity": opacity,
            }
        )

    d3_links = []
    for edge in valid_edges:
        etype = edge.get("type") or _classify_edge(edge["source"], edge["target"], node_by_id)
        if etype in ("soft_depends_on", "link", "wikilink"):
            etype = "ref"
        force = EDGE_FORCE.get(etype, EDGE_FORCE["ref"])

        if etype == "parent":
            color, width, dash = "#3b82f6", 3.0, ""
        elif etype == "depends_on":
            color, width, dash = "#ef4444", 2.5, ""
            tw = target_weight.get(edge["target"], 0)
            if tw > 0 and max_weight > 0:
                crit_ratio = min(math.log1p(tw) / math.log1p(max_weight), 1.0)
                if crit_ratio > 0.5:
                    width = 2.0 + crit_ratio * 2.0
                    color = "#dc2626"
        else:
            color, width, dash = "#94a3b8", 1.5, "4,3"

        # For parent edges, flip direction so arrows point parent→child
        # (graph.json stores child→parent, but visually we want "contains")
        if etype == "parent":
            link_source, link_target = edge["target"], edge["source"]
        else:
            link_source, link_target = edge["source"], edge["target"]

        d3_links.append(
            {
                "source": link_source,
                "target": link_target,
                "type": etype,
                "color": color,
                "width": round(width, 1),
                "dash": dash,
                "strength": force["strength"],
                "distance": force["distance"],
            }
        )

    return {"nodes": d3_nodes, "links": d3_links, "forceConfig": FORCE_CONFIG}


# ---------------------------------------------------------------------------
# Embedded HTML renderer
# ---------------------------------------------------------------------------


def render_embedded_graph(graph_data: dict, height: int = 500, force_settings=None):
    """Render the graph using the bi-directional Streamlit Custom Component."""
    from d3_component import d3_task_graph

    return d3_task_graph(data=graph_data, height=height, force_settings=force_settings)
