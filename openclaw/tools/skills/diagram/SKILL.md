---
name: diagram
description: Draw, edit and review diagrams — Mermaid for flowcharts, sequences and architecture that live in version control, or Excalidraw canvases for mind maps, concept maps, PKB task/knowledge graphs and hand-drawn sketches. Use when asked to diagram, chart, map, sketch or visualise a system, flow, hierarchy or task graph; when editing an existing `.excalidraw` or Mermaid file; or when exporting, diffing or syncing a PKB graph to a canvas. Covers objective setting, layout routing, the house palette and typography, `excalidraw-view` CLI mechanics, and `pkb excalidraw` export/diff/sync. Not for plotting quantitative datasets (use a data-visualisation skill), and not for UI mockups or page design.
---

# Diagram

Mermaid and Excalidraw syntax is public knowledge. What follows is the routing
rule, the user's taste, and the hazards syntax knowledge does not cover.

## Fix the objective and audience before drawing

Write two sentences and keep them with the chart. Ask the user when they are
not stated, because a wrong objective produces a chart that is beautiful and
useless.

- **Objective** — the decision or action this chart makes possible ("choose
  what to do with a free afternoon", "find where the request stalls"). A topic
  ("the projects", "the architecture") is not an objective. Test it: what can
  the reader do after looking that they could not before?
- **Audience** — who reads it, what they know, what they do next, where they
  read it (phone, laptop, print, meeting). An expert needs _less_ on the page;
  a newcomer needs orientation and labels.

Everything downstream derives from them: only what serves the objective earns a
place, only attributes the reader acts on get a visual channel, and density
follows the viewing surface.

### Layout family routing

| The reader's question         | Family                       | Notes                                                                   |
| ----------------------------- | ---------------------------- | ----------------------------------------------------------------------- |
| "What do I do next?"          | Containment + state emphasis | Group by what the doer navigates by; make live and startable items pop. |
| "How does this work?"         | Flow / sequence              | Needs arrows and direction — usually Mermaid, not Excalidraw.           |
| "Where does this fit?"        | Containment / nesting        | Cover the whole space; nesting past ~3 deep stops being readable.       |
| "How do these compare?"       | Matrix / grid                | The one case where a uniform grid is correct — equal cells compare.     |
| "What changed / what is off?" | Comparison or anomaly        | Do not smooth the data; the outliers are the message.                   |
| "When does this happen?"      | Timeline                     | Position encodes time; nothing else may.                                |
| "What is central here?"       | Radial / hub                 | One thing at the centre, relationships roughly equal in kind.           |

Reaching for a grid by default is the failure, not the shape itself.

### Bind every channel to a real field

- **Read structure, weight and status from the source of truth** — the task
  graph, the repo, the dataset — never author them. If the source does not
  carry the value, fix it there or say plainly that the chart cannot show it.
  An invented ranking is indistinguishable from real data once it is drawn.
- **Spot-check the extremes of a field before encoding it**, because computed
  and propagated fields routinely mean something other than their name: a score
  summing an unbounded term ranks a trivial item above the goal it serves; an
  "exposure" flag propagated up a tree marks containers that have no exposure
  of their own. If it fails, encode something else and file the defect.
- **One channel, one meaning**, declared in a legend or companion note. Unspent
  channels stay uniform, because variation the reader cannot decode is noise.

### Omit honestly

- Say so on the container when it shows fewer children than it has ("showing 3
  of 12"), and verify child counts before labelling.
- Reserve "collapsed" for a true chain-of-one; one branch of a wide tree is a
  subset.
- Never dress your own selection up as a property of the data — leftovers from
  a subset are not "unfiled" or "orphaned" unless the source says so.

## Style routing

- `style="mermaid"` — documentation, diffs, version control.
- `style="excalidraw"` — mind maps, concept maps, PKB knowledge/task graphs,
  informal architecture sketches, presentation visuals where feel matters.

Ask when the user has not said, because converting after the fact loses the
layout work.

## Working on a file the user has open

Their edits in the app are messages to you, made in the diagram's own visual
language. Before writing, check whether the file changed since you last saved
it (mtime, or diff against what you last wrote); read what moved, what was
deleted, what was relabelled, and treat that as their reply. Never overwrite a
live file blind. Fold what you learn into whatever else it implies — a PKB
task, a spec, code — then answer as a change to the same diagram.

## Craft rules (both styles)

- **One message per chart.** State the purpose in one line, then cut what does
  not serve it. A deep sub-process gets its own chart.
- **Chunk**: keep any group under 6–9 nodes.
- **Happy path on a straight spine.** Exceptions and loops to the side;
  minimise backward arrows and edge crossings.
- **Verb-first labels, 3–9 words.** Detail goes in a note or legend, never
  inside the box.
- **State the fact, not its history.** A node or tag says what is true now
  (`[DARK]`, `[PROPOSED]`) — no dates, no "removed 2026-08", no "was: X"
  trails. A diagram that narrates change is a log wearing a diagram's shape.
- **Distinct shapes carry distinct semantics** — process, decision, terminal,
  data/IO — and never two meanings in one chart.
- **Same hierarchy level, same size and weight.**
- **Never append prose or investigation notes to a diagram file.** Those belong
  in git commits, specs, or memory (`remember`).

## Style: mermaid

**Default to `LR`.** Charts trend too tall and screens are wide. Reach for `TD`
only when branching genuinely fans out. For phases-with-steps, use `LR` at top
level with `direction TB` inside each subgraph.

**Link subgraph to subgraph**, never a subgraph-internal node to an outside
node — internal-to-external links force direction inheritance and wreck layout.

**Past ~15 nodes, or with many cross-links, switch to the ELK layout engine**
(`layout: elk`, `mergeEdges: true`, `nodePlacementStrategy: SIMPLE` in the
frontmatter config block); the default renderer degrades badly at that size.

**At 10+ steps, organise into numbered phases** (① ② ③) rather than one chain.
Colour phases by position (green → gold → gray for start → work → end) from the
palette below. Route hooks, agents and external services into a side panel
connected only by dashed edges, and only where the interaction is essential.

## Style: excalidraw

### Aesthetic defaults

| Property      | Value        | Why                                      |
| ------------- | ------------ | ---------------------------------------- |
| `roughness`   | `2`          | Maximum sketchiness — commit to the look |
| `fontFamily`  | `1` (Virgil) | Handwritten, never Helvetica             |
| `fillStyle`   | `"hachure"`  | Sketchy hatching, not solid fill         |
| `strokeStyle` | `"solid"`    | Reads as hand-drawn at roughness 2       |

Canvas background is **white**, always — diagrams need contrast and
printability.

### Compose in five layers, then let an engine place them

Build conceptually in layers rather than as a flat array of boxes:

1. **Scenery** — background boundaries and logical zones (`--preset zone`),
   each enclosing every element it subsumes (captions, boxes).
2. **Spine** — critical path and focal landmark nodes (`--preset hero`): the
   root of an ego-network, the active task, the main sequence. Scale carries
   hierarchy, so children are markedly smaller than parents.
3. **Satellites** — supporting and standard operational nodes (default style).
4. **Annotations** — human commentary and rationale (`--preset sticky`).
5. **Connectors** — solid flows vs dashed telemetry (`--curved`,
   `--stroke-style dashed`). Curved arrows radiate out (spiral, star/spoke) or
   down (hierarchy).

Declare topology and let the layout engine compute coordinates — never guess
X,Y pixels when building mechanically (batch JSON DSL, CLI). Use
`--layout radial` for ego-networks and hub-and-spoke concept maps; the Sugiyama
layered DAG (the `layout.rs` default) for pipelines, dependency trees and
directed workflows. Then **manually move nodes to break the grid**, because the
hand-drawn aesthetic demands irregular, pleasing spacing.

### Emphasis and placement

A uniform chart claims nothing matters more than anything else, so the reader
gets inventory instead of an argument. Give the thing the reader must act on
the deepest fill, biggest type and most surrounding whitespace — a handful at
most, since six emphasised items are none. Placement is a claim: one cluster
per effort with macro-whitespace around it, child beside parent, a deliberate
pair overlapping like stacked paper. A grid equalises every distance and so
erases every relationship the layout could carry, so vary offsets, let clusters
breathe unevenly, and put the emphasised thing off-axis.

Two disciplines keep a long-lived canvas honest:

- **A hand-edited canvas is user speech: restore, never regenerate.** Moved,
  deleted, resized and recoloured elements carry the person's judgment.
  Regenerating from data destroys it. Diff against the last revision, apply
  changes around their geometry (zones grow outward; frozen positions stay
  byte-identical), and treat deletions as decisions to honour.
- **Keep the encoding in a companion registry and re-reconcile every pass.**
  One note beside the canvas states what each channel means, which conventions
  are suspended, and what the last pass changed. Read it before editing, update
  it after — otherwise the next agent reverse-engineers meaning from pixels.

### Reading an existing file

Never read a `.excalidraw` file raw: it is minified JSON, offset/limit cannot
window it, and dumping it wastes context. Use `excalidraw-view`:

```bash
excalidraw-view FILE summary        # counts, extents, max index, order sanity
excalidraw-view FILE map            # shapes with labels, free text, arrow topology
excalidraw-view FILE nodes          # tabular list of nodes
excalidraw-view FILE edges          # tabular list of edges
excalidraw-view FILE style          # modal style values to copy for new elements
excalidraw-view FILE check          # structural validation — exit 1 on any fault
excalidraw-view FILE1 diff FILE2    # summary before/after diff (counts, removals, topology)
excalidraw-view FILE1 struct-diff FILE2 # semantic structural diff (ignores coordinate jitter)
excalidraw-view FILE inspect <id>   # inspect specific element attributes
excalidraw-view FILE get <id>       # retrieve element JSON
```

`summary` then `map` gives full situational awareness; add `style` before
creating elements so additions match the house look.

### Mutating a file

Mutate through `excalidraw-view` or declarative batch specs, never by ad-hoc
string replacement against raw JSON.

```bash
excalidraw-view FILE add-node --type <type> --text "<text>" [--preset hero|sticky|zone] [--at X,Y] [--size W,H] [--color <hex>]
excalidraw-view FILE add-text --text "<text>" --at X,Y [--font-size <size>] [--color <hex>]
excalidraw-view FILE connect --from <id1> --to <id2> [--label "<label>"] [--curved] [--stroke-style dashed|solid]
excalidraw-view FILE set-text <id> "<new_text>"
excalidraw-view FILE fit <id> "<new_text>"   # regrow container centred on recomputed text box
excalidraw-view FILE move-elem <id> [--to X,Y | --by DX,DY]
excalidraw-view FILE delete-elem <id> [--cascade-arrows]
excalidraw-view FILE batch <changes.json | ->
excalidraw-view FILE theme apply retro-terminal
```

Validate after every mutation:

```bash
excalidraw-view FILE check         # referential integrity and z-index ordering
excalidraw-view FILE overlap       # bounding-box collisions between non-nested siblings
excalidraw-view FILE arrows-check  # arrows cutting through shapes they are not bound to
```

Invariants:

- **Text binds to its container** (`containerId` on text, `boundElements` on
  shape); **arrows bind at both ends** (`startBinding`, `endBinding`).
- **Write both text layers**: update `text` and `originalText` together, or
  Excalidraw re-wraps stale text on the next edit.
- **Elements stay strictly sorted by ascending fractional `index`** (`a00`,
  `a01`, …).

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

**Add only version-2 libraries**, because a v1 file stores bare element arrays
under `library` with no item names and nothing can request an item by name.

**Library text is usually unbound** — outside `simple-sticky-notes` labels
float, which is the desync the invariants above forbid. After pasting, bind the
text or treat the label as decoration you will replace.

Load through the Excalidraw library panel → "Load library from file". Recolour
to the palette below, use 1–3 icons per section, size them to neighbouring
text, and keep one icon style per diagram. Material Symbols Outlined SVGs cover
what the bundled libraries lack.

```bash
excalidraw-view libraries/stick-figures.excalidrawlib lib
excalidraw-view libraries/stick-figures.excalidrawlib \
  item "Grandma" --after b3lh --at 400,3400 > /tmp/group.json
```

`item` mints fresh ids, seeds and indices and rewrites the group's internal
references, so its output appends straight onto `elements`. Pass the target's
current max `index` as `--after` (read it from `summary`) and run `check`
after. Unnamed items in older libraries get a `#N` selector from `lib`.

### PKB export and sync

For any chart whose job is "show a hierarchy and the state of the things in
it" — task trees, org charts, service maps, module structure — use the `pkb`
binary rather than writing generators or editing large JSON arrays:

```bash
pkb excalidraw export <output_path> [--focus <node_id>] [--hops <H>]
pkb graph --format excalidraw [--focus <id>] [--hops <H>]
pkb excalidraw diff <canvas_path> [--base <snapshot>] [--json]
pkb excalidraw sync <canvas_path> [--base <snapshot>] [--dry-run] [--sync-edge-removals]
```

Equivalent MCP tools: `graph_excalidraw`, `diff_excalidraw`, `sync_excalidraw`.

When the user edits a generated canvas — reparenting, status colours, dropped
dependencies — reconcile those edits back into the graph with `diff` then
`sync` rather than re-exporting over them. `diff` is 3-way across base
snapshot, live PKB state and the modified canvas, tracking node additions,
updates (title, status, intent, parent, tags), deletions and edge changes.
`sync` writes back into markdown frontmatter, placing new nodes by spiral and
refusing circular dependencies; a card removed from the canvas is marked
`removed_from_canvas` and its document is never deleted.

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

- **4–6 colours maximum per diagram**, each meaning something.
- **Fills at 10–35% opacity** with `#1a1a1a` text on top; solid fill only where
  maximum contrast is needed.
- **4.5:1 contrast minimum.** `#1a1a1a` clears it on white and on every fill
  above; `#888888` on white is 5.6:1 — de-emphasis only. Light tints
  (`#b8c5b8`, `#a89968`) fail on white, so keep text dark.
- Check the result stays legible to colourblind readers.

## Before calling it done

- One clear primary focus; consistent sizing within each hierarchy level.
- Every arrow bound at both ends; every text bound to its container.
- Flow unambiguous, crossings only where unavoidable.
- Palette limited and meaningful; contrast holds.
- Consistent roughness and fill pattern; no orphaned elements.
- Readable at the size it will actually be viewed.
- `excalidraw-view FILE check` passes.
