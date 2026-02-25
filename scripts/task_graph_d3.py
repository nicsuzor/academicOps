#!/usr/bin/env python3
"""Generate interactive D3-force task graph from fast-indexer JSON output.

Uses d3-force with hierarchical edge weighting for layout, S-curves for
parent edges, and Manhattan routing for dependencies/links. Produces a
self-contained HTML file.

Usage:
    python task_graph_d3.py INPUT.json [-o OUTPUT.html] [--filter reachable]

Examples:
    fast-indexer ./data -o graph -f json -t task,project,goal,epic
    python task_graph_d3.py graph.json -o task-map.html
    python task_graph_d3.py graph.json --filter reachable --ego my-project --depth 3
"""

import argparse
import json
import math
import sys
from pathlib import Path

# Reuse filtering and classification from task_graph.py
from task_graph import (
    ASSIGNEE_COLORS,
    ASSIGNEE_DEFAULT,
    INCOMPLETE_STATUSES,
    PRIORITY_BORDERS,
    classify_edge,
    extract_assignee,
    extract_ego_subgraph,
    filter_completed_smart,
    filter_reachable,
    filter_rollup,
)

# -- Force parameters per edge type --
# soft_depends_on, link, and wikilink are merged into "ref" (reference)
EDGE_FORCE = {
    "parent": {"strength": 0.8, "distance": 80},
    "depends_on": {"strength": 0.35, "distance": 150},
    "ref": {"strength": 0.06, "distance": 220},
}

# -- Charge strength per node type --
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

# -- Base node scale by type (multiplied by weight) --
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

# -- Shape type mapping --
# "pill" = goal, "rounded" = project, "hexagon" = epic, "rect" = everything else
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

# Active-dominant status palette
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

# Type badge labels
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


def _estimate_text_width(text: str, font_size: int) -> float:
    """Rough estimate of text width in pixels."""
    return len(text) * font_size * 0.56


def _wrap_text(label: str, font_size: int, max_width: float) -> list[str]:
    """Wrap text into lines that fit within max_width."""
    if _estimate_text_width(label, font_size) <= max_width:
        return [label]
    chars_per_line = max(10, int(max_width / (font_size * 0.56)))
    lines = []
    words = label.split()
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if len(test) > chars_per_line and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines[:3]


