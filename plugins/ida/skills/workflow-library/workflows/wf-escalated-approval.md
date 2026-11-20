---
alias:
  - wf-escalated-approval
  - wf-approval
description: Hand a complete artifact over for an escalated explicit decision at a point the work must not cross on agent judgment; structures approval so dependent work remains blocked until approval is recorded.
id: wf-escalated-approval
tags:
  - wf-template
  - gate
  - approval
title: Escalated Approval Gate
type: template
---

## What this step does

Ends the current task at a decision requiring explicit user approval after proportionate independent agent review. The worker files the complete artifact and its independent review verdicts on the record and releases the task as `partial`, documenting the required decision in `reason` without minting follow-up tasks so dependent work remains blocked until approval is recorded. Nothing beyond this gate executes in the same task.

## Procedure

1. **Complete the artifact** -- deliver the full artifact under decision (never a summary standing in for it) alongside its independent agent review verdicts.
2. **File on the record** -- state plainly what decision is requested with enough context to decide, proportionate supporting evidence, and a reasoned recommendation explaining what proceeds upon approval; hand back on the record for upstream routing.
3. **Enforce the boundary** -- never release as `done` while approval is pending. Release as `partial` documenting the pending approval decision in `reason`, without minting follow-up tasks. Stop.

## Composition

Cut the composition chain at this gate. Post-approval execution belongs in a separate downstream task wired as blocked by this decision; requested revisions return to the producing step. Specifications preceding an implementation build are reviewed independently on the record and reach the user alongside their implementation deliverable rather than gating standalone before the build.

## Output contract

- Complete artifact and attached independent review verdicts filed on the record.
- Task released as `partial` with the required approval decision documented in `reason`, leaving dependent work blocked until approval is recorded.

## When to include

Before any irreversible one-way-door action, competing research route choice, or commitment the user has reserved for explicit sign-off -- never to gate a pre-build specification standalone.
