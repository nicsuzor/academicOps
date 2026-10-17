---
title: Code task base
type: template
description: Alternative foundation for code-change tasks executed via /ida:pull -- a reviewed design first wherever the change calls for judgment among alternative implementations, then build (test-first for code that executes), push and PR, then a fresh worker's strategic review ending in a verdict on the PR.
tags: [base, task, code, composite]
---

- **GOAL:** <one sentence>
- **ACCEPTANCE CRITERIA:** <one line each>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <repository and base branch the PR targets>
- **REPORT:** Use /ida:dump to update your task. Do not append your observations as a log; update the prose to reflect current state and delete any content that is no longer relevant, true, or that reflects prior state or prior instructions. Update the ACCEPTANCE CRITERIA block: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. On the same line, provide a relevant extract of your evidence supporting your assertion, along with a citation for the source of the evidence.

## Stages

1. **Design** -- for any change that needs the agent's judgment among alternative implementations; a simple bugfix or a mechanical change skips it. The design states how the feature is expected to work, the user stories it serves, and where the change sits in the wider project, and it ends in an independent check by an agent that did not write it:
   - **The project keeps specs**: the design cites the spec that governs the behaviour and holds the change to it. Where no spec governs it, the spec is written first and independently reviewed; the reviewed spec is the design.
   - **The project keeps no specs**: a plan naming the alternatives, the one chosen and why, and how it fits the project, checked by a different agent.
2. **Build** -- implement the acceptance criteria, full suite green at the end. A change to code that executes is built test-first: each changed behaviour's failing test captured before its code. A change that modifies no code that executes adds no test; a criterion it meets is proved by a run or check reported in the PR.
3. **Push and file the PR** -- push the branch and open a pull request against the base branch, its description mapping each acceptance criterion to the evidence that meets it: a test, a command's output, a fresh agent's run, or a commit. Record the PR URL on the task and release it as `done`.
4. **Review and verdict** -- in a separate task, by a fresh worker that did not write the code. Run `/strategic-review` on the PR, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict:
   - **Rejected** -- the approach is wrong, the PR is out of proportion to what the task asks (see the `proportionate` axiom), or it cannot be salvaged: close the PR with the review as the closing comment, and set the implementation task to `cancelled` with the reason.
   - **Extensive revisions** -- the PR is sound in direction but needs more than in-place fixes: file a fix follow-up task that names each required change and `needs` the review task, leave the PR open, and link the follow-up from the review.
   - **Handoff for review** -- the reviewer pushed fixes or modified code on the PR: post the review and changes to the PR, file an independent QA follow-up task that `needs` this review task so a fresh independent reviewer verifies the modified PR, leave the PR open, and release this review task as `partial`. A reviewer that changes code or pushes fixes must never merge or mark merge-ready.
   - **Mergeable** -- the review is clean with no reviewer code changes, checks are green, and GitHub reports the PR mergeable: post a merge recommendation on the PR citing the green checks and the review. For Tier 1 PRs (`triage:auto-mergeable`), merge autonomously (`gh pr merge --squash`) and release the task as `done`. For Tier 2 (`triage:needs-judgment`) and Tier 3 (`criticality:critical`) PRs, post receipts and leave the PR open for reviewer sign-off, releasing the task as `done`. Do not release to `review` for a human merge gate.

## Composition

Where stage 1 applies, it is its own task, and the build task `needs` the recorded check of the design. Where the spec must first be written, writing it and reviewing it are separate tasks ahead of the build. Stages 2--3 form one task; stage 4 is a further task that `needs` it, so a fresh worker picks it up with no shared context.

For a low-risk internal change, chiefly a bugfix, omit the separate stage 4 verification run on the fix task. Instead, look for a blocked task waiting on the fix (`blocks` or inbound `needs` / `depends_on`): if a blocked dependent exists, mint a follow-up task (`needs: [<blocked-task-id>]`) that judges the fix by reviewing that blocked task's next run once it runs; where no blocked dependent exists, mint no verification follow-up task.

## Output contract

- Stage 1 task: the design -- the governing spec it cites, or the new spec, or the plan -- committed or on the task record, and the independent check's verdict.
- Stage 2--3 task: for each changed behaviour of code that executes, its test with the red failure trace; the evidence for each other criterion; a green full-suite run; and the open PR with its URL on the task record.
- Stage 4 task: the review posted on the PR, any in-place fix commits, and one verdict carried out -- PR closed and implementation task `cancelled`, a fix follow-up task filed, a handoff follow-up task filed with the review task released as `partial`, or on a mergeable verdict: Tier 1 PR merged and task released as `done`; Tier 2/3 PR left open with receipts and task released as `done`.

## When to include

Any task whose deliverable is a change to code that executes in a repository. Use in place of the general task base when the work should arrive as a reviewed PR rather than a finished artifact.
