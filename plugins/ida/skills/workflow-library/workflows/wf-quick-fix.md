---
description: Quick-fix delivery for simple, uncontroversial changes -- routes through the repository's shortened PR or merge process where available, exempt from post-hoc review when unit and destination tests pass.
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

Provides a shortened delivery route for simple, uncontroversial changes, bypassing post-hoc review when fully verified by automated tests.

## Scope

- **Eligible**: Isolated bugfixes, minor documentation repairs, small configuration updates, and tight non-breaking edits.
- **Ineligible**: Controversial, architectural, schema-altering, cross-cutting, or security-sensitive changes; executable code without automated test coverage; or contract changes.

## Route Rule and Fallback

Deliver through whichever shortened PR or merge mechanism the destination repository permits under its own rules and branch protections (e.g. auto-merging PR or direct push to an unprotected dev/main branch).

Fall back to the repository's standard PR, full CI, and independent review process whenever a change exceeds eligible scope, executable code lacks unit test coverage, local checks fail, or no shortened route exists.

## Review Exemption

Exempt from post-hoc review if and only if both conditions hold:

1. **Unit tests**: Changes to executable code include unit tests covering the modified behavior (write no tests for instruction text, docs, or configuration values).
2. **Green destination tests**: All destination branch/target environment test suites pass after merge or rebase.

If destination tests fail after merge or rebase, set the task to **`failed`**, record the failure logs on the task, and escalate without retrying delivery in the same session.

## Worker Completion Checklist

1. Implement the minimal change (with unit tests for executable code only) and confirm local tests and linters pass.
2. Deliver via the repository's permitted shortened route; if using a worker PR, open as a draft (`gh pr create --draft`) and mark ready (`gh pr ready`) only after independent checks pass.
3. Verify destination tests are green post-merge/rebase and record primary evidence (test output, commit SHA, or PR URL).
4. Release the task: **`done`** if destination tests pass (minting no review tasks), **`failed`** if destination tests fail, or standard handoff status (`done` or `partial`, never `review`) if fallback triggered prior to delivery.
