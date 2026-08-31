---
name: diagram
description: Creating diagrams in any style — Mermaid flowcharts (structured, code-based) or Excalidraw (hand-drawn, organic, PKB task/knowledge graphs). Use style parameter to select.
---

# Diagram

Make diagrams that communicate one thing clearly. Mermaid and Excalidraw syntax
is public knowledge — what follows is the routing rule, the user's taste, and the
hazards syntax knowledge does not cover.

## Objective and audience — write these before anything else

**A chart is a tool for making a decision. Name the decision first.**

Almost every bad chart is a chart whose author never said who it was for or what
it was for, and so reached for "make it look nice" — or worse, invented
structure to fill the space. Before laying anything out, write two sentences and
keep them with the chart:

- **Objective** — the decision or action this chart makes possible. _"Choose
  what to do with a free afternoon"_, _"find where the request stalls"_, _"decide
  whether to merge these two teams"_. Not the subject: _"the projects"_, _"the
  architecture"_, _"our tasks"_ are topics, not objectives. Test it: if the
  reader finished looking, what could they now do that they could not before?
- **Audience** — who reads it, what they already know, what they will do next,
  where they will read it (phone, laptop, printed, in a meeting), and how long
  they will look. An expert who knows every node needs _less_ on the page, not
  more; a newcomer needs orientation and labels.

Ask the user for both when they are not stated. It is a cheap question and it is
the single highest-leverage thing you can ask about a diagram. Do not guess them
silently — a wrong objective produces a chart that is beautiful and useless.

Everything downstream is derived from these two:

| Derived decision               | How the objective/audience settles it                                                          |
| ------------------------------ | ---------------------------------------------------------------------------------------------- |
| What earns a place             | Only what serves the objective. An item the reader can do nothing with is noise, however true. |
| Which layout family            | See routing table below.                                                                       |
| Which attributes get a channel | Only the ones the reader acts on. Everything else stays uniform.                               |
| How much detail                | Expert audience → less. Unfamiliar audience → labels, legend, orientation.                     |
| Density and size               | Wall poster, laptop, and phone are three different charts.                                     |
| What may be omitted            | Whatever the objective does not need — but say so; see honest omission.                        |

### Layout family routing

| The reader's question         | Family                       | Notes                                                                                        |
| ----------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------- |
| "What do I do next?"          | Containment + state emphasis | Group by whatever the doer navigates by; make live work and small-enough-to-start items pop. |
| "How does this work?"         | Flow / sequence              | Needs arrows and direction — usually Mermaid, not Excalidraw.                                |
| "Where does this fit?"        | Containment / nesting        | Cover the whole space; nesting depth beyond ~3 stops being readable.                         |
| "How do these compare?"       | **Matrix / grid**            | The one case where a uniform grid is _correct_ — equal cells make cells comparable.          |
| "What changed / what is off?" | Comparison or anomaly layout | Do not smooth the data; the outliers are the message.                                        |
| "When does this happen?"      | Timeline                     | Position encodes time; nothing else may.                                                     |
| "What is central here?"       | Radial / hub                 | One thing at the centre, relationships roughly equal in kind.                                |

A grid is not inherently boring — it is _wrong when the question is not
comparison_. Reaching for one by default is the failure, not the shape itself.

### Every channel must be backed by a real field

- **Never author structure, weight, or status into a chart.** They come from the
  source of truth — the task graph, the repo, the dataset. If the source does
  not carry the value, you have found a gap in the source: fix it there, or say
  plainly that the chart cannot show it. Inventing a plausible-looking ranking
  and drawing it is fabrication, and it is indistinguishable from real data once
  it is on the page.
- **Check that the field means what its name says** before you bind it to a
  channel. Computed and propagated fields are the usual trap: a score that sums
  an unbounded term will rank a trivial item above the goal it serves; an
  "exposure" flag that propagates up a tree will mark containers that have no
  exposure of their own. Spot-check the extremes of any field before encoding
  it, and if it fails, encode something else and file the defect.
- **One channel, one meaning**, declared in a legend or a companion note.
- **Unspent channels stay uniform on purpose.** Variation the reader cannot
  decode is noise wearing a vocabulary's clothes.

### Honest omission

Charts lie most often by omission, and the lie is usually accidental: an author
draws a useful subset and the result reads as a complete inventory.

- When a container shows fewer children than it has, **say so on the container**
  ("showing 3 of 12").
- Reserve "collapsed" for a true chain-of-one. If you drew one branch of a wide
  tree, that is a subset, not a collapse — **verify the child counts before
  labelling it either way.**
