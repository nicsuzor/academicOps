---
alias:
  - wf-human-approval
  - wf-approval
description: Hand a complete artifact to a human for an explicit decision at a point the work must not cross on agent judgement; ends the task in review.
id: wf-human-approval
tags:
  - wf-template
  - gate
  - approval
title: wf-human-approval
type: template
---

## What this step does

Ends the current task at a decision only a human can make. The worker files the complete artifact for review and stops. Nothing beyond this point runs in the same task.

## Procedure

1. **Complete the artifact** -- the full artifact the decision is about, never a summary or abstract standing in for it. Attach whatever review verdicts already exist for it.
2. **File it for review** -- delivery goes through Ida Prime: file an Ida-held follow-up under `agent_brains_ida` (or tag the task `ida-tracked` with `assignee: ida`) so the review request actively surfaces to Nic via Ida Prime (on his originating channel, daily note `## Needs Nic's Sign-Off`, and `/mine`). State plainly what decision is being asked for and what happens on approval.
3. **Release the task as `review`** -- with a pointer to the filed artifact. Stop.

## Composition

Cut the chain here. Work that proceeds on approval goes in a separate task that `depends_on` this one. The human marks this task `done` to approve; that releases the dependent task. Requested revisions go back to whichever step produced the artifact.

## Output contract

- The complete artifact, filed for review where the human will find it.
- The task released as `review`, naming the decision asked for and pointing to the artifact.

## When to include

Before any step that must not start on agent judgement alone: an irreversible or one-way-door action, or a commitment the human has reserved for themselves.
