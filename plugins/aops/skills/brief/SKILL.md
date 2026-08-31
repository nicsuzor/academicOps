---
name: brief
description: Prepares tasks for dispatch -- composes workflows, sets acceptance criteria, sets task to 'queued'. Never dispatches, never executes.
---

# Brief: Prepare a task for dispatch

Turn an ask into a task a cold executor can act on and be judged against. You verify its premises, compose its process, record review obligations on the body, write the brief, and set the exit status (§6). You never dispatch, never start the work, and never touch its substance.

**A brief transfers only what the dispatcher has and the executor lacks.** You monopolize intent and strategic context; the executor monopolizes method. Everything the executor can fetch, derive, or decide better itself stays out of the brief.

Brief exactly the ask you were called on — the cohesive unit of intent or epic. Do not conflate "one ask" with a single isolated line item: related tasks serving one atomic deliverable or epic are composed and briefed together as one unit, not fragmented into uncoordinated mini-briefs. Do not pre-write briefs for downstream work behind this one. The return contract attaches to the claimed task — one deliverable, with evidence and an output URL — including any completed child tasks.

PKB MCP tools may live under the **`services`** MCP server using the `pkb__` tool name prefix (e.g. `pkb__search`, `pkb__get_task`, `pkb__create_task`). 

## 1 — Read, then verify

Front-load reconnaissance: run a parallel read-only fan-out across the codebase, PKB, git history, and runtime environments before making decisions or decomposing. Verify all world-claims (paths, schemas, deployed states, negative capability claims) concurrently against reality, not another node.

If the prompt comes in without an existing task id, run `/q` first so the node can be placed appropriately on the graph. Given an id, `pkb__get_task` the unit and its parent. Given prose, search first (`pkb__search`, `pkb__task_search`). Where existing unparented, misparented, or pre-existing tasks already cover part of the work, adopt them under the parent using `pkb__batch_reparent(ids=[...], new_parent="<parent-id>", dry_run=False)` rather than creating duplicate siblings. Merge into any node that already covers the ask, or `pkb__create_task` it at `inbox` under the right parent. Never leave a duplicate sibling.

The record is a claim, not a fact. Claims about intent do not decay; claims about the world — paths, schemas, deployed states, every negative claim — decay silently. Re-verify each world-claim the brief will lean on **against the world, not another node**, before it becomes a constraint, criterion, or pointer. If a load-bearing premise is dead, the unit is not briefable: record what is no longer true, leave it at `inbox`, and stop.

Name the standard the unit will be judged against and where it lives. Record any requirement it reaches that the unit does not cover as a named gap — never absorb it silently or soften a criterion to fit.

## 2 — Route the unknowns

- **DECIDE** — a clear best option exists: make the call, one bullet under `## Assumptions / Decisions`.
- **DEFER** — the missing input is runtime data: say what is missing. Where an investigation would settle it, mint the **probe** — a `classification: spike` task that yields the deciding information most cheaply — and wire the blocked unit `depends_on` it.
- **SURFACE** — a genuine trade-off, wide blast radius, or the user's own intent: one bullet under `## Assumptions / Decisions` giving the options, their costs, and your recommendation.

Agents must NOT originate `priority` bands (0-4); priority bands are user-only. Express strategic importance via `contributes_to` with `stated_weight` (`critical`, `high`, `medium`, `low`), never `priority`.

A decision the work depends on that you cannot settle is a halt: name it and stop. Use `AskUserQuestion` only when it blocks finishing at all.

## 3 — Cut only at forks and boundaries

Default: no cut. The dispatchable unit is the largest chunk containing no unresolved fork. Cut only where (1) an unresolved fork sits inside the chunk, or (2) the chunk spans a responsibility boundary — a different owner, authority, or evaluator identity. Never cut on size or feel.

When minting child nodes (`pkb__create_task`), mint slugged, human-readable IDs upfront (`id: "aops_<slug>"`, etc.) rather than leaving `id` empty for auto-generation. Note that `pkb__create_task` accepts only `status: "inbox"` or `"ready"`; transitioning child tasks to `queued` requires a two-step write via `pkb__update_task(id=..., updates={"status": "queued"})`.

All related tasks and child units under an epic must ship together on a single shared feature branch (`task/<epic-slug>`) and a single PR against the integration target branch (e.g. `v0.9.1`), never scattered across multiple individual PRs.

Every cut carries its own owner and return contract: DONE + deliverable + evidence, BLOCKED + what is missing, NEEDS-REDISPATCH + what changed, or partial + handback. A cut that cannot support that contract is cut wrong — re-cut. `depends_on` only where one unit's start genuinely needs another's output; everything else runs parallel. Subtasks are the owner's internal sequencing, never a cut.

## 4 — Compose the process

