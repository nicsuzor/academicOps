---
alias:
  - wf-strategic-fit
  - wf-fit-check
description: Universal strategic-direction and congruence review -- evaluate candidate artifact, change, or proposal for core premise soundness, strategic direction, and congruence with the seamless web of existing knowledge-base material (specifications, notes, prior art, parent objectives, parsimony, and lifecycle coherence), returning PASS, REVISE, or FAIL.
id: wf-strategic-fit
tags:
  - wf-template
  - review
  - strategic-fit
  - strategy
  - congruence
title: Strategic Direction and Congruence Review
type: template
---

## What this step does

Universal strategic-direction and congruence review: a strategic coherence reviewer evaluates core premise soundness, strategic direction, and congruence with the **seamless web** of existing knowledge-base material (graph topology, prior art, specifications, topic notes, parent objectives, parsimony, and lifecycle coherence).

## Input contract

Draws its brief from the shared review briefing (supplied inline for graph-level evaluation) plus graph context: parent objectives, active tasks, competing proposals or PRs, existing specifications, and relevant topic notes.

## Procedure

1. **Question the core premise and direction** -- verify the right problem is addressed, name the problem class, trace causal chains, separate fatal premise flaws from fixable gaps, and flag unrequested scope drift, principal-agent inversion in user stories (casting an agent as the user rather than stating the human user requirement), flawed reasoning, untested load-bearing assumptions, missing edge cases, and negative space.
2. **Maintain the seamless web (congruence with prior art)** -- check alignment with existing specifications, architectural decisions, topic notes, and active sibling tasks; surface silent contradictions, unacknowledged departures, or duplicated structures:
   - **Doc claims vs completed task evidence**: A note stating a behavior exists proves only what the note says, not current live state. Require a completed task record (`status: done` with verification evidence) before treating a mechanism or problem as settled/obsolete; otherwise record an **open question**.
   - **Authority of cited PRs or code**: Verify cited PRs or snippets are merged/current and backed by an authoritative specification or decision record before treating them as settled design.
3. **Check parsimony and lifecycle coherence** -- test whether existing tools, native capabilities, or competing proposals already meet the need more simply, and verify task dependencies do not deadlock downstream workflows.
4. **Respect boundaries & issue verdict** -- judge strictly on core premise, strategic coherence, and graph congruence (leaving axiom compliance and runtime requirement verification to their respective review roles), returning one explicit verdict (`PASS`, `REVISE`, or `FAIL`).

## Output contract

Structured Markdown review (never programmatic JSON/YAML) containing:

- **Verdict**: `PASS`, `REVISE`, or `FAIL`.
- **Strategic direction & congruence assessment**: evaluation of premise soundness, alignment with the seamless web of specifications, notes, and prior art, authority of cited changes, parsimony, and lifecycle coherence.
- **Identified conflicts, missing elements, and open questions**: flawed reasoning, untested assumptions, negative space, contradictions, unnecessary abstractions, lifecycle deadlocks, or unverified current-state questions.

## When to include

Any workflow proposing an architecture, specification, design change, plan, or feature addition before detailed implementation or final sign-off.
