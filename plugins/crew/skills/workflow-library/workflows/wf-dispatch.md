---
title: Dispatch workflow
type: template
description: Direct worker dispatch workflow for headless execution -- reifies the task, then delegates to the dispatcher to launch worker containers seeded with its instructions, with no child task creation and Argdown-only handback per premise-check.
tags: [workflow, dispatch, worker, execution, fast-path]
---

# Dispatch Workflow

## Purpose and Scope

Governs direct delegation of headless execution to the dispatcher. The dispatcher never executes code directly; in an interactive session, it launches isolated worker containers against the existing outer task without creating child tasks on the task graph. A worker container has no plugins and no PKB access; it receives the task's reified instructions as its prompt.

## Requirements

1. **Reify, then delegate to dispatcher**: Reify the task (`/reify`) just before dispatch so its instructions are complete without PKB knowledge, then dispatch the request directly to the dispatcher to launch worker containers.
2. **No child task creation**: Dispatch against the existing outer task without minting child tasks on the graph.
3. **No pull or dump ceremony**: Neither the caller nor the dispatcher executes `/pull`, `/dump`, or task claim or release; the dispatched worker runs none of them either, and hands back through the final output message the dispatch service records on the task.
4. **Handback requirement**: Report back solely in clean Argdown prose per `premise-check`, stating the original ask upfront and quoting deciding dispatch outputs inline.
