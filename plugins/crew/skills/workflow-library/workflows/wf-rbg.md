---
alias:
  - wf-rbg
  - wf-rule-check
  - wf-rbg-review
description: "Review: rule-compliance lens -- judge an artifact, change or decision against the axioms, user and project rules, scope of authority and data boundaries, returning PASS, REVISE or FAIL."
id: wf-rbg
tags:
  - wf-template
  - review
  - rules
  - compliance
title: Rule compliance review
type: template
---

## What this step does

An independent adjudicator tests the work against the law that governs it, without reading other reviews first.

## Procedure

1. Load the governing law in priority order: universal axioms, project rules, user rules. Never rule from memory.
2. From the ask alone, before reading the work, state the smallest proportionate remedy. Work that goes well beyond it, or deletes what the ask did not touch, is out of scope (`do-one-thing`).
3. Read the whole change, deletions included, and judge it: scope of authority, fail-fast, single source of truth, data boundaries on anything published (commits, titles, bodies). For instruction text, also its craft standard.
4. State each breach with the rule broken and a remedy cheaper than the harm it prevents. Anything else is a suggestion, and a suggestion asks for less, not more.
5. Where defects are clearly fixable without ambiguity, fix them in place if write permissions and instructions permit; otherwise suggest the exact fix alongside unresolved breaches.

## Output contract

One verdict with required changes and suggestions, each citing the rule and the place in the work. Internal handbacks in prose Argdown per `premise-check`.

## When to include

Reviewing any instruction, code change, design or decision for compliance.
