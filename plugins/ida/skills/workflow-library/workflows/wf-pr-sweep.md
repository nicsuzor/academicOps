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
   - For each PR requiring action:
     - Audit CI check status.
     - Inspect review status: verify whether a proportionate review is posted on the PR thread.
     - Check mergeability and base branch conflict state.
     - If checks pass and approval is required, but no review is posted on the PR thread, classify as `Queued for Review` and queue a review task; strictly forbid classifying as `Blocked on Approval`.
     - Identify the discrete next action needed (e.g. address review feedback, settle merge conflicts, conduct risk-tier review, or merge).
     - Verify an existing open task covers this action, or queue a discrete follow-up task.

4. **Compile Sweep Disposition Report**:
   - For every enumerated PR, record an explicit disposition:
     - `Queued for Review`: Awaiting initial or proportionate review; next-step review task queued. PRs requiring approval that lack posted reviews are always categorized here.
     - `Queued for Feedback`: Blocked on requested changes or review feedback; next-step task queued.
     - `Queued for Conflicts`: Merge conflicts against base branch; next-step task queued.
     - `Blocked on Approval`: CI checks green and proportionate review already posted on the PR thread, awaiting designated principal sign-off per project policy. If a review has not been posted on the PR thread, the PR must never be classified as `Blocked on Approval`.
     - `Merged`: Merged into base branch (for fully approved, green hotfixes where authorized).
     - `Excluded`: Draft or automated release PR outside automated sweep scope.
   - File a closed summary task recording the full sweep disposition manifest.

## Output contract

- A complete sweep disposition report accounting for every evaluated PR with its exact status, next step, and queued task identifier.
- Closed coordinator summary task filed on the record.

## Must not

- Must not merge automated release PRs without explicit human release approval.
- Must not merge PRs lacking required project-level approvals or reviews.
- Must not merge PRs with active changes-requested reviews or failing checks.
- Must not classify any PR requiring approval as `Blocked on Approval` unless an agent-generated proportionate review has already been posted to the PR thread.
- Must not execute complex multi-PR inline resolutions within the triage sweep.
- Must not omit any evaluated PR from the sweep handback report.
