---
alias:
  - wf-signoff
description: Author a concise, one-page summary digest for decision or release sign-off.
id: wf-signoff
tags:
  - wf-template
  - review
  - signoff
title: Sign-Off Brief
type: template
---

## What this step does

Produces a concise, one-page summary on the record when a full task (leaf or composite parent task with children) completes: what was delivered against what was asked, with every checked claim carrying a resolvable link. Serves as a synthesis capstone of prior steps, not a re-review.

## Input contract

- Commissioning ask and acceptance criteria.
- Completed deliverable references (PR, document ID, or artifact paths).
- Recorded verification and review verdicts from prior stages.

## Output contract

The sign-off brief must:

- Fit on one page/screen in readable prose (not a raw bullet dump of every subtask).
- State what was delivered and link directly to it (PR, doc ID, or artifact).
- Ground every load-bearing claim ("works", "complete", "matches spec") in resolving evidence -- command output, `file:line`, or a linked prior verdict -- never an unlinked claim unless explicitly marked `"unverified"`.
- State plainly what was omitted or could not be verified, if anything.

## When to include

At completion of any task (leaf or composite) requiring an explicit sign-off record; author once at the unit level, not per subtask.
