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
- **Delivery mechanism**: Open a pull request (not a draft) targeting the base branch. Merge authority is governed by PR risk tier below. Never push directly to protected default branches.
- **Merge authority by PR risk tier**:
  - The QA worker independently evaluates PR risk against the three-tier taxonomy (canonical: [[kb_48809ad0]], amended in [[aops_a7366995]]):
  - **Tier 1 (Autonomous QA-Merge)**: Low-risk changes (pure documentation, specifications, formatting, typing stubs). A fresh QA worker independently verifies claims and test suite in a clean context. On a verified pass, the QA worker merges the PR autonomously via `gh pr merge --squash` and releases the QA task as `done`.
  - **Tier 2 (Operational Gate)**: Code, workflows, tools, skills, rules, agent definitions, or tests. Reviewer sign-off required; a fresh QA worker independently verifies claims, runs tests, and posts receipts to the PR as a structured review comment. The QA worker does not merge, leaving the PR open for reviewer sign-off. The QA task is released as `done` with the PR URL recorded on the task record so `/reconcile` tracks merge without human wait states. No task rests or releases in `review` for a human merge gate.
  - **Tier 3 (Critical Hazard & Public Gate)**: Host infrastructure, credentials, manuscripts, public releases, or high blast radius. Gated on principal review and merge; agents are forbidden from merging. QA workers independently verify and post receipts, leaving the PR open, and release the QA task as `done`.
- **Merge**: For verified Tier 1 PRs, QA worker merges upon verified pass. For Tier 2 and Tier 3 PRs, reviewer sign-off merges the PR; QA worker verifies, posts receipts, and leaves the PR open. `/reconcile` writes `done` when the PR merges, which unblocks follow-ups.
- **Commit trailer**: Commits must include `Task: <task-id>` (and `Epic: <epic-id>` if applicable).
- **QA review**:
  - **Functional changes** (code, schema, or runtime changes): Require independent QA, except for low-risk internal changes below. `/reify` mints a follow-up verifying task dependent on the implementation task.
  - **Low-risk internal changes (chiefly bugfixes)**: Get no separate verification run. Instead, the finish step looks for a blocked task waiting on the fix (`blocks` or inbound `needs` / `depends_on`). If a blocked dependent exists, mint a follow-up task (`needs: [<blocked-task-id>]`) that judges the fix by reviewing that blocked task's next run once it runs. Where no blocked dependent exists, mint no verification follow-up task; the fix finishes without a separate verification run.
  - **Documentation, notes, or trivial chore changes**: No QA follow-up required unless explicitly requested in the task objective.

## Worker Completion Checklist

The implementation worker satisfies these obligations, then exits:

1. Verify automated tests and linter pass locally.
2. Push feature branch to remote and open a pull request (not a draft) targeting the project's base branch.
3. Update the task record: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. Record verifiable evidence with pinpoint citations (`file:line`, test command output, PR URL).
4. Release the task as `review` via `pkb.release_task`, with the PR URL in `pr_url` and `reason` stating the PR awaits merge. Do not wait for CI, review or merge. `partial` is only for the worker's own unfinished acceptance items.

## Follow-up QA Task Specification

When QA review is required for standard functional changes, `/reify` mints a follow-up task with:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task (or `part_of` edge per FQ1)
- **Needs**: `[<primary-task-id>]` (hard blocking dependency)
- **Workflow**: Composes independent verification workflow
- **Goal**: Independently verify the deliverable and claims against literal acceptance criteria in a clean context. Evaluate tier membership against the taxonomy: for verified Tier 1 PRs with low-risk changes, merge to base branch on a verified pass; for Tier 2 and Tier 3 PRs, post verification receipts to the PR and leave open for reviewer sign-off. Never release to `review` for a human merge gate; release as `done` with receipts and PR URL on record. A reviewer that changes code delivers it through this finish template and hands off for independent review by filing a follow-up QA task.

### Low-risk internal bugfixes (next-run review)

When the task is a low-risk internal change, chiefly a bugfix, mint no separate verification run on the fix task. Instead, look for a blocked task waiting on the fix (`blocks` or inbound `needs` / `depends_on`):

- **Blocked dependent exists**: Mint a follow-up task (`Title`: `QA next run: <primary task title>`, same parent, `Needs`: `[<blocked-task-id>]`, status `queued`) that judges the fix by reviewing that blocked task's next run once it runs.
- **No blocked dependent exists**: Mint no verification follow-up task; the fix finishes on its PR without a separate verification run.
