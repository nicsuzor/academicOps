# Maintain / Garden — Triage Detail

## Actionable-layer strategy selection

Each cycle, pick the strategy `graph_stats` shows needs the most attention:

| Condition                                 | Strategy               | Action                                                       |
| ----------------------------------------- | ---------------------- | ------------------------------------------------------------ |
| `disconnected_epics` > 10                 | Connect epics          | Reparent — find project parents for disconnected epics       |
| `targets_without_contributing_edges` > 10 | Wire edges             | Run [Wire mode](../SKILL.md#1-wire-strategy--contributes_to) |
| `flat_tasks` > 100                        | Reparent flat tasks    | Find epic/project parents for orphans                        |
| `orphan_count` > 20                       | Fix orphans            | Connect or archive disconnected nodes                        |
| `knowledge_orphan_count` > 50             | Curate knowledge layer | Knowledge-layer triage (below), one bounded batch            |
| All metrics healthy                       | Densify edges          | Add dependency edges between related nodes                   |

A cycle may run one actionable strategy **and** one knowledge-layer batch in parallel — they're
different metrics with separate bounded-effort caps; don't let one crowd out the other.

**Concrete moves:**

- Split oversized containers: epic with >20 direct children → split by theme, `batch_reparent(dry_run=false)`.
- Find misparented tasks: `pkb_orphans` for wrong-type-parent orphans → reparent to the right epic.
- Nest loose tasks: read title + body, search for a related epic, `batch_reparent`. If 3+ loose
  tasks share a theme with no home, create an epic — never speculatively, only when the cluster is
  real.
- Connect disconnected epics: parent is an `epic` (or root-level `epic` for a top-level area).
  `frontmatter.project` is a polecat slug — use it to discover which repo the work belongs to, not
  as a parent id.

## Knowledge-layer curation (`note`/`knowledge`/`memory`)

Invisible to `graph_stats.orphan_count` — enumerate with
`pkb_orphans(types=["note","knowledge","memory"], include_all=true)`. Enforces the Relational
Integrity rule ("never allow orphan nodes or unlinked knowledge to persist"; "every note weaves
into the graph with back-references"). Same surface-don't-decide discipline as the actionable
layer: mechanical, unambiguous dispositions execute autonomously; anything needing judgment is
flagged, never guessed.

**Per-orphan triage — read the node (title, tags, dates, body) before acting; never act on
title/tag keywords alone.** Assign exactly one disposition:

| Disposition       | Signal                                                                                         | Action                                                                                                                                                                                                                                                                                                     |
| ----------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **link/reparent** | Active knowledge whose parent concept clearly exists (a canonical topic note, MOC, or epic).   | Add the structured edge (`batch_reparent`/`batch_update`, `dry_run=false`). For memories (no `parent` at capture), a body `[[wikilink]]` to a live hub clears orphan status too — connect to a node that is itself graph-reachable, not to another orphan.                                                 |
| **MOC**           | A cluster of 5+ orphans on one first-class topic, no hub note exists.                          | Create/extend a Map of Content and wire the cluster under it. Earned, not scheduled — only when the cluster is real.                                                                                                                                                                                       |
| **merge**         | Duplicate/near-duplicate of an existing canonical note (confirm via `find_duplicates`/search). | `merge_node`/`batch_merge(dry_run=false)` into the canonical note, preserving provenance.                                                                                                                                                                                                                  |
| **archive**       | Legacy import or superseded episodic record with no live consumer.                             | Verify by observation first: confirm zero inbound references (backlinks/search) — "no live consumer" must be observed, never assumed from title or age. Any inbound reference or doubt → SURFACE instead. Age alone is never the trigger. Then `batch_archive` with reason. Reversible (archive ≠ delete). |
| **SURFACE**       | Ambiguous parent, possible-but-unconfirmed duplicate, or anything needing human judgment.      | Flag with the node id and the specific ambiguity. Do not guess a parent.                                                                                                                                                                                                                                   |

**Bounded effort.** Up to 100 knowledge orphans per cycle, sharing the batch-limit cap with the
actionable strategy — split the budget, don't let either starve. Quality over coverage: a wrong
reparent is worse than a surfaced one.

**Terminal condition.** Complete for the loop when EITHER `knowledge_orphan_count` is unchanged
for 2 consecutive cycles (the residual is the genuinely-SURFACE population awaiting a human call),
OR two consecutive cycles process zero non-SURFACE dispositions.

## What NOT to do

- Don't reorganize for aesthetics — a correctly-parented-but-not-pretty grouping stays put.
- Don't create epics or MOCs speculatively (need 3+ / 5+ real members respectively).
- Don't reparent, merge, or archive on keyword/title/age matching alone — read the body.
- Don't split an epic that's actively being worked — flag for the next quiet period.
- Don't undo a prior human decision.
- Don't archive without the inbound-reference check — an unread consumer is exactly what
  "reversible" doesn't protect against.
- Don't fabricate a parent just to clear a count — an unsurfaced wrong home is the failure this
  activity exists to prevent.

## Known metric limitations

- `flat_tasks`: tasks parented to a catch-all "misc" epic show as connected even if meaningless.
- `orphan_count`: doesn't catch tasks parented to archived/cancelled containers.
- `metrics_hash`: unchanged hash means the actionable metrics have stabilised — use for
  convergence detection, but don't skip knowledge-layer curation on that basis (it's a separate
  metric).

Don't treat all-green metrics as "done." Spot-check qualitatively.
