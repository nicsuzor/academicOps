"""D3 force-directed graph for the overwhelm dashboard.

Renders a rich manhattan-routed force graph using graph.json data from the
fast-indexer. Features weight-based visual dominance, shaped nodes per type,
differentiated edges (S-curves for parent, manhattan routing for deps,
dashed for refs), legend, detail panel, and hover highlighting.
"""

import json
import math
import re
from pathlib import Path

import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Constants (mirrored from scripts/task_graph_d3.py to avoid cross-path import)
# ---------------------------------------------------------------------------

EDGE_FORCE = {
    "parent": {"strength": 0.8, "distance": 80},
    "depends_on": {"strength": 0.35, "distance": 150},
    "ref": {"strength": 0.06, "distance": 220},
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

        label = node.get("label", nid)
        if len(label) > 50:
            label = label[:47] + "..."

        type_scale = TYPE_BASE_SCALE.get(node_type, 1.0)
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
            color, width, dash = "#3b82f6", 2.5, ""
        elif etype == "depends_on":
            color, width, dash = "#ef4444", 2.0, ""
            tw = target_weight.get(edge["target"], 0)
            if tw > 0 and max_weight > 0:
                crit_ratio = min(math.log1p(tw) / math.log1p(max_weight), 1.0)
                if crit_ratio > 0.5:
                    width = 2.0 + crit_ratio * 2.0
                    color = "#dc2626"
        else:
            color, width, dash = "#94a3b8", 1.0, "4,3"

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

    return {"nodes": d3_nodes, "links": d3_links}


# ---------------------------------------------------------------------------
# Embedded HTML renderer
# ---------------------------------------------------------------------------


def render_embedded_graph(graph_data: dict, height: int = 500) -> None:
    """Render the rich manhattan-routed D3 graph embedded in Streamlit."""
    data_json = json.dumps(graph_data, separators=(",", ":")).replace("</", "<\\/")

    bg = "#0f172a"
    panel_bg = "rgba(15,23,42,0.95)"
    panel_border = "#334155"
    panel_text = "#e2e8f0"
    muted = "#94a3b8"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: {bg}; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; overflow: hidden; }}
#graph {{ width: 100%; height: {height}px; }}
svg {{ width: 100%; height: 100%; }}
.node-text {{ pointer-events: none; user-select: none; }}
.node-badge {{ pointer-events: none; user-select: none; }}

#legend {{
  position: absolute; top: 8px; left: 8px; z-index: 10;
  background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 10px;
  padding: 10px 14px; font-size: 10px; max-width: 190px; color: {panel_text};
  backdrop-filter: blur(12px); box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}}
#legend h3 {{ font-size: 11px; margin-bottom: 6px; font-weight: 700; }}
#legend .section {{ margin-bottom: 6px; }}
#legend .st {{ font-weight: 600; color: {muted}; text-transform: uppercase; font-size: 8px; letter-spacing: 0.6px; margin-bottom: 3px; }}
#legend .row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 2px; line-height: 1.3; font-size: 9px; }}
#legend .sw {{ width: 14px; height: 10px; border-radius: 2px; flex-shrink: 0; border: 1px solid rgba(0,0,0,0.08); }}
#legend-toggle {{
  position: absolute; top: 8px; left: 8px; z-index: 11;
  background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 6px;
  padding: 4px 10px; font-size: 10px; cursor: pointer; color: {panel_text};
  display: none; font-family: inherit;
}}

#detail {{
  position: absolute; top: 8px; right: 8px; z-index: 10;
  background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 10px;
  padding: 14px; font-size: 11px; max-width: 280px; min-width: 200px; color: {panel_text};
  backdrop-filter: blur(12px); display: none; box-shadow: 0 2px 12px rgba(0,0,0,0.12);
}}
#detail h3 {{ font-size: 13px; margin-bottom: 8px; word-break: break-word; font-weight: 600; line-height: 1.3; padding-right: 20px; }}
#detail .f {{ margin-bottom: 4px; }}
#detail .fl {{ color: {muted}; font-size: 8px; text-transform: uppercase; letter-spacing: 0.4px; font-weight: 600; }}
#detail .fv {{ font-weight: 500; margin-top: 1px; font-size: 11px; }}
#detail .cb {{ position: absolute; top: 8px; right: 12px; cursor: pointer; font-size: 16px; color: {muted}; background: none; border: none; }}
#detail .cb:hover {{ color: {panel_text}; }}
#detail .nb {{ margin-top: 8px; max-height: 140px; overflow-y: auto; }}
#detail .ni {{ padding: 2px 0; cursor: pointer; color: #3b82f6; font-size: 10px; }}
#detail .ni:hover {{ text-decoration: underline; }}
#detail .sb {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 9px; font-weight: 600; text-transform: uppercase; }}

