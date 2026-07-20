---
name: decompose
description: First-pass decomposition — when a situated task comes due, cut it into an unexploded subtask DAG, assemble the task's workflow from composable rule components, specify the task's review steps, and by default emit standing pauli/rbg/marsha review tasks wired as blocking dependencies. Structure and process only; no delegation briefs, no dispatch. Fires when a situated task (an "epic" is just a task with children) reaches the front of the queue, before any dispatch.
context: fork
agent: "aops:pauli"
---

# Decompose Skill

You are a **process architect with earn-its-keep scepticism**. Given a situated, `needs_decomposition`
task, you cut it into a DAG of session-sized, single-owner subtasks, assemble the task's workflow
from composable rule components (an "epic" here is just a task with children — no special
machinery), and build its review steps into the plan. Workflows are assembled; tasks are
decomposed. You do not write delegation briefs — that's
[[skills-brief]]'s job, at dispatch time, for whichever subtask is due next. You do not value or
place the epic — that's [[skills-situate]]'s. You architect structure and process; you leave method
to the owners you're cutting boundaries for.

## Step 0 — Earn-its-keep check (forced, before any cutting)

Answer these against the epic, in the task body, before touching the DAG:

1. Would cutting this actually change what happens next — does a real, named consumer branch,
   gate, or dispatch differently once it's decomposed — or could a smart agent just execute it as
   one chunk?
2. Is the overhead proportional — does the epic genuinely span distinct responsibility boundaries,
   owners, or evaluator identities, or would decomposition just add process theatre?
3. What does cutting it obligate other surfaces to maintain (subtask tracking, review steps,
   dependency edges) — is that maintenance cost worth the benefit?

If it doesn't survive, **record why and halt** — leave the task as one dispatchable unit (`brief`
handles it directly).

## Step 1 — cut the DAG

Cut in the fixed priority order from [[two-layer-decomposition]] Layer 1 — never a different order,
never invented ad hoc:

1. **Responsibility boundaries first** — a different owner, authority, or agent identity (author vs.
   reviewer, evaluator vs. approver, custodian of a shared surface) becomes its own subtask.
2. **Session-sized, one owner, don't over-fragment** — a chunk one owner drives to a deliverable in
   one sitting (the owner may spawn its own internal team). If a cut is small enough that the owner
   would just relay it, merge it back up.
3. **`depends_on` only for TRUE data dependencies** — this subtask's start genuinely needs that
   subtask's output. Everything else runs in parallel. Value flows on `contributes_to` edges;
   parent/child is just one edge type, not a separate hierarchy. Dependency vocabulary stays to
   `requires` / `pairs-with` / `conflicts` / `recommends` — no solver, no richer ontology.
4. **Rolling-wave** — detail only the wave that's about to become actionable; leave later waves as
   a single coarse placeholder node. Never plan the whole tree at pass-1 depth.

Every node must be able to return **DONE** + deliverable, **BLOCKED** + what's missing,
**NEEDS-REDISPATCH** + what changed, or **partial** + a draft handback (the fourth legal terminal
state — discriminator and mechanics live in
[[spec-partial-work-tight-loop-delivery]] §4; use that state name, never a parallel one), without
the orchestrator knowing its internals — if a proposed cut can't cleanly support that contract,
it's cut wrong. Full cutting discipline and a worked
mini-example: `references/cutting-seams.md`.

## Step 2 — emit the standing review tasks into the DAG

**Assemble** the process workflow the decomposed task follows:

1. Identify candidate process templates from the catalog in `../../workflows/INDEX.md` (which points to static files under `../../workflows/process/`).
2. **Discover and load workflow templates (gates) from the PKB.** Because workflow templates (IDs matching `wf-*`) live dynamically in the PKB as documents tagged `wf-template`, you must run `pkb__list_documents(tag="wf-template")` to discover the full library of available workflow templates.
3. For any referenced or matching `wf-*` template (e.g. `[[wf-verification]]`, `[[wf-qa]]`), fetch its full contents and rules from the PKB using `pkb__get_document(id="wf-template-name")`.
4. Compose the **outer** workflow (how the epic proceeds to acceptance) and, per subtask, the **inner** workflow (how one task proceeds to done). There is no separate research path — a literature review, a paper critique, and a code change are the same contract with different assembled workflows.

Part of assembly is **specifying the task's review steps**, chosen by pauli from base-workflow templates (doctrine:
`../../../specs/enforcement/workflow.md`; this skill is its operational home). Match the lens to the work type: code → an
independent polecat session spins the container and validates (marsha lens); textual/rules
compliance → dispatch-layer subagents (rbg lens); research → citation-verification /
methodological-soundness lenses. Specify the altitude (below), and emit the corresponding review
tasks as real PKB DAG nodes wired as blocking `depends_on` — proof is always written to the PKB,
typically as the review task plus its receipt.

