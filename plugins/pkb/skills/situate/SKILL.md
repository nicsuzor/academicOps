---
name: situate
description: Strategic intake — turn a hydrated ask into exactly ONE valued, well-connected task on the graph, marked needs_decomposition, then stop. Fires after hydrate for any non-trivial ask. Never decomposes, briefs, or dispatches.
agent: "pauli"
---

# Situate

Turn a hydrated ask into **one** task, placed on the graph, valued, wired, and
marked `needs_decomposition`. Nothing more. You stop the instant the task is
placed. `needs_decomposition` is a graph signal, not a promise a stage exists to
consume it: no shipped skill consumes it today. Mark it anyway.

You work from the bundle `hydrate` emits — `## Intent`, `## Context`,
`## Standards`, `## Dependencies`. Trust it. Re-searching what it already found
is hydrate's job done twice. If the bundle is thin or missing for work that is
clearly substantial, that is a hydration gap: flag it, do not silently backfill.

Node types, edges, weights, and the priority and severity rules are the ones the
PKB MCP tool schemas declare. Read the schema of the tool you are about to call
and write in its terms.

## 1 — Search before you create

`search`, `pkb_context`, `task_search` before writing anything. If something
already covers this ask, update it (`update_task` / `update_body`) —
integrating into the body it already has, never stacking a new section under
old content. Never create a sibling of a node that already exists. Once you have a candidate parent
or a near-duplicate, check its neighbourhood with `get_semantic_neighbors` before
committing.

## 2 — Place it

One task, under the right parent, by `create_task`.

| Signal                                       | Level                                          |
| -------------------------------------------- | ---------------------------------------------- |
| Desired future state, identity-scale         | Goal — outside the tree                        |
| Countable milestone, done or not done        | Target — outside the tree, carries the stakes  |
| Bounded body of work with real sub-structure | Epic, parented to the epic or area it serves   |
| One verifiable unit, one session             | Task, parented to the epic it belongs to       |
| High uncertainty, information needed first   | Task with `classification: spike`, same parent |

Get the `project` slug right the first time — it is baked into the task id and
cannot be renamed afterwards. Inherit it from the parent; if the ancestor chain
gives nothing, ask.

If the right parent is genuinely ambiguous between two live candidates — not
merely unclear at a glance — that is a SURFACE case. Do not flip a coin.

## 3 — Wire and densify

Add a `contributes_to` edge to the target this work actually serves, with a
verbal weight and one sentence of justification. Then densify: `depends_on` for
true hard blockers, `soft_depends_on` for context-only relations, `supersedes`
where this replaces prior work, and body `[[wikilinks]]` to the neighbours the
bundle's Context and Dependencies sections already named.

**The graph should come out of this denser, not just longer.** A task whose only
edge is its parent has not been situated, it has been dumped.

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

Populate what the bundle makes clear. Do not fabricate precision the ask does not
support. `voi_value` is graph-computed and currently over-rewards deliverables
wired to busy targets rather than genuine uncertainty-resolving work — trust it
for spikes, discount it for deliverables, and record your own honest estimate
where the two disagree.

## 5 — Surface the assumptions

Name, as one-line bullets under `## Assumptions` in the task body, what must be
true for this task to matter — the beliefs that, if wrong, invalidate the
estimate or the placement. An unexamined assumption here is a silent failure
two stages downstream.

## 6 — Route the unknowns

- **DECIDE** — a clear best option exists. Make the call and record it as one
  bullet under `## Assumptions`, move on.
- **DEFER** — the missing input is runtime data you do not have. Say what is
  missing as one bullet under `## Assumptions`, and wait.
- **SURFACE** — a genuine trade-off, a naming call, a wide blast radius, or
  anything touching the user's own intent, priority included. Raise it via
  `AskUserQuestion`, the visible channel. Writing it into the body alone is not
  surfacing; an unread body section is a dropped decision. If you cannot raise it
  this turn, leave the task `inbox` and ask next turn — never let a parked
  decision settle quietly into `queued`.

## 7 — Mark and stop

`update_task` to set `needs_decomposition: true`. Then stop. Frame the question;
do not answer it.

## Must not

- Create subtasks, write a brief, or dispatch — not this skill's job, shipped
  owner or not.
- Investigate the ask beyond what placing and valuing it required.
- Write `priority`. New work sits at the default band unless the user directed
  otherwise in this turn. To give work weight, reach for `contributes_to` weight
  and target `severity`.
- Put non-zero `severity` on anything that is not a `type: target` node.
- Manufacture a `due` date to carry urgency. `due` means a real external
  deadline.

## Fitness test

After you run: the graph shows **one** new node, well connected — parent, a
`contributes_to` edge to a real target, densified relations — carrying a value
estimate and an `## Assumptions` bullet list a reviewer can audit against the
bundle it came from. And nothing else changed. If a reviewer cannot reconstruct
why the placement and the estimate are what they are from the body's bullets and
edges alone — not from a prose justification — the pass was rushed.
