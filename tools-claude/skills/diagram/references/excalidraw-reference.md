# Excalidraw Reference

Schemas, CLI commands, structural invariants, and house palette for `.excalidraw` diagrams.

## Aesthetic Defaults and Layered Composition

| Property | Value | Rationale |
| - | - | - |
| `roughness` | `2` | Sketch aesthetic |
| `fontFamily` | `1` (Virgil) | Hand-drawn typeface |
| `fillStyle` | `"hachure"` | Sketch hatching |
| `strokeStyle` | `"solid"` | Consistent hand-drawn stroke |
| Background | `#ffffff` | High contrast and printability |

Build canvases in five layers, keeping uneven density on purpose (room for headline claims, tightly packed detail):

1. **Scenery**: Zones and boundaries (`--preset zone`).
2. **Spine**: Focal landmarks and critical paths (`--preset hero`).
3. **Satellites**: Standard operational nodes.
4. **Annotations**: Contextual commentary (`--preset sticky`).
5. **Connectors**: Solid flows or dashed telemetry (`--curved`, `--stroke-style dashed`).

**Text wrapping and chord checks**: Wrap Virgil text at `(width - 28) / (font * 0.62)` characters and size container widths to the longest line (`screenshot` renders stored lines unwrapped). Generate layouts from source data with stable slugged `id`s, and run a segment-versus-box check alongside `pkb-excalidraw check` because `arrows-check` tests chords and reports false positives on curved or routed arrows.

## CLI Commands (`pkb-excalidraw` and `pkb excalidraw`)

Requires `pkb-excalidraw` from `mem >= v0.3.101`, which natively trims `connect` arrow endpoints to shape outlines and mints valid fractional index keys. Run `pkb-excalidraw --help` for full flags.

```bash
pkb-excalidraw FILE [summary | map | nodes | edges | style | check | overlap | arrows-check]
pkb-excalidraw FILE add-node --type <type> --text "<text>" [--preset hero|sticky|zone] [--role <role>] [--at X,Y]
pkb-excalidraw FILE connect --from <id1> --to <id2> [--label "<label>"] [--curved] [--stroke-style dashed] [--color <hex>]
pkb-excalidraw FILE [set-text <id> "<text>" | fit <id> "<text>" | move-elem <id> --by DX,DY | delete-elem <id>]
pkb-excalidraw FILE update <id> --set '{"strokeStyle": "dashed"}'
pkb-excalidraw FILE screenshot [--out <path>] [--format svg|png] [--no-background]

pkb excalidraw export <output_path> [--focus <node_id>] [--hops <H>]
pkb excalidraw diff <canvas_path> [--base <snapshot>] [--json]
pkb excalidraw sync <canvas_path> [--base <snapshot>] [--dry-run]
```

Reconcile external user canvas edits with `diff` and `sync` back to markdown frontmatter rather than overwriting.

## Structural and Schema Invariants

Validate after every edit with `pkb-excalidraw FILE check` and `pkb-excalidraw FILE overlap`:

- **Text bindings**: Bound text links to its container via `containerId` and `boundElements`. Update text with `set-text` or `fit` so `text` and `originalText` stay in sync (`check` ignores wrap-only differences); update other fields with `update <id> --set '<json>'`.
- **Arrowheads, not bindings, determine direction**: `startBinding` and `endBinding` are attachment points only; edge direction comes from `startArrowhead` and `endArrowhead`. Both arrowheads set means bidirectional (`<->`), and a start-only arrowhead points at `startBinding` (opposite binding order). Derive topology direction from `startArrowhead`/`endArrowhead` rather than assuming `startBinding -> endBinding`.
- **Arrow bindings and edge editability**: Inspect every arrow so edges remain selectable and draggable in the Excalidraw editor:
  1. `startBinding` and `endBinding` are valid objects with an existing `elementId`, numeric `focus` in `[-1.0, 1.0]`, numeric `gap`, and optional normalized `fixedPoint` (`[x_ratio, y_ratio]` in `[0.0, 1.0]`).
  2. Source and target elements each list `{ "id": arrow_id, "type": "arrow" }` in `boundElements`.
  3. `points` begins at `[0, 0]`, with `width` and `height` matching the points' bounding box envelope.
- **Fractional index keys**: Validate every element's `index` against Excalidraw's `fractional-indexing` schema:
  1. Base-62 characters only (`0-9`, `A-Z`, `a-z`).
  2. Integer head length: for `a-z`, `head.charCodeAt(0) - 97 + 2` (e.g., `'a'` -> 2 chars `a0`--`az`, `'b'` -> 3 chars `b00`--`bzz`); for `A-Z`, `90 - head.charCodeAt(0) + 2` (`'Z'` -> 2 chars, `'A'` -> 27 chars).
  3. No trailing zero in non-empty fractional part: `fractionalPart = index.slice(integerLength)`; reject any key where `fractionalPart.length > 0 && fractionalPart.endsWith('0')` (e.g., `a000`, `a00100`).

## House Palette

| Role | Hex | Role | Hex |
| - | - | - | - |
| Emphasis / headers | `#c9b458` (gold) | Error / blocked | `#ff6666` (soft red) |
| Success / active | `#8fbc8f` (soft green) | Text / labels | `#1a1a1a` (primary dark) |
| Active accent | `#76c893` (bright green) | De-emphasized text | `#888888` (muted) |
| Info / links | `#7a9fbf` (soft blue) | Borders / arrows | `#404040` (charcoal) |
| Warning / queued | `#ffa500` (orange) | Completed fills | `#252525` (surface) |

- Use at most 4--6 colors per diagram, 10--35% fill opacity with `#1a1a1a` text, and 4.5:1 minimum contrast.