Discover templates in three tiers; resolution order **project ≻ PKB ≻ universal** (matching is case-insensitive and ignores `wf-`/`_`/`-`; the winner shadows whole, never merge tiers):

1. **Project** — `$CWD/.agents/templates/*.md`; absent directory means empty list.
2. **PKB** — `pkb__list_documents(type="template")`, excluding retired, instance, and other-project nodes.
3. **Universal** — `plugins/aops/workflows/*.md` catalogued by `plugins/aops/workflows/INDEX.md` (legacy templates archived in `plugins/aops/workflows/archive/`); minimum standards, non-derogable.

Read every template you compose — a catalogue row is not the template. A template you need that no tier holds is a library gap: name it and halt; never freelance a process. Weight the process proportional to real consequence — heavier is theatre, lighter is unmitigated risk.

Sort each obligation by who discharges it: executor-internal steps go on the task checklist; review obligations become Acceptance Criteria on the task body. Never emit speculative review or sign-off graph nodes during planning — acceptance gates live in the brief's criteria and the PR merge boundary.

## 5 — Write the brief

Rewrite the brief prose to exactly this shape, deleting event logs, prior drafts, and inconsistent directions. Frontmatter, edges, and intake-stage strategic valuation are preserved, not part of the rewrite:

```markdown
## Goal — the outcome, 1–2 sentences, never the activity. Test: could a reviewer judge from this alone whether the result is the right kind of thing?

## Context — the user's verbatim ask where its wording carries constraints or tolerances; unfetchable facts only, plus exact load-bearing values (an id, path, gate name) where a fetch error would be silent

## Deliverable — one line: the artifact and where it lands (landing surface)

## Scope — what is in; what adjacent thing is out (negative scope: one clause per real collision risk, no rationale)

## Constraints — decisions already taken, phrased as outcomes, each citing its home

## Acceptance criteria — 3–7 observable end-states, each naming an artifact and a condition checkable by a stranger who never watched the work; only work THIS executor will do

## Assumptions / Decisions — §2's calls made and open calls awaiting the user (never repeat a taken decision from Constraints); where non-empty

## Pointers — [[id]] + ≤1 clause saying why to open it ("the method", "precedent — do not redo", "do-not-touch"), never what it says
```

**Budget: 150–400 words; ~500 for a campaign plan. One screen.**

Excluded, always:

- **Method** — no procedure, ordering, batch sizes, or techniques, even good ones. Canonical method binds by reference to its home; a binding rule converts to an AC citing its home, never transcribing its text.
- **Summaries of linked content** — an inline copy is a fork the executor acts on stale. Elevate by reference, never by transcription.
- **Provenance, supersession narrative, session diary** — edges, receipts, and git carry history.
- **Restated doctrine** the executor loads anyway.
- **Perishable facts** — counts, SHAs, dates-as-state, other nodes' statuses. State the threshold; let the executor measure.
- **Meta-commentary** whose subject is the brief itself — one scope line is the whole budget for self-reference.
- **Pre-completed ACs** — the AC list is exactly what this executor is on the hook for; done work lives in edges and receipts.

Deletion test, per sentence: if this line vanished, would the executor act differently, or success be judged differently? If neither, delete it.

AC-vs-method litmus: a line checkable only by watching the executor work is method — delete it or convert it to the end-state it was trying to guarantee.

Your verification notes, composition trace (which tier each template came from and what it shadowed), cut rationale, and proportionality call go in your reply to the caller — never in the task body.

## 6 — Set status and stop

- Every fork settled or carrying a designed probe (§2), dependencies wired, brief on the body → transition to **`queued`** via `pkb__update_task(id=..., updates={"status": "queued"})`.
  _(If the existing task body carried an artifact rot annotation, premise falsification note,
  or KILL triage verdict, you must explicitly clear/resolve that condition in the new brief;
  otherwise the task must remain at `inbox` or be cancelled)._
- A hard dependency genuinely unmet → **`blocked`** (with blocker reason), naming what it waits on.
- Premise dead, ask under-specified, or an unsettleable decision → leave at **`inbox`**, saying what is missing. Do not backfill by guessing.

One pass: you are making the task actionable, not doing it. If briefing it properly would mean doing the work, record that the unit is a spike and stop. Never re-brief unchanged inputs, never emit speculative review nodes, never dispatch, never begin the work. A halt that names its gap is a complete pass. (Prose-only constraints in this skill are unproven-to-bind until backed by schema or hook guards).

## Must not

- Do not write or originate `priority` bands (0-4); use `contributes_to` with `stated_weight`.
- Do not emit speculative review or sign-off graph nodes during planning.
- Do not scatter an epic's related child tasks across multiple PRs; use a single shared feature branch and PR.
- Do not attempt to set `status: "queued"` via `pkb__create_task`; always use `pkb__update_task`.
