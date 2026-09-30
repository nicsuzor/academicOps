---
alias:
  - wf-finish
description: Universal finish template fallback -- defines how tasks finish when a project has no local finish template, targeting default branch and specifying QA follow-up for functional changes.
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

## Resolution

`/dispatch` resolves finish templates using standard tier precedence:

1. **Project-local**: `$CWD/.agents/templates/wf-finish.md`
2. **PKB**: Document carrying `id: wf-finish` and `type: template`
3. **Universal Fallback**: This template (`plugins/ida/skills/workflow-library/workflows/wf-finish.md`)

## Finish Policy

- **Target branch**: Repository default branch (`main` or `master`), or `dev` if it exists.
- **Delivery mechanism**: Open a Pull Request targeting the base branch. Never push directly to protected default branches.
- **Commit trailer**: Commits must include `Task: <task-id>` (and `Epic: <epic-id>` if applicable).
- **QA review**:
  - **Code, schema, or runtime changes**: Require independent QA. `/dispatch` mints a follow-up task composing `wf-qa` dependent on the implementation task.
  - **Documentation, notes, or trivial chore changes**: No QA follow-up required unless explicitly requested in the task objective.

## Worker Completion Checklist

The implementation worker must satisfy these obligations before marking `status: done`:

1. Verify automated tests and linter pass locally.
2. Push feature branch to remote and open a Pull Request targeting the project's base branch.
3. Update the task record: check off met acceptance criteria and record verifiable evidence with pinpoint citations (`file:line`, test command output, PR URL).
4. Release the task as `done` via `pkb.release_task`.

## Follow-up QA Task Specification

When QA review is required, `/dispatch` mints a follow-up task with:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task
- **Depends on**: `[<primary-task-id>]` (hard blocking dependency)
- **Workflow**: Composes `wf-qa` (or `wf-signoff` / `wf-fact-check` if specified)
- **Goal**: Independently verify PR deliverable and claims against literal acceptance criteria in a clean context.
