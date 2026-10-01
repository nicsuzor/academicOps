---
alias:
  - wf-finish
description: academicOps finish template -- defines task delivery targeting active version branch, PR requirements, and independent QA review before merge into the version branch.
id: wf-finish
tags:
  - wf-template
  - finish
  - aops
title: academicOps Task Finish Template
type: template
---

## What this template does

Specifies how tasks in `nicsuzor/academicOps` finish. All individual task changes deliver via PR targeting a common unprotected version branch (e.g. `v0.10`). Functional changes require independent QA review before merge into that branch. Releases to `dev` deliver via batch PRs from the common version branch.

## Finish Policy

- **Target branch for tasks**: Active common unprotected version branch (`v0.y.z`, e.g. `v0.10`). Individual tasks must not target protected `dev` or `main` directly.
- **Delivery mechanism**: Open a pull request targeting the active version branch (`gh pr create --base <version-branch> --fill`).
- **Merging to version branch**: The follow-up verifying task reviews the PR and merges it to the version branch upon successful verification.
- **Releases to dev**: Verified changes accumulate on the version branch. A single release PR is opened _from_ the common unprotected version branch into `dev`, avoiding individual small PR approvals into `dev`.
- **Commit trailer**: Commits must carry `Task: <task-id>` (and `Epic: <epic-id>` if applicable).
- **QA review**:
  - **Required**: For any changes touching plugins, hooks, skills, agents, runtimes, or scripts. `/dispatch` mints a follow-up verifying task.
  - **None**: For pure documentation, notes, or prompt triage changes with no functional impact.

## Worker Completion Checklist

Before marking `status: done`, the worker must:

1. Ensure test suite and linter pass (`uv run pytest`, `uv run ruff check`).
2. Push feature branch (`task/<id>-<slug>`) to remote and open a PR targeting the active version branch (`v0.y.z`).
3. Check off each acceptance criterion on the PKB task with pinpoint evidence (`file:line`, command output, PR link).
4. Mark task `status: done` and release claim.

## Follow-up QA Task Specification

Where QA is required, the verifying task runs independently on a clean checkout:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task
- **Depends on**: `[<primary-task-id>]`
- **Workflow**: Composes independent verification workflow
- **Goal**: Independently verify PR changes on clean checkout against literal acceptance criteria. Once verified, merge the PR to the version branch.
