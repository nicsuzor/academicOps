---
name: premise-gate
title: Premise judgment — where it happens now
type: reference
category: framework
description: Where the framework's premise/worth/shape judgment lives today — at decomposition time, inside the decompose skill's pauli lens, and again at review time — not as a standalone dispatch-time gate.
permalink: premise-gate
tags: [framework, enforcement, premise-gate, agent-judgment, judgment-non-delegable]
---

# Premise judgment — where it happens now

**This is not a standalone gate any more.** An earlier design ran a dedicated two-judge (`rbg` + `pauli`) hard-refuse ceremony at the spend surfaces (`/pull`, `/dispatch`) — a task couldn't be dispatched until both judges cleared its premise. That standalone mechanism is retired. The judgment it performed still happens, but at two points that already exist for other reasons, not a third gate built to hold it:

1. **Pre-hoc, at decomposition.** The `decompose` skill always emits a standing pauli premise task — an early-blocking node in the epic's DAG that the rest of the epic's work depends on clearing — see [`aops/skills/decompose/SKILL.md`](../../decompose/SKILL.md). This task IS the mechanism; the planner emits it into the graph but never dispatches or judges it itself. Dispatch surfaces (`/pull`, `/dispatch`) trust that decomposition and do not re-judge the premise themselves.
2. **Post-hoc, at review.** `/verify` and `/strategic-review` both force a premise read against the finished artifact before any other check — see [`aops/skills/verify/SKILL.md`](../../verify/SKILL.md) (Step 0, "Premise Test") and [`aops/skills/strategic-review/references/premise-test.md`](../../strategic-review/references/premise-test.md). A bad premise fails the review regardless of test coverage or how clean the implementation is.

## What a good premise judgment looks like

Whichever point it runs at, the question is the same: **as a sharp principal seeing only this task, is this worth doing, and is the shape right — or would you bounce it?** Judge it holistically as one open-ended prose reaction — never a checklist, never a form, never a frontmatter field. A form invites mechanical completion; the judgment this exists to protect (`judgment-non-delegable`) requires an actual read.

What a sharp principal notices (priming, not a rubric — do not enumerate these as required boxes):

- Is this worth doing at all, for a real consumer with a real need?
- Is the _shape_ right, or is it over-built for what it does?
- Is a qualitative judgment call being mechanised into a deterministic rig (regex / keyword match / magic threshold / bespoke parser / classifier) when a smart agent reading once would just _decide_?
- Does it duplicate work that already exists, or re-open a settled decision?

**Precondition for any new-mechanism task.** Before judging the premise of a task proposing a new or changed mechanism (gate, env var, context builder, classifier, schema, dispatch path), first establish whether it already exists or was already decided — actually look (PKB search, `rg`/`git`/`gh` against live code and the PR/issue/memory record), don't judge from memory or the task body's own claims. "Adds a second path beside an existing one" and "re-raises a settled decision as novel" are both premise defects.

## Referenced by

- [`specs/enforcement/workflow.md`](../../../../specs/enforcement/workflow.md) — the five-step workflow shape, step 1 (Contract).
- [`specs/enforcement/task-contract.md`](../../../../specs/enforcement/task-contract.md) — the work-unit contract's premise mechanism.
- [`aops/skills/decompose/SKILL.md`](../../decompose/SKILL.md) — pre-hoc lens, where the judgment is recorded.
- [`aops/skills/verify/SKILL.md`](../../verify/SKILL.md) and [`aops/skills/strategic-review/references/premise-test.md`](../../strategic-review/references/premise-test.md) — the post-hoc review-time twin.
