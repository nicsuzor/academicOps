---
alias:
  - wf-human-approval
  - wf-approval
description: Present the full artifact to the human principal for explicit approval before crossing an execution boundary; blocks until approved.
id: wf-human-approval
tags:
  - wf-template
  - gate
  - approval
title: wf-human-approval
type: template
---

## What this step does

Halts execution to present the full artifact (e.g. the complete specification, not an executive summary) to the human principal for explicit review and authorization. Implementation or irreversible actions cannot start until explicit approval is received on record.

## Procedure

1. **Prepare the full artifact** -- verify the artifact is complete, reviewed, and formatted in full. Do not condense or replace it with an abstract or bullet summary.
2. **Present for decision** -- present the complete artifact directly to the human principal along with prior review verdicts (`[[wf-qa]]`) and state the implementation boundary to be crossed.
3. **Halt and await explicit decision** -- pause execution. Implementation must not proceed without an affirmative, unambiguous approval from the human principal. Silence, timeout, or inferred consent is not approval.
4. **Record approval outcome** -- record the decision, timestamp, and any stipulations or requested modifications. If revisions are requested, return to authoring or research before re-submitting.

## Output contract

- Presentation of the full artifact directly to the principal.
- An explicit, verifiable human approval record on the task or thread before proceeding.
- Absolute block on implementation until approval is granted.

## When to include

Mandatory before crossing from specification to implementation, committing to irreversible changes, or executing one-way-door decisions.
