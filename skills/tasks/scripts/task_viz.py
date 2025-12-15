#!/usr/bin/env python3
"""Generate task visualization with force-directed layout.

Reads tasks from data/tasks/inbox/, computes layout using networkx,
and outputs a valid excalidraw JSON file.

Usage:
    python task_viz_layout.py /path/to/writing/repo output.excalidraw
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import networkx as nx
import yaml


# Colors by goal/status
GOAL_COLORS = {
    "world-class-academic-profile": {"bg": "#d4edda", "stroke": "#28a745"},
    "tangible-accountability-wins": {"bg": "#cce5ff", "stroke": "#004085"},
    "get-paid": {"bg": "#e2d5f1", "stroke": "#6f42c1"},
    "be-happy-and-do-fun-things": {"bg": "#fff3cd", "stroke": "#856404"},
    "default": {"bg": "#f8f9fa", "stroke": "#6c757d"},
}

PRIORITY_COLORS = {
    0: {"bg": "#f8d7da", "stroke": "#721c24"},  # P0 - red
    1: {"bg": "#ffe5d0", "stroke": "#fd7e14"},  # P1 - orange
    2: {"bg": "#fff3cd", "stroke": "#856404"},  # P2 - yellow
    3: {"bg": "#e9ecef", "stroke": "#6c757d"},  # P3 - gray
}


def parse_task_file(path: Path) -> dict[str, Any] | None:
    """Parse a task markdown file."""
    content = path.read_text()

    # Extract YAML frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None

    if not fm:
        return None

    return {
        "id": path.stem,
        "title": fm.get("title", path.stem)[:50],  # Truncate long titles
        "project": fm.get("project", "uncategorized"),
        "priority": fm.get("priority", 2),
        "status": fm.get("status", "inbox"),
    }


def discover_tasks(repo_path: Path) -> list[dict]:
    """Find all tasks in inbox."""
    inbox = repo_path / "tasks" / "inbox"
    if not inbox.exists():
        raise FileNotFoundError(f"Task inbox not found: {inbox}")

    tasks = []
    for f in inbox.glob("*.md"):
        if f.name == "CLAUDE.md":
            continue
        task = parse_task_file(f)
        if task:
            tasks.append(task)

    return tasks


def discover_goals(repo_path: Path) -> tuple[list[dict], dict[str, str]]:
    """Find goals from goal files.

    Returns:
        Tuple of (goals list, title_to_id mapping)
        - goals: List of {"id": permalink, "title": title}
        - title_to_id: Dict mapping goal title to goal id/permalink
    """
    goals_dir = repo_path / "goals"
    goals = []
    title_to_id = {}

    if goals_dir.exists():
        for f in goals_dir.glob("*.md"):
            content = f.read_text()
            match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if match:
                try:
                    fm = yaml.safe_load(match.group(1))
                    if fm and fm.get("title"):
                        goal_id = fm.get("permalink", f.stem)
                        goal_title = fm["title"]
                        goals.append({
                            "id": goal_id,
                            "title": goal_title,
                        })
                        title_to_id[goal_title] = goal_id
                except yaml.YAMLError:
                    pass

    # Default goals if none found
    if not goals:
        goals = [
            {"id": "academic", "title": "World-Class Academic Profile"},
            {"id": "accountability", "title": "Tangible Accountability Wins"},
            {"id": "paid", "title": "Get Paid"},
            {"id": "happy", "title": "Be Happy"},
        ]
        for g in goals:
            title_to_id[g["title"]] = g["id"]

    return goals, title_to_id


def discover_projects(repo_path: Path, goal_title_to_id: dict[str, str]) -> tuple[dict[str, dict], dict[str, str]]:
    """Find projects and their goal mappings from project files.

    Reads goal relationships from the ## Relations section of project files,
    looking for 'supports [[Goal Title]]' links. Also builds alias mapping.

    Args:
        repo_path: Path to repository root
        goal_title_to_id: Mapping from goal title to goal id/permalink

    Returns:
        Tuple of (projects dict, alias_to_permalink mapping)
    """
    projects_dir = repo_path / "projects"
    projects = {}
    alias_to_permalink = {}

    if projects_dir.exists():
        # Find both projects/*.md and projects/<slug>/<slug>.md
        project_files = list(projects_dir.glob("*.md"))
        for subdir in projects_dir.iterdir():
            if subdir.is_dir():
                slug_file = subdir / f"{subdir.name}.md"
                if slug_file.exists():
                    project_files.append(slug_file)

        for f in project_files:
            content = f.read_text()

            # Extract YAML frontmatter
            fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if not fm_match:
                continue

            try:
                fm = yaml.safe_load(fm_match.group(1))
            except yaml.YAMLError:
                continue

            if not fm:
                continue

            slug = fm.get("permalink", f.stem)
            title = fm.get("title", slug)

            # Build alias mapping
            aliases = fm.get("aliases", [])
            if aliases:
                for alias in aliases:
                    alias_to_permalink[alias] = slug

            # Parse Relations section for goal links
            goal_id = None
            relations_match = re.search(r'## Relations\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
            if relations_match:
                relations_text = relations_match.group(1)
                # Look for "supports [[Goal Title]]" pattern
                supports_matches = re.findall(r'-\s*supports\s+\[\[([^\]]+)\]\]', relations_text)
                for goal_title in supports_matches:
                    # Map goal title to goal id
                    if goal_title in goal_title_to_id:
                        goal_id = goal_title_to_id[goal_title]
                        break  # Take first matching goal

            projects[slug] = {
                "id": slug,
                "title": title,
                "goal": goal_id,
            }

    return projects, alias_to_permalink


def build_graph(goals: list, projects: list, tasks: list) -> nx.Graph:
    """Build networkx graph."""
    G = nx.Graph()

    for goal in goals:
        G.add_node(goal["id"], type="goal", title=goal["title"])

    for proj in projects:
        G.add_node(proj["id"], type="project", title=proj["title"])
        if proj.get("goal"):
            G.add_edge(proj["id"], proj["goal"], weight=5.0)

    for task in tasks:
        G.add_node(task["id"], type="task", title=task["title"],
                   priority=task.get("priority", 2))
        proj_id = task.get("project", "uncategorized")
        if proj_id and G.has_node(proj_id):
            G.add_edge(task["id"], proj_id, weight=6.0)  # Strong attraction to project

    return G


def compute_layout(G: nx.Graph) -> dict[str, tuple[float, float]]:
    """Compute force-directed layout."""
    if len(G.nodes()) == 0:
        return {}

    # k=1.8 balanced spacing, high weight pulls tasks to projects
    pos = nx.spring_layout(G, k=1.8, iterations=300, scale=3500, seed=42, weight='weight')

    # Normalize to positive coords
    if pos:
        min_x = min(p[0] for p in pos.values())
        min_y = min(p[1] for p in pos.values())
        pos = {n: (x - min_x + 100, y - min_y + 100) for n, (x, y) in pos.items()}

    return pos


def node_size(node_type: str, title: str) -> tuple[int, int]:
    """Get node dimensions - large gradation between types."""
    if node_type == "goal":
        font = 48
        min_w, h = 350, 140  # Much larger for goals
    elif node_type == "project":
        font = 24
        min_w, h = 180, 70
    else:  # task
        font = 14
        min_w, h = 120, 40  # Smaller for tasks

    text_w = len(title) * font * 0.5
    return max(min_w, int(text_w) + 30), h


def make_excalidraw_element(
    elem_id: str,
    elem_type: str,
    x: float,
    y: float,
    width: int,
    height: int,
    bg_color: str,
    stroke_color: str,
) -> dict:
    """Create excalidraw rectangle/ellipse element."""
    seed = hash(elem_id) % 2000000000
    return {
        "id": elem_id,
        "type": "ellipse" if elem_type == "goal" else "rectangle",
        "x": int(x),
        "y": int(y),
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": stroke_color,
        "backgroundColor": bg_color,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 3} if elem_type != "goal" else {"type": 2},
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": [{"id": f"text-{elem_id}", "type": "text"}],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }


def make_text_element(
    container_id: str,
    text: str,
    x: float,
    y: float,
    width: int,
    height: int,
    font_size: int,
) -> dict:
    """Create text element bound to container."""
    seed = hash(f"text-{container_id}") % 2000000000
    return {
        "id": f"text-{container_id}",
        "type": "text",
        "x": int(x) + 10,
        "y": int(y) + height // 2 - font_size // 2,
        "width": width - 20,
        "height": font_size + 10,
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
        "text": text,
        "fontSize": font_size,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "baseline": font_size,
        "containerId": container_id,
        "originalText": text,
        "lineHeight": 1.25,
        "autoResize": True,
    }


def make_arrow(source_id: str, target_id: str, positions: dict, sizes: dict) -> dict:
    """Create arrow between two elements."""
    sx, sy = positions[source_id]
    tx, ty = positions[target_id]
    sw, sh = sizes[source_id]
    tw, th = sizes[target_id]

    # Arrow from center of source to center of target
    seed = hash(f"arrow-{source_id}-{target_id}") % 2000000000

    return {
        "id": f"arrow-{source_id}-{target_id}",
        "type": "arrow",
        "x": int(sx + sw / 2),
        "y": int(sy + sh / 2),
        "width": int(tx - sx),
        "height": int(ty - sy),
        "angle": 0,
        "strokeColor": "#868e96",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 60,
        "groupIds": [],
        "roundness": {"type": 2},
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
        "points": [[0, 0], [int(tx - sx), int(ty - sy)]],
        "lastCommittedPoint": None,
        "startBinding": {"elementId": source_id, "focus": 0, "gap": 5},
        "endBinding": {"elementId": target_id, "focus": 0, "gap": 5},
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python task_viz_layout.py /path/to/repo output.excalidraw")
        return 1

    repo_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    # Discover data
    print("Discovering tasks...")
    tasks = discover_tasks(repo_path)
    print(f"  Found {len(tasks)} tasks")

    goals, goal_title_to_id = discover_goals(repo_path)
    print(f"  Found {len(goals)} goals")

    # Get projects with goal mappings (reads from Relations section)
    known_projects, alias_to_permalink = discover_projects(repo_path, goal_title_to_id)
    print(f"  Found {len(alias_to_permalink)} project aliases")

    # Normalize task project references using aliases
    for task in tasks:
        proj_slug = task.get("project", "uncategorized")
        if proj_slug in alias_to_permalink:
            task["project"] = alias_to_permalink[proj_slug]

    # Extract unique projects from tasks, merge with known
    project_ids = set(t.get("project", "uncategorized") for t in tasks)
    projects = []
    unmapped_projects = []  # Projects with no goal link
    unknown_projects = []   # Project slugs not in data/projects/
    for p in project_ids:
        if p in known_projects:
            proj = known_projects[p]
            projects.append(proj)
            if proj["goal"] is None:
                unmapped_projects.append(p)
        else:
            projects.append({"id": p, "title": p, "goal": None})
            unknown_projects.append(p)

    print(f"  Found {len(projects)} projects")
    if unmapped_projects:
        print(f"  ⚠️  {len(unmapped_projects)} projects missing goal link: {unmapped_projects[:5]}")
    if unknown_projects:
        print(f"  ⚠️  {len(unknown_projects)} unknown project slugs: {unknown_projects}")

    # Build and layout graph
    print("Computing layout...")
    G = build_graph(goals, projects, tasks)
    positions = compute_layout(G)

    # Generate excalidraw elements
    print("Generating excalidraw...")
    elements = []
    sizes = {}

    # Add timestamp
    ts_text = f"Generated: {time.strftime('%Y-%m-%d @ %H:%M')}"
    max_x = max(p[0] for p in positions.values()) if positions else 1000
    elements.append({
        "id": "timestamp",
        "type": "text",
        "x": int(max_x) + 200,
        "y": 50,
        "width": 250,
        "height": 30,
        "text": ts_text,
        "fontSize": 16,
        "fontFamily": 1,
        "textAlign": "right",
        "strokeColor": "#868e96",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "groupIds": [],
        "roundness": None,
        "seed": 12345,
        "version": 1,
        "versionNonce": 12345,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
        "containerId": None,
        "originalText": ts_text,
        "lineHeight": 1.25,
        "baseline": 14,
        "verticalAlign": "top",
    })

    for node_id in G.nodes():
        node = G.nodes[node_id]
        x, y = positions.get(node_id, (0, 0))
        w, h = node_size(node["type"], node["title"])
        sizes[node_id] = (w, h)

        # Get colors
        if node["type"] == "goal":
            slug = node["title"].lower().replace(" ", "-")
            colors = GOAL_COLORS.get(slug, GOAL_COLORS["default"])
        elif node["type"] == "task":
            colors = PRIORITY_COLORS.get(node.get("priority", 2), PRIORITY_COLORS[2])
        else:
            colors = {"bg": "#e9ecef", "stroke": "#495057"}

        # Font size by type (match node_size function)
        font_size = {"goal": 48, "project": 24, "task": 14}.get(node["type"], 14)

        # Collect arrow bindings for this node
        arrow_bindings = []
        for source, target in G.edges():
            if source == node_id or target == node_id:
                arrow_id = f"arrow-{source}-{target}"
                arrow_bindings.append({"id": arrow_id, "type": "arrow"})

        # Add box with text AND arrow bindings
        box = make_excalidraw_element(
            node_id, node["type"], x, y, w, h,
            colors["bg"], colors["stroke"]
        )
        box["boundElements"] = [{"id": f"text-{node_id}", "type": "text"}] + arrow_bindings
        elements.append(box)
        elements.append(make_text_element(
            node_id, node["title"], x, y, w, h, font_size
        ))

    # Add arrows
    for source, target in G.edges():
        if source in positions and target in positions:
            elements.append(make_arrow(source, target, positions, sizes))

    # Build final document
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "gridSize": 20,
            "gridStep": 5,
            "gridModeEnabled": False,
            "viewBackgroundColor": "#ffffff",
        },
        "files": {},
    }

    output_path.write_text(json.dumps(doc, indent=2))
    print(f"✅ Written to {output_path}")
    print(f"   {len(elements)} elements, canvas ~{int(max_x)}px wide")

    return 0


if __name__ == "__main__":
    sys.exit(main())
