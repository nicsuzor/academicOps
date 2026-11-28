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
   - _Shared feature branches (`bundle/<slug>` or `feat/<slug>`)_: Gather related work targeting base (never push directly to protected branches).
     - Merge clean constituent branches in after checks and three-lens review, close absorbed donor PRs with a link, verify `## RBG Review: PASS`, and defer rebase and combined-diff review until post-approval.
   - _Standalone PRs & pre-build specs_: Open standalone draft PRs (`gh pr create --draft`) directly against base only for isolated zero-overlap work or authorized hotfixes. Pre-build design/spec tasks persist design, drafted specs, and review verdicts in a PKB note (no committed plan file or PR); the build task commits the spec alongside implementation.
   - _Non-PR deliverables & public hygiene_: Persist artifacts in the PKB or target path (never ephemeral scratch). Strip private PKB IDs and internal task, parent, or session trailers from commits and PRs; state what changed and why without line-by-line diff detail.
3. **Tick acceptance criteria with primary evidence**: In `## Acceptance`, tick `[x]` only with inline primary evidence (`file:line`, test output, PR URL, or artifact pointer); leave unmet items `[ ]` with their limit stated.
4. **Release as `done`**: Run `/dump` and release the task with **`status: "done"`**, recording `pr_url` and `branch` (or PKB artifact pointer):
   - Never release `review`, and never use `partial` to wait on CI, review, merge, or proof the user installed, pulled, or deployed a shipped release once informed (`done` unblocks downstream work at once).
   - Use `partial` strictly when the worker's own acceptance items remain unfinished or hit an approval boundary, and `failed` when checks fail. Mint follow-ups only when work crosses an out-of-session boundary.

## Independent Review and PR Readiness Check

Every code, bugfix, configuration, rule, skill, workflow, and spec deliverable undergoes independent proportionate review (zero low-risk bypass); routine notes or chores complete on the work task alone as `done`.

- **Review topology**: When run in-session, subagent review completes before release (releasing `done`, never `review`). When split onto the graph, mint two tasks under the same parent: (1) the work task (`done` once draft PR or artifact lands) and (2) the review task (`needs: [<work-task-id>]`).
- **PR Readiness Check (`--draft` -> `gh pr ready`)**: Require before marking ready or merging:
  - Green `HEAD` CI (zero errored, bypassed, cancelled, or `startup_failure` runs) and zero unresolved `CHANGES_REQUESTED`.
  - Zero uncommitted reviewer edits (`fix(review):` commits pushed and matched to `HEAD` before verdicts post) and zero deferred DRY/SSoT/compliance findings.
  - Head-SHA-matched posted `## RBG Review: PASS` plus proportionate independent review (for consolidated PRs: constituent diff receipts, green `HEAD` CI, and posted description-only `## RBG Review: PASS` pre-approval, then full combined-diff review after post-approval rebase).
- **Pass (Reviewed / Ready for Decision)**: Post verdicts and receipts to the PR thread (gating external audiences under `data-boundaries`), mark ready (`gh pr ready`) once the **PR Readiness Check** holds on `HEAD`, and apply risk-tier rules:
  - _Tier 1 (Pure documentation, formatting, typing stubs)_: With the **PR Readiness Check** satisfied on `HEAD`, merge autonomously (`gh pr merge --squash`) ONLY where a standing user ruling names the repository and zero external audience exists; otherwise hold for explicit user approval with receipts and recommendation, releasing `done`.
  - _Tier 2 / Tier 3 (Code, workflows, skills, rules, specs, infrastructure, public outputs)_: Post receipts and a reasoned merge recommendation, leave open for sign-off, and release **`done`** (never `review`).
- **Handoff after reviewer edits**: Commit and push reviewer fixes, post changes, leave the PR open without marking merge-ready, and release **`partial`**.
- **Fail (Revisions needed / Rejected)**: Post unmet criteria/findings (close PR if rejected) and release **`failed`** with root cause; reviewers mint no follow-up tasks.
