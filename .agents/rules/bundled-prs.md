---
trigger: always_on
description: Commit to the designated epic or bundle branch for consolidated PRs, enforce partitioned bundle/<slug> review gates, and apply academicOps integration-branch and feature-freeze merge rules.
---

## Bundled Pull Requests under Epics

When tasks execute under a parent task marked `bundle_pr: true` or under an active epic (`type: epic`), workers commit directly to the designated epic or bundle branch (`polecat/<epic-id>`, `topic/<slug>`, or `bundle/<slug>`) and must not open detached pull requests against `dev`. All changes, test receipts, and review records bundle into the single consolidated pull request for cohesive user review. If a standalone tracking or donor pull request exists, close it immediately upon consolidation linking to `#<bundle-PR>`.

### Consolidated `bundle/<slug>` Review Gates

- **Pre-consolidation**: Each constituent branch passes 3-lens diff review (`pauli`, `rbg`, `marsha`) before merging into `bundle/<slug>`, and donor PRs close immediately upon consolidation linking to `#<bundle-PR>`.
- **Pre-approval readiness (`gh pr ready`)**: Requires constituent review receipts, green `HEAD` CI, and a head-SHA-matched posted description-only `## RBG Review: PASS` without premature rebase.
- **Post-approval landing**: After owner approval and rebase onto `dev`, run a full combined-diff 3-lens review matching the rebased `HEAD` SHA with green CI before merge.

### Integration Branch and Feature-Freeze Merge Policy

- **Integration base branch**: Pull requests target `dev` (the integration base branch declared in `.agents/CORE.md`). PRs targeting deprecated or non-integration branches must be retargeted before processing.
- **Feature-freeze merge authority**:
  - Standard features and structural changes require explicit repository owner approval before merging.
  - Hotfixes explicitly directed by the user merge autonomously to `dev` once CI checks are green, with compliance review verifying alignment with what was asked. Hotfixes proposed autonomously by an agent require confirmation from the front agent that they fit hotfix scope before merging autonomously.
  - Any pull request with an active `CHANGES_REQUESTED` review must not merge under any circumstances.
  - Release pull requests (`release-please`) are excluded from consolidation sweeps and autonomous merging; they merge only on explicit manual user release approval.
- **Pre-approval readiness vs. post-approval rebase**: Before approval, PRs must be green and reviewed with feedback addressed (mergeability is not required before approval; do not rebase or resolve conflicts prematurely). Rebase onto `dev` and conflict resolution happen after approval, just before merge.
