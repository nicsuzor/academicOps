---
title: Capstone Verification
type: template
category: gate
description: Final completeness audit before an epic or multi-task milestone transitions to done or merge-ready. Select as the final gate when closing a composite epic. Not for single unit tasks (use `wf-verification`).
tags: [capstone, epic-closure, audit, completeness, gate]
---

# Gate: Capstone Verification

Terminal audit to ensure all deliverables, tests, and documentation across an epic are complete.

## 1. Deliverable and Sub-Task Audit

- Verify that every planned sub-task in `<epic>` has reached a terminal completed state.
- Ensure no orphaned requirements or unverified tasks remain in flight.

## 2. Full Regression and Build Verification

- Run full repository test suite, linters, and type checkers (`<full-test-suite>`).
- Confirm build artifacts and packages generate cleanly without warnings.

## 3. Documentation and Spec Synchronization

- Verify that user guides, API specifications, and architectural notes reflect all changes made during the epic.
- Ensure changelog and version manifests are updated where applicable.

## 4. Status Flip

- Transition epic status to `done` or `merge_ready`.
- Notify stakeholders or prepare release notes.

## Exit Condition

All epic sub-tasks closed and full repository verification passes.
