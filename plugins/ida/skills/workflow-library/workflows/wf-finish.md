---
alias:
  - wf-finish
default: true
description: Default task completion workflow -- defines how a work task completes and releases as done, and how an optional review step on a reviewed class of task separates work and review deliverables.
id: wf-finish
tags:
  - wf-template
  - finish
  - lifecycle
  - default
title: Default Task Completion Template
type: template
---

## What this template does

Defines the default completion and release contract (`done` on the work task) plus the optional independent review contract for reviewed task classes.

## Work Task Completion and Single Release Status

Every completed work task has **one completion release status: `done`**:

1. **Verify locally**: Run required automated tests, linters, and build checks (or fresh-agent execution proof for instruction changes).
2. **Package and deliver where `OUTPUT` names**:
   - **Pull request deliverables**: Related work (tasks under a composite parent task, tasks touching shared surfaces, or PR consolidation batches) gathers on a shared feature branch (`bundle/<slug>` or `feat/<slug>`) targeting the repository's configured development, version, or default branch (never push directly to protected branches). When a constituent branch passes local checks and the three-lens diff review (strategic fit, rule compliance, quality), merge it directly into `bundle/<slug>` without waiting for user approval, open or update the consolidated PR into the base branch, and immediately close any superseded standalone donor PR with a link to the consolidated PR. Pre-approval review on a consolidated PR is a compliance description-only check (`## Compliance Review: PASS`) without re-reviewing constituent code or pre-approval rebase; post-approval landing rebases onto the base branch and runs the full three-lens diff review on the combined diff before merging. Open a standalone per-task PR into the base branch only for isolated zero-overlap changes or authorized hotfixes. Pre-build design or spec tasks record design, drafted spec changes, and review verdicts in a PKB note with no committed plan file or PR; the subsequent build task commits the spec change alongside the build.
   - **Non-PR deliverables**: Persist in the PKB or designated target path (never ephemeral container scratch paths).
   - **Clean public metadata**: Strip private PKB IDs and internal task, parent, or session trailers from public repository commits and PR descriptions; explain what changed and the approach without line-by-line diff detail.
3. **Tick acceptance criteria with primary evidence**: In `## Acceptance`, tick `[x]` only with inline primary evidence (`file:line`, test output, PR URL, or artifact pointer); leave unmet items `[ ]` with their limit stated.
4. **Release as `done`**: Run `/dump` and release the task with **`status: "done"`**, recording `pr_url` and `branch` (or PKB artifact pointer). Never release `review`, and never use `partial` to wait on CI, review, merge, or proof that the user installed, pulled, or deployed a shipped release once informed -- `done` unblocks downstream dependencies immediately. Use `partial` strictly when the worker's own acceptance items are incomplete or halted at a pre-work approval boundary, and `failed` when checks or execution fail. Leaf `/pull` workers mutate only their claimed task and never mint follow-up tasks.

## Optional Review Process

Review depends on the task class:

- **Unreviewed classes** (routine docs, notes, chores, low-risk internal bugfixes): Complete on the work task alone and release `done` with no review task; the composite parent task sequences any `needs`-blocked dependents.
- **Reviewed classes** (functional code, schemas, workflows, rules, specs): When reified separately, split into two tasks under the same parent: (1) the work task (`done` once draft PR or artifact is recorded) and (2) the review task (`needs: [<work-task-id>]`), which runs an independent proportionate review. Under `/supervise`, subagent review may run inside the combined container session (still releasing `done`, never `review`).
  - **Pass (Reviewed / Ready for Decision)**: Post review verdicts and verification receipts to the PR thread, mark ready (`gh pr ready`), and apply risk-tier rules:
    - **Tier 1 (Low-risk pure documentation, formatting, typing stubs)**: Merge autonomously (`gh pr merge --squash`) ONLY where a standing user ruling explicitly names the repository and no external audience exists; otherwise stop for explicit user approval with receipts and a reasoned recommendation. Release the review task as **`done`**.
    - **Tier 2 / Tier 3 (Code, workflows, skills, rules, specs, infrastructure, or public outputs)**: Post receipts and a reasoned merge recommendation, leave the PR open for sign-off, and release the review task as **`done`** (never `review`). Graph maintenance updates the tracking parent task once merged.
  - **Handoff after reviewer edits**: If the reviewer pushed fixes, post the changes, leave the PR open without marking merge-ready, and release **`partial`**.
  - **Fail (Revisions needed / Rejected)**: Post unmet criteria/findings (close PR if rejected) and release **`failed`** with root cause; reviewers never mint follow-up tasks.
