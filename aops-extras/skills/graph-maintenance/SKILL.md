---
name: graph-maintenance
type: skill
category: instruction
description: Keep the PKB task/knowledge graph structurally sound — wire weighted contributes_to edges from deliverables to type:target nodes, and run garden/densify passes (parent-type hierarchy, wikilink/dedup hygiene, orphan reconnection, target/edge quality flags). Fires on graph-hygiene asks, not task valuation or decomposition. Bound to pauli as the graph's sole shaper.
triggers:
  - "wire edges"
  - "contributes_to"
  - "Renooij-Witteman"
  - "garden"
  - "densify graph"
  - "reparent"
  - "graph hygiene"
  - "graph maintenance"
  - "orphan nodes"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - planning
  - knowledge-management
allowed-tools: AskUserQuestion,Read,mcp__pkb__list_tasks,mcp__pkb__get_task,mcp__pkb__update_task,mcp__pkb__append,mcp__pkb__get_semantic_neighbors,mcp__pkb__get_network_metrics,mcp__pkb__get_dependency_tree,mcp__pkb__pkb_trace,mcp__pkb__pkb_orphans
version: 1.0.0
permalink: skills-graph-maintenance
---

# Graph Maintenance Skill

Custodian of the PKB graph's **structure**, not its strategy: edge density (Wire) and structural
health (Garden/Maintain). Carved out of `planner`'s Wire and Maintain modes — `planner`'s
capture/plan/decompose modes moved to [[skills-situate]] and [[skills-decompose]]; this skill
covers what's left. Do not resurrect capture, plan, decompose, or explore here — route those asks
to situate/decompose instead of handling them inline.

**Personality binding — permission-control.** Earmarked to `pauli`: wiring `contributes_to` edges,
reparenting, merging duplicate nodes, and archiving orphans require the PKB graph-mutation tool
surface, which only `pauli`'s agent frontmatter grants (`specs/agents/pauli.md` — "sole
graph-shaper"). This is capability wiring, not a claim that only pauli's judgment could do this
work; the restriction keeps exactly one agent authoritative for graph structure so scores and
edges never drift from two writers disagreeing.

## Disposition

**Custodial, not strategic.** You don't value work or decide what to build — that's `situate`. You
keep the graph that strategy already produced honest: correctly shaped, densely connected,
free of drift. Mechanical and unambiguous dispositions execute autonomously; anything needing
judgment gets surfaced, never guessed.

## Modes

### 1. Wire (`/strategy` / `contributes_to`)

Outcome: a directed `contributes_to` edge from a deliverable task to a class-level `type: target`
node (never a vague goal), carrying a Renooij-Witteman weight and a one-sentence justification.
This edge is the primary lever for raising a task's `downstream_weight`/`focus_score` — reach for
it, not `priority`, when asked for "more weight."

| Term        | Weight | Meaning                                               |
| ----------- | ------ | ----------------------------------------------------- |
| Certain     | 1.00   | Single point of failure; if this fails, target fails. |
| Probable    | 0.85   | Strong contribution; very likely needed.              |
| Expected    | 0.75   | Expected contribution; standard path.                 |
| Fifty-Fifty | 0.50   | Redundancy exists; half the importance.               |
| Uncertain   | 0.25   | Weak contribution; might be relevant.                 |
| Improbable  | 0.15   | Very weak contribution.                               |
| Impossible  | 0.00   | No contribution.                                      |

Full interactive procedure (target selection, candidate search, elicitation), the canonical edge
schema, and the reverse-scoring mechanics (an edge raises the _target's_ score, never the source
task's own) live in `references/wire-scale.md` — read it before wiring; the reverse-scoring rule
is the most common mistake.

### 2. Maintain / Garden (`/garden` / `/densify`)

Outcome: the graph stays structurally sound — correct parent-type hierarchy (every task has a
parent of the correct type; targets link via `contributes_to`, never as a parent), valid
wikilinks, de-duplicated nodes, no avoidable orphans. Fix broken links and prefix/type/filename
mismatches (e.g. `epic-` prefix with `type: task`). Flag targets missing `consequence` prose,
edges missing justifications, and more than 2 concurrent committed SEV4 targets. Reconnect
disconnected epics and flat tasks; complete stale tasks from email/calendar evidence; reclassify
email-dumps as memories.

The `note`/`knowledge`/`memory` population is invisible to `graph_stats.orphan_count` — enumerate
it separately with `pkb_orphans(types=["note","knowledge","memory"], include_all=true)`. Full
per-orphan disposition triage (link/reparent, MOC, merge, archive, SURFACE), the actionable-layer
strategy table, and the "what NOT to do" guardrails (no aesthetic reorganizing, no speculative
epics, no keyword-only reparenting, no undoing prior human decisions) live in
`references/maintenance-triage.md`.

## Severity Assignment Rules (graph structure)

Severity belongs only on `type: target` nodes, with explicit `consequence` prose — never on tasks,
epics, or other leaves, which default to `severity: 0`/omit. Agent-assigned non-zero severity on a
non-target node is prohibited and blocked by the write-boundary guard; it artificially inflates
focus scores and inverts the priority queue. Canonical scale:
[[../../../aops-pkb/skills/remember/references/TAXONOMY.md#severity-ladder-sev0sev4]].

## Must not

- Capture, plan, or decompose a task — that's [[skills-situate]] / [[skills-decompose]]. (Pure
  think-out-loud ideation that creates nothing needs no dedicated skill — it's an ordinary
  conversational turn; when it converges on something worth keeping, hand the result to `hydrate`
  → `situate`. The old planner's standalone "Explore" mode is retired, not rehomed.)
- Write delegation briefs or dispatch work — that's `brief`.
- Assign or suggest `priority` — that's Nic's personally curated intent, never this skill's
  estimate, however important a target looks.
- Assign non-zero `severity` to a non-target node.
- Reorganize for aesthetics, create epics speculatively (need 3+ tasks that clearly belong
  together), reparent on keyword matching alone (read the body), split an actively-worked epic
  (flag for a quiet period instead), or undo a prior human decision.

## Fitness test (self-check before you finish)

A reviewer can audit every change you made independently: each new/changed `contributes_to` edge
carries a weight and a one-sentence justification a stranger can check against the target; each
reparent/merge/archive traces to an observed disposition (body read, backlink check), not a guess
from title or tags; anything ambiguous is named in a SURFACE flag, not silently resolved. If you
can't point to the evidence behind a structural change, it isn't done.
