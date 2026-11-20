---
description: Shortened delivery workflow for isolated, uncontroversial changes -- keeps changes minimal while still requiring local verification, independent proportionate review, and explicit repository merge authority.
id: wf-quick-fix
tags:
  - wf-template
  - quick-fix
  - finish
  - delivery
title: Quick-fix workflow
type: template
---

## What this template does

Provides a compact delivery path for small, isolated, uncontroversial changes without skipping verification, independent proportionate review, or standing merge boundaries.

## Scope

- **Eligible**: Isolated bugfixes, minor documentation repairs, small configuration updates, and tight non-breaking edits.
- **Ineligible**: Controversial, architectural, schema-altering, cross-cutting, or security-sensitive changes; executable code lacking regression tests; or contract changes (route through standard task/PR composition instead).

## Route and Merge Authority

- **No low-risk review bypass**: Every change (bugfixes included) requires proportionate independent review and green checks on `HEAD` before marking ready (`gh pr ready`) or merging.
- **Shortened merge boundary**: Merge autonomously (`gh pr merge --squash`) only when project rules authorize it AND a standing user ruling explicitly names the repository with zero external audience (`data-boundaries`, `exercise-authority` Exceptions 1-2). Otherwise leave the draft-then-ready PR open for explicit user approval with verification receipts and a reasoned recommendation.
- **Post-merge test failure**: Never retry or mask failures; record logs, mark failed if checks regress, and escalate verbatim (`fail-fast`).

## Worker Completion Checklist

1. Implement the minimal fix (adding red-before-green tests for executable code; proving instruction or doc changes via live checks or lint).
2. Confirm local tests, linters, and builds pass cleanly.
3. Open a draft PR (`gh pr create --draft`), obtain independent proportionate review (`PASS`), satisfy head-SHA CI checks, and mark ready (`gh pr ready`) or merge strictly if an explicit standing user ruling covers the repository with zero external audience.
4. Record primary evidence (test output, review links, commit SHA, PR URL) and release strictly per outcome (`done` when shipped/ready per contract, `failed` on failing checks; never `review`).
