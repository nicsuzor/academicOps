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

Specifies how tasks in `nicsuzor/academicOps` finish. All individual task changes deliver via PR targeting the designated integration base branch declared in `.agents/CORE.md`. A PR merges on green; functional changes also require independent QA review first. Merging to `main` requires escalated review.

## One PR, opened by the build

- Stage 1 records its design, any drafted spec change, and its independent agent review verdicts in a PKB note the Stage 2 task points to. Stage 1 commits no plan or design file and opens no PR.
- Stage 2 opens the PR into `dev` as a draft, carrying the build and any spec change. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review (`gh pr ready`) only after the proportionate review on the build is posted to the PR thread by independent agents. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Finish Policy

- **Target branch for tasks**: The designated integration base branch declared in `.agents/CORE.md` (`dev`). Individual tasks must not target `main`.
- **Delivery mechanism**: Open a pull request targeting `dev`. When the work is a Stage 1 design or spec preceding a build, the design, drafted spec change, and independent agent review verdicts are recorded in a PKB note the Stage 2 task points to; Stage 1 commits no plan or design file, opens no PR, and never puts a spec to the user for approval on its own. The Stage 2 build opens the PR into `dev` as a draft (`gh pr create --draft --base dev`), carrying the build and any spec change, and marks the PR ready for review (`gh pr ready`) only after proportionate review by independent agents is posted to the PR thread, without waiting for approval. Spec and feature merge together after full review. For standalone single-stage implementation changes, open a standard pull request (`gh pr create --base dev`). PR descriptions focus on what was done and the approach taken, structured as a scannable decision aid; do not enumerate every single change in detail, as the diff is available for that. Follow the repository template at `.github/PULL_REQUEST_TEMPLATE.md`.
- **Merging**: Merge on green after required review and approval. Where QA is required, the verifying agent task reviews the PR and posts verdicts to the PR thread; if verification fails, the verifying task releases `failed` with failure evidence documented on the record and does not file fix tasks or follow-up tasks. A spec or design stage preceding a feature build records on the PKB and opens no PR; the following build opens the only PR carrying any spec change, and both merge together after full review.
- **Releases to main**: A PR from `dev` into `main` merges only on explicit release approval.
- **Commit messages and trailers**: Commits to public repositories must never carry PKB IDs or `Task:`, `Epic:`, or `Claude-Session:` trailers (`data-boundaries`). Task linkage is maintained in the private task record, not in public repository commits.
- **QA review**:
  - **Required**: For any changes touching plugins, hooks, skills, agents, runtimes, or scripts, except for low-risk internal changes below. A review by independent agents is required and a proportionate review is selected, with verdicts posted to the PR thread. `/reify` mints a follow-up verifying task.
  - **Low-risk internal changes (chiefly bugfixes)**: Get no separate verification run. Where a blocked dependent exists waiting on the fix (inbound `depends_on` or `needs` on the dependent task), the parent epic handles sequencing the dependent task's next run; workers never mint verification follow-up tasks.
  - **None**: For pure documentation, notes, or prompt triage changes with no functional impact.

## Worker Completion Checklist

Before marking `status: done`, the worker must:

1. Ensure test suite and linter pass (`uv run pytest`, `uv run ruff check`). For headless worker sessions on isolated containers, run the test suite directly; coordinator sessions must not execute test suites in-session and instead verify against CI/PR checks or delegate testing to a polecat.
2. Push feature branch to remote and open or update the PR: for a Stage 1 design or spec task preceding a build, record the design, drafted spec change, and independent agent review verdicts in a PKB note the Stage 2 task points to, committing no plan or design file and opening no PR; for a Stage 2 build, open the PR into `dev` as a draft (`gh pr create --draft --base dev`) carrying the build and any spec change, and mark the PR ready for review (`gh pr ready`) once proportionate review by independent agents is posted to the PR thread, without waiting for approval; for standalone changes, open a PR targeting `dev`. Write a PR description explaining what was done and the approach taken, following `.github/PULL_REQUEST_TEMPLATE.md`, leaving fine-grained inspection to the diff.
3. Update acceptance criteria on the PKB task: tick an item only with evidence of that item itself; leave any other item unticked with its limit stated, citing pinpoint evidence (`file:line`, command output, PR link).
4. Mark task `status: done` and release claim. Never release as `review`. A worker whose own deliverable is complete releases its task `done`, even when a dependent check (QA, merge, deploy) is still to run; `partial` is only for the worker's own unfinished acceptance items. Workers never create or name follow-up tasks.

## Follow-up QA Task Specification

Where QA is required for standard changes, the verifying agent task runs independently on a clean checkout:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task
- **Depends on**: `[<primary-task-id>]`
- **Workflow**: Composes independent agent verification workflow
- **Goal**: Independently verify PR changes on clean checkout against literal acceptance criteria and post agent review verdicts to the PR thread. If verification fails, the verifying task releases `failed` with failure evidence and root cause documented on the record; it does not file fix tasks.

### Low-risk internal bugfixes (next-run review)

When the task is a low-risk internal change, chiefly a bugfix, mint no separate verification run on the fix task. Where a blocked dependent exists waiting on the fix (inbound `depends_on` or `needs` on the dependent task), the parent epic handles sequencing the dependent task's next run; workers never mint verification follow-up tasks. Where no blocked dependent exists, the fix finishes on its PR without a separate verification run.
