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

## One branch, one PR

- Stage 1 opens a **draft** PR into the base branch carrying the spec or design, and its review verdict is recorded on that PR. Stage 1 never merges on its own.
- Stage 2 builds on Stage 1's branch and pushes to the same PR. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review once the feature is written. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Stages

1. **Research** -- grounded findings on the problem space and the candidate approaches, with primary citations and a recommended direction.
2. **Spec** -- a complete specification built on those findings: design, interfaces, and falsifiable acceptance criteria mapped to tests, or runs for instruction text. Committed on a feature branch and opened as a **draft** PR (`gh pr create --draft`) targeting the base branch.
3. **Review** -- an independent verdict on the research and on the spec, from an evaluator who did not author them, covering factual claims, rule compliance, and proportionality. Recorded on the draft PR. Resolve defects before advancing.
4. **Approval** -- the full spec, not a summary, filed on the record for an explicit decision. The spec task is not released as `done` while an approval decision is pending; it is structured per the review rules (e.g. released as `partial` with a queued review task that the spec task `depends_on`, or as an explicit decision task that implementation depends on) so dependent implementation work remains strictly blocked until approval is recorded. The draft PR never merges on its own.
5. **Implementation** -- in a separate task that `depends_on` the approved spec (or the approval decision task), so it cannot start until the spec is approved. Built on the spec's branch and pushed to the same PR, keeping the spec editable as more is learned. Implementation of the approved spec, test-first for code that executes, marks the PR ready for review (`gh pr ready`) once the feature is written without waiting for approval, an independent check against its acceptance criteria, and a sign-off summary. Spec and feature merge together after full review.

## Composition

Cut the chain at stage 4: stages 1–4 form the spec task and stage 5 the implementation task (or stage 4 forms an explicit decision task). The spec task opens a draft PR and never merges on its own; implementation builds on Stage 1's branch and PR, keeping the spec editable, and marks the PR ready for review once the feature is written, without waiting for approval. Implementation is strictly blocked until approval is recorded on the record. Spec and feature merge together after full review. Requested revisions return to stage 2.

## Output contract

- Research findings with citations.
- The full specification.
- Review verdicts on both, recorded on the draft PR.
- The spec filed for approval on the draft PR, with approval structured so implementation is strictly blocked until the decision is recorded.
- Implementation committed to the spec's branch and PR, with the PR marked ready for review, merging spec and feature together after full review.

## When to include

Any ask to research, design, and then build something ("research, design, and implement…") where the design should be agreed before engineering effort is committed.
