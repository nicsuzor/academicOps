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
- **Releases to main**: A PR from `dev` into `main` merges only with Nic's review.
- **Commit trailer**: Commits must carry `Task: <task-id>` (and `Epic: <epic-id>` if applicable).
- **QA review**:
  - **Required**: For any changes touching plugins, hooks, skills, agents, runtimes, or scripts. `/dispatch` mints a follow-up verifying task.
  - **None**: For pure documentation, notes, or prompt triage changes with no functional impact.

## Worker Completion Checklist

Before marking `status: done`, the worker must:

1. Ensure test suite and linter pass (`uv run pytest`, `uv run ruff check`).
2. Push feature branch (`task/<id>-<slug>`) to remote and open a PR targeting `dev`.
3. Check off each acceptance criterion on the PKB task with pinpoint evidence (`file:line`, command output, PR link).
4. Mark task `status: done` and release claim.

## Follow-up QA Task Specification

Where QA is required, the verifying task runs independently on a clean checkout:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task
- **Depends on**: `[<primary-task-id>]`
- **Workflow**: Composes independent verification workflow
- **Goal**: Independently verify PR changes on clean checkout against literal acceptance criteria. Once verified, merge the PR to `dev`.
