---
description: Drives an individual open pull request through CI checks, proportionate review, feedback resolution, merge conflict settlement, and landing under the project-override model.
tags:
  - wf-template
  - pr
  - lifecycle
  - review
title: PR Move-Along Workflow
type: template
---

## What this template does

Drives an individual open pull request through its progression lifecycle: confirming passing checks, securing a proportionate review, addressing review feedback, settling merge conflicts against the base branch, and executing or staging the merge according to project-local merge rules.

A worker executing this workflow may coordinate parallel subagents to conduct independent checks or review lenses concurrently.

## Input contract

- An open pull request identifier or URL.
- Repository git access and platform CLI (`gh`).
- Project rules and merge policy (from repository project rules or local templates).

## Obligations

1. **Resolve Project Merge Policy**:
   - Inspect the target repository for project-local PR rules, branch policies, or local finish templates.
   - The project's own policy strictly overrides universal defaults:
     - Target base branch is defined by project rules.
     - Merge authority (such as autonomous merge on green, human sign-off gate, or release cut approval) is determined by project policy.
     - When no project override exists, fallback to standard risk-tier governance: low-risk changes merge on independent verification; operational or high-risk changes require reviewer sign-off.

2. **Audit CI Checks and Proportionate Review**:
   - Query CI pipeline status on the latest head commit. All required checks must pass cleanly.
   - Verify that a review proportionate to the PR's blast radius and risk tier has been posted to the pull request thread.
   - If the PR lacks a proportionate review on its thread, coordinate a fresh independent review and post findings to the thread before advancing. Under no circumstances may a pull request be transitioned to ready or left in an awaiting-approval disposition without an agent-generated review present on the pull request thread.

3. **Address Review Feedback and Requested Changes**:
   - Inspect open review threads, comments, and review states.
   - Review comments and requested changes must be met by diff modifications on the feature branch or answered with substantiated rebuttals on the record.
   - A pull request with unresolved requested changes must not merge.

4. **Settle Merge Conflicts and Verify Clean State**:
   - Query mergeability state against the base branch.
   - When merge conflicts exist, update the feature branch by rebasing or merging the latest base branch, resolving conflicts, running local tests, and pushing the resolved head.

5. **Evaluate Merge Gate and Land**:
   - Check whether all merge prerequisites are met: green checks, satisfied review obligations, resolved feedback, and required approvals per project policy.
   - If authorized to merge, execute the merge following repository merge conventions (merge commit, rebase, or squash).
   - If the PR is gated on external human approval, verify that the proportionate review is already posted to the PR thread, convert from draft to ready (`gh pr ready`) if applicable, leave the PR open, and record an explicit disposition reason. Never classify or leave a PR as awaiting approval without a posted review.

## Output contract

- The pull request merged into its base branch, or left open with an explicit, substantiated status and blocking reason recorded.

## Must not

- Must not merge a pull request with failing or pending required checks.
- Must not merge a pull request with an active changes-requested review.
- Must not bypass project-specific merge gates or approval requirements.
- Must not classify or leave a pull request as awaiting approval without a proportionate review posted to the PR thread.
- Must not leave an unmerged pull request without a documented, checkable reason.
