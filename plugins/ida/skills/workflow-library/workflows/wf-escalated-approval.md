---
alias:
  - wf-escalated-approval
  - wf-approval
description: Hand a complete artifact over for an escalated explicit decision at a point the work must not cross on agent judgement; structures approval so dependent work remains blocked until approval is recorded.
id: wf-escalated-approval
tags:
  - wf-template
  - gate
  - approval
title: wf-escalated-approval
type: template
---

## What this step does

Ends the current task when directed work reaches an approval boundary that must not proceed on agent or directed authority alone: external-audience transmission, unruled repository merge, unbounded reach or cost lacking scope/volume/cost confirmation, external-party gate, or a specific hold explicitly reserved by the user. A review by independent agents is required and a proportionate review is selected. The worker files the complete artifact and its independent agent review verdicts on the record and releases the task as `partial` documenting the required approval decision in `reason` (without minting follow-up tasks), so dependent work remains strictly blocked until approval is recorded. The task is not released as `done` while an approval decision is pending. Specifications preceding a build are reviewed by independent agents in Stage 1 and delivered with implementation code on the single Stage 2 PR; they are never released for user approval on their own. Nothing beyond this point runs in the same task.

## Procedure

1. **Complete the artifact** -- the full artifact the decision is about, never a summary or abstract standing in for it. Attach the independent agent review verdicts for it.
2. **File it on the record** -- route delivery through the record: state plainly what decision is being asked for with enough information to decide, proportionate evidence supporting it, and a reasoned recommendation stating what happens on approval. Hand back on the record; whichever agent one level up next reads the record decides what happens.
3. **Structure the approval gate** -- do not release the task as `done`. Release the task as `partial` documenting what approval decision is needed in `reason`, without minting follow-up tasks. Implementation work is strictly blocked until the approval decision is recorded on the record. Stop.

## Composition

Cut the chain here. Work that proceeds on approval goes in a separate task that depends on the approval decision (such as an unqueued PKB plan or decision hold explicitly reserved by the user, or a confirmed external-party, unruled-merge, or unbounded-cost boundary). Never insert this cut by task class on user-directed work; specifications preceding a build do not use this gate in Stage 1: they are reviewed by independent agents on the PKB and reach the user together with their implementation code on the single PR opened by Stage 2. Requested revisions go back to whichever step produced the artifact.

## Output contract

- The complete artifact and its independent agent review verdicts, filed on the record.
- The approval boundary recorded (task released as `partial` with the required decision documented in `reason`), strictly blocking dependent work until approval is recorded.

## When to include

Before an operation reaching a boundary that must not start on user direction alone: external-audience transmission, an unruled repository merge, an operation with unbounded reach or cost lacking explicit prior approval naming scope, volume, and cost (or expanding beyond approved scope), an external-party gate, or a specific hold or choice explicitly reserved by the user prior to execution. Never include by task class (complexity, new components, or competing alternatives) or to gate a Stage 1 specification before its Stage 2 build.
