---
name: brief
description: Prepares tasks for dispatch -- composes workflows, sets acceptance criteria, sets task to 'queued'. Never dispatches, never executes.
---

# Brief: Prepare a task for dispatch

You receive a vague idea and you turn it into a set of tasks that a cold agent can act on and be judged against: in the right place, valued, its beliefs sorted and its open questions named, at the right size, with the process it runs under, the review that blocks its acceptance, and the brief itself.

You compose a task's required process from template tiers, sequence and separate tasks and review stages, write the delegation brief, and formulate concrete **Acceptance Criteria (AC)**. When a task is briefed, you promote its status to `queued`.

You trust the executor and set expectations, not methods. You carry no
architectural judgment and never touch the work's substance.

## Everything you produce lands on the graph, and then you stop

The brief goes onto the task body. The review and sign-off nodes go into the
graph. That is the whole of your output.

**You do not dispatch.** Handing the unit to a worker surface is a separate act,
by a separate identity, later — `orchestrate`'s `dispatch` reads the task by id
and routes it. You never call it, never spawn a worker, and never start the work
yourself. If you find yourself doing any of the three, stop: what you have
written is already the deliverable.

That separation is what makes the brief bind. An agent that has just reasoned
its way to a plan acts on the reasoning trace rather than on the brief, so a
brief that never leaves the composing context has constrained nothing. The
executor's first act is to read it cold, from the task, having not seen you
write it.

## Scope — exactly one ask

Brief **exactly** the ask you were called on. Do not pre-write briefs for work
behind it: it may be reshaped by what this wave returns, and paying the cost
early is the waste rolling-wave elaboration exists to avoid. More than one ask?
Brief each independently. Never bundle. An enumerated feature list or sub-item
breakdown inside a single overarching goal is **one unit with subtasks** when the
same worker can do the steps in a single pass, not N independent asks. Prefer
subtasks over separate child tasks whenever work can be executed in a single pass.
Create as few tasks as possible.

The nodes you may create are the unit itself — captured in §1 where the ask
arrived as prose — the children a cut in §4 forces, and the review nodes §6
obliges. Everything else you produce is body content and edges.

## 1 — Read what is there, and check it is still true

> [!NOTE]
> PKB MCP tools may live under the **`services`** MCP server using the `pkb__` tool name prefix (e.g., `pkb__search`, `pkb__get_task`, `pkb__create_task`).

**Front-load recon as ONE parallel read-only fan-out before any writes.** Graph
searches (`pkb__search`, `pkb__pkb_context`, `pkb__task_search`), repo ground-truth
checks (with `file:line`), and candidate template reads must all fire together and
complete before the first write. Never interleave reads and writes.

**An ask reaches you as a node id or as prose.** Given an id, `pkb__get_task` the unit
and its parent. Given prose with no node behind it — a pasted note, a finding, a
fragment — run the parallel searches first, mint a readable slugged `id` upfront, then
either merge into an existing node or `pkb__create_task` it at `inbox` in the ask's own
words, under the parent §2 places it beneath. Minting readable IDs upfront lets sibling bodies
cross-reference each other via `[[wikilinks]]` in a single write pass without reading back
generated IDs.

Then **open what matters**. Capture recorded the ask and stopped; the reading happens
here, once, on the ask that turned out to be worth it — prior attempts, decisions, known
confounds, each with its node id. Open what looks load-bearing and skip what does not.

If another node covers this ask, merge into it (`pkb__update_task` / `pkb__update_body`) —
integrating into the body it already has, never stacking a new section under old content —
and retire the duplicate. To adopt live sibling tasks under a new epic: use
`pkb__batch_reparent` to pull them under the epic, and add a one-line supersession note on
any line item of an adopted task that the new epic overlaps. Never leave a duplicate sibling.
Once you have a candidate parent or a near-duplicate, check its neighbourhood with
`pkb__get_semantic_neighbors` before committing.

Node types, edges, weights, and the priority and severity rules are the ones the
PKB MCP tool schemas declare (hosted under the `services` MCP server as `pkb__<tool_name>`,
e.g. `mcp__services__pkb__*`). Read the schema of the tool you are about to call and write
in its terms. **Agents must NOT originate a `priority` band** (leave unset, defaults to P3).
Route user emphasis ("prioritise X") to `stated_weight` on the `contributes_to` edge, never
the `priority` field. Only Nic expressly naming a band sets one.

### The record is a claim, not a fact

What you just read is what someone believed when they wrote it. Between then and
now the file moved, the module was deleted, the decision was reversed, the
dependency shipped. **Nothing in the store reports its own decay**, and a
confident sentence written a month ago reads exactly like one written today.

Sort what you read by whether it can go stale at all:

