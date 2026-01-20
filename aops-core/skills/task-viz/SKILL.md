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
- `-f, --format FORMAT`: Output format - `json` (default), `graphml`, `dot`

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

## Examples

```bash
# Generate JSON graph of all notes
$AOPS/scripts/bin/fast-indexer ./data -o graph -f json

# Generate GraphML for yEd/Gephi
$AOPS/scripts/bin/fast-indexer ./data -o graph -f graphml

# Generate DOT and render with Graphviz
$AOPS/scripts/bin/fast-indexer ./data -o graph -f dot
dot -Tpng graph.dot -o graph.png
```