def prepare_graph_data(
    nodes: list[dict],
    edges: list[dict],
    structural_ids: set[str],
) -> dict:
    """Transform graph data for d3 visualization."""
    node_by_id = {n["id"]: n for n in nodes}
    node_ids = {n["id"] for n in nodes}
    valid_edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]
    max_depth = max((n.get("depth", 0) for n in nodes), default=0)

    # Compute weight range for normalization
    # weights = [n.get("downstream_weight", 0) for n in nodes]
    # max_weight = max(weights) if weights else 1

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

        # Label
        label = node.get("label", nid)
        if len(label) > 50:
            label = label[:47] + "..."

        # --- Sizing: driven by total weight (type base + downstream weight) ---
        type_scale = TYPE_BASE_SCALE.get(node_type, 1.0)
        # Weight factor: log-scale so huge weights don't dominate
        weight_factor = 1 + math.log1p(dw) * 0.3 if dw > 0 else 1.0
        scale = type_scale * weight_factor

        # Font size scales with node importance
        base_font = 10
        font_size = max(8, min(16, round(base_font * scale)))

        # Wrap text
        max_text_w = 160 * scale
        lines = _wrap_text(label, font_size, max_text_w)
        line_widths = [_estimate_text_width(line, font_size) for line in lines]
        text_w = max(line_widths) if line_widths else 40

        # Node dimensions
        pad_x = 16 * type_scale
        pad_y = 10 * type_scale
        node_w = max(text_w + pad_x * 2, 55 * type_scale)
        node_h = max(len(lines) * (font_size + 4) + pad_y * 2, 30 * type_scale)

        # Fill color
        fill = STATUS_FILLS.get(status, "#f1f5f9")
        if is_structural:
            fill = "#e2e8f0"
        text_col = STATUS_TEXT.get(status, "#475569")
        if is_structural:
            text_col = "#94a3b8"

        # Border: assignee for incomplete, priority fallback
        is_incomplete = status in INCOMPLETE_STATUSES
        border_color = PRIORITY_BORDERS.get(priority, "#cbd5e1")
        assignee = None
        if is_incomplete:
            file_path = node.get("path", "")
            if file_path:
                assignee = extract_assignee(file_path)
                if assignee:
                    border_color = ASSIGNEE_COLORS.get(assignee, ASSIGNEE_DEFAULT)

        border_width = 1.5 + min(math.log1p(dw) * 0.5, 2.5)
        if priority <= 1 and is_incomplete:
            border_width = max(border_width, 3)

        # Shape
        shape = TYPE_SHAPE.get(node_type, "rect")

        # Badge
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
            }
        )

    d3_links = []
    for edge in valid_edges:
        etype = edge.get("type") or classify_edge(edge["source"], edge["target"], node_by_id)
        # Merge soft_depends_on, link, wikilink into "ref"
        if etype in ("soft_depends_on", "link", "wikilink"):
            etype = "ref"
        force = EDGE_FORCE.get(etype, EDGE_FORCE["ref"])

        # Edge styling
        if etype == "parent":
            color, width, dash = "#3b82f6", 2.5, ""
        elif etype == "depends_on":
            color, width, dash = "#ef4444", 2.0, ""
        else:  # ref
            color, width, dash = "#94a3b8", 1.0, "4,3"

        d3_links.append(
            {
                "source": edge["source"],
                "target": edge["target"],
                "type": etype,
                "color": color,
                "width": width,
                "dash": dash,
                "strength": force["strength"],
                "distance": force["distance"],
            }
        )

    return {"nodes": d3_nodes, "links": d3_links}


def generate_html(graph_data: dict, title: str = "Task Graph", theme: str = "dark") -> str:
    """Generate self-contained HTML with d3-force visualization."""
    data_json = json.dumps(graph_data, separators=(",", ":"))

    is_dark = theme == "dark"
    bg = "#0f172a" if is_dark else "#f8fafc"
    panel_bg = "rgba(15,23,42,0.95)" if is_dark else "rgba(255,255,255,0.97)"
    panel_border = "#334155" if is_dark else "#e2e8f0"
    panel_text = "#e2e8f0" if is_dark else "#1e293b"
    muted = "#94a3b8" if is_dark else "#64748b"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: {bg}; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; overflow: hidden; }}
#graph {{ width: 100vw; height: 100vh; }}
svg {{ width: 100%; height: 100%; }}
.node-text {{ pointer-events: none; user-select: none; }}
.node-badge {{ pointer-events: none; user-select: none; }}

#legend {{
  position: fixed; top: 16px; left: 16px; z-index: 10;
  background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 12px;
  padding: 16px 20px; font-size: 11px; max-width: 220px; color: {panel_text};
  backdrop-filter: blur(12px); box-shadow: 0 4px 24px rgba(0,0,0,0.12);
}}
#legend h3 {{ font-size: 14px; margin-bottom: 10px; font-weight: 700; letter-spacing: -0.3px; }}
#legend .section {{ margin-bottom: 10px; }}
#legend .st {{ font-weight: 600; color: {muted}; text-transform: uppercase; font-size: 9px; letter-spacing: 0.8px; margin-bottom: 5px; }}
#legend .row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; line-height: 1.4; }}
#legend .sw {{ width: 18px; height: 12px; border-radius: 3px; flex-shrink: 0; border: 1px solid rgba(0,0,0,0.08); }}
#legend-toggle {{
  position: fixed; top: 16px; left: 16px; z-index: 11;
  background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 8px;
  padding: 6px 14px; font-size: 12px; cursor: pointer; color: {panel_text};
  display: none; font-family: inherit;
}}

