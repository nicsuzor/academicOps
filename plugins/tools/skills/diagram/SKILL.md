---
name: diagram
description: Draw, edit, and review diagrams -- Mermaid for version-controlled flowcharts, sequences, and architecture; Excalidraw for mind maps, concept maps, PKB graphs, and sketches. Covers layout routing, house palette, pkb-excalidraw CLI, SVG/PNG rendering, visual QA, fractional index validation, and PKB export/diff/sync. Not for plotting quantitative data or UI mockups.
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

`pkb-excalidraw` is the preferred way to read and edit `.excalidraw` files; use it before reading or writing the JSON directly, because its mutations refuse to save a file that fails validation. Run `pkb-excalidraw --help` for the full command set.

```bash
pkb-excalidraw FILE [summary | map | nodes | edges | style | check | overlap | arrows-check]
pkb-excalidraw FILE add-node --type <type> --text "<text>" [--preset hero|sticky|zone] [--role <role>] [--at X,Y]
pkb-excalidraw FILE connect --from <id1> --to <id2> [--label "<label>"] [--curved] [--stroke-style dashed] [--color <hex>]
pkb-excalidraw FILE [set-text <id> "<text>" | fit <id> "<text>" | move-elem <id> --by DX,DY | delete-elem <id>]
pkb-excalidraw FILE update <id> --set '{"strokeStyle": "dashed"}'
pkb-excalidraw FILE screenshot [--out <path>] [--format svg|png] [--no-background]
```

- **Invariants**: Text binds to container (`containerId`/`boundElements`); arrows bind both ends (`startBinding`/`endBinding`).
- Change text with `set-text` or `fit`, which update `text` and `originalText` together. Change any other property with `update <id> --set '<json>'`.
- Validate after every edit with `pkb-excalidraw FILE check` and `pkb-excalidraw FILE overlap`. `check` does not flag line-wrap-only differences between `text` and `originalText`.
- Requires `pkb-excalidraw` from `mem >= v0.3.101` (carrying `mem#691`) or newer, which natively trims `connect` arrow endpoints to shape outlines and mints valid fractional index keys.
- **Structural arrow binding check and edge editability**: Inspect every arrow against Excalidraw's element schema so edges remain interactively selectable and draggable in the Excalidraw editor:
  1. `startBinding` and `endBinding` must be valid objects with `elementId` matching existing elements, numeric `focus` (between -1.0 and 1.0), numeric `gap`, and optional `fixedPoint` (`[x_ratio, y_ratio]` normalized between 0.0 and 1.0).
  2. Reciprocal `boundElements`: The source and target elements must each list `{ "id": arrow_id, "type": "arrow" }` in `boundElements`.
  3. Points envelope: `points` array must start at `[0, 0]`, with `width` and `height` matching the points' bounding box envelope.
  4. Editability cause: Canvases whose arrows pass static checks and static rendering can still fail interactive editing in Excalidraw (edges cannot be selected or dragged, or detach on movement). The cause is malformed bindings, out-of-envelope points, or missing `boundElements` backreferences that Excalidraw's interactive editor engine rejects.
- **`add-node` and `connect` invalid index key defect**: `pkb-excalidraw add-node` and `connect` mint fractional `index` keys by appending digit pairs (`00`, `01`) to the previous key (`a000`, `a001`, `a00100`, `a00101`, `a0010100` ...), leaving trailing zeros in the fractional part. While `pkb-excalidraw check` passes these files (verifying only monotonic ordering), `fractional-indexing` (`validateOrderKey`/`midpoint`) strictly rejects keys with trailing zeros in their fractional part (`invalid order key`). Excalidraw 0.18.1 validates keys whenever minting a key next to an existing element (e.g. on arrow labelling, duplicate, or z-order adjustments), throwing `invalid order key` and causing operations to silently fail, leaving edges uneditable.
- **Structural fractional index check**: Validate every element's `index` key against Excalidraw's `fractional-indexing` schema:
  1. Base-62 character set: Keys must consist only of base-62 digits (`0-9`, `A-Z`, `a-z`).
  2. Integer head and length: For keys starting with lowercase `a-z`, integer part length is `head.charCodeAt(0) - 97 + 2` (e.g. `'a'` is 2 characters: `a0`--`az`; `'b'` is 3 characters: `b00`--`bzz`). For uppercase `A-Z`, integer part length is `90 - head.charCodeAt(0) + 2` (`'Z'` is 2 characters, `'A'` is 27 characters).
  3. Reject trailing zeros in fractional part: The fractional part comprises all characters after the integer part (`index.slice(integerLength)`). If the fractional part is non-empty, its final character must NOT be `'0'`. Reject any key where `fractionalPart.endsWith('0')` (e.g. `a000`, `a00100`, `a0010100`).

