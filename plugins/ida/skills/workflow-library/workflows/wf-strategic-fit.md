---
alias:
  - wf-strategic-fit
  - wf-fit-check
description: Universal strategic-direction and congruence review -- evaluate candidate artifact, change, or proposal for core premise soundness, strategic direction, and congruence with the seamless web of existing PKB material (specifications, notes, prior art, parent objectives, parsimony, and lifecycle coherence), returning an explicit PASS, REVISE, or FAIL verdict.
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

Universal strategic-direction and congruence review (`pauli`): evaluates the core premise, strategic direction, and congruence with the "seamless web" of existing material in the Personal Knowledge Base (PKB graph topology, prior art, existing specifications, topic notes, parent objectives, parsimony, and lifecycle coherence).

## Input contract

Draws its brief from the shared review briefing (supplied inline so the reviewer operates strictly on the PKB graph). Additional role-specific inputs:

- **Graph context** -- parent objectives, active tasks, competing proposals or PRs, existing specifications, and relevant topic notes.

## Procedure

1. **Question the core premise and strategic direction** -- ask whether the right question is being answered before evaluating the answer. Name the class of problem rather than just the instance, trace causal chains, distinguish what cannot be known in advance from what is merely unexamined, and separate fatal premise flaws from fixable gaps. Verify whether the artifact serves the claimed parent target and strategic direction in the PKB graph, flagging unrequested scope drift, flawed reasoning (non-sequiturs, circular logic), untested load-bearing assumptions, overconfident claims, missing edge cases, and negative space (what should be here that isn't).
2. **Maintain the seamless web (congruence with existing material and prior art)** -- evaluate alignment with existing specifications, architectural decisions, topic notes, active sibling tasks under the parent epic, and Maps of Content in the PKB; surface silent contradictions, unacknowledged departures from settled design, or duplicated structures:
   - **Documentation notes vs completed task evidence**: A PKB note stating that a behaviour exists proves only what the note says, not current working state. Before concluding that a problem or mechanism is obsolete, require a completed PKB task record (`status: done` with verification evidence); if it cannot be established definitively on the graph, report it as an **open question** rather than settled fact.
   - **Authority of cited PRs or code**: Never treat a random reference to a PR or code snippet as authoritative on its own. Verify whether the change is merged/most recent, reflects current working behaviour, and is supported by an authoritative specification or decision record.
3. **Parsimony, necessity, and lifecycle coherence** -- determine whether the mechanism should exist at all, or whether an existing tool, native capability, or competing proposal already solves the need more simply, and verify that task lifecycle dependencies do not deadlock downstream workflows.
4. **Determine boundaries** -- operates strictly on the core premise, strategic direction, congruence with existing PKB material, and lifecycle coherence. Does not inspect code for axiom violations (the compliance role, `rbg`) and does not test whether the delivered implementation satisfies functional requirements at runtime (the quality role, `marsha`).
5. **Issue verdict**: return an explicit `PASS`, `REVISE`, or `FAIL` verdict with specific, actionable guidance calibrated to the stakes.

## Output contract

The structured review artifact (composed in standard Markdown sections for human readability, never programmatic JSON/YAML payloads) returning:

- **Verdict**: `PASS`, `REVISE`, or `FAIL`.
- **Strategic direction & congruence assessment**: evaluation of core premise soundness, strategic alignment, congruence with the seamless web of existing specifications/notes/prior art, authority of cited changes, parsimony, and systemic coherence.
- **Identified conflicts, missing elements, and open questions**: flawed reasoning, untested assumptions, negative space, contradictions with existing PKB material, competing proposals, unnecessary abstractions, lifecycle deadlocks, or unverified current-state questions (if any).

## When to include

Any workflow proposing an architecture, specification, design change, plan, or feature addition before detailed implementation or final sign-off.
