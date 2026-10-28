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

## Policy and Merge Gates

- **Base branch**: PRs target `release/v1.0-rc0`. PRs targeting deprecated branches must be retargeted before processing.
- **Merge authority under feature freeze**:
  - Hotfixes: Clearly labeled hotfixes merge autonomously to `release/v1.0-rc0` once CI checks are green and an agent confirms hotfix scope.
  - Standard features and structural changes: Require explicit approval from the repository owner before merging.
  - Changes requested: A PR with an active "changes requested" review must not merge under any circumstances.
  - Release pull requests (`release-please`): Excluded from autonomous merging; merge only on explicit manual release approval.
- **Commit hygiene**: Commits to public repositories must never carry private task, note, or session identifiers, or commit trailers.

## Obligations

1. **Verify Triage and Eligibility**:
   - Confirm the PR is not a draft. Draft PRs remain with their author or owning task until marked ready for review.
   - Confirm the PR is not an excluded release PR.
   - Verify the base branch is `release/v1.0-rc0`. If targeting another branch, retarget the base branch.

2. **Audit CI Checks and Proportionate Review**:
   - Query automated checks (`gh pr checks`). All required test, lint, and type check suites must pass cleanly.
   - Verify that the PR has undergone a review proportionate to its risk tier. If review is absent, dispatch an independent review before proceeding.

3. **Resolve Review Feedback and Requested Changes**:
   - Inspect existing review threads and reviews.
   - Review comments and requested changes must be met by concrete diff edits on the PR branch or rejected with reasoned arguments recorded on the PR thread.
   - If changes requested remain unaddressed or require higher-level architectural decisions, leave the PR open and document the exact blocking feedback as the disposition reason.

4. **Verify Approvals and Mergeability**:
   - Verify that required approvals are recorded per the merge authority policy.
   - Check PR merge state (`gh pr view --json mergeable,mergeStateStatus`).
   - If merge conflicts exist (`mergeable: CONFLICTING`), resolve conflicts by rebasing or merging `release/v1.0-rc0` into the feature branch, ensuring tests remain green.

5. **Execute Landing**:
   - Once all checks are green, required approvals are filed, and mergeability is clean, merge the PR into `release/v1.0-rc0` via standard merge (`gh pr merge <number> --merge`).
   - If the PR cannot be merged (e.g. awaiting owner approval, active requested changes, or unresolved substantive conflicts), leave the PR open with its disposition and reason documented on the record.

## Output contract

- Merged PR on `release/v1.0-rc0`, or an open PR with an explicit, substantiated disposition status and reason recorded on the record.

## Must not

- Must not merge any release-please PR.
- Must not merge any PR without required owner approval unless it is a verified hotfix.
- Must not merge any PR with failing checks or unresolved changes requested.
- Must not leave an unmerged PR without an explicit stated reason.
