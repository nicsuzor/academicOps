#!/usr/bin/env python3
"""Compute force-directed layout for task visualization graph.

Uses networkx spring_layout (Fruchterman-Reingold) to compute
non-overlapping positions for goals, projects, and tasks.

Usage:
    python layout_task_graph.py input.json output.json

Input format:
    {
        "goals": [{"id": "g1", "title": "Goal Name"}, ...],
        "projects": [{"id": "p1", "title": "Project", "goal": "g1"}, ...],
        "tasks": [{"id": "t1", "title": "Task", "project": "p1", "priority": 1}, ...]
    }

Output format:
    {
        "nodes": [
            {"id": "g1", "type": "goal", "title": "...", "x": 100, "y": 200, "width": 300, "height": 100},
            ...
        ],
        "edges": [
            {"source": "p1", "target": "g1"},
            ...
        ]
    }
"""

import json
import sys
from pathlib import Path
from typing import Any

import networkx as nx


def compute_node_size(node_type: str, title: str) -> tuple[int, int]:
    """Compute box dimensions based on type and title length.

    Returns (width, height).
    """
    if node_type == "goal":
        font_size = 48
        min_width, height = 300, 120
    elif node_type == "project":
        font_size = 28
        min_width, height = 200, 80
    else:  # task
        font_size = 18
        min_width, height = 150, 60

    # Estimate text width: ~0.55 * font_size per character
    text_width = len(title) * font_size * 0.55
    width = max(min_width, int(text_width) + 40)  # 40px padding

    return width, height


def build_graph(data: dict[str, Any]) -> nx.Graph:
    """Build networkx graph from task data."""
    G = nx.Graph()

    # Add goal nodes
    for goal in data.get("goals", []):
        G.add_node(goal["id"], type="goal", title=goal["title"])

    # Add project nodes and edges to goals
    for project in data.get("projects", []):
        G.add_node(project["id"], type="project", title=project["title"])
        if project.get("goal"):
            G.add_edge(project["id"], project["goal"], weight=3.0)  # Strong connection

    # Add task nodes and edges to projects
    for task in data.get("tasks", []):
        G.add_node(task["id"], type="task", title=task["title"],
                   priority=task.get("priority", 2))
        if task.get("project"):
            G.add_edge(task["id"], task["project"], weight=1.0)  # Lighter connection

    return G


def compute_layout(G: nx.Graph, scale: float = 2000) -> dict[str, tuple[float, float]]:
    """Compute force-directed layout.

    Args:
        G: NetworkX graph
        scale: Canvas scale in pixels

    Returns:
        Dict mapping node_id to (x, y) position
    """
    if len(G.nodes()) == 0:
        return {}

    # Use spring layout with weights
    # k controls optimal distance between nodes
    # iterations for convergence
    pos = nx.spring_layout(
        G,
        k=2.5,  # Increase spacing
        iterations=100,
        scale=scale,
        seed=42  # Reproducible
    )

    # Convert numpy arrays to tuples and center on canvas
    return {node: (float(x), float(y)) for node, (x, y) in pos.items()}


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python layout_task_graph.py input.json output.json")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    # Load input data
    data = json.loads(input_path.read_text())

    # Build graph
    G = build_graph(data)

    # Compute layout
    positions = compute_layout(G)

    # Build output with positions and sizes
    nodes = []
    for node_id in G.nodes():
        node_data = G.nodes[node_id]
        x, y = positions.get(node_id, (0, 0))
        width, height = compute_node_size(node_data["type"], node_data["title"])

        nodes.append({
            "id": node_id,
            "type": node_data["type"],
            "title": node_data["title"],
            "x": x,  # Will normalize below
            "y": y,
            "width": width,
            "height": height,
            "priority": node_data.get("priority"),
        })

    # Normalize coordinates to positive values with 100px margin
    if nodes:
        min_x = min(n["x"] for n in nodes)
        min_y = min(n["y"] for n in nodes)
        for n in nodes:
            n["x"] = int(n["x"] - min_x + 100)
            n["y"] = int(n["y"] - min_y + 100)

    # Build edges
    edges = [{"source": u, "target": v} for u, v in G.edges()]

    # Output
    output = {"nodes": nodes, "edges": edges}
    output_path.write_text(json.dumps(output, indent=2))

    print(f"✅ Layout computed: {len(nodes)} nodes, {len(edges)} edges")
    print(f"   Canvas: ~{int(max(n['x'] for n in nodes) - min(n['x'] for n in nodes))}x"
          f"{int(max(n['y'] for n in nodes) - min(n['y'] for n in nodes))} px")

    return 0


if __name__ == "__main__":
    sys.exit(main())
