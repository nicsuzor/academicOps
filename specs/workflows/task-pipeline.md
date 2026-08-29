---
id: workflows-task-pipeline
title: The Task Pipeline — capture to return channel
type: spec
category: workflow
status: ready
tags: [spec, workflow, pipeline, pkb, dispatch]
related: [[work-management]], [[feedback-loops]]
---

# The Task Pipeline

Design intent for the stages a piece of work passes through, and for why the
boundaries between them sit where they do. The stages themselves are operative
instructions and live in `plugins/aops-core/skills/` — with the one lens that is not a
stage, `strategize`, in `plugins/aops-core/skills/`. Nothing here restates them.

## The map

```
/q (Stage 1: Intake & Capture) ──► hydrate ──► one inbox node (NO AC), and stop
   ├─► placed under the right parent, valued (marginal career benefit, synergies, VoI)
   ├─► densely wired: contributes_to, depends_on, [[wikilinks]]
   ├─► assumptions sorted: tested vs hopes
   ├─► forks named, each with the probe that would settle it
   ├─► sizing: default no cut; cut only at an unresolved fork or boundary
   └─► status: inbox with NO acceptance criteria (non-dispatchable)
                              │
                              ▼
===================================================================
BREAKPOINT 1 — the user calls brief on an inbox node, or on a raw ask that
brief captures itself first. Being called is the gate.
===================================================================
brief (Stage 2: Dispatch Preparation — composes only) ──► status: queued
   ├─► validates / refines Stage 1 placement, valuation, and fork map
   ├─► process composed from the three template layers, risk-proportionate
   │   · steps this worker takes in this session ──► the task checklist
   ├─► anything a different owner does ──► its own child node on the graph
   │   · review obligations are nodes: reviewer ≠ executor
   │   · empty review set ──► halt, task blocked, no brief written
   │   · one-way or ambiguous door ──► sign-off node, uncomposed
   ├─► brief written to task body + concrete Acceptance Criteria (AC)
   └─► flips status: inbox ──► queued (ready for dispatch) ──► STOP
===================================================================
orchestrate's dispatch reads the task BY ID and routes it
(Inboxes without Acceptance Criteria are non-dispatchable by engine invariant)
the unit executes ──► PR lands, or closes
===================================================================
reconcile (return channel, facts only)
   ├─► folds merged and closed PRs, probes stale claims, routes the
   │   completed-but-uncertified
   └─► returns the tasks a landed wave touched to inbox
===================================================================
BREAKPOINT 2 — the user: PR review and merge, plus the one-way-door sign-offs
===================================================================
```

## Why the stages are cut here

**Stage 1 (Intake, Placement & Densification) belongs to `/q`.** `/q` gets the shortlist
from `hydrate`, records one `inbox` node under the parent it belongs to, wires
`contributes_to` and `depends_on` relationships, densifies the neighbourhood with `[[wikilinks]]`,
and applies initial strategic valuation (marginal career benefit, cross-project synergies, Value of Information [VoI]).
Placement and densification happen here because a node without a parent is an orphan, and a task with no edges is dumped rather than placed.
Crucially, **Stage 1 writes NO acceptance criteria and leaves the status at `inbox`**. Very fast, raw notes can be captured via incoming capture first before being situated under `/q`.

**The Engine Readiness Invariant.**
An `inbox` node without Acceptance Criteria is strictly non-dispatchable.
Dispatchers and worker agents pull only `queued` nodes that carry completed Stage 2 briefs and concrete Acceptance Criteria.
Leaving tasks in `inbox` with no AC ensures intake cannot accidentally trigger autonomous worker dispatch.

**Stage 2 (Dispatch Preparation) belongs to `brief`.**
When the user explicitly invokes `brief` on an `inbox` node (or raw note), it validates Stage 1 placement,
composes the process across template layers, emits blocking review and sign-off nodes, drafts the brief,
and formulates concrete **Acceptance Criteria (AC)**. Once AC and review nodes are present, `brief` flips
the node from `inbox` to `queued`.

**Hydrate points; it does not read.** It runs on every ask, which is the widest
point in the funnel, so it does the cheap half: a few differently-worded
semantic searches, cut down to the handful of ids worth someone's attention.
Synthesis at that width is synthesis spent mostly on asks that never become
work. What it hands back is pointers, and pointers stay true as the graph moves
in a way a prose snapshot does not — which is what makes it safe for `/q` to
persist the shortlist onto the node.

**Everything that requires reading is one pass, afterwards.** Opening what the
shortlist points at, placement, valuation, wiring, the assumption sort, the fork
map, and the decision list all work over the same neighbourhood; splitting them
across two stages meant two passes loading the same context to write to the same
node. So `brief` does all of it, in the one pass the user calls for.

