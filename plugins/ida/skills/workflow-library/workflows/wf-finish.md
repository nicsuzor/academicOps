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

## One PR, opened by the build

- Stage 1 records its design, any drafted spec change, and its independent agent review verdicts in a PKB note the Stage 2 task points to. Stage 1 commits no plan or design file and opens no PR.
- Stage 2 opens the PR into the base branch as a draft, carrying the build and any spec change. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review (`gh pr ready`) only after the proportionate review on the build is posted to the PR thread by independent agents. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

## Finish Policy

- **Target branch**: Common unprotected version or development branch where configured; repository default branch (`main` or `master`) if no intermediate branch exists.
- **Delivery mechanism**: Open a pull request targeting the base branch. When the work is a Stage 1 design or spec preceding a build, the design, drafted spec change, and independent agent review verdicts are recorded in a PKB note the Stage 2 task points to; Stage 1 commits no plan or design file, opens no PR, and never puts a spec to the user for approval on its own. The Stage 2 build opens the PR into the base branch as a draft (`gh pr create --draft`), carrying the build and any spec change, and marks the PR ready for review (`gh pr ready`) only after proportionate review by independent agents is posted to the PR thread, without waiting for approval. For standalone single-stage implementation changes, open a standard pull request. Never push directly to protected default branches. PR descriptions explain what was done and the approach taken to do it, making the PR easy to read and understand without listing every single change in detail (the diff is available for that). Specific PR structure is modular and defers to project-level templates or style conventions where defined. Merge authority is governed by PR risk tier below.
- **Merge authority by PR risk tier**:
  - The QA agent worker independently evaluates PR risk against the three-tier taxonomy (`specs/enforcement/enforcement.md#pr-risk-taxonomy-enforcement`):
  - **Tier 1 (Autonomous QA-Merge)**: Low-risk changes (pure documentation, formatting, typing stubs). A spec or design stage records on the PKB and opens no PR; the following build opens the only PR carrying any spec change, and both merge together after full review. For standalone Tier 1 changes, a fresh QA agent worker independently verifies claims and test suite in a clean context. On a verified pass, the QA agent worker merges the PR autonomously via `gh pr merge --squash` and releases the QA task as `done`.
  - **Tier 2 (Operational Gate)**: Code, workflows, tools, skills, rules, agent definitions, or tests. Reviewer sign-off required; a fresh QA agent worker independently verifies claims, runs tests, and posts receipts to the PR as a structured review comment. The QA worker does not merge, leaving the PR open for reviewer sign-off. The QA task is released as `done` with the PR URL recorded on the task record so `/reconcile` tracks merge without human wait states. No task rests or releases in `review` for a human merge gate.
  - **Tier 3 (Critical Hazard & Public Gate)**: Host infrastructure, credentials, manuscripts, public releases, or high blast radius. Gated on principal review and merge; agents are forbidden from merging. QA agent workers independently verify and post receipts, leaving the PR open, and release the QA task as `done`.
- **Merge**: For verified standalone Tier 1 PRs, QA agent worker merges upon verified pass. For Tier 2 and Tier 3 PRs (and combined spec-and-feature PRs), reviewer sign-off merges the PR; QA agent worker verifies, posts receipts, and leaves the PR open. The primary implementation task releases `done` upon PR filing to unblock QA; when the PR merges, the parent epic progresses.
- **Commit messages and trailers**: Commits to public repositories must never carry PKB IDs or `Task:`, `Epic:`, or `Claude-Session:` trailers (`data-boundaries`). Task linkage is maintained in the private task record, not in public repository commits.
- **QA review**:
  - **Functional changes** (code, schema, or runtime changes): Require independent QA by agents, except for low-risk internal changes below. A review by independent agents is required and a proportionate review is selected. `/reify` mints a follow-up verifying task dependent on the implementation task.
  - **Low-risk internal changes (chiefly bugfixes)**: Get no separate verification run. Where a blocked dependent exists waiting on the fix (prerequisite `needs` on the dependent task), the parent epic handles sequencing the dependent task's next run; workers never mint verification follow-up tasks.
  - **Documentation, notes, or trivial chore changes**: No QA follow-up required unless explicitly requested in the task objective.

## Standard Pre-Handback Review

