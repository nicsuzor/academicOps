---
description: Sweeps open pull requests across repositories, triaging each against project-local rules, advancing eligible PRs through review and landing, and reporting disposition reasons for unmerged items.
tags:
  - wf-template
  - pr
  - sweep
  - triage
title: PR Sweep Workflow
type: template
---

## What this template does

Coordinates a comprehensive sweep of open pull requests across repositories. Enumerates open PRs, categorizes each against project-specific branch and merge policies, advances eligible PRs through the move-along lifecycle, and generates an honest disposition report accounting for every item.

## Execution Modes

Sweep execution may run via either:

- **Distributed dispatch**: Dispatch individual tasks for each PR candidate to separate workers.
- **Single-worker fan-out**: Dispatch a single coordinator worker with an instruction to fan out across open PRs in parallel (using concurrent subagents or isolated worktrees), advancing each PR independently and aggregating dispositions into a single sweep handback.

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

2. **Apply Project-Override Rules**:
   - Evaluate each PR against project-local governance rules:
     - Verify active base branch matches the project's designated integration branch.
     - Identify required approval roles (autonomous agent merge vs. human/principal sign-off).
     - Respect repository-specific feature freezes, review blocking rules, and risk boundaries.

3. **Advance Eligible PRs**:
   - For ready, non-draft PRs:
     - Audit CI check status.
     - Verify proportionate review has been completed.
     - Confirm review feedback and requested changes have been addressed.
     - Check mergeability and resolve base branch conflicts.
     - Execute merge where authorized by project policy.

4. **Compile Sweep Disposition Report**:
   - For every enumerated PR, record an explicit disposition:
     - `Merged`: Merged into base branch, citing the merge commit SHA.
     - `Blocked on Review`: Awaiting initial review or addressing requested changes.
     - `Blocked on Conflicts`: Substantive merge conflicts requiring author resolution.
     - `Blocked on Approval`: Green and reviewed, awaiting designated principal sign-off per project policy.
     - `Excluded`: Draft or automated release PR outside automated sweep scope.

## Output contract

- Eligible, fully approved, green PRs merged into their base branches.
- A complete sweep report accounting for every evaluated PR with its exact status and primary reason.

## Must not

- Must not merge automated release PRs without explicit human release approval.
- Must not merge PRs lacking required project-level approvals or reviews.
- Must not merge PRs with active changes-requested reviews or failing checks.
- Must not omit any evaluated PR from the sweep handback report.
