---
title: Dispatch workflow
type: template
description: Direct worker dispatch workflow for headless execution -- delegates directly to the dispatcher to launch worker containers running /ida:pull, with no child task creation and Argdown-only handback per premise-check.
tags: [workflow, dispatch, worker, execution, fast-path]
---

# Dispatch Workflow

## Purpose and Scope

Governs direct delegation of headless execution to the dispatcher. The dispatcher never executes code directly; in an interactive session, it launches isolated worker containers running `/ida:pull` against the existing outer task without creating child tasks on the task graph.

## Requirements

1. **Direct delegation to dispatcher**: Dispatch the request directly to the dispatcher to launch worker containers running `/ida:pull`.
2. **No child task creation**: Dispatch against the existing outer task without minting child tasks on the graph.
3. **No pull or dump ceremony**: Neither the caller nor the dispatcher executes `/pull`, `/dump`, or task claim or release (the dispatched worker claims and releases).
4. **Handback requirement**: Report back solely in clean Argdown prose per `premise-check`, stating the original ask upfront and quoting deciding dispatch outputs inline.
