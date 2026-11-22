---
title: Dispatch workflow
type: template
description: Direct worker dispatch workflow for headless execution -- delegates directly to the dispatcher to launch worker containers running /supervise for repo-scoped epic tasks or /pull for plain leaf tasks, with no child task creation and Argdown-only handback per premise-check.
tags: [workflow, dispatch, worker, execution, fast-path]
---

# Dispatch Workflow

## Purpose and Scope

Governs direct delegation of headless polecat execution to `sara` (the sole dispatcher). Other agents never dispatch polecats directly; `sara` launches isolated polecat containers fire-and-forget running `/ida:supervise` (complex/composite tasks) or `/ida:pull` (atomic leaf tasks), calibrating model selection from the `fast` tier default, against the existing outer task without creating child tasks on the task graph.

## Requirements

1. **Direct delegation to `sara`**: Hand off the queued task to `sara` (`sara:dispatch`) to launch isolated polecat containers fire-and-forget running `/ida:supervise` or `/ida:pull` by complexity, defaulting model selection to `fast`.
2. **No child task creation**: Dispatch against the existing outer task without minting child tasks on the graph.
3. **No pull or dump ceremony**: Neither the caller nor the dispatcher executes `/pull`, `/dump`, or task claim or release (the dispatched worker claims and releases).
4. **Handback requirement**: Report back solely in clean Argdown prose per `premise-check`, stating the original ask upfront and quoting deciding dispatch outputs inline.