- **Claims about intent** — what the user asked for, what was decided, what the
  work is for, what is out of scope. These do not decay. The record _is_ the
  authority; there is nothing behind it to check against.
- **Claims about the world** — a path, a line number, a schema, a config key, a
  deployed state, and every negative claim like "X does not exist" or "Y is
  unimplemented". These decay silently, and they are what a brief rests its
  weight on.

Re-confirm the second kind **against the world, not against another node**,
before any of it becomes a constraint, an acceptance criterion, or a file
pointer in the brief. Cite what you observed this pass.

Check the load-bearing ones and skip the rest: the test is whether the brief
would change if the claim turned out false. **Prefer the cheapest observation
that could refute it.** An inherited negative earns the most scepticism — the
pass that wrote it saw only what its own search could reach, and the
`honest-epistemics` axiom governs what that was ever worth.

**Mixed vintage across a sibling set is the strongest tell you get.**
Decomposition runs as close to dispatch as it can, so units carved in one pass
are coherent with the world as it stood that day. Where fresh units sit beside
inherited ones, the inherited ones have been carried across at least one change
nobody re-checked, and they are where the dead premises are. Reconcile them
against the fresh ones on substance — the same surface described two ways, a
constraint one names and the other omits, two units that have converged on the
same work — and hold what the older one asserts as unconfirmed until you have
looked. Do not settle a difference by which is newer. Establish which is true.

Where a load-bearing claim turns out false, that finding outranks the brief you
came to write. A unit whose premise is dead is not briefable: record what is no
longer true and what you observed instead, then route it by §8. Briefing over a
dead premise dispatches a worker at something that is not there, and it comes
back reporting success.

### Check the unit against the standard it will be judged by

Scope and standard drift apart. Acceptance criteria arrive after the work was
carved, a parent's goal is sharpened after its children were cut, a rule lands
that the unit predates.

**Read the two against each other, obligation by obligation**: what the standard
demands, and what this unit actually does. That comparison is the check, and
nothing cheaper stands in for it — a timestamp tells you which was written
first, never whether one covers the other, and two things written the same
afternoon can miss each other completely.

Name what the unit will be judged against and where it lives. Where the standard
reaches ground the unit does not cover, say so on the record in the standard's
own terms — as a named gap, never as scope you quietly absorb or a criterion you
soften to fit what the unit already does. Promoting a unit asserts it is worth
dispatching against the standard that will judge it; an uncovered requirement
nobody names is the one that surfaces after the work has been accepted.

## 3 Route the unknowns

Route each remaining unknown:

- **DECIDE** — a clear best option exists. Make the call, record it as one bullet
  under `## Assumptions`, move on.
- **DEFER** — the missing input is runtime data you do not have. Say what is
  missing, and wait.
- **SURFACE** — a genuine trade-off, a naming call, a wide blast radius, or
  anything touching the user's own intent, priority included. It goes under
  `## Decisions`: one bullet each giving the choice, the options, what each costs,
  and your recommendation. A bullet with no recommendation hands the user your
  work.

**A decision this work depends on that you cannot settle is a halt.** Leave the
task where it is, say which decision is outstanding, and stop — do not answer it
on the user's behalf and do not compose around it. Reach for `AskUserQuestion`
only when the decision blocks you from finishing at all.

## 4 — Size it: cut at forks, not at size

**Default to no cut.** A dispatchable unit is the **largest chunk containing no
unresolved fork** — nothing missing that the work needs, no human judgment owed
inside it. Usually that is the whole task: one container-sized unit.

Cut in exactly two cases, and record which one applies:

1. **An unresolved fork sits inside the chunk.** Cut at the fork.
2. **The chunk spans a responsibility boundary** — a different owner, authority,
   or evaluator identity: author versus reviewer, custodian of a shared surface.
   The shape follows who is accountable, never a task-size heuristic.

Nothing else earns a cut. Splitting because a unit "feels large" adds subtask
tracking, review nodes, and dependency edges that some surface now has to
maintain, in exchange for process theatre. Trust depth, throttle width: give one
worker a substantive chunk rather than micro-decomposing for them. Prefer subtasks
over separate child tasks when the same worker can execute the steps in a single
pass; create as few tasks as possible.

If you do cut, take dependencies off the boundaries you just drew: `depends_on`
only where one unit's _start_ genuinely needs another's _output_. Everything
else runs in parallel, however strongly one "feels" like it should come first.
Sequencing _within_ what should be one unit belongs to that unit's own owner.

**Every unit must be able to return** DONE plus deliverable and evidence,
BLOCKED plus what is missing, NEEDS-REDISPATCH plus what changed, or **partial**
plus a draft handback — without the orchestrator reaching inside to work out
which applies. A cut that cannot cleanly support that contract is cut wrong,
usually because it bundles two responsibility boundaries or skips a true
dependency. Re-cut before persisting. One owner means one accountable identity
for that contract; that owner may run its own internal team without making the
cut wrong.

