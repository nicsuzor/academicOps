---
name: diagram
description: Draw, edit, and review diagrams -- Mermaid for version-controlled flowcharts, sequences, and architecture; Excalidraw for mind maps, concept maps, PKB graphs, and sketches. Covers layout routing, pkb-excalidraw CLI, SVG/PNG rendering, visual QA, and PKB sync. Not for plotting quantitative data or UI mockups.
---

# Diagram

Mermaid and Excalidraw diagramming standards, layout routing, and visual invariants.

## Objective and Layout Routing

Identify the chart's core objective (the action or decision it enables) and reader context before drawing.

| Reader question | Layout family | Guidance |
| - | - | - |
| "What do I do next?" | Containment + state | Group by navigation paths; emphasize active items. |
| "How does this work?" | Flow / sequence | Directional arrows; default to Mermaid. |
| "Where does this fit?" | Containment / nesting | Boundary nesting up to ~3 levels deep. |
| "How do these compare?" | Matrix / grid | Uniform grid with comparable cells. |
| "What changed / is off?" | Anomaly / comparison | Highlight outliers without data smoothing. |
| "When does this happen?" | Timeline | Position strictly encodes chronological time. |
| "What is central here?" | Radial / hub | Focal node centered with balanced spokes. |

### Channel and Craft Rules

- **Bind channels to real fields**: Derive weights, status, and structure from source data; document encodings in a legend and keep unassigned channels uniform.
- **Explicit omission and live edits**: Label truncated containers (e.g., "showing 3 of 12"); when editing an open file, diff against disk mtime to preserve external user edits.
- **Single message and chunking**: One primary argument per chart (6--9 nodes per cluster, happy path along a straight spine); sub-processes get dedicated diagrams.
- **Labels and shapes**: Terse, verb-first labels (3--9 words) stating current facts. Use rectangles for processes, diamonds for decisions, circles for terminals/actors, and ellipses for mind maps.

## Mermaid Conventions

- **Orientation and subgraphs**: Default to `LR` (`TD` only for wide fan-outs; `direction TB` inside subgraphs). Link subgraph to subgraph rather than internal nodes to external nodes.
- **Scale and phases**: Past ~15 nodes or heavy cross-links, switch to ELK (`layout: elk`, `mergeEdges: true`, `nodePlacementStrategy: SIMPLE`). Group 10+ steps into numbered phases (`① ② ③`) colored start (green) -> work (gold) -> end (gray).

## Excalidraw Workflow

Before editing or validating `.excalidraw` JSON, read [references/excalidraw-reference.md](references/excalidraw-reference.md).

- **Use `pkb-excalidraw` first**: Prefer `pkb-excalidraw` over raw JSON edits because mutations refuse to save invalid files. When updating an existing canvas, edit in place (`move-elem`, `set-text`/`fit`, `update`, `delete-elem`) to preserve every `id` for `pkb excalidraw diff`/`sync`; never draw a parallel duplicate system alongside old elements.
- **Hierarchies (nest first, arrow last)**: Use large unboxed headlines for top levels, plain panels for groups, columns for sub-groups, and packed small boxes for leaves. Draw labelled connectors only for moves between groups (grid-routed; curved 12% off-centre max 60 px; relax-then-repair free layouts; at most 5 colors bound to node kind).
- **PKB note derivation**: When creating a PKB note from a canvas via `pkb.create`, pass the canvas's PKB-relative path as `source` (or set `parent` to a node in that directory).

## Rendering and Visual QA

Render every finished canvas and inspect the rendered image directly before presentation, handback, or release:

```bash
pkb-excalidraw FILE screenshot --out <path>.svg --format svg
# Or when PNG is required: pkb-excalidraw FILE screenshot --out <path>.png --format png
```

- **Fail-fast on missing renderer**: If `pkb-excalidraw` is missing or fails, halt and report verbatim -- never substitute ad-hoc SVG or canvas scripts. If `--format png` falls back to SVG because no system rasterizer (`resvg`, `rsvg-convert`, `magick`) is on `PATH`, inspect the SVG fallback unless PNG was explicitly required (then halt).
- **Visual QA criteria**: Verify directly in the image that (1) arrowheads terminate cleanly outside shapes without crossing labels, (2) text fits within container bounds, (3) elements and labels do not overlap, (4) connector polylines avoid unrelated boxes and labels, and (5) visual hierarchy and flows read clearly at standard zoom.
