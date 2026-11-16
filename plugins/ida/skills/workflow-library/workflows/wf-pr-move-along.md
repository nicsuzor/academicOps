---
description: Drives an individual open pull request through CI checks, proportionate review, feedback resolution, and post-approval merge conflict settlement and landing under the project-override model.
tags:
  - wf-template
  - pr
  - lifecycle
  - review
title: PR Move-Along Workflow
type: template
---

## What this template does

Drives an individual open pull request through its progression lifecycle: confirming passing checks, securing a proportionate review, addressing review feedback, settling merge conflicts against the base branch post-approval, and executing or staging the merge according to project-local merge rules.

**Review lenses**: Conduct required independent checks or review lenses concurrently.

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
     - Pre-approval readiness: Before approval, a PR must be green and reviewed by independent agents; mergeability against the base branch is not required before approval. A worker PR opens as a draft (`gh pr create --draft`) and is marked ready for review (`gh pr ready`) only after the independent check passes and proportionate review by independent agents is posted to the PR thread, without waiting for approval.

2. **Audit CI Checks and Proportionate Review**:
   - Query CI pipeline status on the latest head commit. All required checks must pass cleanly.
   - For a constituent branch (`polecat/<slug>`) or standalone pull request, verify that the full three-lens diff review (strategic fit, rule compliance, and quality) by independent agents has returned `PASS`. When a constituent branch targeting a shared feature branch (`bundle/<slug>` or `feat/<slug>`) passes its three-lens diff review and checks, merge it directly into the shared feature branch without waiting for user approval and immediately close any superseded donor PR with a comment linking to the consolidated PR.
   - For a consolidated feature-branch pull request (`bundle/<slug>` -> base) whose constituent branches already passed three-lens diff review, pre-approval review is satisfied by the rule-compliance reviewer running a description-only check ("is this stupid?") on the consolidated PR title and description and posting `## RBG Review: PASS` to the PR thread, without re-reviewing every line of constituent code before user approval.

3. **Address Review Feedback and Requested Changes**:
   - Inspect open review threads, comments, and review states.
   - Review comments and requested changes must be met by diff modifications on the feature branch or answered with substantiated rebuttals on the record. Once the independent check passes and review verdicts are posted to the PR thread, ensure any draft PR is marked ready for review (`gh pr ready`).
   - A pull request with unresolved requested changes must not merge.

4. **Verify Approval and Pre-Approval Readiness**:
   - Check whether required approvals are recorded per project policy.
   - Before approval, a PR only requires green checks and its required pre-approval review posted to the PR (`## RBG Review: PASS` description check on a consolidated feature-branch PR, or three-lens diff review on a standalone PR) with any absorbed donor PRs closed; do not rebase or resolve merge conflicts against the base branch before approval. Ready PRs are presented to the user one at a time.
   - If the PR is gated on external human approval, unmerged dependencies, or substantive author revisions, leave the PR open and record an explicit disposition reason.

5. **Post-Approval Rebase, Full Combined-Diff Review, and Land**:
   - Once all approvals required for merge are filed (or for changes authorized for autonomous merge):
     - Bring the branch up to date with the latest base branch, resolving any merge conflicts, running local tests, and pushing the resolved head.
     - For a consolidated feature-branch PR (`bundle/<slug>`) or any PR whose rebase resolved conflicts, run the full three-lens review (strategic fit, rule compliance, and quality) over the complete combined diff against the base branch and post the verdict (`## Strategic Review: PASS` and `## RBG Review: PASS`) to the PR thread.
     - Once the combined-diff review returns `PASS`, all checks are green, and zero `CHANGES_REQUESTED` reviews remain, execute the merge following repository merge conventions (merge commit, rebase, or squash).

## Output contract

- The pull request merged into its base branch, or left open with an explicit, substantiated status and blocking reason recorded.

## Must not

- Must not merge a pull request with failing or pending required checks.
- Must not merge a pull request with an active changes-requested review.
- Must not rebase or resolve merge conflicts before required approvals are recorded.
- Must not bypass project-specific merge gates or approval requirements.
- Must not leave an unmerged pull request without a documented, checkable reason.
