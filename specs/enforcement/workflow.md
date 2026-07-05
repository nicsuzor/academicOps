---
id: enforcement-workflow
title: Enforcement — The Workflow (Layer 3)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, workflow]
---

# Enforcement — The Workflow (Layer 3)

## aops-pkb — Workflow

A set of PKB tasks and subtasks that make up a more user-reviewable,
user-directed unit of work.

This is the first layer where the framework cares about _how_ the work is done,
not only the outcome — in contrast to Layer 0, where the posture is
trust-the-method.

### Mechanisms

- **`/planner` decomposition**, task-template conventions, and proof-of-compliance
  tool fields — the workflow is composed compliant at task-creation time.
- **`cohesive-pr-epic`** — a coupled set of tasks shares one draft PR; a
  workflow-level invariant that constrains the shape of the whole set, not one
  task.
- **`/supervisor`** — the multi-tick delegate-and-verify loop that runs across a
  set of tasks.

The boundary contract for this layer is not yet formalised.
