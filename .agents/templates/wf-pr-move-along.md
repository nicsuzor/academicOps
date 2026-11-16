---
alias:
  - wf-pr-move-along
description: academicOps PR move-along workflow -- drives an open PR through checks, proportionate review, feedback resolution, merge conflict resolution, and landing under academicOps feature freeze policy.
id: wf-pr-move-along
tags:
  - wf-template
  - pr
  - move-along
  - aops
title: academicOps PR Move-Along Workflow
type: template
---

## What this template does

Specifies how open pull requests in `nicsuzor/academicOps` are moved along to resolution. Governs check validation, proportionate review, feedback resolution, merge conflict resolution, and landing under the repository's feature freeze and review policy.

**Single-Worker Parallel Fan-Out (Trial)**: A worker executing this workflow may be dispatched with an instruction to coordinate parallel subagents to conduct independent checks or review lenses concurrently. This capability is designated as an empirical trial evaluated on observed run performance.

## Policy and Merge Gates

- **Base branch**: PRs target the designated integration base branch declared in `.agents/CORE.md`. PRs targeting deprecated branches must be retargeted before processing.
- **Merge authority under feature freeze**:
  - Hotfixes: Pull requests explicitly directed by the user as hotfixes merge autonomously to the designated integration base branch once CI checks are green, leaving compliance review to verify alignment with what was asked. Hotfixes proposed autonomously by an agent require confirmation from the front agent that they fit hotfix scope before merging autonomously.
  - Standard features and structural changes: Require explicit approval from the repository owner before merging.
  - Changes requested: A PR with an active "changes requested" review must not merge under any circumstances.
  - Release pull requests (`release-please`): Excluded from autonomous merging; merge only on explicit manual release approval.
- **Pre-approval readiness & consolidated feature branches**: Related changes gather on a shared feature branch (`bundle/<slug>` or `feat/<slug>`) targeting `dev`. Self-contained changes on constituent `polecat/*` branches undergo the three-lens diff review (strategic fit, compliance, quality) and, on `PASS`, are merged directly into the shared feature branch by the agent without waiting for owner approval, immediately closing any superseded donor PR with a link to the consolidated PR. Pre-approval review on a consolidated feature-branch PR is a compliance description-only check (`## RBG Review: PASS`, "is this stupid?") without re-reviewing every line of constituent code and without rebasing onto `dev` before approval (standalone PRs with zero overlap carry the three-lens diff review pre-approval). Ready PRs are presented to the owner one at a time. After owner approval, bring the branch up to date with `dev`, resolve conflicts, run the full three-lens diff review across the combined diff against `dev`, and merge when green.
- **Commit hygiene**: Commits to public repositories must never carry private task, note, or session identifiers, or commit trailers.

## Obligations

1. **Verify Triage, Retargeting, and Consolidation Scope**:
   - Confirm whether the PR is a draft. Draft PRs remain in draft until the independent check passes and required review is posted to the PR thread, at which point the PR is marked ready for review (`gh pr ready`).
   - Confirm the PR is not an excluded release PR.
   - Verify the base branch matches the designated integration base branch declared in `.agents/CORE.md` (`dev`). If targeting another branch, retarget the base branch.

2. **Audit CI Checks and Review (Constituent Diff vs Consolidated Description)**:
   - Query automated checks (`gh pr checks`). All required test, lint, and type check suites must pass cleanly.
   - For a constituent `polecat/*` branch or standalone PR, run the three-lens diff review (strategic fit, compliance, quality) by independent agents. When a constituent branch targeting a shared feature branch (`bundle/<slug>`) passes, merge it directly into `bundle/<slug>` without waiting for owner approval and immediately close any superseded donor PR with a pointer comment to the consolidated PR.
   - For a consolidated feature-branch PR (`bundle/<slug>` -> `dev`) whose constituent branches already passed three-lens diff review, run the compliance description-only check ("is this stupid?") and post `## RBG Review: PASS` to the PR thread without re-reviewing the combined code diff pre-approval.

3. **Resolve Review Feedback and Requested Changes**:
   - Inspect existing review threads and reviews.
   - Review comments and requested changes must be met by concrete diff edits on the PR branch or rejected with reasoned arguments recorded on the PR thread. Once the independent check passes and review verdicts are posted to the PR thread, ensure any draft PR is marked ready for review (`gh pr ready`).
   - If changes requested remain unaddressed or require higher-level architectural decisions, leave the PR open and document the exact blocking feedback as the disposition reason.

4. **Verify Approvals and Pre-Approval Readiness**:
   - Verify whether required approvals are recorded per the merge authority policy.
   - Before owner approval, verify checks are green, required pre-approval review (`## RBG Review: PASS` description check on a consolidated PR, or three-lens diff review on a standalone PR) is posted with feedback addressed, and any absorbed donor PRs are closed. Do not rebase or resolve conflicts before approval; mergeability with `dev` is not required before approval.
   - If the PR is awaiting owner approval, leave the PR open ready for one-at-a-time presentation to the owner.

5. **Post-Approval Rebase, Full Combined-Diff Review, and Landing**:
   - Once required approvals are recorded (or for verified hotfixes where authorized to merge autonomously):
     - Bring the branch up to date with `dev` and resolve any merge conflicts, ensuring tests remain green.
     - For a consolidated feature-branch PR (`bundle/<slug>`) or any PR whose rebase resolved conflicts, run the full three-lens review (strategic fit, compliance, quality) over the complete combined diff against `dev` and post `## Strategic Review: PASS` and `## RBG Review: PASS` on the PR thread.
     - Once the combined-diff review returns `PASS`, all checks are green, required approvals are filed, and zero `CHANGES_REQUESTED` reviews remain, merge the PR into `dev` (`gh pr merge <number> --merge`).
   - If the PR cannot be merged (e.g. active requested changes or unresolved substantive conflicts), leave the PR open with its disposition and reason documented on the record.

## Output contract

- Merged PR on the designated integration base branch, or an open PR with an explicit, substantiated disposition status and reason recorded on the record.

## Must not

- Must not merge any release-please PR.
- Must not merge any PR without required owner approval unless it is a hotfix directed by the user or confirmed by the front agent.
- Must not rebase or resolve merge conflicts on a PR before required approval is recorded.
- Must not merge any PR with failing checks or unresolved changes requested.
- Must not leave an unmerged PR without an explicit stated reason.
