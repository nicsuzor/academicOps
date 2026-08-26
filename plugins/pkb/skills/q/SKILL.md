---
name: q
type: command
description: Stage 1 Intake & Capture — place an ask, fragment, or idea on the graph under the right parent, wire contributes_to/depends_on, densify with wikilinks, and record strategic valuation at intake, leaving status at inbox with NO acceptance criteria.
allowed-tools: [Skill, AskUserQuestion, mcp__services__pkb__create_task, mcp__services__pkb__update_task, mcp__services__pkb__update_body, mcp__services__pkb__search, mcp__services__pkb__task_search]
---

# /q — Situate tasks on the graph, well-connected and weighted.

Invoke `pauli` to silently capture, place, and densify the user's intent on the task graph by creating or updating one or more tasks in the `inbox` state.

## 1: Intake, Placement & Densification

Stage 1 places the task under the right parent, values it strategically (marginal career benefit, cross-project synergies, Value of Information [VoI]), wires edges (`contributes_to`, `depends_on`, `soft_depends_on`, `[[wikilinks]]`), sorts assumptions into tested vs. hopes, and names forks with discriminating probes.

- **Front-load recon as ONE parallel read-only pass**: Run graph searches (`pkb__search`, `pkb__pkb_context`, `pkb__task_search`) and repo lookups concurrently before writing. Never interleave reads and writes.
- **One ask vs enumerated goals**: An enumerated feature list or sub-item breakdown inside a single overarching goal is **one unit plus forced children**, not N independent intake asks.
- **Order writes in separate rounds**: Create parent first, then child tasks, then wire dependent edges/gates in subsequent passes to avoid race conditions.
- **Place under an appropriate parent node**: Identify the right parent (epic, target, or active task). Do not insert new tasks under complete or stale parent nodes.
- **Never park tasks in a catch-all, and never leave them unparented.** Everything belongs somewhere real on the graph. A node with no parent is an orphan the next sweep has to chase, and a junk-drawer parent is an orphan that does not show up as one — which is worse.
- **Wire graph relationships**:
  - Add a `contributes_to` edge to the target or goal this work actually serves, with a verbal weight and one sentence of justification.
  - Wire `depends_on` for known hard blockers and `soft_depends_on` for context/informational relationships.
- **Densify with wikilinks**: Include `[[wikilinks]]` in the body to related nodes, prior attempts, and relevant documentation. The graph should come out denser, not just longer. A task whose only edge is its parent has been dumped, not placed.
- **Strategic Valuation at intake**: Record initial estimates across strategic dimensions:
  - **Marginal career benefit**: The specific publication, grant, credential, or career milestone advanced.
  - **Synergies**: Cross-project or cross-workstream reuse of methods, datasets, or findings.
  - **Value of Information (VoI)**: How much this reduces uncertainty on critical downstream assumptions (`uncertainty` / `classification: spike`).
  - **Effort & downstream unblocking**: High-level initial calibration without fabricating precision.

## 2: Place it, value it, wire it

One task, under the right parent.

| Signal                                       | Level                                          |
| -------------------------------------------- | ---------------------------------------------- |
| Desired future state, identity-scale         | Goal — outside the tree                        |
| Countable milestone, done or not done        | Target — outside the tree, carries the stakes  |
| Bounded body of work with real sub-structure | Epic, parented to the epic or area it serves   |
| One verifiable unit, one session             | Task, parented to the epic it belongs to       |
| High uncertainty, information needed first   | Task with `classification: spike`, same parent |

`project` comes from the parent. Where re-parenting moves the node to a different
project, move the slug with it. If the right parent is genuinely ambiguous
between two live candidates — not merely unclear at a glance — that is a SURFACE
case (§3). Do not flip a coin.

Add a `contributes_to` edge to the target this work actually serves, with a
verbal weight and one sentence of justification. Then densify: `depends_on` for
true hard blockers, `soft_depends_on` for context-only relations, `supersedes`
where this replaces prior work, and body `[[wikilinks]]` to the neighbours you
confirmed by opening. **The graph should come out of this denser, not just
longer.** A task whose only edge is its parent has not been placed, it has been
dumped.

Record an initial estimate across key strategic valuation dimensions:

- **Marginal benefit**: The milestone, advantage, or capability this work advances.
- **Cross-project synergies**: Work that is reusable across other active projects.
- **Value of Information (VoI)**: How much doing this work reduces uncertainty on other nodes on the graph.
- **Downstream unblocking & contribution**: Hard unblocking (`depends_on` from work this frees), target contribution (`contributes_to` verbal weight + justification), consequence of failure (`consequence` prose on the target), and initial `effort`. Populate what you actually established; do not fabricate precision the ask does not support.

**`focus_score` is computed by the graph engine, and you never write it.** You influence it only by wiring up edges.

## 3 — Sort the assumptions, name the forks, route the unknowns

Start from the **means**: what actually exists — what is built, what is known,
who is available, which constraints are real. The work is what those afford, not
what the goal demands.

Model tasks on the graph to the extent that you can draw a reliable inference. You should work through the information required to validate the task's assumptions and add those elsewhere on the graph as blocking nodes that must be resolved before progressing. Where you are reasonably confident about the potential alternatives that will eventually be available, fork the graph at that point and outline each option. Keep going while you are reasonably confident and adding value. Stop decomposing before you hit implementation details.

Where you need to block a step pending further information, **you must also create the `spike`** that will yield the information you need most efficiently. The spike will usually belong elsewhere on the graph; not a sibling or parent of the nodes it blocks. You must wire an edge from the blocked node to the spike with the `depends_on` relationship.

If you can decide by yourself, do not block. Where there is a reasonably clear choice that aligns with the project's strategy and the graph's approach, you should decide it and record the call and your reasons and move on. Don't create extra roadblocks where you can settle a decision with minimal effort.

## Must NOT

- Do not write `priority`. Priority is solely set by the user's intent, not your estimate. New work sits at the default band unless the user directed otherwise in this turn. To give work weight, connect the task to an outcome and weight the edges properly.
- Do not set `severity` on anything that is not a `type: target` node.
- Manufacture a `due` date to carry urgency. `due` means a real external deadline.

## Output

**RETURN Task ID and title** in the following format:

```
- Queued [TASK-ID] - [TASK-TITLE] (under [PARENT TASK-ID]) [inbox]
... [ Repeat if necessary ]
```
