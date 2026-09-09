---
name: diagram
description: Draw, edit, and review diagrams -- Mermaid for version-controlled flowcharts, sequences, and architecture; Excalidraw for mind maps, concept maps, PKB graphs, and sketches. Covers layout routing, house palette, excalidraw-view CLI, and PKB export/diff/sync. Not for plotting quantitative data or UI mockups.
---

# Diagram

Mermaid and Excalidraw diagramming standards, layout routing, and visual invariants.

## Objective and layout routing

Identify the chart's core objective (the action or decision it enables) and reader context before drawing.

| Reader question          | Layout family         | Guidance                                           |
| ------------------------ | --------------------- | -------------------------------------------------- |
| "What do I do next?"     | Containment + state   | Group by navigation paths; emphasize active items. |
| "How does this work?"    | Flow / sequence       | Directional arrows; default to Mermaid.            |
| "Where does this fit?"   | Containment / nesting | Boundary nesting up to ~3 levels deep.             |
| "How do these compare?"  | Matrix / grid         | Uniform grid with comparable cells.                |
| "What changed / is off?" | Anomaly / comparison  | Highlight outliers without data smoothing.         |
| "When does this happen?" | Timeline              | Position strictly encodes chronological time.      |
| "What is central here?"  | Radial / hub          | Focal node centered with balanced spokes.          |

### Visual channel rules

- **Bind channels to real fields**: Derive weights, status, and structure from source data -- never author arbitrary hierarchies.
- **One channel, one meaning**: Document encodings in a legend; unassigned channels remain uniform.
- **Explicit omission**: Label truncated containers (e.g., "showing 3 of 12"); never invent category names for unselected items.
- **Respect live files**: When editing an open diagram, diff against mtime/disk state to preserve external user edits.

## Craft rules

- **Single message**: One primary argument per chart; sub-processes get dedicated diagrams.
- **Chunking**: Limit clusters to 6--9 nodes; align happy path along a straight spine.
- **Labels**: Terse, verb-first labels (3--9 words). State current facts, not change logs or historical commentary.
- **Shapes**: Process (rectangles), decision (diamonds), terminal/actors (circles), mind maps (ellipses).

## Mermaid conventions

- **Default orientation**: Use `LR`. Use `TD` only for wide fan-outs. In subgraphs, use `direction TB`.
- **Subgraphs**: Link subgraph to subgraph, not internal nodes to external nodes.
- **Scale**: Past ~15 nodes or heavy cross-links, switch to ELK (`layout: elk`, `mergeEdges: true`, `nodePlacementStrategy: SIMPLE`).
- **Phases**: Group 10+ steps into numbered phases (① ② ③) colored start (green) -> work (gold) -> end (gray).

## Excalidraw conventions

### Aesthetic defaults

| Property      | Value             | Rationale                      |
| ------------- | ----------------- | ------------------------------ |
| `roughness`   | `2`               | Sketch aesthetic               |
| `fontFamily`  | `1` (Virgil)      | Hand-drawn typeface            |
| `fillStyle`   | `"hachure"`       | Sketch hatching                |
| `strokeStyle` | `"solid"`         | Consistent hand-drawn stroke   |
| Background    | White (`#ffffff`) | High contrast and printability |

### Layered composition

1. **Scenery**: Zones and boundaries (`--preset zone`).
2. **Spine**: Focal landmarks and critical paths (`--preset hero`).
3. **Satellites**: Standard operational nodes.
4. **Annotations**: Contextual commentary (`--preset sticky`).
5. **Connectors**: Solid flows or dashed telemetry (`--curved`, `--stroke-style dashed`).

### CLI tools and invariants

Inspect and modify `.excalidraw` files via `excalidraw-view`:

```bash
excalidraw-view FILE [summary | map | nodes | edges | style | check]
excalidraw-view FILE add-node --type <type> --text "<text>" [--preset hero|sticky|zone] [--at X,Y]
excalidraw-view FILE connect --from <id1> --to <id2> [--label "<label>"] [--curved]
excalidraw-view FILE [set-text <id> "<text>" | fit <id> "<text>" | move-elem <id> --by DX,DY | delete-elem <id>]
```

- **Invariants**: Text binds to container (`containerId`/`boundElements`); arrows bind both ends (`startBinding`/`endBinding`).
- Update `text` and `originalText` together. Keep elements sorted by ascending fractional `index`.
- Validate with `excalidraw-view FILE check` and `excalidraw-view FILE overlap`.

### PKB export and sync

```bash
pkb excalidraw export <output_path> [--focus <node_id>] [--hops <H>]
pkb excalidraw diff <canvas_path> [--base <snapshot>] [--json]
pkb excalidraw sync <canvas_path> [--base <snapshot>] [--dry-run]
```

Reconcile user canvas edits with `diff` and `sync` back to markdown frontmatter rather than clobbering.

## Palette

| Role               | Hex                      | Role               | Hex                      |
| ------------------ | ------------------------ | ------------------ | ------------------------ |
| Emphasis / headers | `#c9b458` (gold)         | Error / blocked    | `#ff6666` (soft red)     |
| Success / active   | `#8fbc8f` (soft green)   | Text / labels      | `#1a1a1a` (primary dark) |
| Active accent      | `#76c893` (bright green) | De-emphasized text | `#888888` (muted)        |
| Info / links       | `#7a9fbf` (soft blue)    | Borders / arrows   | `#404040` (charcoal)     |
| Warning / queued   | `#ffa500` (orange)       | Completed fills    | `#252525` (surface)      |

- Maximum 4--6 colors per diagram.
- Opacity: 10--35% for fills with `#1a1a1a` text; 4.5:1 minimum contrast.