**Sizing happens at dispatch, not at intake.** Cutting a tree at intake spends
budget on information that does not exist yet and produces structure that is
rewritten before it is read. `brief` fires on the unit that is due, with
whatever the last wave established already folded in.

**A unit is cut at forks, never at size.** The largest chunk containing no
unresolved fork is one dispatchable unit — usually the whole task. Every cut
obliges some surface to maintain a node, its review, and its dependency edges,
so a cut made because a unit "feels large" buys process theatre with real
maintenance. Where a fork is blocked on missing information, the cheapest
experiment that discriminates between the branches is what gets dispatched; the
work behind it stays a placeholder.

**Children and subtasks are different objects, and the difference is who does
the work.** A subtask travels with its parent, is hidden from the ready set, and
is how one worker tracks its own steps inside one session. A child is a real
node with its own owner, its own return contract, and its own visibility to a
dispatcher. So the question a cut answers is never "does this block?" but "does
the same worker do this, in the same sitting?" — sequenced steps stay inside the
unit as checklist lines, and anything belonging to another owner becomes a
child. Review obligations are children for exactly this reason: reviewer ≠
executor means a different identity, so review was never the unit's own work.

**The composer is not the executor, and does not become one.** An agent that has
just reasoned its way to a plan acts on the reasoning trace rather than on the
brief, so the brief does not bind the identity that wrote it. `brief` persists
everything to the task body and the graph, then stops; `orchestrate`'s
`dispatch` reads the task by id later and routes it, and the executor reads the
brief cold. Three identities, and the separation is structural rather than a
rule anyone has to remember: the composer holds no dispatch surface at all.

**Composition lives with the brief, routing does not.** Assembling a process
from the three template layers only ever served the unit about to be worked, so
it belongs in `brief` rather than in a skill of its own. Routing — which
template a class of work follows — is a different job serving a much wider set
of asks, most of which never reach dispatch, so its tree stays in
[`plugins/aops-core/workflows/INDEX.md`](../../plugins/aops-core/workflows/INDEX.md) where
any agent reads it directly.

**The return channel writes facts and re-plans nothing.** `reconcile` has
exactly the authority of what it observed. Letting it close on its own judgment
would make a sweep that runs unattended into a surface that deletes work, and
letting it re-plan would put planning somewhere no one reads. So it writes what
happened and returns the affected tasks to `inbox` — re-plan when the wave
lands, on the user's call, in the stage that owns planning.

## The two breakpoints

Both are the user's, and no agent crosses either.

1. **Promotion.** `brief` runs only when the user calls it, so being called _is_
   the gate, and `brief` is the only thing that writes `queued`. Agents pull
   only from `queued` and never promote into it — which is what makes writing
   the decision list a surface rather than a drop: the user reads it on the body
   of the task they just released.
2. **The pull request, and the sign-offs.** PR review and merge, plus every
   one-way-door sign-off node `brief` wired into the graph. The
   [`one-way-door`](../../lib/axioms/one-way-door.md) axiom binds the agent that
   crosses; the node is what leaves the obligation somewhere a reviewer can see
   it was owed.

## One status vocabulary

The pipeline carries no status vocabulary of its own. `inbox` and `queued` mean
what the PKB MCP tool schemas declare they mean, and every stage writes in those
terms. A parallel vocabulary — "situated", "briefed", "dispatchable" — would
need its own transitions, its own sweep, and its own reconciliation against the
real one.

There is no flag beside the status, either. `inbox` is what marks a node as not
yet worked out and `queued` is what marks it as ready to dispatch; a second
field saying the same thing is a second thing to keep true.

`focus_score` is computed by the graph engine from the signals on the nodes. No
stage writes it; a stage moves it by wiring edges and by putting `severity` on
the target the work serves.

## Stage ownership

| Stage            | Owns                                                                                                                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `hydrate`        | A shortlist of ids, from a few reworded searches. Read-only, opens nothing.                                                                                                          |
| `/q`             | Stage 1 Intake & Capture: placement under parent, wiring contributes_to/depends_on, [[wikilinks]], strategic valuation (career benefit, synergies, VoI). Status: `inbox` with NO AC. |
| `brief`          | Stage 2 Dispatch Preparation: process composition, review & sign-off nodes, brief & Acceptance Criteria (AC). Flips `inbox` to `queued`. Composes; never dispatches.                 |
| `pull`           | Claim, execute, record, hand over.                                                                                                                                                   |
| `reconcile`      | What is true about in-flight and finished work. Facts only; returns re-planning to `inbox`.                                                                                          |
| `ida:strategize` | An on-demand lens, ida's: fix the altitude, route each piece to the stage that owns it.                                                                                              |

Each runs, then stops. No stage fires the next.
