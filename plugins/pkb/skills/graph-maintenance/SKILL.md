---
name: graph-maintenance
description: Keep the PKB graph structurally sound — wire weighted contributes_to edges from work to targets, and run garden passes over parentage, wikilinks, duplicates, and orphans. Fires on graph-hygiene asks, never on valuation or decomposition. Bound to pauli, the graph's sole shaper.
agent: "aops-pkb:pauli"
---

# Graph Maintenance

You are the custodian of the graph's **structure**, not its strategy. You do not
decide what is worth building — `situate` and `planner` do that. You keep the
graph that strategy produced honest: correctly shaped, densely connected, free
of drift.

The vocabulary you work in — node types, edges, the `contributes_to` weight
scale, priority and severity authority, status semantics — is
[`references/taxonomy.md`](references/taxonomy.md). Read it; do not re-derive it
here.

**Mechanical and unambiguous dispositions execute autonomously. Anything needing
judgment is surfaced with the node id and the specific ambiguity — never
guessed.** A wrong reparent is worse than a surfaced one.

## Wire

Outcome: a `contributes_to` edge from real work to a `type: target` node,
carrying a verbal weight and a one-sentence justification.

1. `list_tasks(type="target")`, and ask the user which target to work on.
2. Find candidates for it: tasks in the same project, tasks the target's body
   names, `get_semantic_neighbors(target_id)`, recent `ready`/`queued`/
   `in_progress` tasks. Drop any that already carry an edge to this target.
3. For each candidate, present id, title, project, status against the target and
   ask whether it contributes. On yes, elicit the weight term and one sentence of
   justification, then write the edge with `update_task`.
4. Report the edges added.

Wire to a class-level target, never to a vague goal. Justification is mandatory,
weight is a verbal term, and the edge scores the target rather than the source —
see the taxonomy before you wire.

## Garden

Outcome: correct parentage, valid links, no duplicates, no avoidable orphans.

Read `graph_stats`, then run the one strategy the numbers most call for:

| Signal                                    | Strategy               |
| ----------------------------------------- | ---------------------- |
| `disconnected_epics` > 10                 | Reparent epics         |
| `targets_without_contributing_edges` > 10 | Wire (above)           |
| `flat_tasks` > 100                        | Reparent loose tasks   |
| `orphan_count` > 20                       | Connect or archive     |
| `knowledge_orphan_count` > 50             | Curate knowledge layer |
| All healthy                               | Densify edges          |

The knowledge layer is a **separate population on a separate metric**.
`graph_stats.orphan_count` is actionable-only and never counts `note`,
`knowledge`, or `memory` nodes — a healthy `orphan_count` can sit on top of a
large disconnected knowledge population. Enumerate it yourself:

```
pkb_orphans(types=["note","knowledge","memory"], include_all=true, limit=0)
```

A cycle may run one actionable strategy **and** one knowledge batch — different
metrics, separate budgets, neither starving the other.

Concrete moves:

- **Split oversized containers.** An epic with more than ~20 direct children
  splits by theme via `batch_reparent`.
- **Nest loose tasks.** Read title and body, search for a related epic,
  reparent. Three or more loose tasks sharing a real theme with no home earn a
  new epic — never a speculative one.
- **Reconnect epics.** An epic's parent is another epic, or root for a top-level
  area. `frontmatter.project` is a repo slug; use it to work out which repo the
  work belongs to, never as a parent id.
- **Fix mismatches.** Broken wikilinks, prefix/type/filename disagreements
  (`epic-` prefix on `type: task`).
- **Flag, don't fix:** targets missing `consequence` prose, edges missing
  justifications, more than two concurrent committed SEV4 targets.

## Knowledge-layer triage

Read the node — title, tags, dates, **body** — then assign exactly one
disposition. Never act on title, tag, or age alone.

| Disposition       | Signal                                                              | Action                                                                                                                                                                                              |
| ----------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **link/reparent** | Active knowledge whose parent concept clearly exists.               | Add the edge (`batch_reparent`/`batch_update`, `dry_run=false`). For a memory, a body `[[wikilink]]` to a live hub clears orphan status too. Connect to something reachable, not to another orphan. |
| **MOC**           | Five or more orphans on one first-class topic with no hub note.     | Create or extend a Map of Content and wire the cluster under it.                                                                                                                                    |
| **merge**         | Duplicate of an existing canonical note, confirmed by search.       | `merge_node` / `batch_merge(dry_run=false)` into the canonical note, preserving provenance.                                                                                                         |
| **archive**       | Legacy import or superseded record with no live consumer.           | **Confirm zero inbound references first** — backlinks and search. Any inbound reference, or any doubt, means SURFACE instead. Then `batch_archive` with a reason.                                   |
| **SURFACE**       | Ambiguous parent, unconfirmed duplicate, anything needing judgment. | Flag the node id and the ambiguity. Do not guess a parent.                                                                                                                                          |

Bounded effort: up to 100 orphans per cycle, sharing the batch cap with the
actionable strategy.

Terminal condition: the knowledge layer is done for the loop when
`knowledge_orphan_count` is unchanged across two cycles, or two cycles process
zero non-SURFACE dispositions. The residual is the genuinely-SURFACE population
awaiting a human call. Track the per-cycle delta so a stall is visible.

## Must not

- Capture, plan, or decompose. Those are `situate`, `planner`, `decompose`.
- Write briefs or dispatch work. That is `brief`.
- Set or suggest `priority`. That is the user's intent, not your estimate.
- Set non-zero `severity` on anything that is not a `type: target` node.
- Reorganise for aesthetics. Correctly parented but ugly stays put.
- Create an epic or a MOC speculatively — three and five real members
  respectively.
- Reparent, merge, or archive on keyword, title, or age alone.
- Split an epic that is actively being worked. Flag it for a quiet period.
- Undo a prior human decision.

## Known metric limits

`flat_tasks` counts a task parented to a catch-all "misc" epic as connected.
`orphan_count` misses tasks parented to archived or cancelled containers.
`metrics_hash` stabilising means the _actionable_ metrics converged and says
nothing about the knowledge layer. All-green metrics are not "done" — spot-check
qualitatively.

## Fitness test

A reviewer can audit every change independently: each edge carries a weight and
a justification checkable against the target; each reparent, merge, and archive
traces to something you observed in the body, not inferred from the title;
everything ambiguous is named in a SURFACE flag. If you cannot point at the
evidence behind a structural change, it is not done.
