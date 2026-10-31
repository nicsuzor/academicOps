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

Ends the current task at a decision that requires escalation for review. The worker files the complete artifact on the record and structures the approval boundary per the review rules (e.g. `partial` with a queued review task wired with `depends_on`, or an explicit decision task) so dependent work remains strictly blocked until approval is recorded. The task is not released as `done` while an approval decision is pending. Nothing beyond this point runs in the same task.

## Procedure

1. **Complete the artifact and review thread** -- the full artifact the decision is about, never a summary or abstract standing in for it. If the artifact is delivered via a pull request requiring user approval, verify that an agent-generated review proportionate to the change has been posted to the pull request thread, and that the pull request is marked ready for review only after review receipts are visible on GitHub. Attach whatever review verdicts already exist for it.
2. **File it on the record** -- route delivery through the record: state plainly what decision is being asked for with enough information to decide, proportionate evidence supporting it, and a reasoned recommendation stating what happens on approval. Hand back on the record and enforce one-level-per-hop escalation (never assign directly to `ida` or jump to the top); whichever agent one level up next reads the record decides what happens under the bazaar model.
3. **Structure the approval gate** -- do not release the task as `done`. Per the review rules (outcome 2), release the task as `partial` with a queued review task that this task `depends_on`, or queue an explicit decision task before dependent work can unblock. Implementation work is strictly blocked until the approval decision is recorded on the record. Stop.

## Composition

Cut the chain here. Work that proceeds on approval goes in a separate task that depends on the approval decision (either directly on an explicit decision task or on the spec task once approval is recorded and the task is completed). The approval gate ensures dependent work cannot unblock prematurely. Requested revisions go back to whichever step produced the artifact.

## Output contract

- The complete artifact, filed on the record where the reviewer will find it. For pull request deliverables, the proportionate review posted to the PR thread before submission for approval.
- The approval boundary recorded (e.g. task released as `partial` with a queued review task wired with `depends_on`, or an explicit decision task), strictly blocking dependent work until approval is recorded.

## When to include

Before any step that must not start on agent judgement alone: an irreversible or one-way-door action, or a commitment the principal has reserved for themselves.
