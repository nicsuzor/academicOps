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
4. **Approval** -- where research addresses an open design question or architectural alternatives, a dedicated decision task assigned to the user (`assignee: user`) is queued by default (`Title: Decide implementation route for <topic>`, `depends_on: [<research_task_id>]`), wherein the user selects the implementation route. The full spec is filed on the record; implementation work remains strictly blocked until the user records the decision.
5. **Implementation** -- in a separate task that `depends_on` the decision task (and approved spec), so implementation cannot start until the user selects the route. Implementation of the approved spec, test-first for code that executes, an independent check against its acceptance criteria, and a sign-off summary.

## Composition

Multi-stage research-and-implementation workflows are structured per the follow-up placement invariant: either as a single task with internal subtasks (if all stages execute in one continuous session) or as a dedicated epic with child tasks (e.g. Child 1: Research and Spec, Child 2: Decision Gate assigned to the user, Child 3: Implementation, with child-to-child `needs` edges), never as loose siblings under an external parent. Cut the chain at stage 4: Stage 5 (Implementation) is strictly blocked until the decision is recorded. Requested revisions return to stage 2.

## Output contract

- Research findings with citations.
- The full specification.
- Review verdicts on both.
- The spec filed for approval, with approval structured so implementation is strictly blocked until the decision is recorded.

## When to include

Any ask to research, design, and then build something ("research, design, and implement…") where the design should be agreed before engineering effort is committed.
