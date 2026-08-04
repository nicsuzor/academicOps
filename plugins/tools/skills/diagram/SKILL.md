---
name: diagram
description: Creating diagrams in any style — Mermaid flowcharts (structured, code-based) or Excalidraw (hand-drawn, organic). Use style parameter to select.
---

# Diagram

Make diagrams that communicate one thing clearly. Mermaid and Excalidraw syntax
is public knowledge — what follows is the routing rule, the user's taste, and the
hazards syntax knowledge does not cover.

## Style routing

- `style="mermaid"` — structured, code-based flowcharts. Use when the diagram
  lives in documentation, is read in a diff, and must stay in version control.
- `style="excalidraw"` — hand-drawn, organic. Use for mind maps, concept maps,
  informal architecture sketches, and presentation visuals where feel matters.

If the user has not said which, ask before drawing. Converting after the fact
loses the layout work.

## Craft rules (both styles)

- **One message per chart.** State the purpose in one line first ("how a session
  moves from prompt to cleanup"), then cut everything that does not serve it. A
  deep sub-process gets its own chart.
- **Chunk.** Group related steps; keep any one group under 6–9 nodes.
- **Happy path on a straight spine.** Exceptions and loops go to the side.
  Minimise backward arrows and edge crossings.
- **Verb-first labels, 3–9 words.** Detail goes in a note or legend, never inside
  the box. Big blocks of text in boxes are the most common failure.
- **Distinct shapes carry distinct semantics** — process, decision, terminal,
  data/IO. Never reuse one shape for two meanings in the same chart.
- **Same hierarchy level, same size and weight.** Uniform everything is chaos;
  so is arbitrary variation.

## Style: mermaid

**Default to `LR`.** Charts trend too tall and screens are wider than they are
tall. Reach for `TD` only when branching logic genuinely fans out. For
phases-with-steps, use `LR` at the top level with `direction TB` inside each
subgraph.

**Link subgraph to subgraph — never a subgraph-internal node to an outside
node.** Internal-to-external links force direction inheritance and wreck the
layout.

**Past ~15 nodes, or with many cross-links, switch to the ELK layout engine**
(`layout: elk`, `mergeEdges: true`, `nodePlacementStrategy: SIMPLE` in the
frontmatter config block). The default renderer degrades badly at that size.

**At 10+ steps, organise into numbered phases** (① ② ③) instead of one long
chain. Colour phases by position in the flow (green → gold → gray for
start → work → end) using the palette below. Route hooks, agents, and external
services into a separate side panel connected only by dashed edges, and only
where the interaction is essential.

## Style: excalidraw

### Aesthetic defaults

| Property      | Value        | Why                                      |
| ------------- | ------------ | ---------------------------------------- |
| `roughness`   | `2`          | Maximum sketchiness — commit to the look |
| `fontFamily`  | `1` (Virgil) | Handwritten, never Helvetica             |
| `fillStyle`   | `"hachure"`  | Sketchy hatching, not solid fill         |
| `strokeStyle` | `"solid"`    | Reads as hand-drawn at roughness 2       |

Canvas background is **white**, always. The palette below is a terminal theme,
but diagrams need contrast and printability — never a dark canvas.

### Binding is mandatory

- **Text binds to its shape** — `containerId` on the text element,
  `boundElements` on the shape. Unbound text does not move with its box, and the
  diagram desynchronises on the first edit. Text should auto-size to container
  width. Manual equivalent: select both → Cmd/Ctrl+G.
- **Arrows bind at both ends** — `startBinding` and `endBinding`. A floating
  arrow points at nothing the moment a box moves. Never create one.

### The index-order hazard

When writing `.excalidraw` files directly: every element carries a fractional
`index` key setting z-order, and **the `elements` array must itself be
serialised in ascending `index` order**. If array order and index order
disagree, Excalidraw will not open the file — while every referential check
still passes (ids resolve, bindings match, each index is individually valid), so
nothing warns you. Sort by `index` immediately before writing, every time.

Use fixed-width keys of equal length over the `0-9A-Za-z` ASCII alphabet (`a00`,
`a01`, …) so lexicographic order is numeric order with no prefix collisions. An
ad hoc scheme like `c00`, `d02` is silently regenerated on the next open/save,
resorting the whole array with it.

### Reading an existing file

Never Read a `.excalidraw` file raw. It is one long line of JSON — offset/limit
cannot window it, a 135KB file is ~35k+ tokens, and Read refuses past 25k. The
semantics fit in ~6% of that. Project them with the bundled viewer
(`scripts/excalidraw-view.py` beside this file, stdlib only):

```bash
python3 scripts/excalidraw-view.py FILE summary  # counts, extents, max index, order sanity
python3 scripts/excalidraw-view.py FILE map      # shapes with labels, free text, arrow topology
python3 scripts/excalidraw-view.py FILE style    # modal style values to copy for new elements
python3 scripts/excalidraw-view.py FILE check    # structural validation — exit 1 on any fault
```

`summary` then `map` is full situational awareness; add `style` before creating
elements so new work matches the house look. For anything the viewer does not
cover, write a small jq/python projection — never dump the file.

Projected output is for reasoning, **not for Edit anchors**: jq and python
decode JSON, so `\n` and unicode escapes no longer match the bytes on disk.

### Editing an existing file

Mutate through a short python script — load, modify, dump — never by
string-matching Edits against the JSON. In the script:

- **Back up first** (`cp FILE FILE.bak-<date>`). Fix a bad result by editing the
  script and re-running it against the backup — never by patching its output.
- **Prefer append-only.** New elements added in free canvas (`summary` prints
  the extents) leave every existing binding untouched.
- **Clone, don't author.** `copy.deepcopy` an existing element of the same type
  as the template, then reset the identity fields: `id`, `seed`, `versionNonce`,
  `version`, `updated`, and clear `groupIds`, `containerId`, `boundElements`
  before wiring the new relationships.
- **Continue `index` past the current maximum** (`summary` prints it) so
  existing elements keep their z-order and the array stays sorted.
- **Validate on both sides of the write**: `check` mode before editing proves
  you started from a well-formed file; `check` plus a fresh-interpreter re-parse
  after proves you left one. A file can pass every referential check and still
  be unopenable — that is exactly what `check`'s order test catches.

If a targeted Edit is genuinely simpler (one text swap), extract the exact
`old_string` with `grep -o` from the raw file so the escaping matches.

To see layout rather than structure, render the changed region to PNG with
matplotlib (`uv run --with matplotlib`, not system python) and read the image.
Say what that proves: geometry and collisions, not Excalidraw's true rendering —
bound-text wrapping can still differ.

### Layout

- **No rigid alignment.** Radial and clustered, spreading in all directions —
  not a top-to-bottom tree.
- **Arrows are directional, so a child can sit anywhere around its parent** —
  360° of freedom. Use it to keep arrows from crossing and overlapping.
- **Curved multi-point arrows** (click-click-click, not drag), routed _around_
  unrelated boxes, never through them.
- **Whitespace is structure.** Macro gaps separate concept groups; micro gaps
  pad within them. If it feels crowded, it is crowded — add more than you think.
- **Scale carries hierarchy.** The canvas is unlimited: make the important thing
  genuinely big and let children shrink.

### Structure first, then look

Map every component and relationship for accuracy alone, ignoring position and
style; challenge the connections while doing it. Only then reposition, restyle,
and balance — without changing what the diagram claims. Doing both at once
produces diagrams that are pretty and wrong.

### Typography and shapes

XL 40–48px titles · L 24–32px headers · M 16–20px body · S 12–14px labels.

Rectangles for most things, circles for start/end/actors, diamonds for
decisions, ellipses when a mind map wants an organic feel. Arrows thin (1–2px)
by default, medium (3–4px) for emphasis.

### Bundled libraries

`.excalidrawlib` files ship in `libraries/` beside this file:

- `simple-sticky-notes` — sticky notes in seven colours; the only bundled
  library whose text is already bound to its container
- `banners`, `clouds` — section headers, and mind-map topic holders
- `calendar`, `organization-chart` — month templates, org charts
- `flow-chart-symbols` — start/end, process, decision, document, manual input
- `mathematical-symbols` — drawn to sit beside Virgil text
- `data-processing` — pipeline stages
- `stick-figures`, `stick-figures-collaboration` — people, and group scenes

**Only version-2 libraries ship here.** A v1 file stores bare element arrays
under `library` with no item names, so nothing can ask it for anything by name.
Do not add one: find a v2 equivalent, or go without.

**Library text is usually unbound.** Only `simple-sticky-notes` ships text with
a `containerId`; everywhere else the labels float, which is the desync this
skill forbids. After pasting an item, either bind its text or treat the label as
decoration you will replace.

Load through the Excalidraw library panel → "Load library from file". Recolour
to the palette below, use 1–3 icons per section, size them to the neighbouring
text, and do not mix icon styles within one diagram. Material Symbols Outlined
SVGs are a good source for anything the bundled libraries lack.

To place a library item by script instead, list the items and emit one as an
appendable element group:

```bash
python3 scripts/excalidraw-view.py libraries/stick-figures.excalidrawlib lib
python3 scripts/excalidraw-view.py libraries/stick-figures.excalidrawlib \
  item "Grandma" --after b3lh --at 400,3400 > /tmp/group.json
```

`item` mints fresh ids, seeds and indices and rewrites the group's internal
references, so the output appends straight onto `elements`. Pass the target's
current max `index` as `--after` (read it from `summary`) and validate with
`check` afterwards. Older libraries store items unnamed — `lib` gives those a
`#N` selector.

### Export

White background, background enabled, 2–3× scale, "Embed scene" on so the file
stays editable. Export properly — never screenshot.

## Colour palette (user's theme)

Muted retro-terminal, low saturation, dark text on white.

| Role                          | Hex                    |
| ----------------------------- | ---------------------- |
| Emphasis / goals / headers    | `#c9b458` (muted gold) |
| Success / active              | `#8fbc8f` (soft green) |
| Success, brighter accent      | `#76c893`              |
| Info / links                  | `#7a9fbf` (muted blue) |
| Warning / queued              | `#ffa500` (orange)     |
| Error / blocked               | `#ff6666` (soft red)   |
| Primary text, text on fills   | `#1a1a1a`              |
| De-emphasised text, done work | `#888888`              |
| Borders, default arrows       | `#404040`              |
| Surface / completed fills     | `#252525`              |

Rules:

- **4–6 colours maximum per diagram.** Rainbow explosion and saturation fights
  both read as noise. Colour must mean something.
- **Fills at 10–35% opacity**, with `#1a1a1a` text on top. Solid fill only where
  maximum contrast is needed.
- **4.5:1 contrast minimum.** `#1a1a1a` on white is 19.6:1, on gold 9.2:1, on
  green 8.1:1, on orange 7.5:1. `#888888` on white is 5.6:1 — de-emphasis only.
- **Never light text on white** (`#b8c5b8`, `#a89968` fail there).
- Check the result is still legible to colourblind readers.

## Before calling it done

- One clear primary focus; consistent sizing within each hierarchy level.
- Every arrow bound at both ends; every text bound to its container.
- Flow unambiguous, crossings only where unavoidable.
- Palette limited and meaningful; contrast holds.
- Consistent roughness and fill pattern; no orphaned elements.
- Readable at the size it will actually be viewed.
- For a hand-written or script-edited `.excalidraw`:
  `scripts/excalidraw-view.py FILE check` passes, and the file opens.
