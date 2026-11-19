---
description: Drives an individual open pull request through CI checks, partitioned pre- and post-approval review gates, feedback resolution, Class D learning handover, and merge under project policy.
tags:
  - wf-template
  - pr
  - lifecycle
  - review
title: PR Move-Along Workflow
type: template
---

## What this template does

Drives an individual open pull request through CI validation, partitioned review gates, feedback resolution, Class D learning handover, post-approval conflict settlement, and landing under project rules. Conduct required independent checks and review lenses concurrently.

## Input contract

- An open pull request identifier or URL.
- Repository git access and platform CLI (`gh`).
- Project rules, base-branch declarations, consolidation rules, and merge policy.

## Obligations

1. **Resolve Project Policy and Route Consistency**:
   - Inspect the target repository's project rules and local policies to determine base branch, merge authority (autonomous vs human sign-off, release-PR exclusions), and consolidated feature-branch rules. Defer repo-specific merge, base, and consolidation rules to the project rather than assuming global defaults.
   - Verify PR labels align with the confirmed user-directed route or standing policy. Coordinator routing cannot hold or override a user-designated PR route without a verified superseding user reversal; halt and surface mismatched labels.
   - Enforce `data-boundaries` before posting comments or merging on external-audience surfaces.

2. **Audit CI Checks and Partitioned PR Gates**:
   - Query checks on current `HEAD` SHA: all required checks must pass cleanly. Reject bypassed, errored, cancelled, or `startup_failure` runs; never treat unrun or errored workflows as green.
   - Require head-SHA-matched posted reviews carrying distinct lens headers (`## RBG Review`, `## Strategic Review`, `## Enforcer Review` where applicable). Reject stale-SHA approvals or passes from prior commits and never treat committed verdict files as posted reviews. Any reviewer `fix(review):` commits must be pushed before posting verdicts.
   - **Constituent / standalone PRs**: Open as a draft (`gh pr create --draft`). Mark ready (`gh pr ready`) only after green `HEAD` CI, zero open `CHANGES_REQUESTED`, and head-SHA-matched **posted** `## RBG Review: PASS` plus proportionate dialectical review verdicts per project risk policy.
   - **Consolidated feature-branch PRs** (where configured by project rules): Require constituent diff reviews prior to merging components into the shared feature branch. For pre-approval readiness (`gh pr ready`), require constituent receipts, green `HEAD` CI, and head-SHA-matched **posted** description-only `## RBG Review: PASS` without premature rebase. After approval and rebase onto base, run a full combined-diff review matching the rebased `HEAD` SHA before merge.
   - Prohibit passing or advancing any PR that defers DRY, single-source-of-truth, or rule-compliance findings.

3. **Resolve Feedback and Flag Class D Handover**:
   - Inspect all PR reviews and threads (never rely solely on summary `reviewDecision` when open `CHANGES_REQUESTED` reviews exist). Address actionable feedback with pushed branch commits before re-review or substantiated rebuttals on the record.
   - Whenever work resolves a maintainer `CHANGES_REQUESTED` review on a PR that already carried an agent review, flag `(repo, pr, review_id)` in the handback report for custodian or authorized coordinator `/q` and `/learn` intake so fast-merged fixes still reach Class D learning. Plain leaf `/pull` workers record this flag in `## Report` only and never mint follow-up tasks themselves.

4. **Verify Approval, Settle Conflicts Post-Approval, and Land**:
   - Do not rebase or resolve base merge conflicts before required approvals are recorded (unless project policy authorizes autonomous landing).
   - Once required approvals are filed (or autonomous merge is authorized by project policy), `HEAD` CI is green, open `CHANGES_REQUESTED` count is zero, and any post-approval combined-diff review passes on current `HEAD`: settle merge conflicts against the base branch if behind, re-verify `HEAD` checks and gates, and merge per repository conventions. Otherwise leave open with an explicit blocking disposition.

## Output contract

- The pull request merged under project policy, or left open with an explicit blocking status, plus any `(repo, pr, review_id)` Class D handover flag in the report.

## Must not

- Must not merge or mark ready with failing, errored, bypassed, or `startup_failure` checks, or stale-SHA approvals/passes.
- Must not merge with any open `CHANGES_REQUESTED` review, label-vs-route mismatch, or deferred DRY/SSoT/compliance finding.
- Must not substitute committed verdict files for posted PR reviews, or post verdicts with uncommitted reviewer edits.
- Must not rebase before required approvals, bypass project merge/consolidation gates, or mint tasks from a leaf `/pull` worker.
