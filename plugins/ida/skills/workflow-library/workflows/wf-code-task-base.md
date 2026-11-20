---
title: Code task base
type: template
description: Foundation for code-change tasks executed via /supervise (or /pull for plain leaf tasks) -- combines reviewed design, test-first build, incremental push and draft PR, and independent multi-lens review ending in a PR verdict.
tags: [base, task, code, composite]
---

- **GOAL:** <one sentence>
- **ACCEPTANCE CRITERIA:** <one line each, observable outcomes>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <repository and base branch the PR targets>
- **REPORT:** Update the task via `/dump` in place (current state only; tick `[x]` items only with inline primary evidence and citation).

## Single PR, Opened by the Build

- **Combined `/supervise` execution (default)**: Stages 1--4 execute in one container session:
  - _Stage 1 (Design)_: Run design and independent subagent review in-session, recording decisions in a PKB note (no committed plan files or premature PRs).
  - _Stage 2 (Build)_: Implement code and any editable spec change on a constituent worker branch (no code-less spec PRs).
  - _Stages 3--4 (Review & PR)_: Run three-lens diff review on the constituent branch.
    - Merge clean constituent branches into the shared feature branch (`bundle/<slug>` or `feat/<slug>`), close absorbed donor PRs, post `## RBG Review: PASS`, and defer base rebase/combined review until approval; open standalone PRs only for zero-overlap fixes or authorized hotfixes.
- **PR Readiness Check (`--draft` -> `gh pr ready`)**:
  - Green `HEAD` CI (zero errored, bypassed, cancelled, or `startup_failure` runs) and zero unresolved `CHANGES_REQUESTED`.
  - Zero uncommitted `fix(review):` edits (pushed and verified against `HEAD` before posting) and zero deferred DRY, SSoT, or compliance findings.
  - Label-vs-confirmed-route consistency, plus head-SHA-matched posted `## RBG Review: PASS` and proportionate independent review (or constituent receipts + posted description-only `## RBG Review: PASS` pre-approval on consolidated PRs, then combined-diff review post-approval).
- **Split execution** (only for separate repositories, execution windows, external sessions, or `/pull` leaf execution):
  - _Pre-build Stage 1_: Record design, drafted spec change, and independent verdicts in a PKB note linked by the work task (no plan file or PR).
  - _Work task (Stages 2--3)_: Open draft PR (`gh pr create --draft`), record `pr_url` and `branch`, and release **`done`** (never `review`).
  - _Review task (`needs: [<work-task-id>]`)_: Verify PR, bundle or post verdicts, mark ready (`gh pr ready`) once **PR Readiness Check** holds, and release per verdict.
- **No low-risk review bypass**: Every code change and bugfix undergoes independent proportionate review without low-risk exemptions or task-class skipping.

## Stages

1. **Design** (skip for simple bugfixes or mechanical changes; never skip Stage 4 review):
   - State expected behavior, **human user stories** (never `"As an agent..."`), and fit, ending with independent review.
   - Cite or draft the governing spec (or record options in a PKB note) with no committed plan file, code-less PR, or spec-only user pause.
2. **Build**:
   - Read target files in full before editing; keep acceptance criteria observable and bounded to executor delivery (never line slices or post-release user acts).
   - Build executable code **test-first** (red failure traces before implementation, green suite at end); prove non-executable changes with a live check reported in the PR.
3. **Push and Draft PR**: Push checkpoints and open the draft PR (`gh pr create --draft`) when standalone (or land onto the shared feature branch), summarizing what changed and why without line-by-line diff trivia or private PKB/session trailers. Leaf `/pull` workers remain strictly state-only.
4. **Independent Review and Verdict**: Run proportionate independent review by an agent authoring zero branch commits, verify pushed `fix(review):` commits at `HEAD`, and execute one verdict:
   - **Rejected**: Close PR with review comment, mark implementation `cancelled`, release `failed`.
   - **Revisions needed**: Post unmet criteria, leave PR open, release `failed` with root cause; mint no fix tasks.
   - **Handoff after reviewer edits**: Commit/push changes, post them, leave PR open without marking merge-ready, release `partial`.
   - **Reviewed / Ready for Decision**: Post review link and receipts, mark ready (`gh pr ready`), and apply approval/tier rules (`data-boundaries`, repo rules, standing user rulings) before merge -- never release `review`, nor hold in `partial` waiting on user installation once informed.

## Output Contract

- **Combined `/supervise`**: Verified in-session design, draft-then-ready PR carrying build and any spec change, red-before-green test evidence for executable code, green full suite, **PR Readiness Check** satisfied on `HEAD`, review verdicts posted on the PR, `pr_url` recorded, and task released per risk tier.
- **Split tasks**: Stage 1 PKB design/spec note with verdicts (no committed plan/PR); Stages 2--3 draft PR URL with red failure traces and green full suite; Stage 4 posted PR verdicts, **PR Readiness Check** verified on `HEAD`, and carried-out verdict release.

## When to Include

Any task delivering changes to code that executes in a repository as a reviewed PR.
