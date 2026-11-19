---
title: Code task base
type: template
description: Foundation for code-change tasks executed via /ida:supervise (or /ida:pull for plain leaf tasks) -- by default in a single supervised container session combining reviewed design, test-first build, incremental push and draft PR, and partitioned independent multi-lens review ending in a verdict posted on the PR.
tags: [base, task, code, composite]
---

- **GOAL:** <one sentence>
- **ACCEPTANCE CRITERIA:** <one line each>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <repository and base branch the PR targets>
- **REPORT:** Use /ida:dump to update your task. Do not append your observations as a log; update the prose to reflect current state and delete any content that is no longer relevant, true, or that reflects prior state or prior instructions. Update the ACCEPTANCE CRITERIA block: an item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated. On the same line, provide a relevant extract of your evidence supporting your assertion, along with a citation for the source of the evidence.

## One PR, opened by the build

- Under container supervision (`/supervise`), Stages 1--4 execute by default within a single combined repo-scoped task in one container session:
  - Stage 1 conducts design and subagent dialectical review in-session (recording in a PKB note or design record without committing plan files or opening premature PRs).
  - Stage 2 opens the PR into the repository's configured base branch as a draft (`gh pr create --draft`) -- or pushes to the shared epic/bundle branch when `bundle_pr: true` or project consolidation rules apply -- carrying the build and any spec change. The spec stays editable on that branch as the build teaches more.
  - Stage 3/4 marks the PR ready (`gh pr ready`) only once the **Partitioned PR Gate** passes (approval comes after readiness, so spec and feature merge together).
- **Partitioned PR Gate (`--draft` -> `gh pr ready`)**:
  - Green `HEAD` CI (zero errored, bypassed, cancelled, or `startup_failure` runs) and zero open `CHANGES_REQUESTED`.
  - Zero uncommitted reviewer edits (`fix(review):` commits pushed before posting) and zero deferred DRY/SSoT/compliance findings.
  - Label-vs-confirmed-route consistency, plus head-SHA-matched **posted** `## RBG Review: PASS` and proportionate dialectical review (for consolidated feature-branch PRs under project consolidation rules: constituent diff receipts, green `HEAD` CI, and head-SHA-matched posted description-only `## RBG Review: PASS` pre-approval, then full combined-diff review after post-approval rebase).
- When split onto the task graph across separate tasks (under `/pull` leaf execution or when explicitly split for a separate review session), splitting yields two tasks under the parent container: **(1) the work task** (Stages 2--3, opening the draft PR via `gh pr create --draft`, recording `pr_url` and `branch`, and releasing **`done`**, never `review`) and **(2) the review task** (Stage 4, `needs: [<work-task-id>]`, running independent review, verifying the partitioned PR gate, posting verdicts, marking ready via `gh pr ready`, and releasing `done` on pass or `failed` on fail). Where a separate pre-build Stage 1 design task precedes the build, it records its design, drafted spec change, and review verdicts in a PKB note that the work task points to, committing no plan file and opening no PR.

## Stages

Under container supervision (`/supervise`), Stages 1--4 execute by default within a single combined repo-scoped task in one session, coordinating subagent fan-out and incremental git push checkpoints. When split across separate tasks (permitted only when explicitly requiring a different repository, different time, or separate external agent/session, or under `/pull` leaf execution), each stage operates within its assigned task boundaries.

1. **Design** -- for any change needing judgment among alternative implementations; a simple bugfix or mechanical change may skip design (never Stage 4 review). State how the feature works, human user stories (never agent-as-user stories), and project fit, ending in an independent check:
   - **The project keeps specs**: cite the governing spec or draft/review the spec first in a PKB note (under `/supervise` verified in-session; when split, Stage 1 commits no plan file, opens no PR, and never puts a spec alone to the user).
   - **The project keeps no specs**: record alternatives, choice, and project fit checked by another agent in a PKB task or note; commit no plan file and open no PR.
2. **Build** -- implement observable acceptance criteria (no `file:line` prescriptions), reading target files in full before editing. Carry the build and any spec change onto the feature branch (or shared epic/bundle branch per project consolidation rules) and open the PR as a draft (`gh pr create --draft`). Build changes to executable code test-first (failing test captured before code); prove non-executable changes via a check reported in the PR.
3. **Push and file the PR** -- push incremental checkpoints and open the draft PR (`gh pr create --draft`). Describe what was done and the approach taken without listing line-by-line diff details or private PKB/session identifiers or internal trailers. Plain `/pull` leaf workers mutate only their claimed task's own record and never mint follow-up tasks. Mark ready (`gh pr ready`) only once the partitioned PR gate passes.
4. **Review and verdict** -- required for every code change and bugfix, executed by independent agent(s) who authored zero commits on the branch (in-session under `/supervise`, or via Stage 4 under `/pull` split execution). Push any uncontroversial `fix(review):` commits before posting verdicts, post verdicts with distinct lens headers to the PR thread (respecting `data-boundaries` on external-audience surfaces), and reach one verdict:
   - **Rejected** -- wrong approach or disproportionate work: close the PR with the review as closing comment and release as `failed` with root cause documented (never mutate sibling tasks from a leaf `/pull` worker).
   - **Revisions needed** -- unmet criteria or substantive changes needed: post findings and unmet criteria to the PR, leave open, and release as `failed` with root cause documented (never mint follow-up tasks).
   - **Handoff for review** -- reviewer pushed code fixes: commit and push changes, post review and changes, leave open without marking merge-ready, and release as `partial`.
   - **Reviewed / Ready for Decision** -- all **Partitioned PR Gate** checks hold against `HEAD`: mark ready (`gh pr ready`). Defer merge authority to project rules, standing user authorization, and `data-boundaries`: merge autonomously only where project rules explicitly permit autonomous merge for the PR's risk level (settling post-approval conflicts against base first); otherwise post receipts and a reasoned merge recommendation, leave open for approval, and release as `done` (never `review`).

## Composition

Under container supervision (`/supervise`), multi-stage code workflows execute by default as one combined repo-scoped task (Stages 1--4 in-session). All code changes and bugfixes undergo independent proportionate review with no low-risk bugfix exemption and no hard-coded task-class skipping. Splitting into separate tasks is permitted ONLY when workflow contracts or execution constraints explicitly require:

1. _Different repository_: strictly one task per repository.
2. _Different time_: a distinct external wait condition or execution window.
3. _Different agent/session_: a workflow-mandated separate external agent or session (including Stage 4 independent review `needs: [<work-task-id>]` or closed-loop user-channel reporting).

Steps never sit as loose siblings under an external parent. Plain `/pull` leaf workers operate strictly state-only on their claimed task and never mint follow-up tasks.

## Output contract

- Combined `/supervise` task (default): verified design, draft PR opened into base (or commits pushed to shared epic/bundle branch), test-first evidence and green suite, **Partitioned PR Gate** satisfied, PR marked ready (`gh pr ready`), `pr_url` recorded, and task released per project merge policy.
- Split tasks (when explicitly required): Stage 1 PKB design/spec note (no PR/plan commit); Stage 2--3 draft PR with test/check evidence and `done` release; Stage 4 posted verdicts, partitioned gate verified, `gh pr ready` + project-policy merge or open-for-approval recommendation (`done`), or `failed`/`partial` on rejection/edits without minting follow-up tasks.

## When to include

Any task whose deliverable changes code in a repository and should arrive as a reviewed PR.
