---
title: Dispatch workflow
type: template
description: Direct worker dispatch workflow for headless execution and worker dispatch -- delegates directly to Sara with no child task creation, no pull or dump ceremony, and handback with premise-check Argdown.
tags: [workflow, dispatch, worker, execution, sara, fast-path]
---

# Dispatch Workflow

## Purpose and Scope

Governs direct delegation of headless execution and worker dispatches to Sara. Sara never executes code directly; when invoked in an interactive session, Sara dispatches isolated polecat workers against the existing outer task created by Face Ida without creating additional child tasks on the task graph.

## Requirements

1. **Direct delegation to Sara**: Dispatch the request directly to `sara`.
2. **No child task creation**: Do not create additional child tasks on the task graph; dispatch against the existing outer task.
3. **No pull or dump ceremony**: Neither the caller nor `sara` executes `/pull`, `/dump`, `claim_task`, or `release_task` (the worker running under `/dispatch` claims and releases).
4. **Handback requirement**: Handback with an Argdown argument in the correct format.
