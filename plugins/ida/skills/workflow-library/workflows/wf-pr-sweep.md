---
description: Sweeps open pull requests across repositories, triaging each against project-local rules, fanning out in parallel to identify next steps, queuing discrete tasks, and reporting disposition reasons.
tags:
  - wf-template
  - pr
  - sweep
  - triage
title: PR Sweep Workflow
type: template
---

## What this template does

Coordinates a comprehensive sweep of open pull requests across repositories. Fanning out in parallel across candidate PRs, the coordinator categorizes each against project-specific branch and merge policies, decouples triage from execution by identifying and queuing discrete next-step tasks, and generates an honest disposition report accounting for every item.

## Execution

Sweep execution runs via parallel fan-out: a single coordinator fans out across all open PRs in parallel (using concurrent subagents or queries), evaluating each PR independently and aggregating dispositions into a single sweep handback.

## Input contract

- List of target repositories or current working repository context.
- Platform CLI credentials (`gh`).
- Project rules, merge policies, and risk tier definitions.

## Obligations

1. **Enumerate and Classify Open PRs**:
   - Query open pull requests across target repositories.
   - For each PR, determine its category:
     - _Draft_: Staged work owned by the author; excluded from sweeping until marked ready for review.
     - _Automated Release_: Package or version release PRs managed by release automation; excluded from automated sweeping and reserved for explicit release approvals.
     - _Standard / Feature_: Active changes subject to review, checks, and project merge rules.

2. **Apply Project-Override Rules in Parallel**:
   - Fan out across candidate PRs in parallel to evaluate each against project-local governance rules:
     - Verify active base branch matches the project's designated integration branch (from project instructions).
     - Identify required approval roles (autonomous agent merge vs. human/principal sign-off).
     - Respect repository-specific feature freezes, review blocking rules, and risk boundaries.

3. **Triage and Queue Next-Step Tasks**:
   - Decouple triage from execution: do not attempt inline multi-PR resolutions.
   - For each ready, non-draft PR requiring action:
     - Audit CI check status.
     - Inspect review status (proportionate review, changes requested, or author feedback).
     - Check approval status per project policy.
     - Before approval, a PR requires green checks and review; mergeability against the base branch is not required before approval, and PRs awaiting approval must not be queued for conflict resolution or rebase.
     - Identify the discrete next action needed:
       - If unreviewed: conduct proportionate risk-tier review.
       - If review feedback or changes requested: address feedback.
       - If green, reviewed, but awaiting required approval: mark blocked on approval (do not queue conflict resolution).
       - If approved (or autonomous merge authorized) and merge conflicts exist: queue task to bring branch up to date with base and resolve merge conflicts.
       - If approved and clean: queue landing / merge.
     - Verify an existing open task covers this action, or queue a discrete follow-up task.

4. **Compile Sweep Disposition Report**:
   - For every enumerated PR, record an explicit disposition:
     - `Queued for Review`: Awaiting initial review; next-step task queued.
     - `Queued for Feedback`: Blocked on requested changes or review feedback; next-step task queued.
     - `Queued for Conflicts`: Approved PR with merge conflicts against base branch; next-step conflict resolution task queued (PRs awaiting approval are never queued for conflicts).
     - `Blocked on Approval`: Green and reviewed, awaiting designated principal sign-off per project policy (mergeable not required before approval).
     - `Merged`: Merged into base branch (for fully approved, green hotfixes where authorized).
     - `Excluded`: Draft or automated release PR outside automated sweep scope.
   - File a closed summary task recording the full sweep disposition manifest.

## Output contract

- A complete sweep disposition report accounting for every evaluated PR with its exact status, next step, and queued task identifier.
- Closed coordinator summary task filed on the record.

## Must not

- Must not merge automated release PRs without explicit human release approval.
- Must not merge PRs lacking required project-level approvals or reviews.
- Must not queue merge conflict resolution or rebase tasks for PRs that are awaiting approval.
- Must not merge PRs with active changes-requested reviews or failing checks.
- Must not execute complex multi-PR inline resolutions within the triage sweep.
- Must not omit any evaluated PR from the sweep handback report.