- Never dress your own selection up as a property of the data. A group of
  leftovers from your subset is not "unfiled" or "orphaned" unless the source
  actually says so.

## Style routing

- `style="mermaid"` — structured, code-based flowcharts. Use when the diagram
  lives in documentation, is read in a diff, and must stay in version control.
- `style="excalidraw"` — hand-drawn, organic. Use for mind maps, concept maps,
  PKB knowledge/task graphs, informal architecture sketches, and presentation visuals where feel matters.

If the user has not said which, ask before drawing. Converting after the fact
loses the layout work.

## Working live with the user

A diagram file the user has open is a two-way conversation surface, not a
one-shot deliverable — their edits in the app are messages to you, made in the
diagram's own visual language instead of prose. Before writing, check whether
the file changed since you last saved it (mtime, or diff against what you last
wrote); if so, read what moved, what was deleted, what was relabelled, and
treat that as their reply before doing anything else. Never overwrite a live
file blind. Fold what you learn into whatever else it implies — a task in the
PKB, a spec, code — then bring your own response back as a change to the same
diagram, not as an explanation of it.

## Craft rules (both styles)

- **One message per chart.** State the purpose in one line first ("how a session
  moves from prompt to cleanup"), then cut everything that does not serve it. A
  deep sub-process gets its own chart.
- **Chunk.** Group related steps; keep any one group under 6–9 nodes.
- **Happy path on a straight spine.** Exceptions and loops go to the side.
  Minimise backward arrows and edge crossings.
- **Verb-first labels, 3–9 words.** Detail goes in a note or legend, never inside
  the box. Big blocks of text in boxes are the most common failure.
- **State the fact, not its history.** A node or tag says what is true now
  (`[DARK]`, `[PROPOSED]`) — never why, when, or what it used to be. No dates,
  no "removed 2026-08", no "was: X, Y, Z" audit trails. That belongs in git or
  a spec; a diagram that narrates change is a log wearing a diagram's shape.
- **Distinct shapes carry distinct semantics** — process, decision, terminal,
  data/IO. Never reuse one shape for two meanings in the same chart.
- **Same hierarchy level, same size and weight.** Uniform everything is chaos;
  so is arbitrary variation.
- **No prose or investigation notes.** Diagrams depict system state and architecture, not investigation history. If something needs a dated log or investigation notes, put it in git commits, specs, or memory (`remember`). Never append investigation notes to an existing diagram file.

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

> **Note:** Excalidraw has a unique hand-drawn aesthetic; graphs look best if they are not regular. If you use an automated layout, you must manually move nodes around afterward to break the grid and make the graph aesthetically pleasing and organic.

Excalidraw charts are hand-drawn, organic, and expressive. When constructing Excalidraw
diagrams, focus on **semantic topology** and **composition** using the **5-Layer Composition Model**,
delegating initial physical coordinate calculation to layout engines and native tooling (`excalidraw-view`), followed by manual organic adjustment.

### Aesthetic defaults

| Property      | Value        | Why                                      |
| ------------- | ------------ | ---------------------------------------- |
| `roughness`   | `2`          | Maximum sketchiness — commit to the look |
| `fontFamily`  | `1` (Virgil) | Handwritten, never Helvetica             |
| `fillStyle`   | `"hachure"`  | Sketchy hatching, not solid fill         |
| `strokeStyle` | `"solid"`    | Reads as hand-drawn at roughness 2       |

Canvas background is **white**, always. The palette below is a terminal theme,
but diagrams need contrast and printability — never a dark canvas.

### The 5-Layer Composition Model

Construct Excalidraw diagrams conceptually using this 5-layer model instead of flat arrays of boxes:

1. **Scenery**: Background boundaries and logical zones (`--preset zone` or enclosing frames). Nodes should be grouped together with their bounding border and all elements within that border (e.g. all text captions and boxes subsumed within).
2. **Spine**: The critical path and focal landmark nodes (`--preset hero`). Highlights the root node of an ego-network, current active task, or main sequence. Scale should be used to indicate hierarchy or importance, with children nodes markedly smaller than parents.
3. **Satellites**: Supporting utility components and standard operational nodes.
4. **Annotations**: Human commentary and context via sticky notes (`--preset sticky`). Explains rationale and "why" connections exist.
5. **Connectors**: Solid flows vs. dashed telemetry (`--curved`, `--stroke-style dashed`). Use curved arrows to radiate either out (spiral or star/spoke layout) or down (hierarchy).

### Aesthetic Presets and Layout Engines

When building diagrams mechanically (e.g., via the `batch` JSON DSL or CLI tools), DO NOT attempt to guess manual X,Y pixel coordinates. Instead, use topology and semantic flags:

- Use layout engines (`--layout radial` for hub-and-spoke ego-networks, or let `layout.rs` use the Sugiyama defaults for pipelines) to place nodes automatically.
- Use `--preset hero` to emphasize landmark focal nodes.
- Use `--preset sticky` for human commentary and rationale.
- Use `--preset zone` for boundary boxes (Scenery).
- Use `--curved` and `--stroke-style dashed` for non-critical path connections.

- **Topology first, layout second**: Declare components and relationships accurately. Let the backend layout engine calculate physical space.
- **Organic adjustment**: After automated layout, **manually move nodes around** to break the perfect grid. The hand-drawn aesthetic demands irregular, pleasing spacing.
- **Layout engine choices**:
  - **Radial Layout** (`--layout radial`): Ideal for ego-networks and hub-and-spoke concept maps (one central focal node, radiating relationships).
  - **Sugiyama Layered DAG Layout**: Default for pipelines, task dependency trees, and directed workflow sequences.
- **Semantic flags**:
  - `--preset hero`: Emphasizes landmark focal nodes.
  - `--preset sticky`: Adds commentary / rationale cards.
  - `--preset zone`: Defines boundary and domain grouping boxes.
  - `--curved` and `--stroke-style dashed`: Differentiates secondary / non-critical path connections.

Construct diagrams conceptually using this model instead of flat arrays of boxes:

1. **Scenery**: Background boundaries and logical zones (`--preset zone`).
2. **Spine**: The critical path and focal landmark nodes (`--preset hero`).
3. **Satellites**: Supporting utility components (default nodes).
4. **Annotations**: Human commentary via sticky notes (`--preset sticky`).
5. **Connectors**: Solid flows vs. dashed telemetry (`--curved`, `--stroke-style dashed`).

### Reading and Inspecting an Existing File

Never read a `.excalidraw` file raw. It is minified JSON — offset/limit cannot window it,
and raw dumping wastes context tokens. Use the native `excalidraw-view` CLI for token-efficient and invariant-safe operations:

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

`summary` then `map` gives full situational awareness. Add `style` before creating
elements so new additions match the house look.

### Editing and Mutating Excalidraw Files

Mutate `.excalidraw` files through `excalidraw-view` CLI commands or declarative batch specs — never
by ad-hoc string replacement against raw JSON.

- **Back up first** (`cp FILE FILE.bak-<date>`).
- **Use CLI mutations (`excalidraw-view`)**:
  - `excalidraw-view FILE add-node --type <type> --text "<text>" [--preset hero|sticky|zone] [--at X,Y] [--size W,H] [--color <hex>]`
  - `excalidraw-view FILE add-text --text "<text>" --at X,Y [--font-size <size>] [--color <hex>]`
  - `excalidraw-view FILE connect --from <id1> --to <id2> [--label "<label>"] [--curved] [--stroke-style dashed|solid]`
  - `excalidraw-view FILE set-text <id> "<new_text>"`
  - `excalidraw-view FILE fit <id> "<new_text>"`: Recomputes text bounding box and grows container centered to prevent text overflow.
  - `excalidraw-view FILE move-elem <id> [--to X,Y | --by DX,DY]`
  - `excalidraw-view FILE delete-elem <id> [--cascade-arrows]`
  - `excalidraw-view FILE batch <changes.json | ->`
- **Validation commands**:
  - `excalidraw-view FILE check`: Full referential integrity and z-index ordering validation.
  - `excalidraw-view FILE overlap`: Flags bounding-box collisions between non-nested sibling elements.
  - `excalidraw-view FILE arrows-check`: Flags any arrow whose polyline cuts through a shape it isn't bound to at either end.
- **Theme application**:
  - `excalidraw-view FILE theme apply retro-terminal`
- **Invariants**:
  - **Text binds to its container** (`containerId` on text, `boundElements` on shape).
  - **Arrows bind at both ends** (`startBinding` and `endBinding`).
  - **Write both text layers, always**: Both `text` and `originalText` must be updated to prevent Excalidraw from re-wrapping stale text on subsequent edits.
  - **Index ordering**: Elements must remain strictly sorted by ascending fractional `index` key (`a00`, `a01`, ...).
  - **Never append investigation notes to a diagram file.** Put investigation notes in git commits, specs, or memory (`remember`).

### Emphasis and placement — the difference between a chart and a grid

A boring chart is a uniform chart: every box the same size, same fill, same
font, snapped to rows and columns. Uniformity claims that nothing matters more
than anything else — which is never true, so the reader gets no argument, only
inventory. Before styling anything, answer three questions and let the answers
drive geometry:

1. **What should the eye hit first?** Not "the title" — the thing the viewer
   should act on or worry about. Give it the strongest signal you have: the
   deepest fill, the biggest type, the most whitespace around it. There can be
   only a handful of first things; if six items are emphasised, none are.
2. **What varies, and what does the variation mean?** Every visual channel —
   size, fill, stroke style, type scale, a corner marker — must be spent on
   exactly one meaning, stated somewhere the reader can find (a small key, or a
   companion note). Size = weight, fill = state, dashed = unshaped is a working
   vocabulary; size = whatever-fit-the-text is noise wearing a vocabulary's
   clothes. Unspent channels stay uniform on purpose.
3. **What is near what, and why?** Placement is a claim. Cards that belong to
   the same effort sit in one cluster with macro-whitespace around it; a child
   sits beside its parent; a deliberate pair overlaps like stacked paper.
   Distance apart reads as unrelatedness — so a grid, which equalises all
   distances, erases every relationship the layout could have carried. Break
   the grid: vary offsets by a few pixels, let clusters breathe unevenly, put
   the emphasised thing off-axis. Organic ≠ sloppy; it means spacing follows
   meaning instead of a ruler.

Two disciplines keep this honest on a canvas that lives longer than one pass:

- **A hand-edited canvas is user speech. Restore, never regenerate.** If a
  person has moved, deleted, resized, or recoloured elements, those positions
  and absences carry their judgment. Regenerating the file from data — however
  much prettier the output — destroys their layout and is the single most
  destructive thing an agent can do to a shared canvas. Diff against the last
  revision, apply your changes around their geometry (zones grow outward;
  frozen positions stay byte-identical), and treat their deletions as decisions
  to honour, not gaps to refill.
- **The encoding lives in a companion registry, and every pass re-reconciles
  it.** A canvas with a visual vocabulary needs one place (a note beside it)
  stating what each channel means, which conventions are suspended, and what
  the last pass changed. Read it before editing; update it after. An agent that
  edits the canvas without the registry — or the registry without the canvas —
  leaves the next agent to reverse-engineer meaning from pixels, and that is
  how vocabularies rot.

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

To inspect or place a library item via CLI:

```bash
excalidraw-view libraries/stick-figures.excalidrawlib lib
excalidraw-view libraries/stick-figures.excalidrawlib \
  item "Grandma" --after b3lh --at 400,3400 > /tmp/group.json
```

`item` mints fresh ids, seeds and indices and rewrites the group's internal
references, so the output appends straight onto `elements`. Pass the target's
current max `index` as `--after` (read it from `summary`) and validate with
`check` afterwards. Older libraries store items unnamed — `lib` gives those a
`#N` selector.

### Generating and Syncing with PKB (Personal Knowledge Base)

For any chart whose job is "show a hierarchy and the state of the things in it" — task trees, org charts, service maps, module structure — use the native `pkb` binary instead of writing new generators or editing large JSON arrays directly.

**Generating Canvases:**

- `pkb excalidraw export <output_path> [--focus <node_id>] [--hops <H>]`: Exports the knowledge graph or an ego-network using the Sugiyama layered DAG layout engine.
- `pkb graph --format excalidraw [--focus <id>] [--hops <H>]`: High-level graph export option.
  _(Also available via MCP server tools: `graph_excalidraw`)_

**Diffing and Syncing:**
When the user edits the generated Excalidraw canvas visually (e.g., reparenting nodes, changing status colors, removing dependencies), reconcile those visual edits back into the markdown graph:

- `pkb excalidraw diff <canvas_path> [--base <snapshot>] [--json]`: Computes a 3-way visual diff between the base snapshot, live PKB graph state, and the modified Excalidraw JSON. Tracks node additions, updates (title, status, intent, parent, tags), deletions, and edge modifications.
- `pkb excalidraw sync <canvas_path> [--base <snapshot>] [--dry-run] [--sync-edge-removals]`: Applies canvas changes back into the markdown frontmatter on disk. Utilizes spiral placement for new nodes and prevents circular dependencies.
  _(Also available via MCP server tools: `diff_excalidraw`, `sync_excalidraw`)_

**Non-destructive removal**: Removing a card from the canvas marks it as `removed_from_canvas` in the `pkb` diff and never deletes the underlying document.

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
- Structural verification passes:
  ```bash
  excalidraw-view FILE check
  ```
