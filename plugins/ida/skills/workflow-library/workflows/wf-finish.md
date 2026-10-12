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
- **Delivery mechanism**: Open a draft pull request targeting the base branch. Never push directly to protected default branches.
- **Commit trailer**: Commits must include `Task: <task-id>` (and `Epic: <epic-id>` if applicable).
- **QA review**:
  - **Functional changes** (code, schema, or runtime changes): Require independent QA. `/reify` mints a follow-up verifying task dependent on the implementation task.
  - **Documentation, notes, or trivial chore changes**: No QA follow-up required unless explicitly requested in the task objective.

## Worker Completion Checklist

The implementation worker must satisfy these obligations before marking `status: done`:

1. Verify automated tests and linter pass locally.
2. Push feature branch to remote and open a draft pull request targeting the project's base branch.
3. Update the task record: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. Record verifiable evidence with pinpoint citations (`file:line`, test command output, PR URL).
4. Release the task as `done` via `pkb.release_task`.

## Follow-up QA Task Specification

When QA review is required, `/reify` mints a follow-up task with:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task
- **Depends on**: `[<primary-task-id>]` (hard blocking dependency)
- **Workflow**: Composes independent verification workflow
- **Goal**: Independently verify PR deliverable and claims against literal acceptance criteria in a clean context. When verified without reviewer code changes, merge to the base branch per project policy. A reviewer that changes code or pushes fixes must never merge; it must hand off for independent review by filing a follow-up QA task.
