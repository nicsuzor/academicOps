---
name: task-viz
description: Generate visual mind-map of tasks using force-directed layout (excalidraw, JSON, GraphML, DOT)
---

# Task Visualization

Generate a force-directed visualization of tasks in multiple formats.

## Usage

```bash
uv run python $AOPS/aops-core/skills/task-viz/scripts/task_viz_bd.py output [--format FORMAT] [--include-closed] [--prefix PREFIX]
```

## Options

- `--format FORMAT`: Output format - `excalidraw` (default), `json`, `graphml`, `dot`, or `all`
- `--include-closed`: Include closed issues (excluded by default)
- `--prefix PREFIX`: Filter issues by ID prefix (e.g., `ns-`, `aops-`)

## Output Formats

| Format | Extension | Compatible Tools |
|--------|-----------|------------------|
| `excalidraw` | `.excalidraw` | Excalidraw, VS Code plugin |
| `json` | `.json` | D3.js, Cytoscape.js, vis.js |
| `graphml` | `.graphml` | yEd, Gephi, Cytoscape |
| `dot` | `.dot` | Graphviz (neato, fdp, dot) |

## Visual Encoding

- Epics: Large green ellipses
- Tasks/bugs: Rectangles colored by priority (P0=red, P1=orange, P2=yellow, P3=gray)
- Arrows: Parent-child relationships
- Legend: Color key in corner (excalidraw only)

## Examples

```bash
# Generate excalidraw (default)
uv run python $AOPS/aops-core/skills/task-viz/scripts/task_viz_bd.py ~/tasks.excalidraw

# Generate JSON for D3/Cytoscape
uv run python $AOPS/aops-core/skills/task-viz/scripts/task_viz_bd.py ~/tasks --format json

# Generate all formats
uv run python $AOPS/aops-core/skills/task-viz/scripts/task_viz_bd.py ~/tasks --format all --prefix aops-

# Render DOT with Graphviz
dot -Tpng tasks.dot -o tasks.png
```
