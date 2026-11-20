---
alias:
  - wf-escalated-approval
  - wf-approval
description: Hand a complete artifact over for an escalated explicit decision at a point the work must not cross on agent judgment; structures approval so dependent work remains blocked until approval is recorded.
id: wf-escalated-approval
tags:
  - wf-template
  - approval
  - workflow
title: Escalated Approval Boundary
type: template
---

## What this step does

Ends the current task when directed work reaches an approval boundary that must not proceed on agent or directed authority alone: external-audience transmission, unruled repository merge, unbounded reach or cost lacking scope/volume/cost confirmation, external-party approval, or a specific hold explicitly reserved by the user. A proportionate independent agent review is required. The worker files the complete artifact and its independent review verdicts on the record and releases the task as `partial`, documenting the required decision in `reason` without minting follow-up tasks so dependent work remains blocked until approval is recorded. Nothing beyond this approval boundary executes in the same task.

## Procedure

1. **Complete the artifact** -- deliver the full artifact under decision (never a summary standing in for it) alongside its independent agent review verdicts.
2. **File on the record** -- state plainly what decision is requested with enough context to decide, proportionate supporting evidence, and a reasoned recommendation explaining what proceeds upon approval; hand back on the record for upstream routing.
3. **Enforce the boundary** -- never release as `done` while approval is pending. Release as `partial` documenting the pending approval decision in `reason`, without minting follow-up tasks. Stop.

## Composition

Cut the composition chain at this approval boundary. Post-approval execution belongs in a separate downstream task wired as blocked by this decision (such as an explicit user-reserved hold or a confirmed external-party, unruled-merge, or unbounded-cost boundary); never insert this cut by task class on user-directed work. Requested revisions return to the producing step. Specifications preceding an implementation build are reviewed independently on the record and reach the user alongside their implementation deliverable rather than holding standalone for approval before the build.

## Output contract

- Complete artifact and attached independent review verdicts filed on the record.
- Task released as `partial` with the required approval decision documented in `reason`, leaving dependent work blocked until approval is recorded.

## When to include

Before an operation reaching a boundary that must not start on user direction alone: external-audience transmission, an unruled repository merge, an operation with unbounded reach or cost lacking explicit prior approval naming scope, volume, and cost (or expanding beyond approved scope), an external-party approval, or a specific hold or choice explicitly reserved by the user prior to execution. Never include by task class (complexity, new components, or competing alternatives) or to hold a pre-build specification for approval standalone.
