---
title: PR lifecycle workflows -- sweep task queuing and move-along fan-out
status: ready
---

# PR Lifecycle Workflows: Sweep Task Queuing and Move-Along Fan-Out

Specifies the pull request lifecycle workflows: separating discovery and triage from execution by having the sweep workflow fan out in parallel to queue next-step tasks and file a closed completion task, and enabling a trial option in the move-along workflow for single-worker parallel fan-out on individual PRs.

## User stories

### US-1 Sweep operates via parallel fan-out and queues next-step tasks

As a workflow coordinator, I want the sweep workflow to fan out in parallel across open pull requests to evaluate each against project policy, queue a discrete next-step task for each item needing action, and record a closed summary task of outstanding items, so that discovery is decoupled from execution and I can decide when and how to dispatch resolutions without redundant execution passes.

- **AC-1.1** Given an open pull request requiring progression (e.g. initial review, feedback resolution, merge conflict rebase, or landing), when the sweep workflow processes the PR, then it queues an existing task or creates and queues a follow-up task targeting that PR's discrete next step, rather than executing the resolution inline.
- **AC-1.2** Given candidate pull requests across target repositories, the sweep coordinator fans out across them in parallel rather than executing sequentially or requiring separate execution modes.
- **AC-1.3** Given the completion of all PR evaluations in a sweep run, when the sweep finishes, then it files a closed task recording the sweep inventory and listing all outstanding queued tasks for the coordinator to review and dispatch.

### US-2 Move-along single-worker fan-out trial

As a workflow dispatcher, I want the move-along workflow to support dispatching an individual pull request to a single worker instructed to fan out sub-actions in parallel as an empirical trial, so that independent checks and reviews can execute concurrently without sequential blocking.

- **AC-2.1** Given an open pull request undergoing progression, when the move-along workflow is invoked, then it allows dispatching to a single worker with instructions to coordinate parallel subagent fan-out for independent operations on that PR (e.g. concurrent check verification and risk-tier review).
- **AC-2.2** Given the adoption of single-worker parallel fan-out, when documenting the capability in the workflow contract, then it is explicitly designated as a trial subject to principal review based on observed execution performance.

## Design

### 1. Sweep Architecture: Decoupling Triage from Execution via Parallel Fan-Out

The sweep workflow operates exclusively as a discovery and triage mechanism, discovering open pull requests and queuing discrete tasks for independent execution:

1. **Parallel Fan-Out**: The sweep coordinator queries open pull requests and evaluates candidates in parallel. There is a single execution model: parallel fan-out across PRs.
2. **Project Policy Resolution**: PRs are evaluated against project-specific branch and merge policies. Target base branches are specified in project-level configuration (e.g. `.agents/CORE.md`) rather than hardcoded in workflow templates.
3. **Queue Next-Step Tasks**: For each PR requiring action:
   - Identify the single next required action (e.g. run risk-tier review, address requested changes, resolve base merge conflicts, or land approved PR).
   - If an existing open task covers this action, ensure it is set to queued status.
   - If no task exists, create and queue a follow-up task scoped strictly to that PR's next action.
   - The sweep workflow does not execute resolutions inline.
4. **Coordinator Summary Handoff**: Upon evaluating all open PRs, the sweep files a closed task recording the full disposition manifest and listing all queued task identifiers, providing the dispatching coordinator with an authoritative inventory to schedule or dispatch.

### 2. Move-Along Parallel Fan-Out (Trial)

The move-along workflow advances an individual PR through check auditing, proportionate review, feedback resolution, merge conflict settlement, and landing:

1. **Single-Worker Fan-Out Option**: Where an individual PR requires multiple independent checks or reviews, the dispatcher may assign the task to a single worker instructed to fan out sub-operations in parallel (e.g. concurrently dispatching review lenses or running test suites in parallel subagents).
2. **Trial Designation**: This fan-out pattern is formally designated as an empirical trial. The principal evaluates system performance and token economy from specimen runs before determining whether to retain or refine the pattern.