#stats {{
  position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%); z-index: 10;
  background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 6px;
  padding: 3px 12px; font-size: 9px; color: {muted};
  backdrop-filter: blur(12px);
}}
</style>
</head>
<body>
<div id="graph" style="position:relative;"></div>

<div id="legend">
  <h3>Task Graph</h3>
  <div class="section">
    <div class="st">Status</div>
    <div class="row"><div class="sw" style="background:#dbeafe"></div> Active</div>
    <div class="row"><div class="sw" style="background:#dcfce7"></div> Done</div>
    <div class="row"><div class="sw" style="background:#fee2e2"></div> Blocked</div>
    <div class="row"><div class="sw" style="background:#fef9c3"></div> Waiting</div>
    <div class="row"><div class="sw" style="background:#e2e8f0"></div> Structural</div>
  </div>
  <div class="section">
    <div class="st">Shape</div>
    <div class="row"><svg width="16" height="12"><rect x="1" y="1" width="14" height="10" rx="5" fill="none" stroke="{panel_text}" stroke-width="1"/></svg> Goal</div>
    <div class="row"><svg width="16" height="12"><rect x="1" y="1" width="14" height="10" rx="3" fill="none" stroke="{panel_text}" stroke-width="1"/></svg> Project</div>
    <div class="row"><svg width="16" height="12"><polygon points="3,1 13,1 15,6 13,11 3,11 1,6" fill="none" stroke="{panel_text}" stroke-width="1"/></svg> Epic</div>
    <div class="row"><svg width="16" height="12"><rect x="1" y="1" width="14" height="10" rx="1" fill="none" stroke="{panel_text}" stroke-width="1"/></svg> Task</div>
  </div>
  <div class="section">
    <div class="st">Edges</div>
    <div class="row"><svg width="20" height="6"><path d="M0,3 C5,0 15,0 20,3" stroke="#3b82f6" stroke-width="2" fill="none"/></svg> Parent</div>
    <div class="row"><svg width="20" height="6"><path d="M0,3 L20,3" stroke="#ef4444" stroke-width="1.5" fill="none"/></svg> Dep</div>
    <div class="row"><svg width="20" height="6"><line x1="0" y1="3" x2="20" y2="3" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3,2"/></svg> Ref</div>
  </div>
</div>
<button id="legend-toggle" onclick="toggleLegend()">Legend</button>

<div id="detail">
  <button class="cb" onclick="closeDetail()">&times;</button>
  <h3 id="dt"></h3>
  <div id="df"></div>
  <div id="dn" class="nb"></div>
</div>

<div id="stats"></div>

<script>
const graphData = {data_json};
const nodes = graphData.nodes;
const links = graphData.links;
const W = window.innerWidth || 800, H = {height};
const maxDepth = nodes.reduce((m, n) => Math.max(m, n.maxDepth), 0);

const svg = d3.select("#graph").append("svg").attr("viewBox", [0, 0, W, H]);
const defs = svg.append("defs");
const filt = defs.append("filter").attr("id", "sh").attr("x", "-20%").attr("y", "-20%").attr("width", "140%").attr("height", "140%");
filt.append("feDropShadow").attr("dx", 0).attr("dy", 1).attr("stdDeviation", 2).attr("flood-color", "rgba(0,0,0,0.08)");

[["ap","#3b82f6"],["ad","#ef4444"],["ar","#94a3b8"]].forEach(([id,c]) => {{
  defs.append("marker").attr("id",id).attr("viewBox","0 -4 8 8")
    .attr("refX",8).attr("refY",0).attr("markerWidth",4).attr("markerHeight",4).attr("orient","auto")
    .append("path").attr("d","M0,-3L8,0L0,3").attr("fill",c);
}});
const mMap = {{ parent:"ap", depends_on:"ad", ref:"ar" }};

const container = svg.append("g");
const zoom = d3.zoom().scaleExtent([0.03,8]).on("zoom", e => container.attr("transform", e.transform));
svg.call(zoom);

