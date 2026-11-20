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
2. **Evaluate and clump in parallel against project policy**: Fan out concurrently to verify base branch, freeze constraints, CI checks, three-lens review status, and approval authority. Screen unreviewed PR titles and descriptions for obvious compliance failures so defective PRs are flagged for closure before diff review. Group related PRs requiring maintainer approval into cohesive consolidated feature-branch clumps (`bundle/<slug>` or `feat/<slug>`), keeping zero-overlap urgent fixes as standalone hotfixes.
3. **Decouple triage from execution**: Never merge into base inline, push fixes, or hand the user mechanical inspection or reading tasks ("read/check PR"). For each actionable PR, locate an existing open task (via the graph custodian or exact PR/branch metadata lookup -- never broad raw-text search) or create and queue a discrete follow-up task:
   - _Unreviewed (including completed drafts awaiting verification)_: queue compliance description screen and three-lens diff review by independent agents.
   - _Changes requested or feedback open_: queue agent task to address feedback on the branch.
   - _Three-lens diff review passed and part of a consolidation clump_: queue task to merge into `bundle/<slug>`, close each absorbed donor PR in the same step with a link to the consolidated PR, and run the compliance description-only check (`## Compliance Review: PASS`) without pre-approval rebase.
   - _Green, reviewed, and awaiting required approval_: record `Blocked on Approval` for one-at-a-time user walkthrough (reaches the user only after independent review and checks are summarized with a concrete recommendation; do not queue rebase or conflict resolution).
   - _Approved (or autonomous merge authorized)_: queue task to rebase onto base, resolve conflicts if any, run full three-lens combined-diff review, and merge.
4. **Report dispositions and file closed summary**: Record an explicit disposition for every enumerated PR (`Queued for Review`, `Queued for Feedback`, `Queued for Conflicts`, `Queued for Landing`, `Blocked on Approval`, or `Excluded`), and file a closed sweep summary task listing all outstanding queued task IDs.

## Must not

- Must not hand the user mechanical inspection or reading tasks ("read/check PR"); `Blocked on Approval` reaches the user only after independent review and checks are summarized with a concrete recommendation.
- Must not merge release PRs without explicit release approval, merge without required reviews/approvals, or queue rebase/conflict resolution before approval.

## Output contract

- Complete sweep disposition report accounting for every enumerated PR with its status, next step, and queued task ID.
- Closed summary task filed on the record listing all queued follow-up task IDs.

## When to include

Periodic or on-demand triage across open pull requests in one or more repositories.
