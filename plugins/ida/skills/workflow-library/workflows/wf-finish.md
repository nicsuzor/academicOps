---
alias:
  - wf-finish
default: true
description: Default task completion workflow -- defines how a work task completes and releases as done, and how an independent review stage executes in-session or as a downstream review task under the partitioned PR gate.
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

Defines the default completion workflow (`done` release on the work task) and the independent review gate across PR and non-PR deliverables.

## Work Task Completion and Single Release Status

Every work task has **one completion release status: `done`**. When the worker finishes its deliverable, it executes these steps and exits:

1. **Verify locally**: Run automated tests, linters, and build checks needed to prove the change works.
2. **Package and deliver where `Output` names**:
   - **Pull request deliverables**: Push the feature branch and open or update a draft pull request (`gh pr create --draft`) targeting the repository's configured base branch (never push directly to protected branches). If the parent task has `bundle_pr: true` or project consolidation rules apply, commit and push to the designated shared epic/bundle branch without opening a detached PR. For a pre-build design or spec task, record the design, drafted spec change, and independent subagent review verdicts in a PKB note without committing a plan file or opening a PR; the subsequent build task opens the single draft PR carrying both build and spec change.
   - **Non-PR deliverables**: Persist the deliverable in the PKB or designated target path (never in ephemeral container scratch paths).
   - **Clean commit and PR metadata**: Never include private PKB IDs or internal task, epic, or session trailers in repository commits or PR descriptions (`data-boundaries`). PR descriptions explain what was done and the approach taken without listing line-by-line diff details.
3. **Tick acceptance criteria with primary evidence**: Update `## Acceptance` on the task record. Tick an item (`[x]`) only with direct primary evidence of that item itself (`file:line`, test output, PR URL, or artifact pointer); leave any unmet item unticked (`[ ]`) with its limit stated.
4. **Release the work task as `done`**: Invoke `/dump` and release the work task via `pkb_release_task` with **`status: "done"`**, recording `pr_url` and `branch` (or the PKB artifact pointer) on the task record.
   - **One release status (`done`)**: A completed work task always releases as **`done`** -- never `review`, and never `partial` to wait for CI, code review, or merge. Releasing `done` immediately unblocks any downstream review or dependent task on the graph.
   - **Exception states**: Use `partial` strictly when the worker's own acceptance items remain unfinished or halt at a pre-work approval gate; use `failed` when a required check or execution fails. Plain leaf workers (`/pull`) operate state-only on their claimed task and never mint follow-up tasks.

## Independent Review and Partitioned PR Gate

All code, configuration, rule, skill, workflow, and specification deliverables undergo independent proportionate review (with no low-risk bugfix exemption or hard-coded task-class skipping). Under single-session container supervision (`/supervise`), independent subagent review runs in-session before readiness; when split onto the task graph (`needs: [<work-task-id>]`, such as plain `/pull` execution), the review task unblocks when the work task releases `done`:

- **Partitioned PR readiness gate**: Before marking a draft PR ready (`gh pr ready`), require green `HEAD` CI (no errored, bypassed, or `startup_failure` checks), zero unresolved `CHANGES_REQUESTED` reviews, zero uncommitted reviewer edits (push any `fix(review):` commits before posting verdicts), no deferred DRY/SSoT/compliance findings, and head-SHA-matched **posted** `## RBG Review: PASS` plus proportionate independent review matching project policy. Where project rules configure consolidated feature-branch PRs, require constituent diff receipts, green `HEAD` CI, and head-SHA-matched posted description-only `## RBG Review: PASS` pre-approval, then full combined-diff review after post-approval rebase onto base.
- **Pass (Ready for Decision / Merge)**: Post review verdicts and verification receipts to the PR thread (respecting `data-boundaries` on external-audience surfaces), mark the draft PR ready (`gh pr ready`), and apply repository project rules and standing user rulings for merge authority:
  - Merge autonomously only where project rules and standing authorization explicitly permit autonomous merge for the PR's risk level inside the user's boundary.
  - Otherwise post receipts and a reasoned merge recommendation, leave the PR open for reviewer or user sign-off, and release the task as **`done`** (never `review`).
- **Handoff after reviewer edits**: If the reviewer pushes code fixes, commit and push them, post the changes without marking merge-ready, and release the review task as **`partial`** for independent check.
- **Fail (Revisions needed / Rejected)**: Post failure findings and unmet criteria to the PR (closing the PR if rejected) and release the review task as **`failed`** with root cause documented on the record. Reviewers never mint fix or follow-up tasks.
