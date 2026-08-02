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
instructions and live in `plugins/pkb/skills/`; nothing here restates them.

## The map

```
/q capture ──► hydrate ──► one inbox node, and stop
                              │
                              ▼
situate (inline when cheap, or the consolidation sweep) ──► status: ready
   ├─► placed under the right parent, valued, densely wired
   ├─► assumptions sorted: tested vs hopes
   ├─► forks named, each with the probe that would settle it
   └─► decision list for the user
===================================================================
BREAKPOINT 1 — the user promotes ready ──► queued, resolving the decision list
===================================================================
brief (fires at dispatch time, on a queued unit)
   ├─► sizing: default no cut; cut only at an unresolved fork or a
   │   responsibility boundary
   ├─► a fork blocked on information dispatches the probe instead
   ├─► process composed from the three template layers, risk-proportionate
   ├─► review nodes emitted as blocking dependencies
   │   · empty review set ──► halt, task blocked, nothing dispatched
   │   · one-way or ambiguous door ──► sign-off node, uncomposed
   └─► brief written to the task body ──► dispatch BY TASK ID
===================================================================
the unit executes ──► PR lands, or closes
===================================================================
reconcile (return channel, facts only)
   ├─► folds merged and closed PRs, probes stale claims, routes the
   │   completed-but-uncertified
   └─► hands the tasks a landed wave touched back to situate
===================================================================
BREAKPOINT 2 — the user: PR review and merge, plus the one-way-door sign-offs
===================================================================
```

## Why the stages are cut here

**Capture is hydrate plus one write, and nothing else.** `/q` gets the shortlist
and records one `inbox` node. It makes no judgment — not the parent, not the
value, not a single edge — because every judgment made there is made on the
thinnest context anyone will ever have about the ask, and because a fragment
that costs more than a few seconds to capture is a fragment that stops being
captured.

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
node. So `situate` does all of it, inline when the shortlist is short and
batched in the consolidation sweep otherwise. Cost decides which; the pass is
identical either way.

**Sizing happens at dispatch, not at intake.** Cutting a tree at intake spends
budget on information that does not exist yet and produces structure that is
rewritten before it is read. `brief` fires on the unit that is due, with
whatever the last wave established already folded in.

**A unit is cut at forks, never at size.** The largest chunk containing no
unresolved fork is one dispatchable unit — usually the whole task. Every cut
obliges some surface to maintain subtask tracking, review nodes, and dependency
edges, so a cut made because a unit "feels large" buys process theatre with real
maintenance. Where a fork is blocked on missing information, the cheapest
experiment that discriminates between the branches is what gets dispatched; the
work behind it stays a placeholder.

**The composer is not the executor.** An agent that has just reasoned its way to
a plan acts on the reasoning trace rather than on the brief, so the brief does
not bind the identity that wrote it. `brief` persists to the task body and
dispatches by task id; the executor reads it cold. This is why brief-writing
sits in `pkb` and `orchestrate`'s `dispatch` composes nothing.

**The return channel writes facts and re-plans nothing.** `reconcile` has
exactly the authority of what it observed. Letting it close on its own judgment
would make a sweep that runs unattended into a surface that deletes work, and
letting it re-plan would put planning somewhere no one reads. So it writes what
happened and hands the affected tasks to `situate` — re-plan when the wave
lands, in the stage that owns planning.

## The two breakpoints

Both are the user's, and no agent crosses either.

1. **Promotion.** `situate` leaves the task at `ready` with a decision list on
   its body. The user resolves that list and sets `queued`. Agents pull only
   from `queued` and never promote into it — which is what makes writing the
   decision list a surface rather than a drop: the gate is where it is read.
2. **The pull request, and the sign-offs.** PR review and merge, plus every
   one-way-door sign-off node `brief` wired into the graph. The
   [`one-way-door`](../../lib/axioms/one-way-door.md) axiom binds the agent that
   crosses; the node is what leaves the obligation somewhere a reviewer can see
   it was owed.

## One status vocabulary

The pipeline carries no status vocabulary of its own. `inbox`, `ready`, and
`queued` mean what the PKB MCP tool schemas declare they mean, and every stage
writes in those terms. A parallel vocabulary — "situated", "briefed",
"dispatchable" — would need its own transitions, its own sweep, and its own
reconciliation against the real one.

There is no flag beside the status, either. `inbox` is what marks a node as
not yet situated and `ready` is what marks it as done; a second field saying the
same thing is a second thing to keep true.

`focus_score` is computed by the graph engine from the signals on the nodes. No
stage writes it; a stage moves it by wiring edges and by putting `severity` on
the target the work serves.

## Stage ownership

| Stage       | Owns                                                                                    |
| ----------- | --------------------------------------------------------------------------------------- |
| `hydrate`   | A shortlist of ids, from a few reworded searches. Read-only, opens nothing.             |
| `/q`        | One `inbox` node carrying the ask and that shortlist. No judgment of any kind.          |
| `situate`   | Placement, valuation, wiring, assumptions, forks, probes, decisions. To `ready`.        |
| `brief`     | Sizing, process composition, review and sign-off nodes, the brief, dispatch by task id. |
| `pull`      | Claim, execute, record, hand over.                                                      |
| `reconcile` | What is true about in-flight and finished work. Facts only; hands re-planning back.     |
| `plan`      | An on-demand lens: fix the altitude, route each piece to the stage that owns it.        |

Each runs, then stops. No stage fires the next.
