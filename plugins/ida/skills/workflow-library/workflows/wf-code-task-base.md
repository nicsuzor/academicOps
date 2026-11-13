---
title: Code task base
type: template
description: Foundation for code-change tasks executed via /ida:supervise (or /ida:pull for plain leaf tasks) -- by default in a single supervised container session combining reviewed design, test-first build, incremental push and draft PR, and independent multi-lens review ending in a verdict on the PR.
tags: [base, task, code, composite]
---

- **GOAL:** <one sentence>
- **ACCEPTANCE CRITERIA:** <one line each>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <repository and base branch the PR targets>
- **REPORT:** Use /ida:dump to update your task. Do not append your observations as a log; update the prose to reflect current state and delete any content that is no longer relevant, true, or that reflects prior state or prior instructions. Update the ACCEPTANCE CRITERIA block: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. On the same line, provide a relevant extract of your evidence supporting your assertion, along with a citation for the source of the evidence.

## One PR, opened by the build

- Under container supervision (`/supervise`), Stages 1--4 execute by default within a single combined repo-scoped task in one container session:
  - Stage 1 conducts design and subagent dialectical review in-session (recording in a PKB note or design record without committing plan files or opening premature PRs).
  - Stage 2 opens the PR into the base branch as a draft, carrying the build and any spec change. The spec stays editable on that branch as the build teaches more.
  - Stage 3/4 marks the PR ready for review (`gh pr ready`) only after proportionate review by independent subagents is posted to the PR thread. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.
- For tasks executed across separate tasks (under `/pull` leaf execution or when explicitly split for different repo/time/agent), Stage 1 records its design in a PKB note that Stage 2 points to, Stage 2 opens the draft PR, and Stage 4 runs as a separate verifying task.

## Stages

Under container supervision (`/supervise`), Stages 1--4 execute by default within a single combined repo-scoped task in one session, coordinating subagent fan-out and incremental git push checkpoints. When split across separate tasks (permitted only when explicitly requiring a different repository, different time, or separate external agent/session, or under `/pull` leaf execution), each stage operates within its assigned task boundaries.

1. **Design** -- for any change that needs the agent's judgment among alternative implementations; a simple bugfix or a mechanical change skips it. The design states how the feature is expected to work, the human user stories it serves (always from a human person's perspective, never "As an agent / custodian / worker, I want...", since agents are given capabilities only to fulfil human user requirements), and where the change sits in the wider project, and it ends in an independent check by an agent that did not write it:
   - **The project keeps specs**: the design cites the spec that governs the behaviour and holds the change to it. Where no spec governs it, the spec is written first and reviewed by independent subagents; the reviewed spec is the design. In a combined `/supervise` session, the design is verified in-session; when split, Stage 1 records its design, any drafted spec change, and its independent agent review verdicts in a PKB note the Stage 2 task points to. Stage 1 commits no plan or design file, opens no PR, and never puts a spec to the user for approval on its own.
   - **The project keeps no specs**: a plan naming the alternatives, the one chosen and why, and how it fits the project, checked by a different agent, recorded in a PKB task or note; no plan file is committed to the repository and no PR is opened.
