---
alias:
  - wf-escalated-approval
  - wf-approval
description: "Worker: stop at a real approval boundary -- external audience, a merge no ruling covers, unbounded cost, an outside party's approval, or a hold the user reserved -- leaving the finished artifact on the record."
id: wf-escalated-approval
tags:
  - wf-template
  - approval
title: Approval boundary
type: template
---

## What this step does

Ends the task at a point the work must not cross on agent authority. Nothing beyond the boundary runs in this task.

## Procedure

1. Finish the artifact up to the boundary and put it where the task's Output names.
2. In the report, name the decision needed and recommend an answer.
3. End `partial`, with the decision in the reason. Mint no follow-up task; whoever picks up the record routes it.

## When to include

Only at one of the boundaries above. Never by task class (size, novelty, competing options), and never to hold a spec for approval before its build.