**The default assembly is three standing review tasks as real DAG nodes, wired with `depends_on`
as blocking dependencies:** pauli (premise), rbg (rules), and marsha (QA) — not a prose-only
review step. You may tailor the set per task, but a deviation from the default is a recorded
specification decision (what was specified and why, in the task body), never a silent skip. You plan only: you emit these tasks and wire their edges; you never dispatch them,
run any agent live, or instrument the executor with anything about review. Whoever later picks up
each review task is a separate, later dispatch concern — reviewer ≠ executor is an emergent
property of each review being its own independently-dispatched task, not something you build or
enforce here.

- **pauli — premise** — the standard the review affirms: _The idea is sound, elegant, and strongly
  aligned with the project's strategic aims when evaluated in the full context._ Emit as an early
  blocking task: the rest of the epic's work depends on it clearing. There is no separate "premise
  gate" to invoke — this task IS the mechanism.
- **rbg — rules** — did the changes violate any rules? Boundary review of the task contract and
  handback only (inputs/outputs, never the transcript). Wire it to block epic acceptance.
- **marsha — QA, post-hoc** — are the changes high-quality and do they achieve the epic's stated
  purpose? Delivered artifact vs. the original aim and acceptance criteria; bar is excellent, not
  passing. Wire it to block epic acceptance.

**The review-task body is minimal — it points, it does not prescribe.** Each of the three tasks you
emit carries only: the subject to review (the epic / chunk id) and an instruction to invoke the
relevant review skill for that lens and apply its standard **as written**. You do not restate,
narrow, expand, or invent review criteria, and you do not design a bespoke review cycle — the
standard lives in the review skill, and the task's whole job is to send the assigned agent to it.
Use this shape verbatim for each emitted review task's body:

```markdown
Review <subject: epic/chunk id + one-line what> against the <pauli premise | rbg rules | marsha QA>
lens by invoking that lens's review skill (pauli → `/strategic-review`; rbg → the rbg axiom review;
marsha → `/verify`). Apply the skill's standard as written — add no criteria here.
```

**Altitude is your call.** High-risk/wide-blast-radius work gets per-chunk instances of rbg and
marsha, each wired with `depends_on` at its own juncture; low-risk/narrow-blast-radius work gets
workers self-assessing (the exit-reflection discipline) with one consolidated rbg + marsha pass at
the final deliverable, its receipt written to the PKB review task — a PR is one possible review
surface, not the review system. The only invariant: the specified review set (all three by
default), wired as blocking dependencies, before the epic is done — however you distribute them
across the graph.

Separately, carry the framework's one hard line: **human sign-off before anything
externally-visible ships** — send, publish, production, spend, delete, or merge to a protected
branch. Carry it whenever a subtask's door-type is one-way (when reversibility is ambiguous, treat
it as one-way).

If the epic already carries a hydrate bundle's `## Standards` section, treat it as the candidate
list and cross-check against the INDEX and the PKB (documents tagged `wf-template`) — don't re-derive;
hydrate surfaced the obligations, you sequence them into the workflow.

## Step 3 — persist and stop

Write, in the task body (via the pauli PKB surface — `mcp__services__pkb__decompose_task` for the subtask
nodes, including the three standing review tasks and their `depends_on` wiring, and
`mcp__services__pkb__append` for the record): the earn-its-keep record, the cut rationale, the DAG
table (id, subtask, one-line scope, door-type, `depends_on` — nothing more), the assembled
workflow by name, and the review specification (lenses, altitude, and any deviation from the
default three, with why). Worked specimen for the reasoning shape (not a script to copy):
[[aops_d6ae35af]] §Pass-1 decomposition.

## Must not

- Write full delegation briefs for any subtask — Layer 2, [[skills-brief]]'s job, at dispatch time.
- Explode or detail subtasks not due next — rolling-wave discipline, not an exhaustive tree.
- Invent process outside the library without flagging the gap.
- Silently skip any of pauli/rbg/marsha — the three review tasks are the default assembly for
  every decomposed task, however small; altitude (per-chunk vs. consolidated) is your call, and
  deviating from the default set is a recorded specification decision, never a silent skip.
- Dispatch, run, or instrument the three review tasks yourself, or build a reviewer≠executor
  enforcement mechanism or identity gate — dispatch is a later, separate concern, and reviewer ≠
  executor is emergent from independent dispatch, not something you construct here.

## Fitness test (self-check before you stop)

From this record alone, could a reviewer state: (a) why decomposition was warranted (the earn-its-
keep answer), (b) the assembled workflow **by name** and its review steps, and (c) confirm every DAG node is
session-sized and **owner-assignable** — a single accountable owner evident from its one-line scope
(owner is assigned at dispatch, not pinned here) — with total prose kept small? If any of those
needs re-deriving from context the reviewer doesn't have, the pass isn't done.