#detail {{
  position: fixed; top: 16px; right: 16px; z-index: 10;
  background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 12px;
  padding: 20px; font-size: 12px; max-width: 340px; min-width: 260px; color: {panel_text};
  backdrop-filter: blur(12px); display: none; box-shadow: 0 4px 24px rgba(0,0,0,0.15);
}}
#detail h3 {{ font-size: 15px; margin-bottom: 12px; word-break: break-word; font-weight: 600; line-height: 1.35; padding-right: 24px; }}
#detail .f {{ margin-bottom: 6px; }}
#detail .fl {{ color: {muted}; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }}
#detail .fv {{ font-weight: 500; margin-top: 1px; }}
#detail .cb {{ position: absolute; top: 12px; right: 16px; cursor: pointer; font-size: 18px; color: {muted}; background: none; border: none; }}
#detail .cb:hover {{ color: {panel_text}; }}
#detail .nb {{ margin-top: 12px; max-height: 200px; overflow-y: auto; }}
#detail .ni {{ padding: 3px 0; cursor: pointer; color: #3b82f6; font-size: 11px; }}
#detail .ni:hover {{ text-decoration: underline; }}
#detail .sb {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; text-transform: uppercase; }}

#stats {{
  position: fixed; bottom: 12px; left: 50%; transform: translateX(-50%); z-index: 10;
  background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 8px;
  padding: 6px 18px; font-size: 11px; color: {muted};
  backdrop-filter: blur(12px); letter-spacing: 0.2px;
}}
</style>
</head>
<body>
<div id="graph"></div>

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
    <div class="row"><svg width="20" height="14"><rect x="1" y="1" width="18" height="12" rx="7" fill="none" stroke="{panel_text}" stroke-width="1"/></svg> Goal</div>
    <div class="row"><svg width="20" height="14"><rect x="1" y="1" width="18" height="12" rx="4" fill="none" stroke="{panel_text}" stroke-width="1"/></svg> Project</div>
    <div class="row"><svg width="20" height="14"><polygon points="4,1 16,1 19,7 16,13 4,13 1,7" fill="none" stroke="{panel_text}" stroke-width="1"/></svg> Epic</div>
    <div class="row"><svg width="20" height="14"><rect x="1" y="1" width="18" height="12" rx="1" fill="none" stroke="{panel_text}" stroke-width="1"/></svg> Task</div>
  </div>
  <div class="section">
    <div class="st">Size</div>
    <div style="color:{muted};line-height:1.5;font-size:10px">Bigger = more downstream impact</div>
  </div>
  <div class="section">
    <div class="st">Edges</div>
    <div class="row"><svg width="24" height="8"><path d="M0,4 C6,0 18,0 24,4" stroke="#3b82f6" stroke-width="2.5" fill="none"/></svg> Parent</div>
    <div class="row"><svg width="24" height="8"><path d="M0,4 L8,4 L8,4 L16,4 L16,4 L24,4" stroke="#ef4444" stroke-width="2" fill="none"/></svg> Dependency</div>
    <div class="row"><svg width="24" height="8"><line x1="0" y1="4" x2="24" y2="4" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4,3"/></svg> Reference</div>
  </div>
  <div class="section">
    <div class="st">Controls</div>
    <div style="color:{muted};line-height:1.5;font-size:10px">
      Drag &middot; Scroll to zoom &middot; Hover &middot; Click
    </div>
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
const W = window.innerWidth, H = window.innerHeight;
const maxDepth = nodes.reduce((m, n) => Math.max(m, n.maxDepth), 0);

// ---- SVG ----
const svg = d3.select("#graph").append("svg").attr("viewBox", [0, 0, W, H]);
const defs = svg.append("defs");

// Shadow
const filt = defs.append("filter").attr("id", "sh").attr("x", "-20%").attr("y", "-20%").attr("width", "140%").attr("height", "140%");
filt.append("feDropShadow").attr("dx", 0).attr("dy", 1).attr("stdDeviation", 2.5).attr("flood-color", "rgba(0,0,0,0.1)");

