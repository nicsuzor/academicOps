---
alias:
- wf-qa-wf-qa
- wf-qa
category: gate
created: 2026-07-20T07:23:37.722328387+00:00
description: The universal QA gate -- assemble criteria, evaluate through a named child workflow, return a per-criterion verdict with evidence. Select it whenever an artifact must be judged before it is accepted; not for diagnosing a failure whose cause is unknown, and not for work with nothing checkable to hand back.
id: wf-qa
last_modified: 2026-09-01T00:00:00+00:00
modified: 2026-09-01T00:00:00+00:00
permalink: wf-qa
tags:
- wf-template
- v0.4
- module-f
- qa
title: wf-qa
type: template
---

## What this step does

The general QA obligation, and the parent of every specific QA workflow. It fixes three things and
nothing else: what counts as success, who judges it, and what the judgment must show. How the
artifact is actually examined belongs to the evaluate slot, which a child workflow fills.

Skip it only for changes with nothing to judge -- a typo fix -- or where the acceptance bar has been
waived outright.

## 1. Assemble criteria

Write the criteria down before any evidence is examined, each stated so a reader who was not present
can tell met from unmet. Criteria settled after the output is in view are not criteria: the pass they
produce says only that the work resembles itself.

Criteria come from the task's own acceptance bar, quoted verbatim wherever one exists. A paraphrase
substitutes the evaluator's bar for the asker's.

## 2. Evaluate -- a slot, not a procedure

**The evaluate step is an explicit slot.** This template names no examination technique. The
composing brief fills the slot with exactly one child workflow, which supplies how this kind of
artifact is exercised and what counts as evidence for it:

| Artifact under review                         | Fills the slot    |
| --------------------------------------------- | ----------------- |
| Rendered visual or UI output                  | [[wf-qa-visual]]  |
| Factual, citation-bearing or empirical claims | [[wf-fact-check]] |
| Machine-checkable code behaviour              | [[wf-tdd]]        |

An unfilled slot is a halt: name the kind of evaluation the artifact needs and stop. An artifact
class with no child workflow is a gap in the library -- report it, rather than improvising the
evaluation inside the brief.

Whoever produced the artifact does not judge it. The evaluator receives the criteria and the
artifact and no history of the work, so that the judgment turns on the evidence rather than on
knowing what was intended. Self-approval is not a verdict; where a constraint forces one agent into
both roles, say so in the handback.

This gate runs once. Where the evaluation is expected to repeat against the same criteria until they
are met, compose [[wf-loop]] around it -- round caps and progress detection are its job, not this
one's.

## 3. Return a per-criterion confirmation

One row per criterion, none omitted, each carrying:

- The criterion as written at step 1.
- `MET` or `UNMET` -- no third state. A criterion that could not be checked is `UNMET` with the
  reason recorded ("evidence unavailable", "could not reproduce").
- The evidence that decides it, cited to a place a reader can go and check: the observation, output,
  file:line, or artifact itself. "The change was made", "the tests pass" and "it looks right" decide
  nothing.

Then the overall verdict -- `PASS` (every criterion met), `FAIL`, or `ESCALATE` (the criteria
themselves turn out to be wrong or undecidable) -- and the counts: criteria checked, met, unmet, so a
downstream reader need not re-derive coverage.

## Declared stakes

Two-way door: a `FAIL` sends work back for another pass and authorises nothing irreversible. This
gate judges whether the work meets its criteria -- not whether it is fit to leave the team, which is a
separate obligation composed alongside it ([[wf-signoff]] for the human-facing capstone).

## Related

- [[wf-qa-visual]] -- child workflow: evaluation of rendered visual output
- [[wf-fact-check]] -- child workflow: evaluation of factual and citation-bearing claims
- [[wf-tdd]] -- child workflow: evaluation of machine-checkable code behaviour
- [[wf-loop]] -- iteration around this gate
- [[wf-signoff]] -- the human-facing capstone composed after this gate passes
