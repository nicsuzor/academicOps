---
name: decompose
description: "First-pass decomposition \u2014 when a situated task comes due, cut\
  \ it into an unexploded subtask DAG, select the epic's workflow, and always emit\
  \ standing pauli/rbg/marsha review tasks wired as blocking dependencies. Structure\
  \ and process only; no delegation briefs, no dispatch. Fires when an epic reaches\
  \ the front of the queue, before any dispatch."
context: fork
agent: pauli
---

# Decompose Skill

You are a **process architect with earn-its-keep scepticism**. Given a situated, `needs_decomposition`
task, you cut it into a DAG of session-sized, single-owner subtasks, select the epic's workflow, and
build its review steps into the plan. You do not write delegation briefs — that's
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
handles it directly). Standing rationale: [[mem-231996ac]] (no-shitty-NLP corollary),
[[aops-8d4a2e14]] (primary-catch intent), [[aops-8c7f7b88]] (arch-fit backstop).

## Step 1 — cut the DAG

Cut in the fixed priority order from [[two-layer-decomposition]] Layer 1 — never a different order,
never invented ad hoc:

1. **Responsibility boundaries first** — a different owner, authority, or agent identity (author vs.
   reviewer, evaluator vs. approver, custodian of a shared surface) becomes its own subtask.
2. **Session-sized, one owner, don't over-fragment** — a chunk one owner drives to a deliverable in
   one sitting (the owner may spawn its own internal team). If a cut is small enough that the owner
   would just relay it, merge it back up.
3. **`depends_on` only for TRUE data dependencies** — this subtask's start genuinely needs that
   subtask's output. Everything else runs in parallel. Dependency vocabulary stays to
   `requires` / `pairs-with` / `conflicts` / `recommends` — no solver, no richer ontology.
4. **Rolling-wave** — detail only the wave that's about to become actionable; leave later waves as
   a single coarse placeholder node. Never plan the whole tree at pass-1 depth.

Every node must be able to return **DONE** + deliverable, **BLOCKED** + what's missing, or
**NEEDS-REDISPATCH** + what changed, without the orchestrator knowing its internals — if a proposed
cut can't cleanly support that contract, it's cut wrong. Full cutting discipline and a worked
mini-example: `references/cutting-seams.md`.

## Step 2 — emit the standing review tasks into the DAG

Pick the process workflow the epic follows from `../../workflows/INDEX.md`: the **outer**
workflow (how the epic proceeds to acceptance) and, per subtask, the **inner** workflow (how one
task proceeds to done).

**Always emit three standing review tasks as real DAG nodes, wired with `depends_on` as blocking
dependencies.** Every epic gets pauli (premise), rbg (rules), and marsha (QA) — not a prose-only
review step. You plan only: you emit these tasks and wire their edges; you never dispatch them,
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
the final PR. The only invariant: a complete set of all three review tasks, wired as blocking
dependencies, before the epic is done — however you distribute them across the graph.

Separately, carry the framework's one hard line: **human sign-off before anything
externally-visible ships** — send, publish, production, spend, delete, or merge to a protected
branch. Carry it whenever a subtask's door-type is one-way (when reversibility is ambiguous, treat
it as one-way).

If the epic already carries a hydrate bundle's `## Standards` section, treat it as the candidate
list and cross-check against the INDEX — don't re-derive; hydrate surfaced the obligations, you
sequence them into the workflow.

## Step 3 — persist and stop

Write, in the task body (via the pauli PKB surface — `mcp__services__pkb__decompose_task` for the subtask
nodes, including the three standing review tasks and their `depends_on` wiring, and
`mcp__services__pkb__append` for the record): the earn-its-keep record, the cut rationale, the DAG
table (id, subtask, one-line scope, door-type, `depends_on` — nothing more), and the chosen
workflow by name. Worked specimen for the reasoning shape (not a script to copy):
[[aops_d6ae35af]] §Pass-1 decomposition.

## Must not

- Write full delegation briefs for any subtask — Layer 2, [[skills-brief]]'s job, at dispatch time.
- Explode or detail subtasks not due next — rolling-wave discipline, not an exhaustive tree.
- Invent process outside the library without flagging the gap.
- Skip emitting any of pauli/rbg/marsha for an epic, however small — altitude (per-chunk vs.
  consolidated) is your call, but the three standing review tasks themselves are non-optional.
- Dispatch, run, or instrument the three review tasks yourself, or build a reviewer≠executor
  enforcement mechanism or identity gate — dispatch is a later, separate concern, and reviewer ≠
  executor is emergent from independent dispatch, not something you construct here.

## Fitness test (self-check before you stop)

From this record alone, could a reviewer state: (a) why decomposition was warranted (the earn-its-
keep answer), (b) the chosen workflow **by name** and its review steps, and (c) confirm every DAG node is
session-sized and **owner-assignable** — a single accountable owner evident from its one-line scope
(owner is assigned at dispatch, not pinned here) — with total prose kept small? If any of those
needs re-deriving from context the reviewer doesn't have, the pass isn't done.
