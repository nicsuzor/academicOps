---
alias:
  - wf-dialectical-review
  - wf-dialectical-design
  - wf-review-dialectic
  - wf-design-dialectic
  - wf-review
  - wf-multi-agent-review
default: true
description: "Review: the default review of handed-back work -- a coordinator sizes the review to the stakes, sends only the lenses the work needs, and reconciles their verdicts into PASS, REVISE or FAIL."
id: wf-dialectical-review
tags:
  - wf-template
  - review
  - dialectic
  - default
title: Review
type: template
---

## What this step does

Reviews work after it is handed back. The coordinator decides how much review the work deserves, sends it to the lenses that apply, and reconciles what comes back. Most work needs one pass by one reviewer; reserve several lenses and rounds for high-stakes work.

## Brief

Every reviewer gets the same neutral brief, in prose Argdown per `premise-check`: the commissioning ask verbatim with its locator, any standard the user set (otherwise a standard reasonable for the work's purpose, audience and stakes), and the artifact itself (branch and commit, path, or text).

## Lenses (send only those the work needs)

- **Strategic fit**: is it the right problem, done in a way congruent with existing work and decisions.
- **Rule compliance**: axioms, user and project rules, scope of authority, data boundaries.
- **Quality**: does the real artifact meet its requirements and serve its audience well. Only when something audience-facing or testable was built.

## Stages

1. **Size**: pick the lenses and whether a second round is warranted.
2. **Review**: run the lenses independently and wait for all of them.
3. **Reconcile**: judge each handback on the message alone per `premise-check` (zero outside substantive checks; proportionate depth, material remands only). Strike findings outside a lens's remit, preferences about phrasing or layout, and demands for a standard inappropriate to the work. A valid in-remit FAIL stands.

Reviewers do not edit the work or mint tasks; they state required changes.

## Output contract

One verdict (`PASS`, `REVISE` or `FAIL`) with its required changes and open questions, on the review's task or record.

## When to include

Reviewing any handed-back artifact, change, plan or decision.
