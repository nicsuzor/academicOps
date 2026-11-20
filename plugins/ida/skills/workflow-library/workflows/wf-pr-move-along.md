---
description: Drive an open pull request through CI checks, proportionate independent review, feedback resolution, post-approval conflict settlement, and landing under project merge rules.
tags:
  - wf-template
  - pr
  - lifecycle
  - review
title: PR Move-Along Workflow
type: template
---

## What this template does

Progresses an individual open pull request through verification, independent review, feedback resolution, post-approval conflict settlement against its base branch, and merge under repository-specific governance.

## Input contract

- An open pull request identifier or URL with repository and git-hosting access.
- Project merge rules, target base branch, risk-tier policy, and any standing user ruling covering the repository.

## Obligations

1. **Resolve project merge policy**: Inspect repository PR rules, branch conventions, and standing user rulings covering merge authority.
   - Project rules and constitutional boundaries govern strictly; never merge into a base branch without an explicit standing user ruling naming the repository and zero external audience (`data-boundaries`, `exercise-authority` Exceptions 1-2).
   - Where no standing ruling authorizes autonomous merge, hold for explicit user approval with verification receipts and a reasoned recommendation.
2. **Ensure pre-approval readiness**:
   - Confirm all required CI checks pass on the latest head commit.
   - _Constituent PRs_: Verify independent three-lens diff review (`PASS`, coordinating one if missing). When clean against checks and review, merge constituent branches targeting `bundle/<slug>` or `feat/<slug>` directly without waiting for approval and close any superseded donor PR with a link to the consolidated PR.
   - _Standalone PRs_: Verify full three-lens diff review (`PASS`), resolve open review feedback via branch commits or substantiated rebuttals on the record, and mark completed drafts ready (`gh pr ready`) once CI checks and verdicts post.
   - _Consolidated feature-branch PRs_: When constituent branches passed three-lens diff review, pre-approval review on `bundle/<slug>` is satisfied by a compliance description-only check posted as `## RBG Review: PASS` without re-reviewing constituent code before approval.
   - Resolve open feedback via branch commits or substantiated rebuttals, and mark completed drafts ready (`gh pr ready`) once CI and review verdicts are posted.
3. **Respect the approval boundary**: Present ready PRs to the user one at a time with green checks, posted review verdicts, and closed donor PRs. If required external approval, unmerged dependencies, or revisions remain pending, leave the PR open with the blocking reason recorded; never rebase or resolve base-branch conflicts before approval.
4. **Post-approval rebase, combined-diff review, and land**:
   - Once required approvals are recorded (or autonomous merge is explicitly authorized by a standing user ruling), rebase onto base, resolve conflicts, run local tests, and push.
   - For consolidated PRs or PRs with resolved conflicts, run the full three-lens diff review over the combined diff against base and post `## Strategic Review: PASS`, `## RBG Review: PASS`, and quality/verification `PASS` before merging with green CI and zero `CHANGES_REQUESTED`.

## Output contract

- Either the pull request merged into its base branch, or the pull request left open with substantiated blocking status recorded on the PR and task.

## Must not

- Must not merge with failing or pending required checks, unresolved changes-requested reviews, or missing project-required approvals.
- Must not rebase or resolve merge conflicts prior to required approvals.

## When to include

Advancing an active feature or fix pull request toward merge under project governance.
