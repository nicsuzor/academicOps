---
title: Verification Floor
type: template
category: gate
description: Lightweight verification floor — lock acceptance criteria before work, confirm evidence against them before calling anything done. Select as the default baseline gate for any task. Not for deep multi-lens quality grading (use `wf-qa`).
tags: [verification, floor, criteria, sanity-check, gate]
---

# Gate: Verification Floor

The lightweight baseline verification obligation: lock criteria before work, confirm direct evidence before calling done.

## 1. Lock Acceptance Criteria (Pre-Work)

- State concrete, machine-checkable acceptance criteria before starting work on `<target>`.
- Criteria must define observable outcomes (test command passes, output file exists with schema, exit code 0).

## 2. Execute Work

- Implement the required change or produce `<artifact>`.

## 3. Confirm Evidence Against Criteria (Post-Work)

- Inspect actual machine outputs, test run logs, or rendered files.
- Verify that every locked criterion from step 1 is satisfied with direct evidence.
- A summary or claim that "it worked" is not evidence; inspect the artifact itself.

## Exit Condition

All locked criteria confirmed by direct machine inspection.
