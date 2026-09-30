---
id: workflows-finish-template
title: Project Finish Template Format and Fallback
type: spec
category: workflow
status: ready
tags: [spec, workflow, dispatch, finish, qa]
---

# Project Finish Template Format and Fallback

Per the task lifecycle ruling ([[mem_1cae6053]]), workers with PKB access mark their tasks `status: done` after `/pull`. The worker's completion claim asserts that local tests and acceptance criteria are satisfied, but substantive independent QA cannot run in the worker's own dirty context.

Where a project requires independent review before merge, `/dispatch` reads the project's finish template and creates a follow-up task for an independent QA review. Each project carries a project-local template explaining how its tasks finish; not all repositories need QA before merge.

## Resolution Hierarchy

`/dispatch` resolves finish templates using the standard three-tier resolution order:

1. **Project-local**: `$CWD/.agents/templates/wf-finish.md` (or repo-root `.agents/templates/wf-finish.md`).
2. **PKB**: Document carrying `id: wf-finish` and `type: template`.
3. **Universal fallback**: `plugins/ida/skills/workflow-library/workflows/wf-finish.md`.

A higher tier shadows lower tiers completely; text is never merged across tiers.

## Finish Template Format

A finish template is a composable workflow template (`type: template`) with the canonical slug `wf-finish`.

### Frontmatter Schema

```yaml
---
alias:
  - wf-finish
description: <one-line summary of delivery target and QA requirements>
id: wf-finish
tags:
  - wf-template
  - finish
  - <project-tag>
title: <Project Name> Task Finish Template
type: template
---
```

### Required Sections

A finish template defines three standard sections:

#### 1. Finish Policy (`## Finish Policy`)

- **Target branch**: The canonical base branch for pull requests (e.g. `dev`, `main`). Feature branches target this base.
- **Delivery mechanism**: PR or direct branch push. Production codebases require pull requests (`gh pr create --base <ref> --fill`).
- **Commit trailer**: Commit metadata requirements (`Task: <task-id>` and optional `Epic: <epic-id>`).
- **QA review**:
  - `required`: Independent QA review must precede merge.
  - `conditional`: Independent QA is required for functional changes (code, runtime, schema) but omitted for pure documentation or notes.
  - `none`: Tasks finish upon worker completion without an independent QA pass.
- **QA template**: The universal QA workflow to compose for the follow-up review:
  - `wf-qa`: General qualitative and behavioral verification against literal acceptance criteria.
  - `wf-signoff`: One-page executive digest for human decision or release sign-off.
  - `wf-fact-check`: Citation and primary-source verification for factual/empirical claims.

#### 2. Worker Completion Checklist (`## Worker Completion Checklist`)

The mechanical obligations the primary worker must satisfy before marking `status: done`:

1. Run automated tests and linters locally.
2. Push feature branch and open a PR targeting the project's base branch.
3. Update the task record: check off met acceptance criteria and cite pinpoint evidence (`file:line`, test command output, PR URL).
4. Release the task as `status: done`.

#### 3. Follow-up QA Task Specification (`## Follow-up QA Task Specification`)

Where QA review is required, the specification directs `/dispatch` on constructing the follow-up task:

- **Title**: `QA: <primary task title>`.
- **Parent**: Same parent as the primary task.
- **Dependency**: `depends_on: [<primary-task-id>]` (hard blocking dependency).
- **Workflow**: Composes the specified QA template (`wf-qa`, `wf-signoff`, or `wf-fact-check`).
- **Goal**: Independently verify the primary task's deliverable against its acceptance criteria in a clean environment.

## Universal Fallback

When a repository contains no `.agents/templates/wf-finish.md`, `/dispatch` falls back to `plugins/ida/skills/workflow-library/workflows/wf-finish.md`.

The universal fallback establishes safe defaults:

- **Base branch**: Repository default branch (`main` or `master`), or `dev` if it exists.
- **Delivery**: Pull request targeting the base branch. Never push directly to default branches.
- **QA policy**:
  - Code, schema, and runtime changes require independent QA via `wf-qa`.
  - Pure documentation, notes, or trivial chore tasks do not mint a QA follow-up unless explicitly requested in the prompt.
- **Completion**: Primary worker runs tests, opens PR with `Task:` trailer, records evidence on acceptance criteria, and marks `done`.
