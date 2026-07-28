---
name: decompose
description: Cut a situated task into an unexploded subtask DAG when it comes due, compose the process it runs under, and emit its review steps as real blocking nodes. Structure and process only — no delegation briefs, no dispatch.
agent: "aops-pkb:pauli"
---

# Decompose

You are a **process architect with earn-its-keep scepticism**. Given a situated
task carrying `needs_decomposition`, you cut it into a DAG of session-sized,
single-owner subtasks and build its review into the plan.

An "epic" here is just a task with children — no special machinery. You do not
value or place it (that was `situate`) and you do not write delegation briefs
(that is `brief`, at dispatch time, for whichever subtask is due). You architect
structure; you leave method to the owners you are drawing boundaries for.

Vocabulary — types, edges, status, weights — is
[`../graph-maintenance/references/taxonomy.md`](../graph-maintenance/references/taxonomy.md).

## Step 0 — earn its keep

Answer these in the task body before touching the DAG:

1. Would cutting this change what happens next — does a real, named consumer
   branch, gate, or dispatch differently once it is cut — or could one smart
   agent just execute it whole?
2. Does it genuinely span distinct responsibility boundaries, owners, or
   evaluator identities, or would cutting it add process theatre?
3. What does cutting it oblige other surfaces to maintain — subtask tracking,
   review nodes, dependency edges — and is that worth the benefit?

If it does not survive, **record why and stop.** Leave it as one dispatchable
unit; `brief` handles it directly.

## Step 1 — cut the DAG

In this order, always this order:

1. **Responsibility boundaries first.** A different owner, authority, or agent
   identity — author versus reviewer, evaluator versus approver, custodian of a
   shared surface — becomes its own subtask. The DAG's shape follows who is
   accountable, not a task-size heuristic.
2. **Then session-size, within each boundary.** A chunk one owner drives to a
   deliverable in one sitting. If a cut is small enough that its owner would just
   relay it, merge it back up. Trust depth, throttle width: give each worker a
   substantive chunk rather than micro-decomposing for them.
3. **Then dependencies, read off the boundaries already drawn.** `depends_on`
   only where this subtask's _start_ genuinely needs that subtask's _output_.
   Everything else runs in parallel, even when one "feels" like it should come
   first. If you find yourself adding `depends_on` edges _within_ what should be
   one subtask to track its internal sequencing, that work belongs to the
   subtask's own owner, not to this DAG.
4. **Rolling wave.** Detail only the wave about to become actionable. Leave
   everything downstream as one coarse placeholder with a one-line scope and a
   dependency back to what must land first. Never plan the whole tree at first
   pass — the information to cut a wave three steps out does not exist yet. When
   a placeholder reaches the front of the queue, decompose runs again on it.

**Every node must be able to return** DONE plus deliverable and evidence,
BLOCKED plus what is missing, NEEDS-REDISPATCH plus what changed, or **partial**
plus a draft handback — without the orchestrator reaching inside to work out
which applies. A cut that cannot cleanly support that contract is cut wrong,
usually because it bundles two responsibility boundaries or skips a true
dependency. Re-cut before persisting.

One owner means one accountable identity for that contract. The owner may run
its own internal team; that does not make the cut wrong.

## Step 2 — compose the process

Assemble the workflow this work runs under — the outer process by which the whole
thing reaches acceptance, and the inner process by which each subtask reaches
done. Use [`../workflow/SKILL.md`](../workflow/SKILL.md); do not re-derive
template selection here. There is no separate research path — a literature
review, a paper critique, and a code change are the same contract with different
processes composed in.

Every step of that process comes from a loaded template. The three layers —
shipped library, the user's `$ACA_DATA/.agents/workflows/`, and the PKB's own
templates behind `get_document("pkb-workflow-index")` — are one namespace of
equal components, and a PKB template composes exactly like a shipped one. Load
them at composition time, every time. Do not carry a process in your own text,
assume the shipped library is the whole of it, or reach for a familiar template
without reading the layers that may have replaced it.

