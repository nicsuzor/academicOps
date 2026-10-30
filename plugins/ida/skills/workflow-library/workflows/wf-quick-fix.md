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

Provides a shortened delivery route for simple, uncontroversial changes to a project, bypassing post-hoc review when fully verified by automated tests.

## Scope

- **Eligible**: Simple, uncontroversial changes to a project -- such as isolated bugfixes, minor documentation repairs, small configuration updates, or tight, non-breaking edits.
- **Ineligible**: Any change that is controversial, architectural, schema-altering, cross-cutting, security-sensitive, code that executes without automated test coverage, or altering established contracts.

## Route Rule

Route delivery through whichever shortened PR or merge process the destination repository offers and permits under its own project rules:

- Takes whichever shortened route the repository provides -- such as an auto-merging pull request, a direct push to a development branch (e.g. `dev`), or a direct push to an unprotected default branch (e.g. `main`).
- The route rule names no fixed mechanism; it adapts to the specific mechanism configured and permitted by the target repository's rules and branch protections.
- Where a project's own rules prohibit a given mechanism (e.g. branch protection forbidding direct pushes to `main` or requiring linear history), the worker complies with the project's rules.

## Review Exemption

A quick fix is exempt from post-hoc review (independent follow-up QA tasks, manual sign-off, or multi-agent review passes) if and only if:

1. **Unit tests**: Where the change touches code that executes, it carries unit tests covering the modified behaviour. Instruction text and docs get no tests.
2. **Green destination tests**: All test suites on the destination branch or target environment are confirmed green following the merge or rebase.

If both conditions are met, the task concludes upon successful merge and verification without scheduling follow-up review.

If destination tests fail after merge or rebase, the change has failed: set the task status to `failed` and record the failure evidence on the task record for escalation. This failure must be escalated, not repeated by the same agent.

## Fallback

Any change falling outside the eligible scope, code that executes lacking unit test coverage, failing local test verification prior to delivery, or where the destination repository offers no shortened route, falls back to the repository's standard delivery process: standard pull request into the development branch, full CI verification, and mandatory independent review.

## Worker Completion Checklist

1. Implement the minimal change, with unit tests where it touches code that executes; write no test for instruction text or docs.
2. Verify automated test suite and linters pass locally.
3. Deliver via the repository's permitted shortened route (e.g. auto-merging PR or direct push); if delivered via a draft PR, mark it ready for review once its code step completes, without waiting for approval.
4. Verify all destination tests are green after merge or rebase. If destination tests fail, set the task status to `failed` and document the failure logs on the task record so it is escalated; do not repeat or retry the delivery within the same session.
5. Record verifiable evidence on the task (test execution output, commit SHA or PR URL).
6. Release the task:
   - As `done` if destination tests pass green, without minting follow-up review tasks.
   - As `failed` if destination tests fail after merge or rebase, escalating for triage.
   - As standard handoff status (e.g. `partial` if blocked, or `done` if delivered via standard PR) if fallback to the standard delivery process was triggered prior to delivery. Never release as `review`.
