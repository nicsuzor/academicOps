---
id: diagram-pkb-graphs
title: Drawing PKB graphs in Excalidraw (tools:diagram)
type: spec
category: skill
status: draft
depends_on: []
tags: [spec, skill, diagram, excalidraw, pkb, graph, layout, encoding]
---

# Drawing PKB graphs in Excalidraw

## Overview

The contract for how an agent using `tools:diagram` turns a PKB graph selection into a layered Excalidraw map that a person can read without clicking, edit by hand, and reconcile with the graph. The agent makes every design decision: layout, encoding, legend, badges. mem enables it and decides none of them.

## Division of labour

| Owner                                                                                                                                       | Provides                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| mem, [`nicsuzor/mem` `specs/graph-visualisation-export.md`](https://github.com/nicsuzor/mem/blob/main/specs/graph-visualisation-export.md)  | Edge and node data (weights, `weight_valid`, justification, `layer`, feeder and onward counts, outside-selection counts); closure and trace selection; the truncation flag; full, untruncated card text; a valid, non-overlapping, deterministic default placement; edit-preserving merge into an existing canvas; the round trip (diff, sync); the route for presentation edits that are not data changes; element primitives and audits ([`specs/excalidraw-tooling.md`](https://github.com/nicsuzor/mem/blob/main/specs/excalidraw-tooling.md)); rendering to PNG and SVG; the career-set test fixture. |
| this skill                                                                                                                                  | The procedure below; layout; the kind and state encoding; the weight-to-width scale; labels, legend, headings, badges and title elements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| overwhelm-dashboard, [`specs/view-force-layered.md`](https://github.com/nicsuzor/overwhelm-dashboard/blob/main/specs/view-force-layered.md) | The interactive force view of the same data. It adopts the encoding table and weight-to-width scale defined here; this spec is canonical where they diverge.                                                                                                                                                                                                                                                                                                                                                                                                                                               |

Nothing here restates a mem requirement. Where a rule below depends on one, it names the mem capability.

## Core behaviour

### Procedure

- **DG-P1 Select by closure [now].** A layered map starts from mem's closure or trace selection over `contributes_to`, never a hop-based fetch. If mem reports the selection truncated, the agent stops and reports the dropped count before drawing.
- **DG-P2 Edit in place [now].** The agent applies layout and encoding to mem's exported elements with mem's primitives. Every managed element (one carrying `customData.pkb`) keeps its `id`; none is deleted and redrawn. Everything the agent adds that is not a node or edge (headings, legend, badges, title, summary) is a presentation element, created through mem's presentation route.
- **DG-P3 Presentation is not data [now].** Every display change to a managed element (restyle, re-wrap, shortened display text) goes through mem's presentation route, so that diff does not read it as a data edit.
- **DG-P4 Zero diff before handover [now].** After drawing, the agent runs mem's diff of the canvas against the live PKB. Any change of any kind is a failure: the agent stops and reports it and does not hand the canvas over.
- **DG-P5 Projection only [now].** The agent never authors parentage, weight or status on the map, and never syncs the canvas to the graph as part of drawing. If the map looks wrong, the fix is to the node; the map is a projection. (Weights written from the canvas by a person: open decision OD-6.)
- **DG-P6 Redraw into an existing canvas [now].** The agent redraws through mem's merge. It lays out only the cards mem flags as new, places them in their layer column without overlap, and leaves every card the person moved or resized where it is. It does not touch unmanaged elements.

### Layout

- **DG-L1 Layer columns [now].** Every card sits in the column for its `layer`, columns left to right in mem's configured layer order. Above each column is a heading naming the layer and the number of cards in it.
- **DG-L2 No collisions [now].** No two cards overlap; no card overlaps a heading, the legend or an arrow label; no `contributes_to` arrow passes through a card that is not one of its endpoints. Arrows are routed around cards, or cards are ordered within columns so that none is crossed. Test: mem's overlap and arrow-crossing audits each report zero over all non-frame elements.
- **DG-L3 Fits a laptop screen [now].** The scene's aspect ratio (width to height) is between 1:1 and 2.5:1, and at zoom-to-fit on a 1,366 by 768 viewport, card title text renders at 9 px or larger. Test: from the scene's extents, `title font size × min(1366 / width, 768 / height) ≥ 9`.
- **DG-L4 Fits an iPad [now].** In Excalidraw on an iPad in landscape (1,180 by 820 points), zoom-to-fit shows every column heading legibly and zoom to 100% shows full card text. Checked by a person on the device.
- **DG-L5 Guard band [now].** Nodes in the `guard` layer sit in a separate, labelled band outside the columns, not in the flow.

### Card text

- **DG-T1 Layer prefix [now].** A title prefix that repeats the layer ("Future:", "Resource class:", "Audience:", "Channel:", "Stakeholder:", "Guard:") may be dropped from the displayed text, only when the card's layer is shown by both its column and its shape, and only through mem's presentation route. The stored title is unchanged and DG-P4 still holds. Any re-wrap keeps the full title.
- **DG-T2 No tags [now].** Cards in a layered map do not print tags.

### Link strength

- **DG-W1 Weight-to-width scale [now].** A `contributes_to` arrow's stroke width comes from its numeric weight on this scale, in scene units at 100% zoom. The scale is binned so that any value in [0, 1] maps, including derived products (DG-W4).

  | Numeric weight | Width              | Vocabulary term at that value |
  | -------------- | ------------------ | ----------------------------- |
  | ≥ 0.95         | 8                  | certain (1.00)                |
  | 0.80 to < 0.95 | 6                  | probable (0.85)               |
  | 0.65 to < 0.80 | 4.5                | expected (0.75)               |
  | 0.40 to < 0.65 | 3                  | fifty-fifty (0.50)            |
  | 0.20 to < 0.40 | 2                  | uncertain (0.25)              |
  | 0.05 to < 0.20 | 1.25               | improbable (0.15)             |
  | < 0.05         | 0.75, muted colour | impossible (0.00)             |

  Test: in the scene JSON, for every pair of fixture arrows with different valid terms, the arrow with the higher weight is wider.
- **DG-W2 Term labels and legend [now].** Each `contributes_to` arrow carries a bound label with its verbal term as stored. A legend on the canvas lists each term, its numeric value and its width.
- **DG-W3 Invalid term [now].** An arrow mem reports with `weight_valid: false` is drawn dashed, width 2, in the palette's warning colour, labelled with the raw term followed by "?". Test: every fixture edge with `weight_valid: false` is drawn this way, and no other.
- **DG-W4 Probability [needs model change].** When edges carry probability, width comes from weight × probability on the DG-W1 bins; the label shows both terms; the legend says so.
- **DG-W5 Negative contribution [needs model change].** A negative edge is drawn dotted, with a bar arrowhead, in the palette's error colour, and its label starts with a minus sign. It reads as negative without colour.
- **DG-W6 Severity [needs model change].** A target's severity is drawn on its card, not its edges: border width in discrete steps plus a text badge. The legend names the channel.

### Kind and state

- **DG-K1 Kind encoding table [now].** Each kind has a distinct combination of shape, fill colour and fill pattern. No two kinds share both shape and fill; no two share both shape and pattern, so kind survives greyscale. Fill colours are skill palette roles.

  | Kind (layer) | Shape                    | Fill colour | Fill pattern |
  | ------------ | ------------------------ | ----------- | ------------ |
  | work         | rectangle, sharp corners | none        | none         |
  | channel      | rectangle, rounded       | info        | hachure      |
  | stakeholder  | ellipse                  | info        | hachure      |
  | audience     | ellipse                  | success     | cross-hatch  |
  | resource     | rectangle, rounded       | success     | solid        |
  | future       | diamond                  | emphasis    | solid        |
  | goal         | ellipse                  | emphasis    | solid        |
  | guard        | rectangle, sharp corners | muted       | cross-hatch  |

  A layer the configuration defines but this table does not gets a rounded rectangle with no fill and a text badge naming the layer, and the agent reports it. The skill ships this table and the DG-W1 scale as one reference file in its own directory; this spec is the contract that file implements. An on-canvas legend shows each kind present.
- **DG-K2 State channel [now].** State uses border style, border colour and a text badge, which kind does not use. `ready`: solid border, no badge. `inbox`: dashed border, badge "inbox". `done`: muted border and text, reduced fill opacity, badge "done". Any other status: solid border, badge naming the status. A node with no status has a solid border and no badge.
- **DG-K3 Greyscale [now].** Kind and state are each readable in a greyscale render of the scene. Checked by a person against a greyscale export.
- **DG-K4 Satisfied [needs model change].** A target in the satisfied state carries a "satisfied" badge and reduced emphasis. Until the model has that state, the card shows its stored status only; the agent never infers state from body prose.
- **DG-K5 Unconfirmed estimate [needs model change; OD-4].** A node or edge recorded as an agent's unconfirmed estimate carries a distinct marker. Not buildable until a field exists; never inferred from prose.
- **DG-K6 Merge markers [now].** A card mem flags as new since the last export carries a "new" badge. A card mem flags as no longer in the selection carries a "no longer in graph selection" badge and muted styling; it is not removed. A card whose colour or shape the person has overridden keeps the override, and also carries text badges for its kind and state so both stay readable.

### Traces

- **DG-R1 Trace layout [now].** A trace-from or trace-into scene follows every layout and encoding rule above. In a trace-into scene, the focus node's direct contributors are ordered top to bottom by edge weight, strongest first; ties by node id; invalid terms last. Each shows its weight label.
- **DG-R2 Trace title [now].** Each trace scene carries a title element stating the focus node's full title, the direction (from or into) and the date of export.

### Gaps

- **DG-G1 No feeders [now].** A card outside the work layer with no incoming `contributes_to` edge in the whole graph (mem's feeder count and outside-contributor count both zero) carries a "no feeders" badge. The guard never carries it.
- **DG-G2 No onward path [now].** A card in any layer before goal with no outgoing `contributes_to` edge in the whole graph (onward count and outside-destination count both zero) carries a "no onward path" badge. Goals and the guard never carry it.
- **DG-G3 Outside the selection [now].** A card with contributors or destinations outside the selection carries a "+n outside" marker, n being mem's count, and no gap badge on that account.
- **DG-G4 Gap legend and summary [now].** The legend explains each badge. A summary text element gives the count of each badge on the canvas.

Test for DG-G1 to DG-G3: the expected sets are computed from the export at test time; the badges on the canvas match them exactly.

### Images

- **DG-I1 Legible PNG [now].** The PNG rendered by mem's renderer at 2× scale shows every card title legibly when viewed at 100%, with no title text outside its card. Checked by a person.
- **DG-I2 Real commands only [now].** `SKILL.md` names only commands that exist. Test: every command it names runs its help in the worker container and exits 0.

## Boundaries and constraints

- The skill does not compute selections, counts or layers, and does not truncate text; those are mem's. It does not reimplement merge or the round trip.
- It draws `contributes_to` only, without frames or containment, unless asked (OD-7).
- It never parses justifications or body prose for state, provenance or weight.
- It never ranks or sorts futures by any computed score. A path's product of weights is not a ranking signal.
- Out of scope: the model changes themselves (probability, negative contributions, non-linear severity, a satisfied state, a provenance field); pricing targets or changing any weight, intent, severity or due date; the dashboard's views; hand-built maps and their separate builder; hosted or multi-user canvas services; PKB search and tag listing.

## Output contract

On handover the agent reports:

- the canvas path and the rendered PNG and SVG paths;
- mem's diff result for the canvas (must be empty, DG-P4);
- the overlap and arrow-crossing audit results (must be zero, DG-L2);
- the selection used, and mem's truncation flag;
- the count of each badge (DG-G4), and any layer not in the DG-K1 table.

Tests compute every expected value (node, edge and badge counts, invalid edges, longest title) from mem's export of the career-set fixture at test time. None is hard-coded.

## Open decisions (Nic)

- **OD-2 A target that feeds futures and is also linked from one.** Recommended: draw it in the layer its edges give it (resource); the goal column holds only nodes with no onward edge, unless edges are added from futures to it.
- **OD-3 Notes tagged into the selection with no contribution edges.** Recommended: off the map by default, available as an option; when included, drawn in a separate labelled band.
- **OD-4 Unconfirmed estimates.** No field exists. Recommended: do not parse prose; make DG-K5 depend on a provenance value on the edge, decided alongside the other edge changes.
- **OD-6 Weights from the canvas.** Should a hand-drawn arrow or an edited weight label be allowed to write a `contributes_to` edge? Recommended: yes, through dry-run and confirmation only, because weights are the user's to set and the canvas is where they will be looking. This reverses DG-P5 for this one field.
- **OD-7 Other edge types.** Recommended: `contributes_to` only by default; `depends_on` as an option, drawn thin and grey with no weight label; `parent` and body links off.
- **OD-8 Done work.** Recommended: shown, greyed (DG-K2), by default, because finished work that built a resource is part of how a future became reachable.
