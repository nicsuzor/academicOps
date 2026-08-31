---
alias:
- wf-decompose-wf-decompose
- wf-decompose
created: 2026-07-11T12:44:09.096269133+00:00
id: wf_1aa15796
last_modified: 2026-08-29T00:47:51.819956804+00:00
modified: 2026-08-29T00:47:51.819954489+00:00
permalink: wf-decompose
tags:
- wf-template
- v0.4
- module-f
- prose-lens
title: wf-decompose
type: template
---

## What this step does

Breaks a goal into actionable work under genuine uncertainty — the decomposition step the planner runs before wiring up the rest of a composed workflow. Covers both general decomposition and the research-specific specialization (research fails differently than software: wrong question / unexamined assumptions / scope collapse / methodology mismatch, not wrong architecture / missing requirements).

## Routing signals

Use for: multi-step/multi-month projects, "what does X actually require?", a vague deliverable with unclear dependencies, a path forward that is genuinely unknown. Do not use for: known tasks with clear steps (skip straight to execution), or a pure information request (no decomposition needed, just answer it).

## Procedure

1. **Articulate the goal clearly.**
2. **Surface assumptions** — what must be true for this to work? Every load-bearing assumption gets a confidence level, a cheap validation path, and a contingency (what changes if it's wrong).
3. **Find the cheapest probe** for each unknown before committing further — investigate before you build. A hypothesis ("X causes Y" / "file F contains Z" / "regression since commit C") pairs with the cheapest test that confirms or refutes it; don't read the whole codebase to check one hypothesis.
4. **Create coarse components** — don't over-decompose prematurely; expanding everything at once is an anti-pattern.
5. **Ensure at least one task is actionable now.**
6. **Sequence by dependency type.** Ask: "what happens if the dependency never completes?" Impossible or wrong output → hard `depends_on`. Still valid but less informed → soft dependency; when an upstream soft dependency resolves, propagate its findings to affected downstream tasks (the downstream task isn't blocked, but should be revisited).
7. **Route by kind of work**: mechanical (create/implement/fix/refactor) → executor assignee; judgment-call (review/evaluate/decide) → unassigned backlog for a human/reviewing agent, never auto-assigned to an executor.

## Research specialization

When the domain is research, use these primitives instead of generic task types (no schema changes — they're semantic labels): **spike** (resolve an unknown before planning further), **lit-review**, **methodology**, **ethics** (hard gate before data-collection — non-negotiable, often has unpredictable external-approval timelines), **data-collection**, **analysis**, **writing**, **pilot**, **collaboration** (gate on another person's input). Typical sequence: spike → lit-review → methodology → {pilot, ethics} → data-collection → analysis → writing, with lit-review carrying a soft dependency back onto analysis (findings often reshape what "relevant literature" means).

Two research-specific outputs beyond the standard task graph: an **assumptions table** (confidence / validation path / contingency per load-bearing assumption) and a **minimum viable contribution (MVC)** — a narrative paragraph naming the minimum publishable claim and the tasks (`mvc: true`) required to substantiate it. The MVC is a floor, not a ceiling; it exists to prevent scope collapse when ambition expands mid-project.

## Failure modes to decompose against

- **Momentum decay** — a completed task unblocks judgment-required work that nobody picks up. Mitigation: every task that unblocks judgment work needs an explicit follow-up mechanism (supervisor check or soft-dependency surfacing), not an implicit hope someone notices.
- **Convergence failure** — parallel tracks (e.g. three independent investigations) never get synthesised. Mitigation: any decomposition creating parallel tracks MUST include an explicit convergence task depending on all of them, assigned to judgment (human or reviewing agent), not to unsupervised execution.
- **Premature execution** — a task that needs multi-step rigor gets rushed in one pass because the task body didn't specify expected depth. Mitigation: decompose to the level of rigor, not just the level of action (methodology decision → implementation → validation → documentation as separate steps for anything requiring care); acceptance criteria state quality, not just completion.

## Output contract

An assumptions table (confidence/validation/contingency), a dependency-aware task graph (hard vs soft edges), at least one immediately actionable task, and — for research — the MVC paragraph. Anti-patterns to flag in the handback if present: hidden assumptions written as if settled, missing project anchors (`parent`/`project` fields not resolving to a real project file), reflexive task creation without a known action path.

## When to include

- Any task the planner routes through before composing the rest of a workflow — this is typically the _first_ wf-* component wired into a chain.
- **Research seedling mode** (half-formed idea): produces exactly five outputs — an interest statement, an assumption inventory, literature pointers, 1-3 spikes, and a go/no-go prompt — and explicitly does **not** produce a task graph, time estimates, dependency chains, an MVC definition, or Mermaid diagrams. Don't force forest-mode ceremony onto an idea that isn't ready for it.

## Source material (provenance)

Reworked and merged from two retired workflow templates — `decompose.md` (routing signals, spike-vs-placeholder, dependency selection, project-structure checklist, anti-patterns) and `base-investigation.md` (hypothesis/probe/conclude pattern, folded in as the spike mechanism), neither of which is on the tree any more; git holds both — and `specs/workflows/research-decomposition.md` (research primitives, sequencing, seedling/forest modes, MVC, the three failure modes and their decomposition-time mitigations — including seedling mode's exact five-item output and its explicit NOT-list, both reconciled against the source spec 2026-08-29). Part of epic_5e9fc3d5 (SSoT: note_296e5520 D4).
