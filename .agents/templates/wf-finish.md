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

## Finish Policy

- **Target branch for tasks**: `dev`. Individual tasks must not target `main`.
- **Delivery mechanism**: Open a pull request targeting `dev` (`gh pr create --base dev --fill`).
- **Merging to dev**: Merge on green. Where QA is required, the follow-up verifying task reviews the PR and merges it to `dev` upon successful verification.
- **Releases to main**: A PR from `dev` into `main` merges only on explicit release approval.
- **Commit messages and trailers**: Commits to public repositories must never carry PKB IDs or `Task:`, `Epic:`, or `Claude-Session:` trailers (`data-boundaries`). Task linkage is maintained in the private task record, not in public repository commits.
- **QA review**:
  - **Required**: For any changes touching plugins, hooks, skills, agents, runtimes, or scripts, except for low-risk internal changes below. `/reify` mints a follow-up verifying task.
  - **Low-risk internal changes (chiefly bugfixes)**: Get no separate verification run. Instead, the finish step looks for a blocked task waiting on the fix (`blocks` or inbound `depends_on` / `needs`). If a blocked dependent exists, mint a follow-up task (`depends_on: [<blocked-task-id>]`) that judges the fix by reviewing that blocked task's next run once it runs. Where no blocked dependent exists, mint no verification follow-up task; the fix finishes without a separate verification run.
  - **None**: For pure documentation, notes, or prompt triage changes with no functional impact.

## Worker Completion Checklist

Before marking `status: done`, the worker must:

1. Ensure test suite and linter pass (`uv run pytest`, `uv run ruff check`).
2. Push feature branch (`task/<id>-<slug>`) to remote and open a PR targeting `dev`.
3. Update acceptance criteria on the PKB task: tick an item only with evidence of that item itself; leave any other item unticked with its limit stated, citing pinpoint evidence (`file:line`, command output, PR link).
4. Mark task `status: done` and release claim. A worker whose own deliverable is complete releases its task `done`, even when a follow-up that depends on it (QA, merge, deploy) is still to run; `partial` is only for the worker's own unfinished acceptance items.

## Follow-up QA Task Specification

Where QA is required for standard changes, the verifying task runs independently on a clean checkout:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task
- **Depends on**: `[<primary-task-id>]`
- **Workflow**: Composes independent verification workflow
- **Goal**: Independently verify PR changes on clean checkout against literal acceptance criteria. Once verified, merge the PR to `dev`.

### Low-risk internal bugfixes (next-run review)

When the task is a low-risk internal change, chiefly a bugfix, mint no separate verification run on the fix task. Instead, look for a blocked task waiting on the fix (`blocks` or inbound `depends_on` / `needs`):

- **Blocked dependent exists**: Mint a follow-up task (`Title`: `QA next run: <primary task title>`, same parent, `Depends on`: `[<blocked-task-id>]`, status `queued`) that judges the fix by reviewing that blocked task's next run once it runs.
- **No blocked dependent exists**: Mint no verification follow-up task; the fix finishes on its PR without a separate verification run.
