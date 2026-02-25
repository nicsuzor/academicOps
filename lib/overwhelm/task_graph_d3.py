import json

import streamlit.components.v1 as components


def generate_graph_from_tasks(tasks: list) -> dict:
    """Convert tasks into a D3-compatible node/link structure."""
    nodes = []
    links = []

    # Track existing nodes to avoid duplicates and missing targets
    node_ids = set()

    # First pass: create nodes
    for t in tasks:
        # Handle both dict and Task object
        tid = t.get("id") if isinstance(t, dict) else t.id
        title = t.get("title") if isinstance(t, dict) else t.title
        status = t.get("status") if isinstance(t, dict) else (t.status.value if hasattr(t.status, "value") else t.status)
        priority = t.get("priority") if isinstance(t, dict) else t.priority
        project = t.get("project") if isinstance(t, dict) else t.project
        type_ = t.get("type") if isinstance(t, dict) else (t.type.value if hasattr(t.type, "value") else t.type)

        nodes.append({
            "id": tid,
            "title": title,
            "status": status,
            "priority": priority,
            "project": project,
            "type": type_
        })
        node_ids.add(tid)

    # Second pass: create links
    for t in tasks:
        tid = t.get("id") if isinstance(t, dict) else t.id

        # Depends on -> Link (target depends on source, so source -> target flow usually means dependency flow)
        deps = t.get("depends_on") if isinstance(t, dict) else t.depends_on
        if deps:
            for dep in deps:
                if dep in node_ids:
                    links.append({"source": dep, "target": tid, "type": "dependency"})

        parent = t.get("parent") if isinstance(t, dict) else t.parent
        if parent and parent in node_ids:
            links.append({"source": parent, "target": tid, "type": "parent"})

    return {"nodes": nodes, "links": links}

def render_d3_graph(graph_data: dict, width: int = None, height: int = 400, mode: str = "summary"):
    """
    Render a D3.js force-directed graph.

    Args:
        graph_data: Dict with 'nodes' and 'links'.
        width: Width in pixels (None = 100%).
        height: Height in pixels.
        mode: 'summary' (static, simple) or 'full' (interactive, controls).
    """

    nodes_json = json.dumps(graph_data.get("nodes", []))
    links_json = json.dumps(graph_data.get("links", []))

    # Adjust physics parameters based on mode
    charge_strength = -100 if mode == "summary" else -200
    link_distance = 30 if mode == "summary" else 50
    node_radius = 4 if mode == "summary" else 6

    # For full mode, enable zoom and click-to-select
    enable_zoom = "true" if mode == "full" else "false"
    enable_drag = "true" if mode == "full" else "false"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            body {{ margin: 0; background-color: #0e1117; overflow: hidden; font-family: sans-serif; }}
            svg {{ display: block; width: 100%; height: {height}px; }}
            .node {{ stroke: #fff; stroke-width: 1.0px; cursor: pointer; }}
            .link {{ stroke: #999; stroke-opacity: 0.6; }}
            .label {{ fill: #ccc; font-size: 10px; pointer-events: none; }}
            .tooltip {{
                position: absolute;
                text-align: center;
                padding: 6px;
                font: 12px sans-serif;
                background: #333;
                color: #fff;
                border: 0px;
                border-radius: 4px;
                pointer-events: none;
                opacity: 0;
            }}
        </style>
    </head>
    <body>
        <div id="graph"></div>
        <div id="tooltip" class="tooltip"></div>
        <script>
            const width = window.innerWidth;
            const height = {height};

            const nodes = {nodes_json};
            const links = {links_json};

            const svg = d3.select("#graph").append("svg")
                .attr("width", "100%")
                .attr("height", height)
                .attr("viewBox", [0, 0, width, height]);

            const g = svg.append("g");

            // Zoom behavior
            if ({enable_zoom}) {{
                svg.call(d3.zoom()
                    .extent([[0, 0], [width, height]])
                    .scaleExtent([0.1, 8])
                    .on("zoom", ({{transform}}) => g.attr("transform", transform)));
            }}

            const simulation = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(links).id(d => d.id).distance({link_distance}))
                .force("charge", d3.forceManyBody().strength({charge_strength}))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collide", d3.forceCollide().radius({node_radius} + 2));

            const link = g.append("g")
                .attr("stroke", "#999")
                .attr("stroke-opacity", 0.6)
                .selectAll("line")
                .data(links)
                .join("line")
                .attr("stroke-width", d => Math.sqrt(d.value || 1));

            const node = g.append("g")
                .selectAll("circle")
                .data(nodes)
                .join("circle")
                .attr("r", {node_radius})
                .attr("fill", d => getNodeColor(d))
                .attr("class", "node");

            if ({enable_drag}) {{
                node.call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            }}

            node.on("mouseover", (event, d) => {{
                d3.select("#tooltip")
                    .style("opacity", .9)
                    .html("<b>" + d.id + "</b><br/>" + d.title)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", (event, d) => {{
                d3.select("#tooltip").style("opacity", 0);
            }})
            .on("click", (event, d) => {{
                if ("{mode}" === "full") {{
                    // Update URL query param to select node
                    const url = new URL(window.parent.location);
                    url.searchParams.set("node_id", d.id);
                    window.parent.location.href = url.toString();
                }}
            }});

            simulation.on("tick", () => {{
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
            }});

            function getNodeColor(d) {{
                const statusColors = {{
                    "done": "#22c55e",
                    "active": "#3b82f6",
                    "blocked": "#ef4444",
                    "waiting": "#eab308",
                    "review": "#a855f7",
                    "cancelled": "#64748b",
                    "in_progress": "#f59e0b"
                }};
                return statusColors[d.status] || "#94a3b8";
            }}

            function dragstarted(event) {{
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }}

            function dragged(event) {{
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }}

            function dragended(event) {{
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }}
        </script>
    </body>
    </html>
    """

    components.html(html, height=height)