To prevent recursive loops, token exhaustion, and multi-round churn, deliverables undergo a single, standardized pre-handback review before final handover:

1. **Parallel Dispatch**: The consolidating main agent (sub-ida in interactive sessions, outer agent / coordinator elsewhere) dispatches **Marsha** and **RBG** concurrently in a single turn.
2. **Self-Contained Briefing**: Both reviewers receive a self-contained brief containing:
   - The originating user ask and task objective.
   - The candidate output artifact (or live rendered reference).
   - Governing genre standards (for Marsha) and applicable rules / itemised criteria (for RBG).
   - Intended audience and purpose.
   - Reviewers do not receive tools to re-query external sources or re-find facts.
3. **Single Synthesis**: The main agent receives both independent reports, reconciles findings into a single plan, and authorizes necessary fixes.
4. **One Fix Pass, No Re-Check Loop**: The writer executes a single fix pass addressing substantive findings. There is no second review round, no re-checking loop, and no fresh cold checker spawned. Good enough is the bar; the handback proceeds immediately following the single fix pass.
5. **Opt-In Boundaries**: Independent runtime test verification (`wf-qa`) and granular citation checking (`wf-fact-check`) remain explicit opt-ins triggered only when calibrated by risk or requested by workflow composition.

## Worker Completion Checklist

The implementation worker satisfies these obligations, then exits:

1. Verify automated tests and linter pass locally.
2. Push feature branch to remote and open or update the pull request: for a Stage 1 design or spec task preceding a build, record the design, drafted spec change, and independent agent review verdicts in a PKB note the Stage 2 task points to, committing no plan or design file and opening no PR; for a Stage 2 build, open the PR into the base branch as a draft (`gh pr create --draft`) carrying the build and any spec change, and mark the PR ready for review (`gh pr ready`) once proportionate review by independent agents is posted to the PR thread, without waiting for approval; for standalone changes, open a standard pull request targeting the project's base branch. PR descriptions explain what was done and the approach taken, following project PR conventions or templates.
3. Conduct the single standard pre-handback review (Marsha + RBG in parallel, one fix pass, no loop) per the procedure above.
4. Update the task record: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. Record verifiable evidence with pinpoint citations (`file:line`, test command output, PR URL).
5. Release the task as `done` via `pkb_release_task`, with the PR URL in `pr_url` and branch recorded on the task record (for Stage 1 tasks, record the PKB note pointer). For a Stage 1 spec or design task whose independent agent review passed, releasing `done` allows Stage 2 to begin. Do not release as `review`. Releasing `done` unblocks the downstream QA or review follow-up task on the graph. Do not wait for CI, review or merge. `partial` is reserved strictly for the worker's own unfinished acceptance items. Workers never create or name follow-up tasks. Dispatched workers operate strictly under the worker state-only invariant: mutate only this task's own record and state, never inspect or modify edges across other tasks or mint follow-up verification tasks.

## Follow-up QA Task Specification

When QA review is required for standard functional changes, `/reify` mints a follow-up task with:

- **Title**: `QA: <primary task title>`
- **Parent**: Same parent as primary task (or `part_of` edge per FQ1)
- **Needs**: `[<primary-task-id>]` (hard blocking dependency)
- **Workflow**: Composes independent verification workflow
- **Goal**: Independently verify the deliverable and claims against literal acceptance criteria in a clean context. If verification fails, the QA task releases `failed` with failure evidence documented on the record; reviewers do not file fix tasks or follow-up tasks. On a verified pass, evaluate tier membership against the taxonomy: for verified Tier 1 PRs with low-risk changes, merge to base branch autonomously via `gh pr merge --squash` and release as `done`; for Tier 2 and Tier 3 PRs, post verification receipts to the PR and leave open for reviewer sign-off without releasing to review; release as `done` with receipts and PR URL on record. A reviewer that changes code delivers it through this finish template and hands off for independent review.

### Low-risk internal bugfixes (next-run review)

When the task is a low-risk internal change, chiefly a bugfix, mint no separate verification run on the fix task. Where a blocked dependent exists waiting on the fix (prerequisite `needs` on the dependent task), the parent epic handles sequencing the dependent task's next run; workers never mint verification follow-up tasks. Where no blocked dependent exists, the fix finishes on its PR without a separate verification run.
