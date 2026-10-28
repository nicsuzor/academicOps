---
alias:
  - wf-finish
description: academicOps finish template -- defines task delivery via PR into dev, PR requirements, and independent QA review before merge into dev.
id: wf-finish
tags:
  - wf-template
  - finish
  - aops
title: academicOps Task Finish Template
type: template
---

## What this template does

Specifies how tasks in `nicsuzor/academicOps` finish. All individual task changes deliver via PR targeting `dev`. A PR merges into `dev` on green; functional changes also require independent QA review first. Merging to `main` requires escalated review.

## One branch, one PR

- Stage 1 opens a **draft** PR into the base branch carrying the spec or design, and its review verdict is recorded on that PR. Stage 1 never merges on its own.
- Stage 2 builds on Stage 1's branch and pushes to the same PR. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review once the feature is written. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Finish Policy

- **Target branch for tasks**: `dev`. Individual tasks must not target `main`.
- **Delivery mechanism**: Open a pull request targeting `dev`. When the work is a Stage 1 spec or design preceding a build, open the PR as a **draft** (`gh pr create --draft --base dev --fill`); when the work is a Stage 2 build continuing an approved spec, build on Stage 1's branch, push to that PR, and mark the PR ready for review once the feature is written, without waiting for approval. Spec and feature merge together after full review. For standalone single-stage changes, open a standard pull request (`gh pr create --base dev --fill`).
- **Merging to dev**: Merge on green. Where QA is required, the verifying task reviews the PR and merges it to `dev` upon successful verification. If verification fails, the verifying task releases `failed` with failure evidence documented on the record; it does not file fix tasks or follow-up tasks. A Stage 1 spec draft PR never merges on its own; it merges only with its feature after full review.
- **Releases to main**: A PR from `dev` into `main` merges only on explicit release approval.
- **Commit messages and trailers**: Commits to public repositories must never carry PKB IDs or `Task:`, `Epic:`, or `Claude-Session:` trailers (`data-boundaries`). Task linkage is maintained in the private task record, not in public repository commits.
- **QA review**:
  - **Required**: For any changes touching plugins, hooks, skills, agents, runtimes, or scripts, except for low-risk internal changes below. `/reify` mints a follow-up verifying task.
  - **Low-risk internal changes (chiefly bugfixes)**: Get no separate verification run. Where a blocked dependent exists waiting on the fix (`blocks` or inbound `depends_on` / `needs`), the parent epic handles sequencing the dependent task's next run; workers never mint verification follow-up tasks.
  - **None**: For pure documentation, notes, or prompt triage changes with no functional impact.

## Worker Completion Checklist

Before marking `status: done`, the worker must:

1. Ensure test suite and linter pass (`uv run pytest`, `uv run ruff check`).
2. Push feature branch to remote and open or update the PR: for a Stage 1 spec or design task preceding a build, open as a draft PR (`gh pr create --draft`); for a Stage 2 build, push to Stage 1's branch and mark the PR ready for review once the feature is written, without waiting for approval; for standalone changes, open a PR targeting `dev`.
3. Update acceptance criteria on the PKB task: tick an item only with evidence of that item itself; leave any other item unticked with its limit stated, citing pinpoint evidence (`file:line`, command output, PR link).
4. Mark task `status: done` and release claim (or `review` where an explicit user decision is required). A worker whose own deliverable is complete releases its task `done`, even when a dependent check (QA, merge, deploy) is still to run; `partial` is only for the worker's own unfinished acceptance items. Workers never create or name follow-up tasks.

## Follow-up QA Task Specification

Where QA is required for standard changes, the verifying task runs independently on a clean checkout:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task
- **Depends on**: `[<primary-task-id>]`
- **Workflow**: Composes independent verification workflow
- **Goal**: Independently verify PR changes on clean checkout against literal acceptance criteria. Once verified, merge the PR to `dev`. If verification fails, the verifying task releases `failed` with failure evidence and root cause documented on the record; it does not file fix tasks.

### Low-risk internal bugfixes (next-run review)

When the task is a low-risk internal change, chiefly a bugfix, mint no separate verification run on the fix task. Where a blocked dependent exists waiting on the fix (`blocks` or inbound `depends_on` / `needs`), the parent epic handles sequencing the dependent task's next run; workers never mint verification follow-up tasks. Where no blocked dependent exists, the fix finishes on its PR without a separate verification run.
