---
name: q
type: command
description: Stage 1 Intake & Capture — place an ask, fragment, or idea on the graph under the right parent, wire contributes_to/depends_on, densify with wikilinks, and record strategic valuation at intake, leaving status at inbox with NO acceptance criteria.
allowed-tools: [Skill, AskUserQuestion, mcp__services__pkb__create_task, mcp__services__pkb__update_task, mcp__services__pkb__update_body, mcp__services__pkb__search, mcp__services__pkb__task_search, mcp__services__pkb__batch_reparent]
---

# /q — Situate tasks on the graph, well-connected and weighted.

Invoke `pauli` to silently capture, place, and densify the user's intent on the task graph by creating or updating one or more tasks in the `inbox` state.

> PKB MCP tools live under the **`services`** MCP server using the `pkb__` tool name prefix (e.g. `pkb__search`, `pkb__get_task`, `pkb__create_task`, `pkb__update_task`, `pkb__batch_reparent`). Note: `pkb__create_task` sets `status: "inbox"` (or `"ready"`). Setting `status: "queued"` requires a two-step write via `pkb__update_task` and belongs to `brief`, not `q`.

## 1: Intake, Placement & Densification

Stage 1 places the task under the right parent, values it strategically (marginal career benefit, cross-project synergies, Value of Information [VoI]), wires edges (`contributes_to`, `depends_on`, `soft_depends_on`, `[[wikilinks]]`), sorts assumptions into tested vs. hopes, names forks with discriminating probes.

- **Place under an appropriate parent node**: Identify the right parent (epic, target, or active task). Do not insert new tasks under complete or stale parent nodes.
- **Never park tasks in a catch-all, and never leave them unparented.** Everything belongs somewhere real on the graph. A node with no parent is an orphan the next sweep has to chase, and a junk-drawer parent is an orphan that does not show up as one — which is worse.
- **Adopt existing work**: Where existing unparented, misparented, or pre-existing tasks already cover the idea, adopt them under the parent using `pkb__batch_reparent(ids=[...], new_parent="<parent-id>", dry_run=False)` rather than creating duplicate nodes.
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

One task, under the right parent. When creating tasks (`pkb__create_task`), mint slugged, human-readable IDs upfront (`id: "aops_<slug>"`, etc.) rather than leaving `id` empty for auto-generation.

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
verbal weight and one sentence of justification ([[kb_pauli_prioritisation_doctrine]]). Then densify: `depends_on` for
true hard blockers, `soft_depends_on` for context-only relations, `supersedes`
where this replaces prior work, and body `[[wikilinks]]` to the neighbours you
confirmed by opening. **The graph should come out of this denser, not just
longer.** A task whose only edge is its parent has not been placed, it has been
dumped.

Record an initial estimate across key strategic valuation dimensions:

- **Marginal benefit**: The milestone, advantage, or capability this work advances.
- **Cross-project synergies**: Work that is reusable across other active projects.
- **Value of Information (VoI)**: How much doing this work reduces uncertainty on other nodes on the graph.
- **Downstream unblocking & contribution**: Hard unblocking (`depends_on` from work this frees), target contribution (`contributes_to` verbal `stated_weight` + justification), consequence of failure (`consequence` prose on the target), and initial `effort`. Populate what you actually established; do not fabricate precision the ask does not support.

**`focus_score` is computed by the graph engine, and you never write it.** You influence it only by wiring up edges.

## 3 — Sort the assumptions, name the forks, route the unknowns

Start from the **means**: what actually exists — what is built, what is known,
who is available, which constraints are real. The work is what those afford, not
what the goal demands.

Model tasks on the graph to the extent that you can draw a reliable inference. You should work through the information required to validate the task's assumptions and add those elsewhere on the graph as blocking nodes that must be resolved before progressing. Where you are reasonably confident about the potential alternatives that will eventually be available, fork the graph at that point and outline each option. Keep going while you are reasonably confident and adding value. Stop decomposing before you hit implementation details.

Where you need to block a step pending further information, **you must also create the `spike`** that will yield the information you need most efficiently. The spike will usually belong elsewhere on the graph; not a sibling or parent of the nodes it blocks. You must wire an edge from the blocked node to the spike with the `depends_on` relationship.

If you can decide by yourself, do not block. Where there is a reasonably clear choice that aligns with the project's strategy and the graph's approach, you should decide it and record the call and your reasons and move on. Don't create extra roadblocks where you can settle a decision with minimal effort.

## Must NOT

- Do not attempt to set `status: "queued"` at intake. `q` leaves tasks at `status: "inbox"`.
- Do not write `intent` (or legacy `priority`). Intent is the principal's personally curated ranking, not an agent estimate. New work sits at the uncurated default band unless the user directed otherwise in this turn. To express strategic importance, wire `contributes_to` edges to targets; only `pauli` authors `stated_weight`.
- Do not set `severity` on anything that is not a `type: target` node (severity is target-only magnitude).
- Do not manufacture a `due` date to carry urgency. `due` means a real external deadline.

## Output

**RETURN Task ID and title** in the following format:

```
- Captured [TASK-ID] - [TASK-TITLE] (under [PARENT TASK-ID]) [inbox]
... [ Repeat if necessary ]
```
