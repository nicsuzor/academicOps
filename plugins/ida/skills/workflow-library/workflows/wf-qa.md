---
alias:
  - wf-qa
description: Universal QA gate -- assemble criteria, critically evaluate live output, effect, or artifact, and return a per-criterion qualitative assessment with evidence.
id: wf-qa
title: Quality Assurance Workflow
type: template
---

## What this step does

Universal QA gate: assemble criteria, evaluate independently, return a per-criterion verdict with evidence.

## Procedure

1. **Assemble criteria** -- record acceptance criteria verbatim from the task specification before inspecting outputs.
2. **Evaluate** -- run a practical, live test or evaluation of the artifact against those criteria. The evaluator must be independent of the artifact's author. An evaluator that changes code or pushes fixes must not approve, accept, or merge its own changes, and must hand off for independent review.
3. **Report per criterion**:
   - **Criterion** -- verbatim from step 1.
   - **Status** -- `MET` or `UNMET`. A criterion that can't be checked is `UNMET` with the reason recorded, never skipped or assumed.
   - **Evidence** -- pinpoint citation: `file:line`, command output, or the visual region a viewer would look at.
4. **PR Risk Tier Action**:
   - For Tier 1 PRs (`triage:auto-mergeable`): when all criteria are `MET` and checks pass, merge the PR autonomously via `gh pr merge --squash` and release the QA task as `done`.
   - For Tier 2 (`triage:needs-judgment`) and Tier 3 (`criticality:critical`) PRs: post the itemized receipt to the PR, leave the PR open for reviewer sign-off, and release the QA task as `done`. Never release to `review` for a human merge gate.

## Output contract

The handback is the itemized report itself -- every criterion accounted for, none silently dropped. A report missing evidence for a `MET` criterion is not a pass.

## When to include

Any artifact that must be judged before it is accepted -- code, prose, a design, a decision -- whenever criteria exist to judge it against.
