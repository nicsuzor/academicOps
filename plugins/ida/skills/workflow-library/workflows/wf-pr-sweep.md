---
description: Sweeps open pull requests and PRs updated or merged since a cursor across repositories, evaluating partitioned gates, surfacing Class D /learn proposals from maintainer feedback on agent-reviewed PRs, and queuing discrete next-step tasks.
tags:
  - wf-template
  - pr
  - sweep
  - triage
title: PR Sweep Workflow
type: template
---

## What this template does

Coordinates a parallel sweep of open pull requests and PRs updated or merged `since: <cursor>` across target repositories. Categorizes open PRs against project rules and partitioned PR gates, detects maintainer `CHANGES_REQUESTED` reviews or rule-miss comments on agent-reviewed PRs for Class D learning intake, and queues discrete next-step tasks without executing resolutions or `/learn` inline.

## Execution

Sweep execution runs via parallel fan-out: evaluate each PR independently and aggregate dispositions and Class D proposals into a single sweep handback.

## Input contract

- List of target repositories or current working repository context.
- Platform CLI credentials (`gh`), project rules, merge/consolidation policies, and optional `since: <cursor>` timestamp.

## Obligations

1. **Enumerate Open PRs and Recent Updates (`since: <cursor>`)**:
   - Query both open pull requests and PRs updated or merged `since: <cursor>` (`gh pr list --state all`, projecting PR metadata, branch/head commit SHA, state/draft/mergeability, labels, check rollups, comments, and `reviews` including review `id`, author, state, `submittedAt`, and body -- or fetching per-PR reviews when list payloads omit review IDs) so fast-merged PRs between sweeps are inspected.
   - Classify open PRs: _Draft_ (author WIP excluded while active; completed worker draft awaiting verification queued for check/review without marking ready inline), _Automated Release_ (excluded from automated sweep), or _Standard / Consolidated Feature_.

2. **Evaluate Project Rules and Partitioned Gates in Parallel**:
   - Fan out across candidate PRs to verify base branch, merge authority, label-vs-confirmed-route consistency, and project consolidation rules.
   - Audit `HEAD` CI (rejecting bypassed, errored, cancelled, or `startup_failure` runs), all open `CHANGES_REQUESTED` reviews, and head-SHA-matched **posted** reviews carrying distinct lens headers (`## RBG Review: PASS` plus proportionate dialectical review; for consolidated feature-branch PRs where configured: constituent diff receipts + green `HEAD` CI + head-SHA-matched posted description-only `## RBG Review: PASS` pre-approval, and full combined-diff review after post-approval rebase). Never queue pre-approval PRs for conflict rebase.

3. **Detect Class D Learning Triggers on Agent-Reviewed PRs**:
   - Across both open PRs and PRs updated or merged `since: <cursor>`, inspect projected `reviews` and comments to detect maintainer `CHANGES_REQUESTED` reviews or rule-miss comments on PRs that already carried an agent review (`## RBG Review`, `## Strategic Review`, `## Enforcer Review`, or agent review comments).
   - Deduplicate each `(repo, pr, review_id)` against existing PKB `/learn` tasks (via custodian `/hydrate` or exact metadata lookup) and open `/learn` GitHub issues (consolidating shared root causes into one issue).
   - Emit structured `/learn` `/q` proposals for non-duplicate findings (naming `repo`, `pr`, `review_id`, maintainer feedback summary, and any matching open `/learn` issue for evidence-comment consolidation) without running `/learn` inline.

4. **Triage and Queue Next-Step Tasks**:
   - For open PRs needing action, locate existing open tasks via custodian/metadata lookup and set `queued`, or create and queue a discrete next-step task (initial review, address feedback, post-approval conflict rebase, or landing; never queue pre-approval PRs for rebase).

5. **Compile Sweep Disposition Report and File Closed Summary Task**:
   - Record explicit dispositions for all open PRs (`Queued for Review`, `Queued for Feedback`, `Queued for Conflicts`, `Queued for Landing`, `Blocked on Approval`, `Excluded`) alongside all deduplicated Class D `/learn` `/q` proposals, and file a closed summary task listing queued task IDs and `/learn` proposals.

## Output contract

- Complete sweep disposition report accounting for every open PR and every `since: <cursor>` Class D `(repo, pr, review_id)` finding with deduplicated `/learn` `/q` proposals.
- Closed coordinator summary task filed on the record.

## Must not

- Must not execute resolutions, merges, or `/learn` diagnoses inline during triage.
- Must not omit fast-merged `since: <cursor>` PRs or `(repo, pr, review_id)` deduplication against PKB `/learn` tasks and open `/learn` issues.
- Must not treat bypassed, errored, or `startup_failure` checks, stale-SHA approvals, or deferred DRY/SSoT/compliance findings as ready.
- Must not queue conflict rebase tasks for PRs awaiting approval, or omit any evaluated PR from the report.