2. **Build** -- implement the acceptance criteria, full suite green at the end. Acceptance criteria define observable outcomes rather than mechanism prescriptions or `file:line` edits. Workers must read target files in full to understand surrounding architecture, conventions, and helper abstractions before executing edits; keyhole reads in isolation are prohibited. Carry the build and any drafted spec change onto the feature branch and open the PR into the base branch as a draft; the spec stays editable on that branch as the build teaches more. A change to code that executes is built test-first: each changed behaviour's failing test captured before its code. A change that modifies no code that executes adds no test; a criterion it meets is proved by a run or check reported in the PR.
3. **Push and file the PR** -- push to the feature branch with incremental checkpoints and open the PR into the base branch (in draft state using `--draft` when requiring reviewer or principal approval). Mark the PR ready for review (`gh pr ready`) only after the proportionate review on the build is posted to the PR thread by independent agents, without waiting for approval; spec and feature merge together after full review. The PR description explains what was done and the approach taken to do it, making the PR easy to read and understand; the diff is available for line-by-line inspection, so do not list every single change in detail. Summarize verification and follow project PR style or templates where defined. Dispatched leaf workers under `/pull` operate strictly under the worker state-only invariant: mutate only this task's own record and state, never inspect or modify edges across other tasks or mint follow-up verification tasks. Record the PR URL and branch on the task.
4. **Review and verdict** -- by an independent reviewing agent (or subagents) that did not write the code (coordinated in-session under `/supervise`, or in a separate task for plain `/pull` leaf execution). A review is required and a proportionate review is selected (defaults to the dialectic review, or a user-chosen substitute). When a review step is included, run independent agent review on the PR, push fixes for defects small enough to settle in place, and post the review verdicts to the PR on GitHub. Then reach exactly one verdict:
   - **Rejected** -- the approach is wrong, the PR is out of proportion to what the task asks (see the `proportionate` axiom), or it cannot be salvaged: close the PR with the review as the closing comment, set the implementation task to `cancelled` with the reason, and release the task as `failed`.
   - **Revisions needed** -- the review fails, criteria are unmet, or the PR needs more than in-place fixes: post the review citing unmet criteria and required changes to the PR, leave the PR open, and release the task as `failed` with documented failure evidence and root cause. Do not file fix tasks or follow-up tasks; the reconcile pass notes failed tasks and decides next actions from the parent epic.
   - **Handoff for review** -- the reviewer pushed fixes or modified code on the PR: post the review and changes to the PR, leave the PR open, and release the task as `partial` with explanation on record; reviewers never file follow-up tasks. A reviewer that changes code or pushes fixes must never merge or mark merge-ready.
   - **Reviewed / Ready for Decision** -- the review is clean with no reviewer code changes and checks are green: post a review summary or merge recommendation on the PR citing the green checks and the review. Confirm tier against the taxonomy: for verified Tier 1 PRs, bring the branch up to date with the base branch if needed, merge autonomously (`gh pr merge --squash`), and release the task as `done`. For Tier 2 or Tier 3 PRs, post receipts (including the link to the posted review and CI status receipts) and a reasoned recommendation, and leave the PR open for reviewer/principal sign-off, releasing the task as `done`. Mergeability against the base branch is not required before approval; bringing the PR up to date with its base and resolving conflicts happens after approval, just before merge. Do not release to `review` for a human merge gate.

## Composition

Under container supervision (`/supervise`), multi-stage code workflows execute by default as a single combined repo-scoped task within one container session: the coordinator manages Stage 1 design review, Stage 2 test-first build, Stage 3 incremental push and draft PR, and Stage 4 multi-lens review and PR readiness marking in-session.

Splitting into separate child/follow-up tasks is prohibited by default and permitted ONLY when a workflow step explicitly requires:

1. _Different repository_: strictly one task per repository.
2. _Different time_: a distinct external wait condition or execution window.
3. _Different agent/session_: a workflow-mandated separate external agent or session (such as user-channel closed-loop reporting).

Steps must never be placed as loose siblings under an external parent. When separate tasks are explicitly required:

- Where Stage 1 applies, it records its design and review verdicts in a PKB note the build task points to, committing no plan file and opening no PR.
- Stages 2--3 form one task that opens the draft PR into the base branch, with the spec still editable.
- Stage 4 is a child task that `needs` it, so a fresh agent worker picks it up.

Plain leaf workers running under `/ida:pull` operate strictly state-only: mutate only the claimed task's own record, never inspect or modify edges across tasks, and never mint follow-up verification tasks.

For a low-risk internal change, chiefly a bugfix, omit the separate Stage 4 verification run on the fix task. Where a blocked dependent exists waiting on the fix (prerequisite `needs` on the dependent task), the parent epic handles sequencing the dependent task's next run; no verification follow-up task is minted by workers.

## Output contract

- Combined `/supervise` task (default): the design verified in-session, the PR opened into the base branch carrying the build and any spec change (with the spec still editable), test evidence and red failure traces for code that executes, green full-suite verification, independent review verdicts posted to the PR thread, the PR marked ready for review with its URL on the task record, and the task released per the PR risk tier.
- Split tasks (when explicitly required):
  - Stage 1 task: the design -- the governing spec it cites, or the drafted spec change, or the plan -- and its independent agent review verdicts recorded in a PKB note the Stage 2 task points to. Stage 1 commits no plan or design file and opens no PR.
  - Stage 2--3 task: the PR opened into the base branch carrying the build and any spec change (with the spec still editable); for each changed behaviour of code that executes, its test with the red failure trace; the evidence for each other criterion; a green full-suite run; and the PR marked ready for review with its URL on the task record, merging spec and feature together after full review.
  - Stage 4 task: the agent review verdicts posted on the PR, any in-place fix commits, and one verdict carried out -- PR closed and review task released as `failed` (implementation task `cancelled`), review task released as `failed` with unmet criteria and required changes documented on failure, or a merge recommendation posted with the review task released as `done`. Workers never file fix follow-up tasks.

## When to include

Any task whose deliverable is a change to code that executes in a repository. Use in place of the general task base when the work should arrive as a reviewed PR rather than a finished artifact.
