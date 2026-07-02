---
id: premise-gate
title: The Premise Gate — the first executive surface for judgment-non-delegable
type: spec
status: ready
tier: core
permalink: premise-gate-spec
depends_on: []
tags: [enforcement, premise-gate, judgment-non-delegable, framework-architecture]
---

<!-- NS: was this retired? -->

# The Premise Gate — the first executive surface for `judgment-non-delegable`

> **Spec, not state.** This file is the **design statement** for the premise gate: what it is, which axiom it enforces, where it sits in the pipeline and the pyramid, and how far it binds. The step-by-step **procedure** an agent runs — what the promoter records, what the dispatcher does — lives in the operative instruction file it ships beside: [`aops-core/skills/remember/references/premise-gate.md`](../../aops-core/skills/remember/references/premise-gate.md). This spec points at that file for the procedure and does not restate it. The **operative register** row is in [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md).

## What the gate is

The premise gate is a **source-level agent-judgment gate** that kills the whole class of dumb ideas at the universal chokepoint — task promotion into the dispatchable set (`→ queued`) — **before any compute is spent building good code for a bad idea**. Every piece of coordinated work passes through `→ queued` before a worker is dispatched, so that crossing is where the _premise_ ("is this worth doing, is the shape right?") is judged once, cheaply, at the source, rather than discovered expensively at review after the build.

The gate has two halves, one at each end of the spend path:

- **Promotion side** (the premise in the task body): a one-sentence, principal-voice judgment of the premise. An agent promoter records it directly; because `→ queued` is a **manual human transition with no hook**, a hand-queued task often leaves none, so the dispatcher makes it legible at the spend side before judging (this is why enforcement attaches at dispatch, not at promotion).
- **Spend side** (`/pull`, `/dispatch`, and the dispatch step of `/supervisor`): the last moment before compute is spent — the dispatcher ensures the premise is legible, then **clears it through two independent judges** (`rbg` for axiom/rig compliance, `pauli` for worth and shape) via `/strategic-review --premise`. Any BOUNCE **hard-refuses the dispatch**. This is the same two judges the full review deploys, scoped to a task and a binary verdict — one judgment, reused, not a bespoke gate (DRY with [[../../aops-core/skills/strategic-review/SKILL.md]]).

## The axiom it enforces — judgment, not mechanism

The premise gate is the **first executive surface for the axiom [`judgment-non-delegable`](../../.agents/rules/AXIOMS.md#judgment-non-delegable)**. Before it, that axiom was legislative-only — declared in `AXIOMS.md`, reviewed by `rbg`, but with no runtime surface that _acted_ on it at the moment a bad idea entered the pipeline. The gate is that surface.

It is itself **judgment, not a mechanism**. Two agents read the task and decide; there is no regex, no field check, no classifier, no threshold, and no checklist anywhere in it. This is not an accident of implementation — it is forbidden by construction. Building a deterministic rig to police _"is this a dumb idea?"_ would be the exact disease the gate exists to stop: a mechanical stand-in for a qualitative call. A rig that decided which task bodies "count" as having a premise would itself be delegating the comprehension call to a matcher, violating `judgment-non-delegable` in the very act of enforcing it. So the enforcement mode is a **two-judge agent read-and-decide** (`rbg` + `pauli`), never a hook, field, or presence-check — deploying the judgment to two named agents is delegating the WORK to judging agents, which the axiom explicitly blesses; it is only delegation to a _mechanism_ that it forbids.

## Enforcement footprint

`premise-gate` is a mechanism enforcing one axiom (`judgment-non-delegable`) across two pipeline positions. Modelled on the `exercise-authority` worked example in [`enforcement.md`](enforcement.md) §4.2, its footprint:

| Position                                             | Surface                                            | What it does                                                                                                                                                             |
| :--------------------------------------------------- | :------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pipeline **L2** (decomposition) / Pyramid **middle** | Promoter (`/planner`), or the dispatcher at step 1 | The premise sentence in the task body — recorded by an agent promoter, or made legible by the dispatcher when a hand-queued task left none. Agent judgment, not a field. |
| Pipeline **L4** (pre-execution) / Pyramid **middle** | `/pull`, `/dispatch`, `/supervisor` dispatch step  | Clears the task through `rbg` + `pauli` via `/strategic-review --premise`. Both CLEAR → dispatch. Any BOUNCE → **hard-refuse** (block) and bounce to the promoter.       |

Both positions are an **agent judgment, not a hook**. The spend-side refusal is a **hard block** (it blocks the dispatch and stops the spend), delivered as the two judges' CLEAR/BOUNCE verdict — there is no PreToolUse hook, no gate config, no env var behind it. It is a triggered gate that hard-refuses, which places it in the **middle tier** of the pyramid (triggered by the event of a queued task reaching a spend surface; invasive — it blocks — only when a premise fails to clear), not the base and not the tip.

## Honest scope

The gate binds **only the coordinated spend path** — everything that flows through `/pull`, `/dispatch`, or `/supervisor` (single-epic or portfolio). That is the bulk of agent compute-spend and all polecat dispatch, and it is repo-agnostic (any project that dispatches through these surfaces).

It is **not universal.** A human who opens an editor and hand-codes, or fires a worker by hand, never touches `queued`, and this gate cannot see them. Do not claim it catches direct hand-coded PRs — it does not.

The **backstop** for premises that bypass the source gate is the **review-time twin**, [`premise-test.md`](../../aops-core/skills/strategic-review/references/premise-test.md): a forced step-0 judgment in `/verify` and `/strategic-review` arch-fit that catches a bad premise from the task + diffstat regardless of test coverage, plus `/learn` recurrence scoring that attributes a slipped-through premise to the approving reviewer. Every PR hits review no matter how it was created, so the pair — source gate + review twin — is surface-agnostic; **this source gate alone is not.** Do not overclaim it.

## Relationships

- **Operative procedure:** [`aops-core/skills/remember/references/premise-gate.md`](../../aops-core/skills/remember/references/premise-gate.md) — what the promoter records and what the dispatcher does, step by step. This spec is the design statement; that file is the procedure. Neither restates the other.
- **Review-time twin:** [`premise-test.md`](../../aops-core/skills/strategic-review/references/premise-test.md) — the review-surface counterpart enforcing the same axiom; the backstop half of the pair.
- **Axiom:** [`judgment-non-delegable`](../../.agents/rules/AXIOMS.md#judgment-non-delegable) — the rule this gate is the first executive surface for.
- **Operative register:** [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) — the `judgment-non-delegable` × `premise gate` row (mechanism, trigger, level, mode).
- **Pyramid / pipeline design:** [`enforcement.md`](enforcement.md) — §4.0 tier table (middle tier) and the §3 pipeline narrative (L2 promotion + L4 spend-surface refusal).
