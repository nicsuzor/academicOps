---
alias:
  - wf-signoff
description: Author a concise, one-page human-facing summary digest for decision or release sign-off.
id: wf-signoff
tags:
  - wf-template
  - gate
title: wf-signoff
type: template
---

## What this step does

Produces the one-page prose summary for user when a full task or epic completes: what was delivered, against what it was asked to do, with every checked claim carrying a resolvable link. This is the human-facing capstone of the workflow -- not a re-review, a synthesis of what the other steps already established.

## Output contract

The signoff brief must:

- Fit on one page/screen -- prose, not a bullet dump of every subtask.
- State what was delivered and link to it (PR, doc id, artifact).
- Name every load-bearing claim ("this works," "this is complete," "this matches the spec") with its resolving evidence -- command output, file:line, or a linked review verdict from an earlier step. No claim without a link or an honest "unverified."
- State plainly what wasn't done or couldn't be verified, if anything -- a clean brief with a stated gap is more useful than a brief that hides one.

## When to include

Every task/epic that reaches human sign-off -- i.e., anything user needs to read to decide "is this actually done." Write one at the level a human actually reviews, not per subtask.
