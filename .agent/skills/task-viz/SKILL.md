---
name: task-viz
description: Generate network graph of notes/tasks using `aops` CLI (JSON, GraphML, DOT)
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

Generate network graphs of markdown files showing wikilink connections. Uses the `aops` CLI binary (from nicsuzor/mem) for high-performance scanning and optional Python styling for task-specific color coding.

## Quick Start

```bash
# Dashboard graph (needed for Overwhelm Dashboard)
aops graph -o graph.json -f json

# All formats
aops graph -o graph -f all
```

## Use Cases

### 1. Knowledge Base Map

Visualize all markdown files and their wikilink connections:

```bash
aops graph -o knowledge-graph -f json
```

Generates: `knowledge-graph.json`, or use `-f all` for `.json`, `.graphml`, `.dot`

### 2. Task Hierarchy Graph

Visualize goals, projects, and tasks with their relationships:

```bash
aops graph -o task-hierarchy -f json
python3 $AOPS/scripts/task_graph.py task-hierarchy.json -o task-hierarchy-styled
```

### 3. Framework Reference Map

Map all file references in the aops framework:

```bash
aops graph --pkb-root $AOPS -o framework-graph
```

## Tools

### aops CLI

High-performance Rust binary for PKB operations including graph export (from nicsuzor/mem).

```bash
aops graph [-o OUTPUT] [-f FORMAT]
```

**Options**:

- `-o, --output OUTPUT`: Output file path (extension auto-added based on format)
- `-f, --format FORMAT`: Output format - `json`, `graphml`, `dot`, `mcp-index`, `all` (default: json)
- `--pkb-root PATH`: Override PKB root directory (default: $PKB_ROOT or ~/brain)

**Features**:

- Semantic search + graph-aware indexing
- Extracts tags from frontmatter and inline hashtags
- Resolves wikilinks and markdown links
- High-performance parallel processing

### task_graph.py

Python script for adding visual styling to task graphs.

```bash
python3 $AOPS/scripts/task_graph.py INPUT.json [-o OUTPUT] [--layout LAYOUT]
```

**Options**:

- `-o, --output`: Output base name (default: `tasks`)
- `--layout`: Graphviz layout engine: `dot`, `neato`, `sfdp`, `fdp`, `circo`, `twopi` (default: `sfdp`)
- `--include-orphans`: Include unconnected nodes
- `--no-filter`: Disable smart filtering (show all tasks including completed)

**Default behavior**: Smart filtering is enabled by default - removes completed leaf tasks but keeps completed parents that have active children (displayed as box3d with dashed border).

**Color Coding**:

| Attribute              | Visual               |
| ---------------------- | -------------------- |
| Status: done           | Fill: green          |
| Status: active         | Fill: blue           |
| Status: blocked        | Fill: red            |
| Status: waiting        | Fill: yellow         |
| Status: inbox          | Fill: white          |
| Priority: 0 (critical) | Border: thick red    |
| Priority: 1 (high)     | Border: thick orange |
| Priority: 2+           | Border: gray         |
| Type: goal             | Shape: ellipse       |
| Type: project          | Shape: box3d         |
| Type: task             | Shape: box           |
| Type: action           | Shape: note          |

## Output Formats

| Format    | Extension  | Compatible Tools                              |
| --------- | ---------- | --------------------------------------------- |
| `json`    | `.json`    | D3.js, Cytoscape.js, vis.js, NetworkX         |
| `graphml` | `.graphml` | yEd, Gephi, Cytoscape                         |
| `dot`     | `.dot`     | Graphviz (neato, fdp, sfdp, dot)              |
| `svg`     | `.svg`     | Browser, any image viewer (via task_graph.py) |

## Complete Workflows

### Generate Interactive Web Visualization

```bash
# 1. Generate JSON
aops graph -o graph -f json

# 2. Use with D3.js or Cytoscape.js (graph.json is standard node-link format)
```

### Generate Print-Ready Task Map

```bash
# 1. Generate JSON
aops graph -o tasks -f json

# 2. Apply styling and render SVG
python3 $AOPS/scripts/task_graph.py tasks.json -o task-map --filter reachable --layout sfdp

# 3. Open SVG
open task-map.svg       # macOS
```

### Generate yEd-Compatible Graph

```bash
aops graph -o graph -f graphml
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
2. **Iterative refinement**: Generate GraphML, open in yEd, apply automatic layout, export
3. **Custom styling**: Modify `$AOPS/scripts/task_graph.py` for different color schemes
