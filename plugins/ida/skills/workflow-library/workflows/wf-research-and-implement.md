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

## One PR, opened by the build

- Stage 1 records its design, any drafted spec change, and its review verdict in a PKB note the Stage 2 task points to. Stage 1 commits no plan or design file and opens no PR.
- Stage 2 opens the PR into the base branch as a draft, carrying the build and any spec change. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review (`gh pr ready`) only after the proportionate review on the build is posted to the PR thread. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Stages

1. **Research** -- grounded findings on the problem space and the candidate approaches, with primary citations and a recommended direction, recorded on the PKB.
2. **Spec** -- a complete specification built on those findings: design, interfaces, and falsifiable acceptance criteria mapped to tests, or runs for instruction text. Recorded on the PKB as a drafted spec change in a note the implementation task points to; commits no plan or design file and opens no PR.
3. **Review** -- an independent verdict on the research and on the spec, from an evaluator who did not author them, covering factual claims, rule compliance, and proportionality. A review is required and a proportionate review is selected. Recorded on the PKB task or note. Resolve defects before advancing.
4. **Approval** -- where research addresses an open design question or architectural alternatives, a dedicated decision task assigned to the user (`assignee: user`) is queued by default (`Title: Decide implementation route for <topic>`, `depends_on: [<research_task_id>]`), wherein the user selects the implementation route. The full spec is filed on the record; implementation work remains strictly blocked until the user records the decision.
5. **Implementation** -- in a separate task that `depends_on` the decision task (and approved spec), so implementation cannot start until the user selects the route. Opens the PR into the base branch as a draft carrying the build and the spec change, keeping the spec editable as more is learned. Implementation of the approved spec, test-first for code that executes, marks the PR ready for review (`gh pr ready`) once the feature is written and proportionate review is posted to the PR thread without waiting for approval, an independent check against its acceptance criteria, and a sign-off summary. Spec and feature merge together after full review.

## Composition

Multi-stage research-and-implementation workflows are structured per the follow-up placement invariant: either as a single task with internal subtasks (if all stages execute in one continuous session) or as a dedicated epic with child tasks (e.g. Child 1: Research and Spec, Child 2: Decision Gate assigned to the user, Child 3: Implementation, with child-to-child `needs` edges), never as loose siblings under an external parent. Cut the chain at stage 4: research and spec stages record their findings, drafted spec changes, and review verdicts on the PKB, committing no plan or design file and opening no PR; implementation opens the draft PR carrying the build and spec change onto the base branch, keeping the spec editable, and marks the PR ready for review once the feature is written and proportionate review is posted to the PR thread, without waiting for approval. Implementation is strictly blocked until approval is recorded on the record. Spec and feature merge together after full review. Requested revisions return to stage 2.

## Output contract

- Research findings with citations recorded on the PKB.
- The full specification drafted and recorded on the PKB in a note the implementation task points to.
- Review verdicts on both, recorded on the PKB task or note.
- The spec filed for approval on the record, with approval structured so implementation is strictly blocked until the decision is recorded.
- Implementation committed on the feature branch with the PR opened into the base branch carrying the build and spec change, marked ready for review after proportionate review, merging spec and feature together after full review.

## When to include

Any ask to research, design, and then build something ("research, design, and implement…") where the design should be agreed before engineering effort is committed.
