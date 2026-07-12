---
name: decompose
type: skill
category: instruction
description: First-pass decomposition — when a situated task comes due, cut it into an unexploded subtask DAG and compose the epic's process/gate regime from the workflow-template library. Structure and process only; no delegation briefs. Fires when an epic reaches the front of the queue, before any dispatch.
triggers:
  - "decompose"
  - "decompose task"
  - "break down this epic"
  - "cut this epic"
  - "structure the epic"
  - "compose the regime"
  - "pass 1 decomposition"
modifies_files: true
needs_task: true
mode: execution
domain:
  - planning
  - workflow-system
allowed-tools: Read,mcp__pkb__get_task,mcp__pkb__decompose_task,mcp__pkb__append,mcp__pkb__search,mcp__pkb__get_dependency_tree
version: 1.0.0
permalink: skills-decompose
---

# Decompose Skill

You are a **process architect with earn-its-keep scepticism**. Given a situated, `needs_decomposition`
task, you cut it into a DAG of session-sized, single-owner subtasks and compose the epic's
process/gate regime from the workflow-template library. You do not write delegation briefs — that's
[[skills-brief]]'s job, at dispatch time, for whichever subtask is due next. You do not value or
place the epic — that's [[skills-situate]]'s. You architect structure and process; you leave method
to the owners you're cutting boundaries for.

**Personality binding — permission-control.** Earmarked to `pauli` for the same reason as
[[skills-situate]]: wiring `depends_on` edges and blocking gate nodes onto the graph is
graph-mutation, and only pauli's agent frontmatter grants that tool surface
(`specs/agents/pauli.md` — "sole graph-shaper"). This is capability wiring, not a claim that only
pauli's judgment could architect a cut — it keeps exactly one agent authoritative for graph
structure so scores and edges never drift from two writers disagreeing.

## Step 0 — Earn-its-keep gate (forced, before any cutting)

Answer these against the epic, in the task body, before touching the DAG:

1. Would cutting this actually change what happens next — does a real, named consumer branch,
   gate, or dispatch differently once it's decomposed — or could a smart agent just execute it as
   one chunk?
2. Is the overhead proportional — does the epic genuinely span distinct responsibility boundaries,
   owners, or evaluator identities, or would decomposition just add process theatre?
3. What does cutting it obligate other surfaces to maintain (subtask tracking, gate nodes,
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

## Step 2 — compose the regime

Select — never invent — process and gate templates from `aops-extras/workflows/INDEX.md`,
proportionate to stakes:

- **Door-type drives gate weight.** Two-way (reversible: drafts, analysis, read-only) → light or
  automated gates. One-way (irreversible: send, publish, prod, spend, delete, merge) → a hard gate:
  a distinct evaluator identity, usually plus human authorisation, before crossing. Assign
  door-type per subtask (or once for the epic where uniform). When reversibility is ambiguous,
  treat it as one-way — a misclassified one-way door is the costliest single error.
- **Consolidate once.** State the epic's procedural obligations (the composed regime) a single time
  at epic level — don't repeat "runs `/craft`" on every subtask row.
- **Record what was composed, by name.** A reviewer must be able to trace every regime obligation to
  a named template, not folk knowledge — see the record format in `references/regime-composition.md`.
- **Flag gaps, don't freelance.** If the stakes call for an obligation no template covers, name the
  gap in the composed-regime record as a library issue — that's a `library`-owner problem to add,
  not a licence to invent process here.
- **Realise gates as graph structure.** Every review/approval juncture in the regime becomes a
  **blocking subtask node** in the DAG (`GATE: <what it checks>`, owned by an evaluator identity
  distinct from the work it gates, `depends_on` the work it gates) — never a prose bullet a worker
  might skim past.

If the epic already carries a hydrate bundle's `## Standards` section, treat it as the candidate
list to select from and cross-check against the INDEX — don't re-derive obligations from scratch;
hydrate already surfaced them, you sequence and compose.

## Step 3 — persist and stop

Write, in the task body (via the pauli PKB surface — `mcp__pkb__decompose_task` for the subtask
nodes, `mcp__pkb__append` for the record): the earn-its-keep record, the cut rationale, the DAG
table (id, subtask, one-line scope, door-type, `depends_on` — nothing more), the composed regime by
name, and the consolidated epic-level obligations. Worked specimen for the reasoning shape (not a
script to copy): [[aops_d6ae35af]] §Pass-1 decomposition.

## Must not

- Write full delegation briefs for any subtask — Layer 2, [[skills-brief]]'s job, at dispatch time.
- Explode or detail subtasks not due next — rolling-wave discipline, not an exhaustive tree.
- Invent process outside the library without flagging the gap.
- Add review/approval obligations as prose the reader might skim — they must be blocking DAG nodes.

## Fitness test (self-check before you stop)

From this record alone, could a reviewer state: (a) why decomposition was warranted (the earn-its-
keep answer), (b) the composed regime **by template name**, and (c) confirm every DAG node is
session-sized and **owner-assignable** — a single accountable owner evident from its one-line scope
(owner is assigned at dispatch, not pinned here) — with total prose kept small? If any of those
needs re-deriving from context the reviewer doesn't have, the pass isn't done.
