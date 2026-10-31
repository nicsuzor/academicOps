---
alias:
  - wf-finish
description: Universal finish template fallback -- defines how tasks finish when a project has no local finish template, targeting common development or version branch and specifying QA verification for functional changes.
id: wf-finish
tags:
  - wf-template
  - finish
  - lifecycle
title: Universal Task Finish Template
type: template
---

## What this template does

Defines the universal baseline contract for how tasks finish when a repository lacks a project-local finish template. Governs delivery targets, worker completion obligations, and independent QA follow-up requirements.

## Finish Policy

- **Target branch**: Common unprotected version or development branch where configured; repository default branch (`main` or `master`) if no intermediate branch exists.
- **Delivery mechanism**: Open a pull request targeting the base branch; a Stage 1 spec or design PR opens as a draft. Any draft PR is marked ready for review as soon as its code step completes, without waiting for approval. Merge authority is governed by PR risk tier below. Never push directly to protected default branches.
- **Merge authority by PR risk tier**:
  - The QA worker independently evaluates PR risk against the three-tier taxonomy (`specs/enforcement/enforcement.md#pr-risk-taxonomy-enforcement`):
  - **Tier 1 (Autonomous QA-Merge)**: Low-risk changes (pure documentation, specifications, formatting, typing stubs). A fresh QA worker independently verifies claims and test suite in a clean context. On a verified pass, the QA worker merges the PR autonomously via `gh pr merge --squash` and releases the QA task as `done`.
  - **Tier 2 (Operational Gate)**: Code, workflows, tools, skills, rules, agent definitions, or tests. Reviewer sign-off required; a fresh QA worker independently verifies claims, runs tests, and posts receipts to the PR as a structured review comment. The QA worker does not merge, leaving the PR open for reviewer sign-off. The QA task is released as `done` with the PR URL recorded on the task record so `/reconcile` tracks merge without human wait states. No task rests or releases in `review` for a human merge gate.
  - **Tier 3 (Critical Hazard & Public Gate)**: Host infrastructure, credentials, manuscripts, public releases, or high blast radius. Gated on principal review and merge; agents are forbidden from merging. QA workers independently verify and post receipts, leaving the PR open, and release the QA task as `done`.
- **Merge**: For verified Tier 1 PRs, QA worker merges upon verified pass. For Tier 2 and Tier 3 PRs, reviewer sign-off merges the PR; QA worker verifies, posts receipts, and leaves the PR open. The primary implementation task releases `done` upon PR filing to unblock QA; when the PR merges, the parent epic progresses.
- **Commit messages and trailers**: Commits to public repositories must never carry PKB IDs or `Task:`, `Epic:`, or `Claude-Session:` trailers (`data-boundaries`). Task linkage is maintained in the private task record, not in public repository commits.
- **QA review**:
  - **Functional changes** (code, schema, or runtime changes): Require independent QA, except for low-risk internal changes below. `/reify` mints a follow-up verifying task dependent on the implementation task.
  - **Low-risk internal changes (chiefly bugfixes)**: Get no separate verification run. Where a blocked dependent exists waiting on the fix (`blocks` or inbound `needs` / `depends_on`), the parent epic handles sequencing the dependent task's next run; workers never mint verification follow-up tasks.
  - **Documentation, notes, or trivial chore changes**: No QA follow-up required unless explicitly requested in the task objective.

## Worker Completion Checklist

The implementation worker satisfies these obligations, then exits:

1. Verify automated tests and linter pass locally.
2. Push feature branch to remote and open or update the pull request targeting the project's base branch; if the PR is a draft and its code step is complete, mark it ready for review without waiting for approval.
3. Update the task record: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. Record verifiable evidence with pinpoint citations (`file:line`, test command output, PR URL).
4. Release the task as `done` via `pkb_release_task`, with the PR URL in `pr_url` and branch recorded on the task record. Do not release as `review`. Releasing `done` unblocks the downstream QA or review follow-up task on the graph. Do not wait for CI, review or merge. `partial` is reserved strictly for the worker's own unfinished acceptance items. Workers never create or name follow-up tasks.

## Follow-up QA Task Specification

When QA review is required for standard functional changes, `/reify` mints a follow-up task with:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task (or `part_of` edge per FQ1)
- **Needs**: `[<primary-task-id>]` (hard blocking dependency)
- **Workflow**: Composes independent verification workflow
- **Goal**: Independently verify the deliverable and claims against literal acceptance criteria in a clean context. If verification fails, the QA task releases `failed` with failure evidence documented on the record; reviewers do not file fix tasks or follow-up tasks. On a verified pass, evaluate tier membership against the taxonomy: for verified Tier 1 PRs with low-risk changes, merge to base branch autonomously via `gh pr merge --squash` and release as `done`; for Tier 2 and Tier 3 PRs, post verification receipts to the PR and leave open for reviewer sign-off without releasing to review; release as `done` with receipts and PR URL on record. A reviewer that changes code delivers it through this finish template and hands off for independent review.

### Low-risk internal bugfixes (next-run review)

When the task is a low-risk internal change, chiefly a bugfix, mint no separate verification run on the fix task. Where a blocked dependent exists waiting on the fix (`blocks` or inbound `needs` / `depends_on`), the parent epic handles sequencing the dependent task's next run; workers never mint verification follow-up tasks. Where no blocked dependent exists, the fix finishes on its PR without a separate verification run.
