---
alias:
  - wf-finish
description: academicOps finish template -- defines task delivery targeting base dev, PR requirements, and independent QA review via wf-qa.
id: wf-finish
tags:
  - wf-template
  - finish
  - aops
title: academicOps Task Finish Template
type: template
---

## What this template does

Specifies how tasks in `nicsuzor/academicOps` finish. All changes deliver via PR to `dev`, and functional changes require independent QA review before merge.

## Finish Policy

- **Target branch**: `dev` (canonical base branch for academicOps; never target `main` directly).
- **Delivery mechanism**: Pull request targeting `dev` (`gh pr create --base dev --fill`).
- **Commit trailer**: Commits must carry `Task: <task-id>` (and `Epic: <epic-id>` if applicable).
- **QA review**:
  - **Required** (`wf-qa`): For any changes touching plugins, hooks, skills, agents, runtimes, or scripts. `/dispatch` mints a follow-up QA task.
  - **None**: For pure documentation, notes, or prompt triage changes with no functional impact.

## Worker Completion Checklist

Before marking `status: done`, the worker must:

1. Ensure test suite and linter pass (`uv run pytest`, `uv run ruff check`).
2. Push feature branch (`task/<id>-<slug>`) to remote and open PR targeting `dev`.
3. Check off each acceptance criterion on the PKB task with pinpoint evidence (`file:line`, command output, PR link).
4. Mark task `status: done` and release claim.

## Follow-up QA Task Specification

Where QA is required:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task
- **Depends on**: `[<primary-task-id>]`
- **Workflow**: Composes `wf-qa`
- **Goal**: Independently verify PR changes on clean checkout against literal acceptance criteria.
