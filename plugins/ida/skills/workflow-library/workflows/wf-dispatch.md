---
title: Dispatch workflow
type: template
description: Direct worker dispatch workflow for headless execution and code tasks -- delegates directly to Sara with no task creation, no pull or dump ceremony, and handback with premise-check Argdown.
tags: [workflow, dispatch, worker, execution, sara, fast-path]
---

# Dispatch Workflow

## Purpose and Scope

Governs direct delegation of headless execution, code tasks, and worker dispatches to Sara. This template provides a ceremony-free dispatch escape hatch.

## Requirements

1. **Direct delegation to Sara**: Dispatch the request directly to `sara`.
2. **No task creation**: Do not create, queue, or reify a task on the task graph.
3. **No pull or dump ceremony**: Neither the caller nor `sara` executes `/pull`, `/dump`, `claim_task`, or `release_task`.
4. **Handback requirement**: Handback with an Argdown argument in the correct format.
