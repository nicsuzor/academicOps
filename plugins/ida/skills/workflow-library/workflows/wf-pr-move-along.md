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
   - For a constituent branch or standalone PR, verify the full three-lens diff review (strategic fit, rule compliance, quality) by independent agents returned `PASS` (coordinating one if missing). When a constituent branch targeting a shared feature branch (`bundle/<slug>` or `feat/<slug>`) passes checks and its three-lens diff review, merge it directly into the shared feature branch without waiting for user approval and immediately close any superseded donor PR with a link to the consolidated PR.
   - For a consolidated feature-branch PR (`bundle/<slug>` -> base) whose constituent branches passed three-lens diff review, pre-approval review is satisfied by a compliance description-only check on the PR title and description posted as `## Compliance Review: PASS` without re-reviewing constituent code before user approval.
   - Resolve open review comments and requested changes via branch commits or substantiated rebuttals on the record, and mark completed drafts ready for review (`gh pr ready`) once independent checks and review verdicts are posted.
3. **Respect the approval boundary**: Before approval, a PR only requires green checks and its required pre-approval review posted (with absorbed donor PRs closed). Present ready PRs to the user one at a time. If required external approval, unmerged dependencies, or substantive revisions remain pending, leave the PR open with the blocking reason recorded. Never rebase or resolve conflicts against base before approval.
4. **Post-approval rebase, combined-diff review, and land**: Once required approvals are recorded (or autonomous merge is authorized), bring the branch up to date with base, resolve any conflicts, run local tests, and push. For a consolidated feature-branch PR (`bundle/<slug>`) or any PR whose rebase resolved conflicts, run the full three-lens diff review over the combined diff against base and post `PASS` verdicts (`## Strategic Review: PASS` and `## Compliance Review: PASS`) before merging via the repository's convention when checks are green and zero `CHANGES_REQUESTED` reviews remain.

## Output contract

- Either the pull request merged into its base branch, or the pull request left open with substantiated blocking status recorded on the PR and task.

## Must not

- Must not merge with failing or pending required checks, unresolved changes-requested reviews, or missing project-required approvals.
- Must not rebase or resolve merge conflicts prior to required approvals.

## When to include

Advancing an active feature or fix pull request toward merge under project governance.
