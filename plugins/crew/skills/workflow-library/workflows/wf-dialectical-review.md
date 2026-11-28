---
alias:
  - wf-dialectical-review
  - wf-dialectical-design
  - wf-review-dialectic
  - wf-design-dialectic
  - wf-review
  - wf-multi-agent-review
description: "Review: dialectical review of handed-back work when selected by the composed workflow -- sizes depth to the stakes, applies the selected lenses, and reconciles their verdicts into PASS, REVISE or FAIL."
id: wf-dialectical-review
tags:
  - wf-template
  - review
  - dialectic
title: Review
type: template
---

## What this step does

Reviews work when the composed workflow selects this review. The coordinator decides depth and round count from the stakes, applies the lenses the composed workflow selects, and reconciles what comes back. Most work needs one pass by one reviewer; reserve several lenses and rounds for high-stakes work.

## Brief

Every reviewer gets the same neutral brief: the commissioning ask verbatim with its locator, any standard the user set (otherwise a standard reasonable for the work's purpose, audience and stakes), and the artifact itself (branch and commit, path, or text).

## Lenses (apply those the composed workflow selects)

- **Strategic fit**: is it the right problem, done in a way congruent with existing work and decisions.
- **Rule compliance**: axioms, user and project rules, scope of authority, data boundaries.
- **Quality**: does the real artifact meet its requirements and serve its audience well (when audience-facing or testable, as selected by the composed workflow).

## Stages

1. **Size**: determine depth and whether a second round is warranted for the selected lenses.
2. **Review**: run the lenses independently and wait for all of them.
3. **Reconcile**: strike findings outside a lens's remit, preferences about phrasing or layout, and demands for a standard inappropriate to the work. A valid in-remit FAIL stands.

Where defects are clearly fixable without ambiguity, reviewers with write permissions and no conflicting instruction restriction apply and commit them in place (itemizing applied fixes); otherwise they suggest the exact fix alongside remaining required changes. Never mint tasks.

## Output contract

One verdict (`PASS`, `REVISE` or `FAIL`) with its required changes and open questions, recorded where the composed workflow and task specify.

## When to include

Reviewing any handed-back artifact, change, plan or decision.
