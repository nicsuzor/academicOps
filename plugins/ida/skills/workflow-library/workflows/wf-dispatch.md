---
title: Dispatch workflow
type: template
description: Direct worker dispatch workflow for headless execution -- delegates directly to the dispatcher to launch worker containers running /supervise for repo-scoped epic tasks or /pull for plain leaf tasks, with no child task creation and Argdown handback.
tags: [workflow, dispatch, worker, execution, fast-path]
---

# Dispatch Workflow

## Purpose and Scope

Governs direct delegation of headless execution to the dispatcher. The dispatcher never executes code directly; in an interactive session, it launches isolated worker containers running `/supervise` for repo-scoped epic tasks or `/pull` for plain leaf tasks against the existing outer task without creating child tasks on the task graph.

## Requirements

1. **Direct delegation to dispatcher**: Dispatch the request directly to the dispatcher to launch worker containers running `/supervise` (repo-scoped epic tasks) or `/pull` (plain leaf tasks).
2. **No child task creation**: Dispatch against the existing outer task without minting child tasks on the graph.
3. **No pull or dump ceremony**: Neither the caller nor the dispatcher executes `/pull`, `/dump`, or task claim or release (the dispatched worker claims and releases).
4. **Handback requirement**: Hand back with a valid `premise-check` Argdown argument.