const adj = new Map();
nodes.forEach(n => adj.set(n.id, new Set()));
links.forEach(l => {{
  const s = typeof l.source === "object" ? l.source.id : l.source;
  const t = typeof l.target === "object" ? l.target.id : l.target;
  if (adj.has(s)) adj.get(s).add(t);
  if (adj.has(t)) adj.get(t).add(s);
}});

const linkG = container.append("g");
const linkEls = linkG.selectAll("path").data(links).join("path")
  .attr("fill","none").attr("stroke", d => d.color).attr("stroke-width", d => d.width)
  .attr("stroke-dasharray", d => d.dash || null)
  .attr("marker-end", d => `url(#${{mMap[d.type]||"ar"}})`)
  .attr("opacity", d => d.type === "ref" ? 0.3 : 0.55)
  .attr("stroke-linecap","round").attr("stroke-linejoin","round");

const nodeG = container.append("g");
const nodeEls = nodeG.selectAll("g").data(nodes).join("g")
  .attr("cursor","pointer").attr("opacity", d => d.opacity || 1)
  .call(d3.drag().on("start",ds).on("drag",dr).on("end",de));

function hexPoints(w, h) {{
  const hw = w/2, hh = h/2, c = Math.min(hh * 0.6, 12);
  return `${{-hw+c}},${{-hh}} ${{hw-c}},${{-hh}} ${{hw}},${{0}} ${{hw-c}},${{hh}} ${{-hw+c}},${{hh}} ${{-hw}},${{0}}`;
}}

nodeEls.each(function(d) {{
  const g = d3.select(this);
  const hw = d.w/2, hh = d.h/2;

  if (d.shape === "pill") {{
    g.append("rect").attr("x",-hw).attr("y",-hh).attr("width",d.w).attr("height",d.h)
      .attr("rx",hh).attr("ry",hh)
      .attr("fill",d.fill).attr("stroke",d.borderColor).attr("stroke-width",d.borderWidth)
      .attr("stroke-dasharray",d.structural?"4,3":null).attr("filter","url(#sh)");
  }} else if (d.shape === "hexagon") {{
    g.append("polygon").attr("points", hexPoints(d.w, d.h))
      .attr("fill",d.fill).attr("stroke",d.borderColor).attr("stroke-width",d.borderWidth)
      .attr("stroke-dasharray",d.structural?"4,3":null).attr("filter","url(#sh)");
  }} else if (d.shape === "rounded") {{
    g.append("rect").attr("x",-hw).attr("y",-hh).attr("width",d.w).attr("height",d.h)
      .attr("rx",8).attr("ry",8)
      .attr("fill",d.fill).attr("stroke",d.borderColor).attr("stroke-width",d.borderWidth)
      .attr("stroke-dasharray",d.structural?"4,3":null).attr("filter","url(#sh)");
  }} else {{
    g.append("rect").attr("x",-hw).attr("y",-hh).attr("width",d.w).attr("height",d.h)
      .attr("rx",2).attr("ry",2)
      .attr("fill",d.fill).attr("stroke",d.borderColor).attr("stroke-width",d.borderWidth)
      .attr("stroke-dasharray",d.structural?"4,3":null).attr("filter","url(#sh)");
  }}

  if (d.stakeholder) {{
    if (d.shape === "hexagon") {{
      g.insert("polygon",":first-child").attr("points", hexPoints(d.w+6, d.h+6))
        .attr("fill","none").attr("stroke",d.borderColor).attr("stroke-width",1).attr("opacity",0.4);
    }} else {{
      const rx = d.shape === "pill" ? hh+3 : d.shape === "rounded" ? 11 : 4;
      g.insert("rect",":first-child").attr("x",-hw-3).attr("y",-hh-3).attr("width",d.w+6).attr("height",d.h+6)
        .attr("rx",rx).attr("ry",rx).attr("fill","none").attr("stroke",d.borderColor).attr("stroke-width",1).attr("opacity",0.4);
    }}
  }}

  if (d.badge) {{
    const bw = d.badge.length * 5.2 + 8;
    g.append("rect").attr("x",-hw+4).attr("y",-hh+4).attr("width",bw).attr("height",12)
      .attr("rx",2).attr("fill",d.borderColor).attr("opacity",0.18);
    g.append("text").attr("class","node-badge")
      .attr("x",-hw+4+bw/2).attr("y",-hh+12.5).attr("text-anchor","middle")
      .attr("font-size","6px").attr("font-weight","700").attr("fill",d.borderColor)
      .attr("letter-spacing","0.5px").text(d.badge);
  }}

  const lh = d.fontSize + 4;
  const th = d.lines.length * lh;
  const ty = -th/2 + d.fontSize * 0.38 + (d.badge ? 4 : 0);
  d.lines.forEach((line, i) => {{
    g.append("text").attr("class","node-text").attr("x",0).attr("y", ty + i * lh)
      .attr("text-anchor","middle").attr("dominant-baseline","central")
      .attr("font-size", d.fontSize + "px")
      .attr("font-weight", d.shape === "pill" ? "700" : d.shape === "rounded" ? "600" : "500")
      .attr("fill", d.textColor)
      .attr("letter-spacing", d.shape === "pill" ? "-0.3px" : "0")
      .text(line);
  }});

  if (d.dw > 0) {{
    const t = d.dw.toFixed(1), tw = t.length * 5 + 12;
    g.append("rect").attr("x",-tw/2).attr("y",hh+3).attr("width",tw).attr("height",13)
      .attr("rx",6).attr("fill",d.borderColor).attr("opacity",0.13);
    g.append("text").attr("class","node-badge").attr("x",0).attr("y",hh+12)
      .attr("text-anchor","middle").attr("font-size","7px").attr("font-weight","600")
      .attr("fill",d.borderColor).text("\\u2696 "+t);
  }}
}});