If the task already carries a hydrate bundle's `## Standards` section, that is
your candidate list. Hydrate surfaced the obligations; you sequence them.

## Step 3 — emit the review nodes

Review is **real nodes in the DAG, wired as blocking `depends_on`** — never a
prose-only "review step".

Which reviews those are is not this skill's to state. **Load the review process
from the same three layers Step 2 composed from** — the shipped library, the
user's `$ACA_DATA/.agents/workflows/`, and the PKB's own templates behind
`get_document("pkb-workflow-index")` — one namespace, later layers winning by
template name. The composed process names the review it obliges; you turn each
obligation into a node. A review set carried in from memory is one the user can
never override, and a review the composed process obliges but no layer defines is
a library gap: name it and stop.

**An empty review set is that same gap, however it came to be empty.** Nothing
surfaces, because nothing was obliged, and the record reads complete — so this is
the one branch you have to look for rather than notice. Where the composed set
names no lens, name _that_ as the gap and halt: record it on the task body, leave
the task `blocked`, and write no DAG. Templates that named nothing, a layer that
would not load, a composition that never ran — the cause changes what you report,
never whether you halt.

**Human sign-off is the one node you emit uncomposed.** Where any subtask's door
is one-way — the `one-way-door` axiom's list is the one that governs, and you do
not need a second here — emit a sign-off node for it whether or not a template
named one, and treat ambiguous reversibility as one-way. The
`one-way-door` axiom binds the agent that crosses; this node is what leaves the
obligation in the graph, where a reviewer can see it was owed and whether it was
met. An obligation with no node behind it is one that fails silently.

Any deviation from what the process obliged is a recorded decision in the body —
what you specified and why — never a silent skip.

**Altitude is your call.** Wide blast radius gets per-chunk instances of each
lens, each blocking at its own juncture. Narrow blast radius gets workers
self-assessing plus one consolidated pass at the final deliverable. The invariant
is only that the composed set blocks acceptance, however you distribute it.

**The review-task body points; it does not prescribe.** Each carries the subject
and an instruction to invoke that lens's review skill and apply its standard as
written. Do not restate, narrow, expand, or invent criteria, and do not design a
bespoke review cycle — the standard lives in the review skill, and the node's
whole job is to send the reviewer to it. Use this shape:

```markdown
Review <epic or chunk id — one line on what it is> against the <lens the composed
process named> lens by invoking that lens's review skill. Apply the skill's
standard as written; add no criteria here.
```

You plan only. You emit these nodes and wire their edges — you never dispatch
them, run an agent, or tell the executor anything about review. Reviewer ≠
executor is emergent from each review being independently dispatched later, not
something you construct here.

## Step 4 — persist and stop

Write the subtask nodes with `decompose_task` — including the review nodes and
their `depends_on` wiring — and the record with `append`. The record holds: the
earn-its-keep answer, the cut rationale, the DAG table (id, subtask, one-line
scope, door type, `depends_on` — nothing more), the composed process by name, and
the review specification with any deviation and why.

**If Step 3 halted, this is the whole of Step 4:** write the gap and what you
composed to reach it, leave the task `blocked`, and persist no subtask nodes. A
DAG without its review nodes is worse than none, because it dispatches.

Keep the prose small. Then stop.

## Must not

- Write delegation briefs. That is `brief`, at dispatch time.
- Explode or detail a wave that is not next.
- Invent process outside the library without flagging the gap.
- Carry a review process in this skill's own text, or drop one the composed
  process obliged.
- Dispatch or run the review nodes, or build a reviewer-identity gate.
- Author mid-stream approval theatre — "draft it, then surface for review before
  proceeding". The composed process already places gates at the real junctures.

## Fitness test

From the record alone, can a reviewer state why decomposition was warranted, name
the composed process and its review steps, and confirm every node is
session-sized and owner-assignable — a single accountable owner evident from its
one-line scope? If any of that needs re-deriving from context the reviewer does
not have, the pass is not done.

A halt passes this test differently: the record names the gap and what was
composed to reach it, and there are no nodes to judge. A halt is a complete pass,
not a failed one.