### Rendering and visual QA

Every finished canvas must be rendered to vector SVG or PNG using `pkb-excalidraw` and pass visual inspection against the rendered image before presentation, handback, or release.

```bash
pkb-excalidraw FILE screenshot --out <path>.svg --format svg
# Or if a PNG deliverable is required:
pkb-excalidraw FILE screenshot --out <path>.png --format png
```

- **What the render shows**: `screenshot` draws the canvas's stored geometry: shape outlines, arrow points, and bound text as its stored lines. It names Virgil without embedding it and draws fills flat, so text in the image uses Virgil only where Virgil is installed. Judge arrow placement, overlaps, and crossings from the image directly; treat a label that sits close to its container edge as a possible overflow in Excalidraw.
- **CLI check blind spots**: `pkb-excalidraw check`, `overlap`, and `arrows-check` cannot catch arrows ending inside boxes. `check` tests structural references and half-bound arrows, `overlap` tests only shape AABBs, and `arrows-check` only checks whether arrow polylines intersect unrelated intermediate boxes (ignoring endpoints at connected shapes). All three checks will pass a canvas whose every arrow ends inside its box. Rendering via `pkb-excalidraw FILE screenshot` and visually inspecting the resulting image is mandatory to verify that arrowheads terminate outside shapes.
- **Missing tool or converter**:
  - If `pkb-excalidraw` is missing or fails to render, halt immediately and report the failure verbatim. Never substitute an ad-hoc or homemade renderer (such as manual SVG construction or custom canvas scripts); alternative renderers produce incorrect typography, drop bindings, and conceal layout defects.
  - When `--format png` is requested without a system rasterizer (`resvg`, `rsvg-convert`, `magick`) on `PATH`, the tool outputs a notice and saves an SVG fallback to `<path>.svg`. Use this SVG render for visual QA. If a PNG image is explicitly required by acceptance criteria and no rasterizer exists, halt and surface the missing dependency.
- **Visual QA criteria**:
  Inspect the rendered image directly to verify:
  1. **Arrowhead placement**: Arrows terminate cleanly at container boundaries; no arrowheads are buried inside boxes or cut across labels.
  2. **Label overflow**: Text does not exceed container bounds, spill across borders, or wrap awkwardly across lines.
  3. **Overlaps**: Text elements and shapes do not collide with or obscure neighbouring elements.
  4. **Crossing arrows**: Connector polylines do not cut through unrelated boxes or labels.
  5. **At-a-glance legibility**: Visual hierarchy is obvious, labels are readable at standard zoom, and flows are intuitive without clutter.

### Editing an existing diagram

When the diagram already exists and the ask changes the plan or state it shows, edit the existing elements in place so the delta is visible on the canvas:

- **Moved** thing: `move-elem` the existing element.
- **Renamed** thing: `set-text` or `fit` the existing element.
- **Changed status**: set `strokeColor`/`backgroundColor` on the existing element to the palette role for its new state.
- **Removed** thing: `delete-elem` it, and its bound text and arrows.
- **Genuinely new** thing: `add-node` only for this.

Keep the `id` of every surviving element. `pkb excalidraw diff` and `sync` match canvas elements to PKB nodes by `id`; a replaced element reads as a deletion plus an unrelated addition.

**Anti-pattern -- the parallel system.** Do not draw a fresh set of elements beside the old ones to depict the new state. It leaves two contradictory versions on one canvas, hides what changed, and severs every `id` binding. Before adding any element, check whether an existing element already represents that thing; if one does, edit it.

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
