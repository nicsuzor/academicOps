---
alias:
  - wf-finish
default: true
description: Default task completion workflow -- defines how a work task completes and releases as done, and how independent review executes in-session or as a downstream review task under the PR Readiness Check.
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

Defines the default completion and release contract (`done` on the work task) plus the independent review contract across PR and non-PR deliverables.

## Work Task Completion and Single Release Status

Every completed work task has **one completion release status: `done`**:

1. **Verify locally**: Run required automated tests, linters, and build checks (or fresh-agent execution proof for instruction changes).
2. **Package and deliver where `OUTPUT` names**:
   - **Pull request deliverables**: Related work (tasks under a composite parent task, tasks touching shared surfaces, or PR consolidation batches) gathers on a shared feature branch (`bundle/<slug>` or `feat/<slug>`) targeting the repository's configured development, version, or default branch (never push directly to protected branches). When a constituent branch passes local checks and the three-lens diff review (strategic fit, rule compliance, quality), merge it directly into `bundle/<slug>` without waiting for user approval, open or update the consolidated PR into the base branch, and immediately close any superseded standalone donor PR with a link to the consolidated PR. Pre-approval review on a consolidated PR is a compliance description-only check (`## Compliance Review: PASS`) without re-reviewing constituent code or pre-approval rebase; post-approval landing rebases onto the base branch and runs the full three-lens diff review on the combined diff before merging. Open a standalone per-task PR into the base branch only for isolated zero-overlap changes or authorized hotfixes. Pre-build design or spec tasks record design, drafted spec changes, and review verdicts in a PKB note with no committed plan file or PR; the subsequent build task commits the spec change alongside the build.
   - **Non-PR deliverables**: Persist in the PKB or designated target path (never ephemeral container scratch paths).
   - **Clean public metadata**: Strip private PKB IDs and internal task, parent, or session trailers from public repository commits and PR descriptions; explain what changed and the approach without line-by-line diff detail.
3. **Tick acceptance criteria with primary evidence**: In `## Acceptance`, tick `[x]` only with inline primary evidence (`file:line`, test output, PR URL, or artifact pointer); leave unmet items `[ ]` with their limit stated.
4. **Release as `done`**: Run `/dump` and release the task with **`status: "done"`**, recording `pr_url` and `branch` (or PKB artifact pointer). Never release `review`, and never use `partial` to wait on CI, review, merge, or proof that the user installed, pulled, or deployed a shipped release once informed -- `done` unblocks downstream dependencies immediately. Use `partial` strictly when the worker's own acceptance items are incomplete or halted at a pre-work approval boundary, and `failed` when checks or execution fail. Leaf `/pull` workers mutate only their claimed task and never mint follow-up tasks.

## Independent Review and PR Readiness Check

All code, bugfix, configuration, rule, skill, workflow, and specification deliverables undergo independent proportionate review (zero low-risk bugfix exemption or task-class skipping). Routine notes or trivial chores complete on the work task alone as `done`. When reified separately, split reviewed work into two tasks under the same parent: (1) the work task (`done` once draft PR or artifact is recorded) and (2) the review task (`needs: [<work-task-id>]`), which runs independent proportionate review. Under `/supervise`, subagent review runs inside the combined container session (still releasing `done`, never `review`).

- **PR Readiness Check (`--draft` -> `gh pr ready`)**: Before marking a draft PR ready or executing a Tier-1 autonomous merge, require green `HEAD` CI (zero errored, bypassed, cancelled, or `startup_failure` runs), zero unresolved `CHANGES_REQUESTED`, zero uncommitted reviewer edits (`fix(review):` commits pushed and verified against `HEAD` before posting verdicts), zero deferred DRY/SSoT/compliance findings, and head-SHA-matched posted `## Compliance Review: PASS` plus proportionate independent review (for consolidated feature-branch PRs: constituent diff receipts, green `HEAD` CI, and head-SHA-matched posted description-only `## Compliance Review: PASS` pre-approval, then full combined-diff review after post-approval rebase).
- **Pass (Reviewed / Ready for Decision)**: Post review verdicts and verification receipts to the PR thread (respecting `data-boundaries` on external-audience surfaces), mark ready (`gh pr ready`) once the **PR Readiness Check** holds on `HEAD`, and apply risk-tier rules:
  - **Tier 1 (Low-risk pure documentation, formatting, typing stubs)**: With the **PR Readiness Check** satisfied on `HEAD`, merge autonomously (`gh pr merge --squash`) ONLY where a standing user ruling explicitly names the repository and no external audience exists; otherwise stop for explicit user approval with receipts and a reasoned recommendation. Release the review task as **`done`**.
  - **Tier 2 / Tier 3 (Code, workflows, skills, rules, specs, infrastructure, or public outputs)**: Post receipts and a reasoned merge recommendation, leave the PR open for sign-off, and release the review task as **`done`** (never `review`). Graph maintenance updates the tracking parent task once merged.
- **Handoff after reviewer edits**: If the reviewer pushed fixes, commit and push them, post the changes, leave the PR open without marking merge-ready, and release **`partial`**.
- **Fail (Revisions needed / Rejected)**: Post unmet criteria/findings (close PR if rejected) and release **`failed`** with root cause; reviewers never mint follow-up tasks.