// Arrows
[["ap","#3b82f6"],["ad","#ef4444"],["ar","#94a3b8"]].forEach(([id,c]) => {{
  defs.append("marker").attr("id",id).attr("viewBox","0 -4 8 8")
    .attr("refX",8).attr("refY",0).attr("markerWidth",5).attr("markerHeight",5).attr("orient","auto")
    .append("path").attr("d","M0,-3L8,0L0,3").attr("fill",c);
}});
const mMap = {{ parent:"ap", depends_on:"ad", ref:"ar" }};

const container = svg.append("g");
const zoom = d3.zoom().scaleExtent([0.03,8]).on("zoom", e => container.attr("transform", e.transform));
svg.call(zoom);

// ---- Adjacency ----
const adj = new Map();
nodes.forEach(n => adj.set(n.id, new Set()));
links.forEach(l => {{
  const s = typeof l.source === "object" ? l.source.id : l.source;
  const t = typeof l.target === "object" ? l.target.id : l.target;
  if (adj.has(s)) adj.get(s).add(t);
  if (adj.has(t)) adj.get(t).add(s);
}});

// ---- Links ----
const linkG = container.append("g");
const linkEls = linkG.selectAll("path").data(links).join("path")
  .attr("fill","none").attr("stroke", d => d.color).attr("stroke-width", d => d.width)
  .attr("stroke-dasharray", d => d.dash || null)
  .attr("marker-end", d => `url(#${{mMap[d.type]||"ar"}})`)
  .attr("opacity", d => d.type === "ref" ? 0.3 : 0.55)
  .attr("stroke-linecap","round").attr("stroke-linejoin","round");

// ---- Nodes ----
const nodeG = container.append("g");
const nodeEls = nodeG.selectAll("g").data(nodes).join("g")
  .attr("cursor","pointer")
  .call(d3.drag().on("start",ds).on("drag",dr).on("end",de));

// Shape builders
function hexPoints(w, h) {{
  const hw = w/2, hh = h/2, c = Math.min(hh * 0.6, 12);
  return `${{-hw+c}},${{-hh}} ${{hw-c}},${{-hh}} ${{hw}},${{0}} ${{hw-c}},${{hh}} ${{-hw+c}},${{hh}} ${{-hw}},${{0}}`;
}}

nodeEls.each(function(d) {{
  const g = d3.select(this);
  const hw = d.w/2, hh = d.h/2;

  // Shape
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

  // Stakeholder glow
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

  // Badge
  if (d.badge) {{
    const bw = d.badge.length * 5.2 + 8;
    g.append("rect").attr("x",-hw+4).attr("y",-hh+4).attr("width",bw).attr("height",12)
      .attr("rx",2).attr("fill",d.borderColor).attr("opacity",0.18);
    g.append("text").attr("class","node-badge")
      .attr("x",-hw+4+bw/2).attr("y",-hh+12.5).attr("text-anchor","middle")
      .attr("font-size","6.5px").attr("font-weight","700").attr("fill",d.borderColor)
      .attr("letter-spacing","0.6px").text(d.badge);
  }}

  // Text
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

  // Weight pill
  if (d.dw > 0) {{
    const t = d.dw.toFixed(1), tw = t.length * 5 + 12;
    g.append("rect").attr("x",-tw/2).attr("y",hh+3).attr("width",tw).attr("height",13)
      .attr("rx",6).attr("fill",d.borderColor).attr("opacity",0.13);
    g.append("text").attr("class","node-badge").attr("x",0).attr("y",hh+12)
      .attr("text-anchor","middle").attr("font-size","7.5px").attr("font-weight","600")
      .attr("fill",d.borderColor).text("\u2696 "+t);
  }}
}});

// ---- Force ----
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

// ---- Edge paths ----
// Rect intersection helper
function ri(cx,cy,w,h,px,py) {{
  const dx=px-cx, dy=py-cy;
  if (dx===0 && dy===0) return [cx,cy];
  const hw=w/2+3, hh=h/2+3;
  const t = Math.abs(dx)*hh > Math.abs(dy)*hw ? hw/Math.abs(dx) : hh/Math.abs(dy);
  return [cx+dx*t, cy+dy*t];
}}

