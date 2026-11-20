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
  - Stage 1 runs design and independent subagent review in-session, recording decisions in a PKB note (no committed plan files or premature PRs).
  - Stage 2 implements the build and any editable spec change on its constituent worker branch (no code-less spec PRs).
  - Stages 3--4 run the three-lens diff review (strategic fit, rule compliance, quality) on the constituent branch. On `PASS`, when related work shares a feature branch (`bundle/<slug>` or `feat/<slug>`), merge directly into the shared feature branch without waiting for user approval, close any superseded standalone donor PR with a link to the consolidated PR, open/update the consolidated PR into the base branch, run a compliance description-only check on the consolidated PR, and mark it ready (`gh pr ready`) without pre-approval rebase. After user approval, rebase onto the base branch, run the full three-lens diff review over the combined diff, and merge when green. Isolated zero-overlap changes or authorized hotfixes post the three-lens diff review to a standalone PR before marking it ready (`gh pr ready`).
- **Split execution** (only when explicitly required for a separate repository, execution window, or external session, or under `/pull` leaf execution):
  - Pre-build Stage 1 (if applicable): records design, drafted spec change, and independent review verdicts in a PKB note linked by the work task; commits no plan file and opens no PR.
  - Work task (Stages 2--3): opens the draft PR (`gh pr create --draft`), records `pr_url` and `branch`, and releases **`done`** (never `review`).
  - Review task (Stage 4, `needs: [<work-task-id>]`): runs independent review, merges into the shared feature branch or posts verdicts to the PR thread, marks ready (`gh pr ready`) on pass, and releases `done`, `partial`, or `failed` per the verdict.
- **Low-risk bugfix exception**: Omit separate Stage 4 verification on a low-risk internal bugfix; any `needs`-blocked dependent is sequenced by the composite parent task without workers minting follow-up tasks.

## Stages

1. **Design** (skip for simple bugfixes or mechanical changes): State expected behavior, **human user stories** (never "As an agent/worker..."), and project fit, ending with independent review. Where the project keeps specs, cite the governing spec or draft and independently review the spec first; otherwise record alternatives, choice, and fit in a PKB note. Commit no plan file, open no code-less spec PR, and never pause for spec-only user approval.
2. **Build**: Read target files in full before editing. Acceptance criteria define observable outcomes bounded to what the executor delivers (ending once shipped and reported) rather than mechanism prescriptions, `file:line` edits, or post-release user acts. Build executable code changes **test-first** (capture each failing test before implementation, full suite green at end); non-executable changes add no tests and are proved by a run or check reported in the PR.
3. **Push and Draft PR**: Push incremental checkpoints and open the draft PR (`gh pr create --draft`) when standalone (or prepare for consolidated feature-branch landing), explaining what changed and the approach taken (omit line-by-line diff detail, follow project PR templates, and strip private PKB/session trailers). Leaf `/pull` workers remain strictly state-only.
4. **Independent Review and Verdict**: Run proportionate independent review (defaulting to dialectical review or caller-chosen substitute) by an agent that did not write the code, fix trivial defects in place if warranted, and execute exactly one verdict:
   - **Rejected** (wrong approach or disproportionate): Close PR with review comment, mark implementation `cancelled`, release `failed`.
   - **Revisions needed** (criteria unmet beyond in-place fixes): Post review citing unmet criteria, leave PR open, release `failed` with root cause; mint no fix tasks.
   - **Handoff after reviewer edits** (reviewer pushed code): Post review and changes, leave PR open without marking merge-ready, release `partial`.
   - **Reviewed / Ready for Decision** (clean review, no reviewer edits, green checks): Post review link and CI receipts, mark PR ready (`gh pr ready`), and follow standard tier/approval rules before any merge (rebase/conflict resolution and combined-diff review happen post-approval, just before merge; never release `review`, and never hold in `partial` or mint follow-up tasks waiting to prove the user installed, pulled, or deployed a shipped release once informed).

## Output Contract

- **Combined `/supervise`**: Verified in-session design, draft-then-ready PR carrying build and any spec change, red-before-green test evidence for executable code, green full suite, review verdicts posted on the PR, `pr_url` recorded, and task released per risk tier.
- **Split tasks**: Stage 1 PKB design/spec note with verdicts (no committed plan/PR); Stages 2--3 draft PR URL with red failure traces and green full suite; Stage 4 posted PR verdicts and carried-out verdict release.

## When to Include

Any task delivering changes to code that executes in a repository as a reviewed PR.
