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
2. **Build** -- implement the acceptance criteria, full suite green at the end. Acceptance criteria define observable outcomes rather than mechanism prescriptions or `file:line` edits. Workers must read target files in full to understand surrounding architecture, conventions, and helper abstractions before executing edits; keyhole reads in isolation are prohibited. A change to code that executes is built test-first: each changed behaviour's failing test captured before its code. A change that modifies no code that executes adds no test; a criterion it meets is proved by a run or check reported in the PR.
3. **Push and file the PR** -- push the branch and open or update the pull request against the base branch, its description mapping each acceptance criterion to the evidence that meets it: a test, a command's output, a fresh agent's run, or a commit. If the PR was opened as a draft, mark it ready for review as soon as its code step completes, without waiting for approval. Record the PR URL and branch on the task and release it as `done`. Releasing `done` satisfies the dependency for Stage 4 (Review and verdict).
4. **Review and verdict** -- in a separate task, by a fresh worker that did not write the code. Defaults to the dialectic review (drawing its brief from the shared review briefing in `wf-dialectical-review`, quoting the originating request verbatim with its source ID before the PR, and spawning internal subagents to provide different perspectives), unless a different review system is specified. Run `/strategic-review` on the PR, push fixes for defects small enough to settle in place, and post the review to the PR on GitHub. Then reach exactly one verdict:
   - **Rejected** -- the approach is wrong, the PR is out of proportion to what the task asks (see the `proportionate` axiom), or it cannot be salvaged: close the PR with the review as the closing comment, set the implementation task to `cancelled` with the reason, and release the review task as `failed`.
   - **Revisions needed** -- the review fails, criteria are unmet, or the PR needs more than in-place fixes: post the review citing unmet criteria and required changes to the PR, leave the PR open, and release the review task as `failed` with documented failure evidence and root cause. Do not file fix tasks or follow-up tasks; the reconcile pass notes failed tasks and decides next actions from the parent epic.
   - **Handoff for review** -- the reviewer pushed fixes or modified code on the PR: post the review and changes to the PR, leave the PR open, and release this review task as `partial` with explanation on record; reviewers never file follow-up tasks. A reviewer that changes code or pushes fixes must never merge or mark merge-ready.
   - **Mergeable** -- the review is clean with no reviewer code changes, checks are green, and GitHub reports the PR mergeable: post a merge recommendation on the PR citing the green checks and the review. Confirm tier against the taxonomy: for verified Tier 1 PRs, merge autonomously (`gh pr merge --squash`) and release the task as `done`. For Tier 2 or Tier 3 PRs, post receipts (including the link to the posted review and CI status receipts) and a reasoned recommendation, and leave the PR open for reviewer sign-off, releasing the task as `done`. Do not release to `review` for a human merge gate.

## Composition

Multi-stage code workflows must be structured in accordance with the follow-up placement invariant: either as a single task with internal subtasks (when all steps can be executed by the same agent in one session) or as a dedicated epic with child tasks (when multi-session or independent context is required). Steps must never be placed as loose siblings under an external parent.

Where stage 1 applies (multi-file changes, architectural choices, or judgment among alternative implementations, preserved even when an implementation plan is provided in the brief), it is its own child task under the epic opening a draft PR, and the build child task `needs` the recorded check of the design. Stage 2 builds on Stage 1's branch and PR, and marks the draft PR ready for review once its code step completes, without waiting for approval. Where the spec must first be written, writing it and reviewing it are separate child tasks ahead of the build. Stages 2--3 form one child task; stage 4 is a further child task that `needs` it, so a fresh worker picks it up with no shared context.

For a low-risk internal change, chiefly a bugfix, omit the separate stage 4 verification run on the fix task. Where a blocked dependent exists waiting on the fix (`blocks` or inbound `needs` / `depends_on`), the parent epic handles sequencing the dependent task's next run; no verification follow-up task is minted by workers.

## Output contract

- Stage 1 task: the design -- the governing spec it cites, or the new spec, or the plan -- committed or on the task record, and the independent check's verdict.
- Stage 2--3 task: for each changed behaviour of code that executes, its test with the red failure trace; the evidence for each other criterion; a green full-suite run; and the open PR with its URL on the task record.
- Stage 4 task: the review posted on the PR, any in-place fix commits, and one verdict carried out -- PR closed and review task released as `failed` (implementation task `cancelled`), review task released as `failed` with unmet criteria and required changes documented on failure, or a merge recommendation posted with the review task released as `done`. Workers never file fix follow-up tasks.

## When to include

Any task whose deliverable is a change to code that executes in a repository. Use in place of the general task base when the work should arrive as a reviewed PR rather than a finished artifact.
