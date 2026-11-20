---
description: Sweep open pull requests across repositories in parallel, triage each against project merge policies, queue discrete next-step tasks without inline execution, and report every disposition.
tags:
  - wf-template
  - pr
  - sweep
  - triage
title: PR Sweep Workflow
type: template
---

## What this template does

Coordinates a parallel triage sweep across open pull requests in one or more repositories, evaluating each against project-local branch and merge policies, queuing discrete next-step tasks, and reporting a complete disposition table.

## Input contract

- Target repository list (or current repository context) with git-hosting access.
- Project merge policies, base branch rules, and risk-tier definitions.

## Obligations

1. **Enumerate and classify open PRs**: Query open pull requests across target repositories. Exclude active WIP drafts and automated release PRs (reserved for explicit release approval); include completed isolated-worker drafts awaiting verification and active feature PRs.
2. **Evaluate in parallel against project policy**: Fan out across candidate PRs concurrently to verify target base branch, feature-freeze constraints, CI check status, proportionate independent review status, and required approval authority (autonomous vs. user sign-off).
3. **Decouple triage from execution**: Never merge PRs, push fixes, or mark drafts ready inline during a sweep. For each actionable PR, locate an existing open task (via the graph custodian or exact PR/branch metadata lookup -- never broad raw-text search) or create a discrete follow-up task and queue it according to next step:
   - _Unreviewed (including completed drafts awaiting verification)_: queue proportionate independent review and verdict posting.
   - _Changes requested or feedback open_: queue feedback resolution.
   - _Green and reviewed, awaiting required approval_: record `Blocked on Approval`; do not queue rebase or conflict resolution.
   - _Approved (or autonomous merge authorized) with conflicts_: queue base-branch update and conflict resolution.
   - _Approved (or autonomous merge authorized) and clean_: queue landing/merge.
4. **Report dispositions and file closed summary**: Record an explicit disposition for every enumerated PR (`Queued for Review`, `Queued for Feedback`, `Queued for Conflicts`, `Queued for Landing`, `Blocked on Approval`, or `Excluded`), and file a closed sweep summary task listing all outstanding queued task IDs.

## Output contract

- Complete sweep disposition report accounting for every enumerated PR with its status, next step, and queued task ID.
- Closed summary task filed on the record listing all queued follow-up task IDs.

## When to include

Periodic or on-demand triage across open pull requests in one or more repositories.
