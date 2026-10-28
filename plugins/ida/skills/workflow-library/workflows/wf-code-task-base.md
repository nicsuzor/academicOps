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

## One branch, one PR

- Stage 1 opens a **draft** PR into the base branch carrying the spec or design, and its review verdict is recorded on that PR. Stage 1 never merges on its own.
- Stage 2 builds on Stage 1's branch and pushes to the same PR. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review once the feature is written. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Stages

1. **Design** -- for any change that needs the agent's judgment among alternative implementations; a simple bugfix or a mechanical change skips it. The design states how the feature is expected to work, the user stories it serves, and where the change sits in the wider project, and it ends in an independent check by an agent that did not write it:
   - **The project keeps specs**: the design cites the spec that governs the behaviour and holds the change to it. Where no spec governs it, the spec is written first and independently reviewed; the reviewed spec is the design. When authoring or updating a spec as Stage 1, open a **draft** PR (`gh pr create --draft`) into the base branch carrying the spec, and record the review verdict on that PR. Stage 1 never merges on its own.
   - **The project keeps no specs**: a plan naming the alternatives, the one chosen and why, and how it fits the project, checked by a different agent.
2. **Build** -- implement the acceptance criteria, full suite green at the end. Where Stage 1 preceded this build, build on Stage 1's branch and push to the same PR; the spec stays editable on that branch as the build teaches more. A change to code that executes is built test-first: each changed behaviour's failing test captured before its code. A change that modifies no code that executes adds no test; a criterion it meets is proved by a run or check reported in the PR.
3. **Push and file the PR** -- push to the feature branch (Stage 1's branch for a Stage 2 build). Where Stage 1 opened a draft PR, mark the PR ready for review (`gh pr ready`) once the feature is written, without waiting for approval; spec and feature merge together after full review. Where no Stage 1 preceded, open a pull request against the base branch. In either case, the PR description maps each acceptance criterion to the evidence that meets it: a test, a command's output, a fresh agent's run, or a commit. Record the PR URL on the task and release it as `done`.
4. **Review and verdict** -- in a separate task, by a fresh worker that did not write the code. The review task draws its brief from the shared review briefing in `wf-review` (quoting the originating request verbatim with its source ID before the PR). Run `/strategic-review` on the PR, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict:
   - **Rejected** -- the approach is wrong, the PR is out of proportion to what the task asks (see the `proportionate` axiom), or it cannot be salvaged: close the PR with the review as the closing comment, set the implementation task to `cancelled` with the reason, and release the review task as `failed`.
   - **Revisions needed** -- the review fails, criteria are unmet, or the PR needs more than in-place fixes: post the review citing unmet criteria and required changes to the PR, leave the PR open, and release the review task as `failed` with documented failure evidence and root cause. Do not file fix tasks or follow-up tasks; the reconcile pass notes failed tasks and decides next actions from the parent epic.
   - **Handoff for review** -- the reviewer pushed fixes or modified code on the PR: post the review and changes to the PR, leave the PR open, and release this review task as `partial` with explanation on record; reviewers never file follow-up tasks. A reviewer that changes code or pushes fixes must never merge or mark merge-ready.
   - **Mergeable** -- the review is clean with no reviewer code changes, checks are green, and GitHub reports the PR mergeable: post a merge recommendation on the PR citing the green checks and the review. Confirm tier against the taxonomy: for verified Tier 1 PRs, merge autonomously (`gh pr merge --squash`) and release the task as `done`. For Tier 2 or Tier 3 PRs, post receipts and leave the PR open for reviewer sign-off, releasing the task as `done`. Do not release to `review` for a human merge gate.

## Composition

Where stage 1 applies, it is its own task that opens a **draft** PR carrying the spec or design, and the build task `needs` the recorded check of the design. Where the spec must first be written, writing it and reviewing it are separate tasks ahead of the build. Stages 2--3 form one task that builds on Stage 1's branch and pushes to the same PR, with the spec still editable; Stage 2 marks the PR ready for review once the feature is written, without waiting for approval. Spec and feature merge together after full review. Stage 4 is a further task that `needs` it, so a fresh worker picks it up with no shared context.

For a low-risk internal change, chiefly a bugfix, omit the separate stage 4 verification run on the fix task. Where a blocked dependent exists waiting on the fix (`blocks` or inbound `needs` / `depends_on`), the parent epic handles sequencing the dependent task's next run; no verification follow-up task is minted by workers.

## Output contract

- Stage 1 task: the design -- the governing spec it cites, or the new spec, or the plan -- committed on the feature branch, the draft PR opened targeting the base branch, and the independent check's verdict recorded on the PR. Stage 1 never merges on its own.
- Stage 2--3 task: built on Stage 1's branch and PR (or a fresh branch where no Stage 1 applies), with the spec still editable; for each changed behaviour of code that executes, its test with the red failure trace; the evidence for each other criterion; a green full-suite run; and the PR marked ready for review with its URL on the task record, merging spec and feature together after full review.
- Stage 4 task: the review posted on the PR, any in-place fix commits, and one verdict carried out -- PR closed and review task released as `failed` (implementation task `cancelled`), review task released as `failed` with unmet criteria and required changes documented on failure, or a merge recommendation posted with the review task released as `merge_ready`. Workers never file fix follow-up tasks.

## When to include

Any task whose deliverable is a change to code that executes in a repository. Use in place of the general task base when the work should arrive as a reviewed PR rather than a finished artifact.
