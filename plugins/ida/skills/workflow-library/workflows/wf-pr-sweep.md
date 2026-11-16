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

Sweep execution runs via parallel fan-out: evaluate each PR independently and aggregate dispositions into a single sweep handback.

## Input contract

- List of target repositories or current working repository context.
- Platform CLI credentials (`gh`).
- Project rules, merge policies, and risk tier definitions.

## Obligations

1. **Enumerate and Classify Open PRs**:
   - Query open pull requests across target repositories.
   - For each PR, determine its category:
     - _Draft_: Active WIP or author-staged draft PRs remain excluded while still in progress; completed worker draft PRs awaiting verification are triaged to queue their independent check and review task without marking ready inline, and transition to ready for review (`gh pr ready`) only after the independent check passes and its review verdict is posted to the PR thread.
     - _Automated Release_: Package or version release PRs managed by release automation; excluded from automated sweeping and reserved for explicit release approvals.
     - _Standard / Feature_: Active changes subject to review, checks, and project merge rules.

2. **Apply Project-Override Rules in Parallel**:
   - Fan out across candidate PRs in parallel to evaluate each against project-local governance rules:
     - Verify active base branch matches the project's designated integration branch (from project instructions).
     - Identify required approval roles (autonomous agent merge vs. human/principal sign-off).
     - Respect repository-specific feature freezes, review blocking rules, and risk boundaries.

3. **Triage, Clump Related PRs, and Queue Next-Step Tasks**:
   - Decouple triage from execution: the sweep does not execute inline code resolutions or final base-branch merges, and never hands the user mechanical inspection or reading tasks ("read/check PR"). It queues tasks for the next step, either queuing an existing task (located via the custodian or exact PR/branch metadata lookup) or creating a follow-up and queuing that.
   - For each non-draft PR or completed worker draft PR awaiting verification requiring action:
     - Screen unreviewed PR titles and descriptions for obvious compliance failures ("is this stupid?") so defective PRs are flagged for closure before diff review.
     - Audit CI check status, three-lens diff review status, and approval status per project policy.
     - Group related PRs requiring maintainer approval into cohesive **consolidated feature-branch clumps** (`bundle/<slug>` or `feat/<slug>`), keeping zero-overlap urgent fixes as standalone hotfixes. When constituent PRs are merged into a shared feature branch (`bundle/<slug>`), each absorbed donor PR must be closed immediately in the same step with a comment linking to the consolidated PR, and pre-approval review on the consolidated PR is a compliance description-only check (`## RBG Review: PASS`) without pre-approval rebase against the base branch.
     - Identify the discrete next action needed:
       - If unreviewed (including a completed worker draft PR awaiting its initial check): queue agent task to conduct compliance description screen and three-lens diff review by independent agents.
       - If review feedback or changes requested: queue agent task to address feedback on the branch.
       - If three-lens diff review passed and the PR belongs to a consolidation clump: queue task to merge into `bundle/<slug>`, close the donor PR with a pointer comment, and run the compliance description check on the consolidated PR.
       - If green, reviewed, and awaiting required approval: mark ready for one-at-a-time user walkthrough; reaches the user only after independent agent review and checks are summarized on the record with a concrete recommendation (do not queue conflict resolution or rebase before approval).
       - If approved (or autonomous merge authorized): queue task to rebase onto the base branch, resolve conflicts, run the full three-lens combined-diff review, and merge.
     - Verify whether an existing open task covers this action by routing the related-work search to the custodian (`pauli`) or performing an exact PR/branch metadata lookup (never running broad semantic searches with raw text), and ensure it is set to `queued` status, or create a discrete follow-up task and set it to `queued` status.

4. **Compile Sweep Disposition Report and File Closed Summary Task**:
   - For every enumerated PR, record an explicit disposition:
     - `Queued for Review`: Awaiting initial review; next-step task queued.
     - `Queued for Feedback`: Blocked on requested changes or review feedback; next-step task queued.
     - `Queued for Conflicts`: Approved PR with merge conflicts against base branch; next-step conflict resolution task queued (PRs awaiting approval are never queued for conflicts).
     - `Queued for Landing`: Approved and clean (or autonomous merge authorized); next-step landing/merge task queued.
     - `Blocked on Approval`: Green and reviewed, awaiting designated principal sign-off per project policy (mergeable not required before approval); reaches the user only after independent agent review and checks are summarized with a concrete recommendation.
     - `Excluded`: Active WIP/author-staged draft or automated release PR outside automated sweep scope.
   - Conclude by filing a closed task for the sweep itself listing all outstanding tasks and their queued task identifiers, so the coordinator can pick it up and decide whether to dispatch.

## Output contract

- A complete sweep disposition report accounting for every evaluated PR with its exact status, next step, and queued task identifier.
- Closed coordinator summary task filed on the record.

## Must not

- Must not hand the user mechanical inspection or reading tasks (such as "read/check PR"); unreviewed PRs and PRs with unaddressed feedback queue agent tasks, and Blocked on Approval reaches the user only after independent agent review and checks are summarized on the record with a concrete recommendation.
- Must not merge automated release PRs without explicit human release approval.
- Must not merge PRs lacking required project-level approvals or reviews.
- Must not queue merge conflict resolution or rebase tasks for PRs that are awaiting approval.
- Must not merge PRs with active changes-requested reviews or failing checks.
- Must not execute inline resolutions or landing within the triage sweep (all next steps are queued as discrete tasks).
- Must not omit any evaluated PR from the sweep handback report.