const sim = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d=>d.id).distance(d=>d.distance).strength(d=>d.strength).iterations(3))
  .force("charge", d3.forceManyBody().strength(d=>d.charge).distanceMax(700).theta(0.8))
  .force("y", d3.forceY().y(d => {{
    if (maxDepth===0) return H/2;
    return H*0.12 + (d.depth+1)*(H*0.7/(maxDepth+2));
  }}).strength(0.1))
  .force("x", d3.forceX().x(W/2).strength(0.02))
  .force("collide", d3.forceCollide().radius(d => Math.sqrt(d.w*d.w + d.h*d.h)/2 + 8).strength(0.8).iterations(3))
  .alphaDecay(0.016).velocityDecay(0.35);

function ri(cx,cy,w,h,px,py) {{
  const dx=px-cx, dy=py-cy;
  if (dx===0 && dy===0) return [cx,cy];
  const hw=w/2+3, hh=h/2+3;
  const t = Math.abs(dx)*hh > Math.abs(dy)*hw ? hw/Math.abs(dx) : hh/Math.abs(dy);
  return [cx+dx*t, cy+dy*t];
}}

function manhattan(sx,sy,sw,sh,tx,ty,tw,th) {{
  const dx = tx-sx, dy = ty-sy;
  if (Math.abs(dx) >= Math.abs(dy)) {{
    const exitX = dx > 0 ? sx + sw/2 + 3 : sx - sw/2 - 3;
    const enterX = dx > 0 ? tx - tw/2 - 3 : tx + tw/2 + 3;
    const midX = (exitX + enterX) / 2;
    return `M${{exitX}},${{sy}} L${{midX}},${{sy}} L${{midX}},${{ty}} L${{enterX}},${{ty}}`;
  }} else {{
    const exitY = dy > 0 ? sy + sh/2 + 3 : sy - sh/2 - 3;
    const enterY = dy > 0 ? ty - th/2 - 3 : ty + th/2 + 3;
    const midY = (exitY + enterY) / 2;
    return `M${{sx}},${{exitY}} L${{sx}},${{midY}} L${{tx}},${{midY}} L${{tx}},${{enterY}}`;
  }}
}}

function edgePath(d) {{
  const s=d.source, t=d.target;
  if (d.type === "parent") {{
    const [bx,by] = ri(s.x,s.y,s.w,s.h,t.x,t.y);
    const [ex,ey] = ri(t.x,t.y,t.w,t.h,s.x,s.y);
    const midY = (by+ey)/2;
    return `M${{bx}},${{by}} C${{bx}},${{midY}} ${{ex}},${{midY}} ${{ex}},${{ey}}`;
  }}
  return manhattan(s.x,s.y,s.w,s.h,t.x,t.y,t.w,t.h);
}}

sim.tick(300);
nodeEls.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
linkEls.attr("d", edgePath);
sim.on("tick", () => {{ linkEls.attr("d", edgePath); nodeEls.attr("transform", d => `translate(${{d.x}},${{d.y}})`); }});

