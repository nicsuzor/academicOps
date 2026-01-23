---
name: task-viz
description: Generate network graph of notes/tasks using fast-indexer (JSON, GraphML, DOT)
triggers:
  - task visualization
  - visualize tasks
  - network map
  - knowledge graph
  - task chart
  - issue mind map
  - graph my notes
---

# Task/Note Visualization

Generate network graphs of markdown files showing wikilink connections. Uses the `fast-indexer` Rust binary for high-performance scanning and optional Python styling for task-specific color coding.

## Quick Start

```bash
# All notes → all formats
$AOPS/scripts/bin/fast-indexer ${ACA_DATA} -o graph

# Tasks only → styled SVG
$AOPS/scripts/bin/fast-indexer ${ACA_DATA} -o tasks -f json -t task,project,goal
python3 $AOPS/scripts/task_graph.py tasks.json -o tasks-styled
```

## Use Cases

### 1. Knowledge Base Map

Visualize all markdown files and their wikilink connections:

```bash
$AOPS/scripts/bin/fast-indexer ${ACA_DATA} -o knowledge-graph
```

Generates: `knowledge-graph.json`, `knowledge-graph.graphml`, `knowledge-graph.dot`

### 2. Task Hierarchy Graph

Visualize goals, projects, and tasks with their relationships:

```bash
$AOPS/scripts/bin/fast-indexer ${ACA_DATA} -o task-hierarchy -f json -t goal,project,task,action
python3 $AOPS/scripts/task_graph.py task-hierarchy.json -o task-hierarchy-styled
```

### 3. Framework Reference Map

Map all file references in the aops framework:

```bash
$AOPS/scripts/bin/fast-indexer $AOPS -o framework-graph
```

## Tools

### fast-indexer

High-performance Rust binary for scanning markdown files.

```bash
$AOPS/scripts/bin/fast-indexer [DIRECTORY] -o OUTPUT -f FORMAT
```

**Options**:
- `-o, --output OUTPUT`: Output file path (extension auto-added based on format)
- `-f, --format FORMAT`: Output format - `json`, `graphml`, `dot`, `all` (default: all)
- `-t, --filter-type TYPE`: Filter by frontmatter type (comma-separated: `task,project,goal`)

**Features**:
- Respects `.gitignore` files
- Extracts tags from frontmatter and inline hashtags
- Resolves wikilinks and markdown links
- Parallel processing (3800+ files in seconds)

### task_graph.py

Python script for adding visual styling to task graphs.

```bash
python3 $AOPS/scripts/task_graph.py INPUT.json [-o OUTPUT] [--layout LAYOUT]
```

**Options**:
- `-o, --output`: Output base name (default: `tasks`)
- `--layout`: Graphviz layout engine: `dot`, `neato`, `sfdp`, `fdp`, `circo`, `twopi` (default: `sfdp`)
- `--include-orphans`: Include unconnected nodes
- `--exclude-done`: Filter out all tasks with status `done` or `completed`
- `--smart-filter`: Smart filter - removes completed leaf tasks but keeps completed parents that have active children (displayed as box3d with dashed border)

**Color Coding**:

| Attribute | Visual |
|-----------|--------|
| Status: done | Fill: green |
| Status: active | Fill: blue |
| Status: blocked | Fill: red |
| Status: waiting | Fill: yellow |
| Status: inbox | Fill: white |
| Priority: 0 (critical) | Border: thick red |
| Priority: 1 (high) | Border: thick orange |
| Priority: 2+ | Border: gray |
| Type: goal | Shape: ellipse |
| Type: project | Shape: box3d |
| Type: task | Shape: box |
| Type: action | Shape: note |

## Output Formats

| Format | Extension | Compatible Tools |
|--------|-----------|------------------|
| `json` | `.json` | D3.js, Cytoscape.js, vis.js, NetworkX |
| `graphml` | `.graphml` | yEd, Gephi, Cytoscape |
| `dot` | `.dot` | Graphviz (neato, fdp, sfdp, dot) |
| `svg` | `.svg` | Browser, any image viewer (via task_graph.py) |

## Complete Workflows

### Generate Interactive Web Visualization

```bash
# 1. Generate JSON
$AOPS/scripts/bin/fast-indexer ${ACA_DATA} -o graph -f json

# 2. Use with D3.js or Cytoscape.js (graph.json is standard node-link format)
```

### Generate Print-Ready Task Map

```bash
# 1. Generate filtered JSON
$AOPS/scripts/bin/fast-indexer ${ACA_DATA} -o data/aops/outputs/tasks -f json -t task,project,goal

# 2. Apply styling and render SVG
python3 $AOPS/scripts/task_graph.py data/aops/outputs/tasks.json -o data/aops/outputs/task-map --layout sfdp

# 3. Open SVG
xdg-open data/aops/outputs/task-map.svg  # Linux
open data/aops/outputs/task-map.svg       # macOS
```

### Generate yEd-Compatible Graph

```bash
$AOPS/scripts/bin/fast-indexer ${ACA_DATA} -o graph -f graphml
# Open graph.graphml in yEd for manual layout refinement
```

## JSON Output Format

The JSON output follows the standard node-link format:

```json
{
  "nodes": [
    {
      "id": "path/to/file.md",
      "label": "File Title",
      "node_type": "task",
      "status": "active",
      "priority": 1,
      "tags": ["tag1", "tag2"]
    }
  ],
  "edges": [
    {
      "source": "path/to/file1.md",
      "target": "path/to/file2.md"
    }
  ]
}
```

## Tips

1. **Large graphs**: Use `sfdp` layout for graphs with 100+ nodes
2. **Focused views**: Use `-t` filter to limit to specific types
3. **Iterative refinement**: Generate GraphML, open in yEd, apply automatic layout, export
4. **Custom styling**: Modify `$AOPS/scripts/task_graph.py` for different color schemes
