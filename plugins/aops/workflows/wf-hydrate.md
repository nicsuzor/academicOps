---
title: Context Hydration
type: template
category: gate
description: Assemble relevant context, locate existing work, and resolve ambiguities before starting execution on a task. Select at the beginning of any non-trivial task. Not for task intake (use `/q`) or execution.
tags: [hydration, context, disambiguation, setup, gate]
---

# Gate: Context Hydration

Pre-execution discovery pass to ensure work operates on true, current system context.

## 1. Disambiguation and Scope Resolution

- Resolve ambiguous terms and pronouns in `<task-ask>`.
- Search the knowledge graph and codebase to locate existing related tasks, specs, and prior work.

## 2. Environment and Branch Verification

- Verify current working directory, active git branch, and repository clean status.
- Ensure branch is rebased on latest upstream changes.

## 3. Dependency and Prerequisite Check

- Check that required environment variables, tool binaries, credentials, and dependencies exist.
- Confirm prerequisite tasks are completed.

## Exit Condition

Unambiguous scope, verified workspace environment, and confirmed prerequisites.
