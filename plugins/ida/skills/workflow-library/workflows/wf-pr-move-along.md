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
- Project merge rules, target base branch, and risk-tier policy (or fallback defaults).

## Obligations

1. **Resolve project merge policy**: Inspect the repository for local PR rules, branch conventions, and merge authority (autonomous merge on green vs. user or maintainer sign-off). Project rules strictly override defaults; where none exist, merge low-risk changes after independent verification and require reviewer sign-off for operational or high-risk changes.
2. **Ensure pre-approval readiness**:
   - Confirm all required CI checks pass on the latest head commit.
   - Verify a proportionate independent review is posted to the PR thread (running independent review lenses concurrently where multiple checks apply); if missing, coordinate an independent review and post verdicts before advancing.
   - Resolve open review comments and requested changes via branch commits or substantiated rebuttals on the record.
   - Transition a completed draft PR to ready for review once independent checks pass and review verdicts are posted, without waiting for merge approval.
3. **Respect the approval boundary**: If required external approval, unmerged dependencies, or substantive author revisions remain pending, leave the PR open and record the blocking reason. Never rebase or resolve merge conflicts before required approvals are recorded.
4. **Settle conflicts and land**: Once required approvals are recorded (or autonomous merge is authorized), check mergeability against the target base branch. If behind or conflicted, update from base, resolve conflicts, run tests, and push; then merge using the repository's convention (merge commit, rebase, or squash).

## Output contract

- Either the pull request merged into its base branch, or the pull request left open with substantiated blocking status recorded on the PR and task.

## Must not

- Must not merge with failing or pending required checks, unresolved changes-requested reviews, or missing project-required approvals.
- Must not rebase or resolve merge conflicts prior to required approvals.

## When to include

Advancing an active feature or fix pull request toward merge under project governance.