// Manhattan routing: H-V-H or V-H-V depending on relative position
function manhattan(sx,sy,sw,sh,tx,ty,tw,th) {{
  const dx = tx-sx, dy = ty-sy;
  const m = 20; // bend margin from node edge

  if (Math.abs(dx) >= Math.abs(dy)) {{
    // Mostly horizontal: exit left/right side, route H-V-H
    const exitX = dx > 0 ? sx + sw/2 + 3 : sx - sw/2 - 3;
    const enterX = dx > 0 ? tx - tw/2 - 3 : tx + tw/2 + 3;
    const midX = (exitX + enterX) / 2;
    return `M${{exitX}},${{sy}} L${{midX}},${{sy}} L${{midX}},${{ty}} L${{enterX}},${{ty}}`;
  }} else {{
    // Mostly vertical: exit top/bottom, route V-H-V
    const exitY = dy > 0 ? sy + sh/2 + 3 : sy - sh/2 - 3;
    const enterY = dy > 0 ? ty - th/2 - 3 : ty + th/2 + 3;
    const midY = (exitY + enterY) / 2;
    return `M${{sx}},${{exitY}} L${{sx}},${{midY}} L${{tx}},${{midY}} L${{tx}},${{enterY}}`;
  }}
}}

function edgePath(d) {{
  const s=d.source, t=d.target;
  if (d.type === "parent") {{
    // S-curve for hierarchy
    const [bx,by] = ri(s.x,s.y,s.w,s.h,t.x,t.y);
    const [ex,ey] = ri(t.x,t.y,t.w,t.h,s.x,s.y);
    const midY = (by+ey)/2;
    return `M${{bx}},${{by}} C${{bx}},${{midY}} ${{ex}},${{midY}} ${{ex}},${{ey}}`;
  }}
  // Manhattan for deps and refs
  return manhattan(s.x,s.y,s.w,s.h,t.x,t.y,t.w,t.h);
}}

// Warm up
sim.tick(300);
nodeEls.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
linkEls.attr("d", edgePath);
sim.on("tick", () => {{ linkEls.attr("d", edgePath); nodeEls.attr("transform", d => `translate(${{d.x}},${{d.y}})`); }});

// Fit
const b = container.node().getBBox();
if (b.width > 0) {{
  const sc = Math.min(W/(b.width+80), H/(b.height+80), 1.5) * 0.85;
  svg.call(zoom.transform, d3.zoomIdentity.translate(W/2,H/2).scale(sc).translate(-b.x-b.width/2,-b.y-b.height/2));
}}

// ---- Drag ----
function ds(e,d) {{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }}
function dr(e,d) {{ d.fx=e.x; d.fy=e.y; }}
function de(e,d) {{ if(!e.active) sim.alphaTarget(0); }}
nodeEls.on("dblclick",(e,d)=>{{ d.fx=null; d.fy=null; sim.alphaTarget(0.1).restart(); setTimeout(()=>sim.alphaTarget(0),500); }});

// ---- Hover ----
nodeEls.on("mouseenter",(e,d)=>{{
  const c = adj.get(d.id) || new Set();
  nodeEls.transition().duration(120).attr("opacity", n => (n.id===d.id||c.has(n.id)) ? 1 : 0.1);
  linkEls.transition().duration(120).attr("opacity", l => (l.source.id===d.id||l.target.id===d.id) ? 0.85 : 0.03);
}}).on("mouseleave",()=>{{
  nodeEls.transition().duration(180).attr("opacity",1);
  linkEls.transition().duration(180).attr("opacity", d => d.type==="ref" ? 0.3 : 0.55);
}});

