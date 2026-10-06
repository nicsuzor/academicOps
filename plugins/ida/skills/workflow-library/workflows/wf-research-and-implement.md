---
alias:
  - wf-research-and-implement
  - wf-research-implement
description: "Composite for research-then-build asks: research, spec, independent review of both, escalated approval of the full spec, then implementation in a dependent task."
id: wf-research-and-implement
tags:
  - wf-template
  - composite
  - research
  - spec
  - implementation
title: wf-research-and-implement
type: template
---

## What this step does

Sequences an ask that needs investigation and an agreed design before anything is built. The composer fills each stage with whatever component meets its contract.

## Stages

1. **Research** -- grounded findings on the problem space and the candidate approaches, with primary citations and a recommended direction.
2. **Spec** -- a complete specification built on those findings: design, interfaces, and falsifiable acceptance criteria mapped to tests.
3. **Review** -- an independent verdict on the research and on the spec, from an evaluator who did not author them, covering both the factual claims and the fitness of the design. Resolve defects before advancing.
4. **Approval** -- the full spec, not a summary, handed to the human who commissioned the work for an explicit decision. The task ends here in `review`.
5. **Implementation** -- in a separate task that `depends_on` the approval task, so it cannot start until the spec is approved. Test-first implementation of the approved spec, an independent check against its acceptance criteria, and a sign-off summary for the human.

## Composition

Cut the chain at stage 4: stages 1–4 form one task and stage 5 another. Requested revisions return to stage 2.

## Output contract

- Research findings with citations.
- The full specification.
- Review verdicts on both.
- The spec filed for approval, with the approval task released as `review`.

## When to include

Any ask to research, design, and then build something ("research, design, and implement…") where the design should be agreed before engineering effort is committed.
