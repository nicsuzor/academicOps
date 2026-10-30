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
2. **Spec** -- a complete specification built on those findings: design, interfaces, and falsifiable acceptance criteria mapped to tests, or runs for instruction text.
3. **Review** -- an independent verdict on the research and on the spec, from an evaluator who did not author them, covering factual claims, rule compliance, and proportionality. Resolve defects before advancing.
4. **Approval** -- the full spec, not a summary, filed on the record for an explicit decision. If the spec is delivered on a draft pull request requiring user approval, verify that the independent review verdict from stage 3 is posted on the pull request thread before human approval is requested. The spec task is not released as `done` while an approval decision is pending; it is structured per the review rules (e.g. released as `partial` with a queued review task that the spec task `depends_on`, or as an explicit decision task that implementation depends on) so dependent implementation work remains strictly blocked until approval is recorded.
5. **Implementation** -- in a separate task that `depends_on` the approved spec (or the approval decision task), so it cannot start until the spec is approved. Implementation of the approved spec, test-first for code that executes, an independent check against its acceptance criteria, and a sign-off summary.

## Composition

Cut the chain at stage 4: stages 1–4 form the spec task and stage 5 the implementation task (or stage 4 forms an explicit decision task). Implementation is strictly blocked until approval is recorded on the record. Requested revisions return to stage 2.

## Output contract

- Research findings with citations.
- The full specification.
- Review verdicts on both.
- The spec filed for approval, with approval structured so implementation is strictly blocked until the decision is recorded.

## When to include

Any ask to research, design, and then build something ("research, design, and implement…") where the design should be agreed before engineering effort is committed.
