---
name: task-viz
description: Generate network graph of notes/tasks using fast-indexer (JSON, GraphML, DOT)
---

# Task/Note Visualization

Generate a network graph of markdown files showing wikilink connections.

## Usage

```bash
$AOPS/scripts/bin/fast-indexer [DIRECTORY] -o OUTPUT -f FORMAT
```

## Options

- `-o, --output OUTPUT`: Output file path (extension auto-added based on format)
- `-f, --format FORMAT`: Output format - `json`, `graphml`, `dot`, `all` (default: all)
- `-t, --filter-type TYPE`: Filter by frontmatter type (e.g., `task,project,goal`)

## Output Formats

| Format | Extension | Compatible Tools |
|--------|-----------|------------------|
| `json` | `.json` | D3.js, Cytoscape.js, vis.js |
| `graphml` | `.graphml` | yEd, Gephi, Cytoscape |
| `dot` | `.dot` | Graphviz (neato, fdp, dot) |

## Features

- Respects `.gitignore` files
- Extracts tags from frontmatter and inline hashtags
- Resolves wikilinks and markdown links
- Parallel processing for speed (3800+ files in seconds)

## Styled Task Graphs

For color-coded visualizations based on status/priority/type:

```bash
# 1. Generate JSON with type filter
$AOPS/scripts/bin/fast-indexer ./data -o graph -f json -t task,project,goal

# 2. Apply styling and render SVG
python3 $AOPS/scripts/task_graph.py graph.json -o styled --layout sfdp
```

Color coding:
- **Fill**: Status (green=done, blue=active, red=blocked, yellow=waiting, white=inbox)
- **Border**: Priority (thick red=P0, thick orange=P1, gray=P2+)
- **Shape**: Type (ellipse=goal, box3d=project, box=task, note=action)

## Examples

```bash
# Generate all formats
$AOPS/scripts/bin/fast-indexer ./data -o graph

# Generate GraphML for yEd/Gephi
$AOPS/scripts/bin/fast-indexer ./data -o graph -f graphml

# Generate DOT and render with Graphviz
$AOPS/scripts/bin/fast-indexer ./data -o graph -f dot
sfdp -Tsvg -Goverlap=prism -Gsplines=true graph.dot -o graph.svg

# Full workflow: tasks/projects/goals with styling
$AOPS/scripts/bin/fast-indexer ./data -o tasks -f json -t task,project,goal
python3 $AOPS/scripts/task_graph.py tasks.json -o tasks-styled
```