const b = container.node().getBBox();
if (b.width > 0) {{
  const sc = Math.min(W/(b.width+60), H/(b.height+60), 1.5) * 0.85;
  svg.call(zoom.transform, d3.zoomIdentity.translate(W/2,H/2).scale(sc).translate(-b.x-b.width/2,-b.y-b.height/2));
}}

function ds(e,d) {{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }}
function dr(e,d) {{ d.fx=e.x; d.fy=e.y; }}
function de(e,d) {{ if(!e.active) sim.alphaTarget(0); }}
nodeEls.on("dblclick",(e,d)=>{{ d.fx=null; d.fy=null; sim.alphaTarget(0.1).restart(); setTimeout(()=>sim.alphaTarget(0),500); }});

nodeEls.on("mouseenter",(e,d)=>{{
  const c = adj.get(d.id) || new Set();
  nodeEls.transition().duration(120).attr("opacity", n => (n.id===d.id||c.has(n.id)) ? 1 : 0.1);
  linkEls.transition().duration(120).attr("opacity", l => (l.source.id===d.id||l.target.id===d.id) ? 0.85 : 0.03);
}}).on("mouseleave",()=>{{
  nodeEls.transition().duration(180).attr("opacity", d => d.opacity || 1);
  linkEls.transition().duration(180).attr("opacity", d => d.type==="ref" ? 0.3 : 0.55);
}});

const nMap = new Map(nodes.map(n=>[n.id,n]));
const sbc = {{ active:"background:#dbeafe;color:#1e40af", done:"background:#dcfce7;color:#166534",
  blocked:"background:#fee2e2;color:#991b1b", waiting:"background:#fef9c3;color:#854d0e",
  review:"background:#f3e8ff;color:#6b21a8", inbox:"background:#f1f5f9;color:#475569" }};

nodeEls.on("click",(e,d)=>{{ e.stopPropagation(); showD(d); }});
svg.on("click",()=>closeD());

function showD(d) {{
  document.getElementById("dt").textContent = d.label;
  const bs = sbc[d.status]||"background:#f1f5f9;color:#475569";
  let h = `<div class="f"><span class="sb" style="${{bs}}">${{d.status}}</span></div>`;
  const fs = [
    d.badge?["Type",d.badge]:null, ["Priority","P"+d.priority],
    d.project?["Project",d.project]:null,
    d.dw>0?["Impact","\\u2696 "+d.dw.toFixed(1)]:null,
    d.stakeholder?["Stakeholder","Yes"]:null,
    d.assignee?["Assignee",d.assignee]:null, ["ID",d.id],
  ].filter(Boolean);
  h += fs.map(([l,v])=>`<div class="f"><span class="fl">${{l}}</span><br><span class="fv">${{v}}</span></div>`).join("");
  document.getElementById("df").innerHTML = h;
  const nb = adj.get(d.id)||new Set();
  const it = [...nb].map(id=>{{ const n=nMap.get(id); return n?`<div class="ni" onclick="focusN('${{id}}')">${{n.label}} <span style="opacity:0.4;font-size:8px">${{n.badge||n.type}}</span></div>`:""; }}).join("");
  document.getElementById("dn").innerHTML = nb.size>0 ? `<div class="st" style="color:{muted};font-size:8px;margin-top:3px;margin-bottom:3px">Connected (${{nb.size}})</div>${{it}}` : "";
  document.getElementById("detail").style.display = "block";
}}
function closeD() {{ document.getElementById("detail").style.display="none"; }}
window.closeDetail = closeD;
window.focusN = function(id) {{
  const n = nodes.find(n=>n.id===id); if(!n) return;
  showD(n);
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(W/2,H/2).scale(1.5).translate(-n.x,-n.y));
}};

function toggleLegend() {{
  const l=document.getElementById("legend"), b=document.getElementById("legend-toggle");
  if(l.style.display==="none"){{l.style.display="block";b.style.display="none";}}
  else{{l.style.display="none";b.style.display="block";}}
}}
window.toggleLegend=toggleLegend;
document.getElementById("legend").addEventListener("dblclick",()=>{{
  document.getElementById("legend").style.display="none";
  document.getElementById("legend-toggle").style.display="block";
}});

document.getElementById("stats").textContent =
  `${{nodes.length}} nodes \\u00b7 ${{links.length}} edges \\u00b7 drag \\u00b7 scroll \\u00b7 hover \\u00b7 click`;
</script>
</body>
</html>"""

    components.html(html, height=height)
