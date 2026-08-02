---
name: situate
description: Turn a captured ask into ONE task that is placed, valued, wired, and actually actionable — assumptions sorted into tested and hopes, open forks named with the probe that would settle each, and a decision list for the user. Promotes `inbox` to `ready`. Runs inline when cheap, batched in the consolidation sweep otherwise, and again when a wave lands. Never cuts, briefs, or dispatches.
agent: "pauli"
---

# Situate

Capture already put the ask on the graph as an `inbox` node. You turn that node
into **one** task somebody could actually pick up: in the right place, valued,
densely wired, with its beliefs sorted and its open questions named. Then you
stop.

You produce no new nodes beyond the one you are situating. Everything else you
produce is body content and edges.

## When you run

- **Inline, right after capture, when the pass is cheap** — the shortlist is
  short, and opening what it points at is a few minutes' reading.
- **Batched otherwise**, in the consolidation sweep, over the `inbox` backlog.
  Cost is the only thing that decides between these two; the pass is identical
  either way.
- **Again when a wave lands.** `reconcile` writes what a merged or closed pull
  request established and hands you the tasks it touched. Re-situate them
  against what actually happened, not against what was assumed.

**Never on the capture path itself.** `/q` stays zero-friction: hydrate gathers,
the command records one `inbox` node, and that is the whole of capture. Doing
this pass there is what turns a five-second thought into a two-minute one, and
then the capture stops happening.

You start from `hydrate`'s shortlist — ids with a line each, no more. **Opening
them is your job.** Hydrate deliberately did not read them; it found them and
stopped, so that the reading happens once, here, on the ask that turned out to
be worth it. Open what the lines suggest matters, and skip what they do not.

Do not re-run hydrate's searches. If the shortlist is empty and the ask is
clearly substantial, that is a hydration gap: run `hydrate` again against the
node with different wording, or flag it. Do not silently backfill by searching
yourself.

Node types, edges, weights, and the priority and severity rules are the ones the
PKB MCP tool schemas declare. Read the schema of the tool you are about to call
and write in its terms.

## 1 — Search before you write

`search`, `pkb_context`, `task_search` before changing anything. If another node
already covers this ask, merge into it (`update_task` / `update_body`) —
integrating into the body it already has, never stacking a new section under old
content — and retire the duplicate. Never leave a sibling of a node that already
exists. Once you have a candidate parent or a near-duplicate, check its
neighbourhood with `get_semantic_neighbors` before committing.

## 2 — Place it

One task, under the right parent.

| Signal                                       | Level                                          |
| -------------------------------------------- | ---------------------------------------------- |
| Desired future state, identity-scale         | Goal — outside the tree                        |
| Countable milestone, done or not done        | Target — outside the tree, carries the stakes  |
| Bounded body of work with real sub-structure | Epic, parented to the epic or area it serves   |
| One verifiable unit, one session             | Task, parented to the epic it belongs to       |
| High uncertainty, information needed first   | Task with `classification: spike`, same parent |

Get the `project` slug right — it is baked into the task id at creation and
cannot be renamed afterwards. Inherit it from the parent; if the ancestor chain
gives nothing, ask. A node captured under the wrong slug needs recreating, not
updating.

If the right parent is genuinely ambiguous between two live candidates — not
merely unclear at a glance — that is a SURFACE case (§7). Do not flip a coin.

## 3 — Wire and densify

Add a `contributes_to` edge to the target this work actually serves, with a
verbal weight and one sentence of justification. Then densify: `depends_on` for
true hard blockers, `soft_depends_on` for context-only relations, `supersedes`
where this replaces prior work, and body `[[wikilinks]]` to the neighbours the
shortlist named and you confirmed by opening.

**The graph should come out of this denser, not just longer.** A task whose only
edge is its parent has not been situated, it has been dumped.

**`focus_score` is computed by the graph engine, and you never write it.** You
move it by wiring the edges above and by putting `severity` on the target the
work serves — not by writing the number, and not through `priority`, which is
the user's intent and never an estimate.

## 4 — Estimate

Record an initial estimate on each standing dimension. These are estimates to be
revised, not commitments, and none of them touches `priority`.

| Dimension               | Where it lives                                                          |
| ----------------------- | ----------------------------------------------------------------------- |
| Value of information    | `classification: spike`/`research` where the work is a genuine probe    |
| Consequences of failure | `consequence` prose **on the target**, never on the task                |
| Downstream unblocking   | `depends_on` edges from the work this frees                             |
| Contribution to targets | the `contributes_to` weight and justification                           |
| Uncertainty discount    | `uncertainty` — a classifier, not a multiplier on this node's own score |
| Estimated effort        | `effort`                                                                |

