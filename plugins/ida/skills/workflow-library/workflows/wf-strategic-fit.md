---
alias:
  - wf-strategic-fit
  - wf-fit-check
description: Universal strategic-direction and congruence review gate -- evaluate candidate artifact, change, or proposal against strategic direction and congruence with existing PKB material (specifications, notes, prior art, parent objectives, parsimony, and lifecycle coherence), returning an explicit FIT or MISFIT verdict.
id: wf-strategic-fit
tags:
  - wf-template
  - review
  - strategic-fit
  - strategy
  - congruence
  - gate
title: Strategic Direction and Congruence Review
type: template
---

## What this step does

Universal strategic-direction and congruence review gate (`pauli`): evaluates whether a candidate artifact aligns with strategic direction and exhibits congruence with existing material in the Personal Knowledge Base (PKB graph topology, prior art, existing specifications, topic notes, parent objectives, parsimony, and lifecycle coherence).

## Input contract

Draws its brief from the shared review briefing (supplied inline so the reviewer operates strictly on the PKB graph). Additional role-specific inputs:

- **Graph context** -- parent objectives, active tasks, competing proposals or PRs, existing specifications, and relevant topic notes.

## Procedure

1. **Strategic direction and objective alignment** -- verify whether the artifact serves the claimed parent target and strategic direction in the PKB graph, identifying any unrequested scope drift or mission creep.
2. **Congruence with existing material and prior art** -- evaluate alignment with existing specifications, architectural decisions, topic notes, and Maps of Content in the PKB; surface silent contradictions, unacknowledged departures from settled design, or duplicated structures.
3. **Parsimony and necessity** -- determine whether the mechanism should exist at all, or whether an existing tool, native capability, or competing proposal already solves the need more simply.
4. **Lifecycle and graph coherence** -- evaluate consistency with established graph topology and verify that task lifecycle dependencies do not deadlock downstream workflows.
5. **Determine boundaries** -- operates strictly on strategic direction, congruence with existing PKB material, and lifecycle coherence. Does not inspect code for axiom violations (the compliance role, `rbg`) and does not test satisfaction of detailed functional requirements or execute runtime test suites (the quality role, `marsha`).
6. **Issue verdict**: exactly one of `FIT` or `MISFIT`. A `MISFIT` identifies the strategic misalignment, contradiction with existing material, redundant machinery, or lifecycle conflict.
7. **Schedule the next step on a failing verdict** -- a review that returns `MISFIT` (the strategic-congruence failing verdict corresponding to `REJECT` or `REVISE`) schedules the next step in the same handback: the reviewer files a subtask of the primary task (`parent: <primary-task-id>`, status `queued`) whose body names each required change from the verdict, and records that subtask's id on the review task.

### Handback on a failing verdict

A review that returns `MISFIT` (the strategic-congruence failing verdict corresponding to `REJECT` or `REVISE`) schedules the next step in the same handback: the reviewer files a subtask of the primary task (`parent: <primary-task-id>`, status `queued`) whose body names each required change from the verdict, and records that subtask's id on the review task.

## Output contract

The structured review artifact returning:

- **Verdict**: `FIT` or `MISFIT`.
- **Strategic direction & congruence assessment**: evaluation of strategic alignment, congruence with existing specifications/notes/prior art, parsimony, and systemic coherence.
- **Identified conflicts**: contradictions with existing PKB material, competing proposals, unnecessary abstractions, or lifecycle deadlocks (if any), and on a `MISFIT` verdict, the queued subtask scheduled under the primary task recorded on the review task.

## When to include

Any workflow proposing an architecture, specification, design change, plan, or feature addition before detailed implementation or final sign-off.
