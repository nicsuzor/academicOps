---
title: Brief Composition Verification
type: template
category: gate
description: Verify that a task brief and composed process satisfy all structural, sizing, and acceptance criteria before dispatch. Select as a pre-dispatch verification gate.
tags: [brief, composition, pre-dispatch, verification, gate]
---

# Gate: Brief Composition Verification

Pre-dispatch quality gate to audit task briefs against structural standards.

## 1. Structural Brief Audit

- Verify task brief for `<task>` contains required sections: Objective, Scope Boundaries, Context Pointers, and Acceptance Criteria.
- Confirm all referenced file paths, tools, and parent epics exist and resolve cleanly.

## 2. Acceptance Criteria Inspection

- Audit acceptance criteria: are they machine-checkable, concrete, and unambiguous?
- Ensure criteria test outcomes rather than prescribing keystrokes.

## 3. Sizing and Decomposition Check

- Check estimated task scope: can a cold executor complete this within a single session budget?
- If the task is too broad, route back to `/decompose` for further slicing.

## 4. Model and Parameter Binding

- Confirm model specification is explicitly set (`<model>`, default sonnet).
- Verify tool permissions and workspace isolation modes are properly configured.

## Exit Condition

Brief approved for dispatch with zero blocking defects.