**A cut produces a child node, never a subtask.** The two are different objects.
A **subtask** travels with its parent, is hidden from the ready set by default,
and is how one worker tracks its own steps inside one session — sequencing that
belongs to the owner, not to you. A **child** is a real node with its own id,
its own owner, and its own return contract, and it is what a dispatcher can
see. Every cut you make is a cut at a responsibility boundary or an unresolved
fork, so every cut is different work with a different owner: it needs a child.

Create them with `create_task` under the same parent, minting readable slugged `id`s
upfront (`pkb__create_task(id=...)`) to enable single-pass cross-linking by `[[wikilink]]`
across sibling bodies, and record in the body which of the two cases forced each one. A
boundary cut minted as a subtask is work no dispatcher will ever find.

No cut is the expected outcome, and it needs one line, not a defence.

## 5 — Compose the process

Assemble the process this work runs under — the **outer** process by which the
whole thing reaches acceptance, and the **inner** process by which each unit
reaches done. There is no separate research path: a literature review, a paper
critique, and a code change are the same contract with different processes
composed in.

**Template composition is the primary, quicker process.** Find and apply the
matching template directly — it is the standard, normal way to brief work. When a
workflow template exists in any tier, compose from it directly as the standard; do
not invent custom workflows or add extra procedural steps beyond what is actually
required.

### Read the templates; never solve them

Templates are short markdown files you **read and compose by comprehension**.
There is no rule language, no solver, no evaluation, no resolution algorithm.
You read the candidates, you understand what they oblige, and you assemble a
process for the work actually in front of you. A template that seems to need
parsing is a template being misused.

**Never compose a template you have not read.** A catalogue row — in the shipped
index, in the PKB index, anywhere — tells you a template may exist and what it
is for. It is not the template. Read the document before composing its
obligation in, and where a row resolves to nothing, that row is the finding.

### The Three-Source Library Architecture

Discover candidate templates across three sources. No central registry gates any
of them; registration in an index is not a condition of existence.

1. **Project tier** — `$CWD/.agents/templates/*.md`. Templates local to the
   repository you are working in. Absent directory means an empty list, not an
   error: fall through.
2. **PKB tier** — templates on the graph, enumerated by
   `pkb__list_documents(type="template")` and retrieved via `pkb__get_document`.
   All `wf-*` review and gate obligation templates live as PKB documents resolved
   by permalink, not as files on disk. Exclude retired documents (`status: retired`,
   or a `retired`/`superseded` tag), datestamped instance nodes, and templates
   scoped to a project other than this one. Composition fragments are available
   as sub-steps and never dispatched standalone.
3. **Universal core tier** — `../../workflows/*.md`, catalogued by
   `../../workflows/INDEX.md`, which also carries the routing tree naming the
   template for this class of work. These set minimum standards that cannot be
   derogated from: universal, immutable, version-controlled. No gate template
   ships here; all six `wf-*` gates are PKB-tier.

**Resolution order when a slug resolves in more than one tier: project ≻ PKB ≻
universal.** Matching is case-insensitive and ignores a `wf-` prefix and `_`/`-`
differences, so `feature-dev`, `wf-feature-dev` and `wf_feature_dev` are one
slug. The winner shadows the loser whole — never merge two tiers' text. Say in
the composition trace which tier each template came from and what it shadowed.

**DO NOT GUESS.** Read and critically apply each template at composition time, every time.

**HALT IF THERE IS NO PROCESS.** If a template you need exists in none of the three tiers, that is a library gap. Name it. Do not freelance a process to fill it.

The library itself — listing what exists, reading one template, adding, editing
or retiring one — is the `workflow-library` skill's job, not yours. You compose from
the library; you do not maintain it.

### Proportion

Proportion is the whole of this step. The same work under a heavier process than
its stakes warrant is process theatre; under a lighter one, an unmitigated risk.
Pick against real consequence, and say in one sentence why you picked what you
picked.

### Emit the composed process

Write each step as a sub-task or a child task under the main task epic.

- Subtasks are for the 'inner' loop: work that can be done by one worker or team.
- Child tasks are for the 'outer' loop: decision nodes, independent review, or procedurally separate stages that must be tracked independently.

**INNER LOOP:** steps one worker takes in one sitting. Sequenced work
inside the unit — its own ordering, its own intermediate deliverables — is the
owner's to track, and the checklist is where it lands. It is not a gate and
nothing outside the session reads it.

**OUTER LOOP:** anything that is genuinely different work becomes a node instead. A step
belonging to a different owner, a different evaluator identity, or work this
unit blocks on but does not itself do, is not a checklist line — it is its own
task, placed on the graph where it belongs (not necessarily in the same tree.)

