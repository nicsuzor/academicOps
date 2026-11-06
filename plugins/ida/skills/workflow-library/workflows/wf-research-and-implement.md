---
alias:
  - wf-research-and-implement
  - wf-research-implement
description: "Composite for research-then-build asks: research, spec, independent agent review of both, agent route decision on open research alternatives, then implementation and single-PR delivery in a dependent task."
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

Sequences an ask that needs investigation and a reviewed design before anything is built. The composer fills each stage with whatever component meets its contract.

## One PR, opened by the build

- Stage 1 records its design, any drafted spec change, and its independent agent review verdicts in a PKB note the Stage 2 task points to. Stage 1 commits no plan or design file and opens no PR.
- Stage 2 opens the PR into the base branch as a draft, carrying the build and any spec change. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review (`gh pr ready`) only after the proportionate review on the build is posted to the PR thread by independent agents. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Stages

1. **Research** -- grounded findings on the problem space and the candidate approaches, with primary citations and a recommended direction, recorded on the PKB.
2. **Spec** -- a complete specification built on those findings: design, interfaces, and falsifiable acceptance criteria mapped to tests, or runs for instruction text. Recorded on the PKB as a drafted spec change in a note the implementation task points to; commits no plan or design file and opens no PR.
3. **Review** -- an independent verdict on the research and on the spec from reviewing agents that did not author them, covering factual claims, rule compliance, and proportionality. A review by independent agents is required and a proportionate review is selected. Recorded on the PKB task or note, never releasing as `review` and never putting a spec to the user for approval on its own. Resolve defects before advancing.
4. **Route Decision (when competing research alternatives exist)** -- where research addresses an open design question or competing architectural alternatives, the agent does the groundwork and decides the route itself (selecting the recommended option and recording why); it never files the task back to the user as their decision (`assignee: user`) unless the user explicitly asked to decide it themselves (tg 1013). Specifications advance directly to implementation once the route is selected and independent agent review passes.
5. **Implementation** -- in a separate task that `depends_on` the research/spec task (and any route decision task). Opens the PR into the base branch as a draft carrying the build and the spec change, keeping the spec editable as more is learned. Implementation of the spec, test-first for code that executes, marks the PR ready for review (`gh pr ready`) once the feature is written and proportionate review by independent agents is posted to the PR thread without waiting for approval. Spec and feature reach the user on that single PR and merge together after full review.

## Composition

Multi-stage research-and-implementation workflows are structured per the follow-up placement invariant: either as a single task with internal subtasks (if all stages execute in one continuous session) or as a dedicated epic with child tasks (e.g. Child 1: Research and Spec with independent agent review and route decision, Child 2: Implementation, with child-to-child `needs` edges), never as loose siblings under an external parent. Research and spec stages record their findings, drafted spec changes, and independent agent review verdicts on the PKB, committing no plan or design file and opening no PR; implementation opens the draft PR carrying the build and spec change onto the base branch, keeping the spec editable, and marks the PR ready for review once the feature is written and proportionate review by independent agents is posted to the PR thread, without waiting for approval. Spec and feature merge together after full review. Requested revisions return to stage 2.

## Output contract

- Research findings with citations recorded on the PKB.
- The full specification drafted and recorded on the PKB in a note the implementation task points to, with no PR opened before the build.
- Independent agent review verdicts on both, recorded on the PKB task or note.
- Where competing research alternatives exist, the selected implementation route and trade-off rationale recorded, unblocking implementation.
- Implementation committed on the feature branch with a single PR opened into the base branch carrying the build and spec change, marked ready for review after proportionate review by independent agents is posted to the PR thread, merging spec and feature together after full review.

## When to include

Any ask to research, design, and then build something ("research, design, and implement…") where the design should be agreed before engineering effort is committed.