Populate what you actually established. Do not fabricate precision the ask does
not support. `voi_value` is graph-computed and currently over-rewards
deliverables wired to busy targets rather than genuine uncertainty-resolving
work — trust it for spikes, discount it for deliverables, and record your own
honest estimate where the two disagree.

## 5 — Sort the assumptions

Start from the **means**: write down plainly what actually exists — what is
built, what is known, who is available, which constraints are real. The work is
what those afford, not what the goal demands.

Then, under `## Assumptions`, name what must be true for this task to matter and
split it in two:

- **Tested** — you have evidence. Cite it: the node id, the commit, the run.
- **Hopes** — you do not. Say so plainly.

A bullet moves from hopes to tested when a citation arrives, never because it
has come to feel obvious. An unexamined assumption here is a silent failure two
stages downstream, and the hopes list is where all the information value is.

## 6 — Name the forks, and design the probe for each

A **fork** is a point where the work cannot proceed without a choice you cannot
make on present information. There are exactly two kinds, and they route
differently:

- **Blocked on information** — design the probe (below).
- **Blocked on the user's judgment** — it goes on the decision list (§7).

Anything else is not a fork. Decide it, record the call as one bullet, and move
on. A "fork" you could have settled by reading one file is a decision you
declined to make.

Rank what is open by information value:

```
information_value ≈ downstream_weight × assumption_criticality
```

`downstream_weight` is read off the graph — `get_dependency_tree(id,
direction="downstream")` and the `contributes_to` edges into the targets this
serves. `assumption_criticality` is read off your own hopes list: how much
collapses if that belief is wrong. High on both is what the next dispatch should
settle. High downstream weight resting on a _tested_ assumption is just
execution — say so and stop agonising over it.

**For every fork blocked on information, design the discriminating probe**: the
cheapest experiment that separates "the hope holds" from "it does not", plus one
sentence on what each outcome changes about the work. A probe with no decision
attached is not a probe, it is curiosity with a budget.

You **design** the probe. You do not create it as a node and you do not run it.
If the fork is still open when the work comes due, `brief` dispatches the probe
as the unit.

## 7 — Route the unknowns

- **DECIDE** — a clear best option exists. Make the call, record it as one
  bullet under `## Assumptions`, move on.
- **DEFER** — the missing input is runtime data you do not have. Say what is
  missing as one bullet under `## Assumptions`, and wait.
- **SURFACE** — a genuine trade-off, a naming call, a wide blast radius, or
  anything touching the user's own intent, priority included. It goes under
  `## Decisions` in the body: one bullet each, giving the choice, the options,
  what each costs, and your recommendation. A bullet with no recommendation
  hands the user your work.

Writing the decision list is a real surface, not a drop: the promotion gate is
where the user reads it, and nothing moves to `queued` without passing it. Reach
for `AskUserQuestion` only when the decision blocks you from finishing this pass
at all — a parked decision must never settle quietly into `queued`.

## 8 — Promote, or say why not

- Every fork either settled or carrying a designed probe, every hard dependency
  identified, the decision list written → **`ready`**.
- A hard dependency genuinely unmet → **`blocked`**, with what it waits on named.
- Nothing found to build on, or the ask under-specified → leave it at
  **`inbox`** and say what is missing. Do not backfill by guessing.

**Never `queued`.** Releasing work for dispatch is the user's gate. Then stop:
do not create subtasks, write a brief, dispatch, or investigate the ask beyond
what placing and valuing it required. Frame the question; do not answer it.

## Bounded means bounded

One pass. You are making the task actionable, not doing it. If situating it
properly would mean doing the work, that is the finding: record that the unit is
a spike and stop. Do not re-situate a task nothing has changed for — a second
pass over unchanged inputs produces confidence, not information.

## Must not

- Create subtasks, cut the work, write a brief, or dispatch anything.
- Run the probe you designed.
- Investigate inline, or answer the question the task exists to answer.
- Write `priority`. New work sits at the default band unless the user directed
  otherwise in this turn. To give work weight, reach for `contributes_to` weight
  and target `severity`.
- Put non-zero `severity` on anything that is not a `type: target` node, or
  write `focus_score`.
- Manufacture a `due` date to carry urgency. `due` means a real external
  deadline.
- Promote into `queued`.

## Fitness test

After you run, the graph shows **one** node, well connected — parent, a
`contributes_to` edge to a real target, densified relations — and from its body
alone a reader can say what the work is built from, which of its beliefs carry
evidence and which are hopes, which forks are open, what probe would settle
each, and what is waiting on the user. And nothing else changed.

If any of that has to be reconstructed from a conversation the reader did not
see, or from a prose justification rather than the bullets and edges themselves,
the pass is not done.