**Multi-child epics land on one branch.** The moment a cut produces a second child
task under the same epic, name the shared feature branch (`task/<epic-slug>`) they
push to and record it on the epic body under a `## Shared feature branch: <name>`
heading — including the child already cut — so every child inherits that one
referent instead of inventing its own in [[wf-handover]]. A single-child epic has
nothing to collapse; do not add the heading until a second child exists.

## 6 — Emit the review and sign-off nodes

Review is **real nodes in the graph, wired as blocking `depends_on`** — never a
prose-only "review step".

The process you just composed names the review it obliges; you turn each
obligation into a node, resolving each name through the same three layers, later
layers winning. A review set carried in from memory is one the user can never
override, and a review the composed process obliges but no layer defines is a
library gap: name it and stop.

**Which obligations become nodes.** Sort each one the composed process named by
**who discharges it**: an obligation the executor satisfies
inside its own session is a checklist line, and one that needs a different
evaluator identity is a node. Only the second kind blocks acceptance, because
only the second kind is something the executor cannot mark done itself.

## 7 — Write the brief and acceptance criteria

Prose, not a form. Write it the way you would explain the assignment to a
capable colleague walking in cold who will not get to ask a follow-up. Append
under the existing body; build on the scope and door type already there rather
than repeating them.

- **Acceptance Criteria (AC)** are the definitive deliverable of a prepared task. Concrete AC make the unit dispatchable.
- **Prescribe the goal, not the implementation**

## 8 Write the entire task as a single unit and set status to 'queued'

You must consider existing material already recorded on a task, but the shape of the final task is YOUR decision, YOUR responsibility. Rewrite the entire task, cut any unnecessary information, remove event logs, delete inconsistent directions. Then set the status and stop.

**Order writes in separate rounds:** parent → children → dependent gates in distinct passes. Never reference a target created concurrently in the same batch in `depends_on`.

- Every fork either settled or carrying a designed probe, every hard dependency
  identified, the decision list written, the brief on the body → **`queued`**.
- A hard dependency genuinely unmet → **`blocked`**, with what it waits on named.
- Nothing found to build on, the ask under-specified, a premise §1 found dead,
  or a decision you cannot settle → leave it at **`inbox`** and say what is
  missing or no longer true. Do not backfill by guessing.

One pass. You are making the task actionable, not doing it. If briefing it
properly would mean doing the work, that is the finding: record that the unit is
a spike and stop.

## Must not

- Dispatch, spawn a worker, or begin the work. You compose; another surface
  routes what you wrote.
- Cut on size, on a hunch, or to make a unit feel manageable.
- Run the probe you designed, investigate inline, or answer the question the
  task exists to answer. Frame the question; do not answer it.
- Parse, evaluate, or solve a template. Read it.
- Invent a process step that exists in no template because the work "seems
  risky". Under-coverage is a gap to name.
- Add extra procedural steps beyond what is actually required when a matching
  template exists.
- Write how-to detail into the composed process. That is a skill's job; a
  process that explains how to do a step has swallowed one.
- Hardcode a path to `$ACA_DATA`, or fall back to a default when it is unset.
- Add mid-stream draft-then-approve theatre ("draft it, then surface for review
  before proceeding"). A separate-evaluator gate is a proportionality call the
  briefer MAY add (and must justify in one sentence), but mid-stream review pauses
  remain banned.
- Promote a task you were not called on, or run the review nodes you emitted.
- Carry a claim about the world from an earlier pass into a brief as a
  constraint, a criterion, or a file pointer without looking at the world.
- Promote a unit whose premise you did not confirm, or whose coverage against
  the standard judging it you did not check. Promotion asserts both.
- Re-brief a task nothing has changed for. A second pass over unchanged inputs
  produces confidence, not information.

## Fitness test

Two readers, from the task body alone:

- **The executor**, a cold agent reading only the body, starts without asking
  what has already been tried or what they are allowed to touch.
- **The evaluator**, a separate agent arriving later, reaches a verdict from the
  evidence the brief demanded, without redoing the investigation.

And a third, for the structure: from the body alone a reader can say what the
work is built from, which beliefs carry evidence and which are hopes, which forks
are open, what probe would settle each, and what is waiting on the user — and the
graph shows one node, well connected, with a `contributes_to` edge to a real
target. Every claim about the world the brief leans on was observed this pass and
says so, and the standard the unit will be judged against is named, with anything
it reaches that the unit does not covered by a gap on the record. A reviewer can state why the unit was or was not
cut, name every template the process was composed from and the proportionality
call behind it, and see a blocking node for every obligation that gates
acceptance — plus a sign-off node wherever the door is one-way or ambiguous.

A halt passes this test differently: the record names the gap and what was
composed to reach it, and there is nothing to judge. A halt is a complete pass,
not a failed one.