// ---- Detail ----
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
    d.dw>0?["Impact","\u2696 "+d.dw.toFixed(1)]:null,
    d.stakeholder?["Stakeholder","Yes"]:null,
    d.assignee?["Assignee",d.assignee]:null, ["ID",d.id],
  ].filter(Boolean);
  h += fs.map(([l,v])=>`<div class="f"><span class="fl">${{l}}</span><br><span class="fv">${{v}}</span></div>`).join("");
  document.getElementById("df").innerHTML = h;

  const nb = adj.get(d.id)||new Set();
  const it = [...nb].map(id=>{{ const n=nMap.get(id); return n?`<div class="ni" onclick="focusN('${{id}}')">${{n.label}} <span style="opacity:0.4;font-size:9px">${{n.badge||n.type}}</span></div>`:""; }}).join("");
  document.getElementById("dn").innerHTML = nb.size>0 ? `<div class="st" style="color:{muted};font-size:9px;margin-top:4px;margin-bottom:4px">Connected (${{nb.size}})</div>${{it}}` : "";
  document.getElementById("detail").style.display = "block";
}}
function closeD() {{ document.getElementById("detail").style.display="none"; }}
window.focusN = function(id) {{
  const n = nodes.find(n=>n.id===id); if(!n) return;
  showD(n);
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(W/2,H/2).scale(1.5).translate(-n.x,-n.y));
}};

// ---- Legend toggle ----
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
  `${{nodes.length}} nodes \u00b7 ${{links.length}} edges \u00b7 drag \u00b7 scroll \u00b7 hover \u00b7 click`;
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate interactive D3-force task graph from fast-indexer JSON"
    )
    parser.add_argument("input", help="Input JSON file from fast-indexer")
    parser.add_argument("-o", "--output", default="task-map.html", help="Output HTML file")
    parser.add_argument(
        "--filter",
        choices=["smart", "rollup", "reachable", "none"],
        default="reachable",
        help="Filter type (default: reachable)",
    )
    parser.add_argument("--include-orphans", action="store_true", help="Include unconnected nodes")
    parser.add_argument("--ego", metavar="ID", help="Extract ego-subgraph centered on this node")
    parser.add_argument("--depth", type=int, default=2, help="Ego-subgraph depth (default: 2)")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark", help="Color theme")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    with open(input_path) as f:
        data = json.load(f)

    all_nodes = [n for n in data["nodes"] if n.get("status", "").lower() != "cancelled"]
    node_ids = {n["id"] for n in all_nodes}
    all_edges = [e for e in data["edges"] if e["source"] in node_ids and e["target"] in node_ids]

    print(f"Loaded {len(all_nodes)} nodes, {len(all_edges)} edges from {input_path}")

    if args.ego:
        all_nodes, all_edges = extract_ego_subgraph(all_nodes, all_edges, args.ego, args.depth)
        if not all_nodes:
            return 1
        print(f"Ego subgraph: {len(all_nodes)} nodes, {len(all_edges)} edges")

    structural_ids: set[str] = set()
    original_count = len(all_nodes)
    if args.filter == "smart":
        all_nodes, structural_ids = filter_completed_smart(all_nodes, all_edges)
    elif args.filter == "rollup":
        all_nodes, structural_ids = filter_rollup(all_nodes, all_edges)
    elif args.filter == "reachable":
        all_nodes, structural_ids = filter_reachable(all_nodes, all_edges)

    excluded = original_count - len(all_nodes)
    if excluded > 0 or structural_ids:
        print(f"Filtered: {excluded} removed, {len(structural_ids)} structural kept")

    if not args.include_orphans:
        connected = set()
        for e in all_edges:
            connected.add(e["source"])
            connected.add(e["target"])
        all_nodes = [n for n in all_nodes if n["id"] in connected]
        print(f"After orphan removal: {len(all_nodes)} nodes")

    graph_data = prepare_graph_data(all_nodes, all_edges, structural_ids)

    output_path = args.output if args.output.endswith(".html") else args.output + ".html"
    html = generate_html(graph_data, title="Task Graph", theme=args.theme)
    Path(output_path).write_text(html)
    print(
        f"Written {output_path} ({len(graph_data['nodes'])} nodes, {len(graph_data['links'])} edges)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
