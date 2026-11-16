---
alias:
  - wf-finish
default: true
description: Default task completion workflow -- defines how a work task completes and releases as done, and how an optional review process on a reviewed class of task is reified as two separate tasks (the work task and the review task).
id: wf-finish
tags:
  - wf-template
  - finish
  - lifecycle
  - default
title: Default Task Completion Template
type: template
---

## What this template does

Defines the default workflow for completing a task (`done` release on the work task) and the optional review step for classes of tasks that require independent review.

## Work Task Completion and Single Release Status

Every work task has **one completion release status: `done`**. When the worker finishes its deliverable, it executes these steps and exits:

1. **Verify locally**: Run automated tests, linters, and build checks needed to prove the change works.
2. **Package and deliver where `Output` names**:
   - **Pull request deliverables**: Related work (tasks under a composite parent task, tasks touching shared surfaces, or PR consolidation batches) gathers on a shared feature branch (`bundle/<slug>` or `feat/<slug>`) targeting the repository's configured development or version branch (or default branch if none exists). Never push directly to protected branches. When a constituent branch (`polecat/<task-id>`) passes local checks and the three-lens diff review (strategic fit, rule compliance, and quality), merge `polecat/<task-id>` directly into the shared feature branch (`bundle/<slug>`) without waiting for user approval, open or update the single consolidated pull request into the base branch, and immediately close any superseded standalone donor PR with a comment linking to the consolidated PR. Pre-approval review on a consolidated feature-branch PR is a compliance description-only check ("is this stupid?") posted as `## RBG Review: PASS` without re-reviewing every line of constituent code and without rebasing onto the base branch before approval; post-approval landing rebases onto the base branch and runs the full three-lens diff review on the combined diff before merging. A standalone per-task PR directly into the base branch is opened only when a change has zero overlap with active feature branches or open PRs, or is an authorized hotfix. For a pre-build design or spec task, record the design, drafted spec change, and independent subagent review verdicts in a PKB note without committing a plan file or opening a PR; the subsequent build task commits the spec change alongside the build.
   - **Non-PR deliverables**: Persist the deliverable in the PKB or designated target path (never in ephemeral container scratch paths).
   - **Clean commit and PR metadata**: Never include private PKB IDs or `Task:`, `Epic:`, or `Claude-Session:` trailers in public repository commits or PR descriptions (`data-boundaries`). PR descriptions explain what was done and the approach taken without listing line-by-line diff details.
3. **Tick acceptance criteria with primary evidence**: Update `## Acceptance` on the task record. Tick an item (`[x]`) only with direct primary evidence of that item itself (`file:line`, test output, PR URL, or artifact pointer); leave any unmet item unticked (`[ ]`) with its limit stated.
4. **Release the work task as `done`**: Invoke `/dump` and release the work task via `pkb_release_task` with **`status: "done"`**, recording `pr_url` and `branch` (or the PKB artifact pointer) on the task record.
   - **One release status (`done`)**: A completed work task always releases as **`done`** -- never `review`, and never `partial` to wait for CI, code review, merge, or proof that the user installed or deployed a shipped release once the user is informed. Releasing `done` immediately unblocks any downstream review or dependent task on the graph.
   - **Exception states**: Use `partial` strictly when the worker's own acceptance items remain unfinished or halt at a pre-work approval gate; use `failed` when a required check or execution fails. Plain leaf workers (`/pull`) operate state-only on their claimed task and never mint follow-up tasks.

## Optional Review Process (Reified as Two Separate Tasks)

Review is an optional step determined by the class of task:

- **Unreviewed task classes** (routine documentation, notes, trivial chores, and low-risk internal bugfixes): Complete on the work task alone and release as **`done`** with no review task. Where a blocked dependent task waits on a bugfix (`needs`), the parent epic sequences the dependent's next run.
- **Reviewed task classes** (functional code, schema, workflow, rule, or specification changes, or any class of task with an independent review process): When reified onto the task graph, a reviewed class of task yields **two separate tasks** under the same parent container:
  1. **The work task**: Completes the deliverable, opens the draft pull request (`gh pr create --draft`) or records the artifact, ticks acceptance criteria with evidence, and releases as **`done`**.
  2. **The review task** (`needs: [<work-task-id>]`, under the same parent container): Unblocks when the work task reaches `done` and runs an independent proportionate review (defaulting to the default review workflow or a caller-chosen substitute) over the deliverable against the originating ask and governing rules:
     - **Pass (Reviewed / Ready for Decision)**: Post review verdicts and verification receipts to the PR thread, mark the draft PR ready for review (`gh pr ready`) without waiting for human approval, and evaluate the PR risk tier (`specs/enforcement/enforcement.md#pr-risk-taxonomy-enforcement`):
       - **Tier 1 (Autonomous QA-Merge)**: Low-risk changes (pure documentation, formatting, typing stubs). Merge autonomously via `gh pr merge --squash` and release the review task as **`done`**.
       - **Tier 2 (Operational Review Boundary)** and **Tier 3 (Critical Hazard & Public Review Boundary)**: Code, workflows, skills, rules, specs, infrastructure, or public outputs. Post receipts and a reasoned merge recommendation, leave the PR open for reviewer or principal sign-off, and release the review task as **`done`** (never `review`). When the PR later merges, `/reconcile` updates the tracking epic.
     - **Handoff after reviewer code edits**: If the reviewer pushes code fixes to the PR, post the changes, leave the PR open without marking merge-ready, and release the review task as **`partial`** for independent check.
     - **Fail (Revisions needed / Rejected)**: Post the failure findings and unmet criteria to the PR (closing the PR if rejected) and release the review task as **`failed`** with root cause documented on the record. Reviewers never mint fix or follow-up tasks; `/reconcile` decides next actions from the parent epic.
- **In-session supervision note**: Under single-session container supervision (`/supervise`), subagent review may execute inside the combined container session when no separate external review session is needed; the task still releases as **`done`** (never `review`).
