---
alias:
  - wf-escalated-approval
  - wf-approval
description: Hand a complete artifact over for an escalated explicit decision at a point the work must not cross on agent judgement; ends the task in done with dependent work following.
id: wf-escalated-approval
tags:
  - wf-template
  - gate
  - approval
title: wf-escalated-approval
type: template
---

## What this step does

Ends the current task at a decision that requires escalation for review. The worker files the complete artifact on the record, records completion evidence, and releases the task as `done`. Nothing beyond this point runs in the same task.

## Procedure

1. **Complete the artifact** -- the full artifact the decision is about, never a summary or abstract standing in for it. Attach whatever review verdicts already exist for it.
2. **File it on the record** -- route delivery through the record: file an Ida-held follow-up (or tag the task `ida-tracked` with `assignee: ida`) so any review request reaches the user-facing session. State plainly what decision is being asked for and what happens on approval.
3. **Release the task as `done`** -- with a pointer to the filed artifact and completion evidence. Stop.

## Composition

Cut the chain here. Work that proceeds on approval goes in a separate task that `depends_on` this one. Once the approval decision is recorded, the dependent task is unblocked. Requested revisions go back to whichever step produced the artifact.

## Output contract

- The complete artifact, filed on the record where the reviewer will find it.
- The task released as `done`, pointing to the filed artifact with verified completion evidence.

## When to include

Before any step that must not start on agent judgement alone: an irreversible or one-way-door action, or a commitment the principal has reserved for themselves.
