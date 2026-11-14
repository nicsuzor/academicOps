---
title: Dispatch workflow
type: template
description: Direct worker dispatch workflow for headless execution and worker dispatch -- delegates directly to the dispatcher to launch containers running /james:supervise for repo-scoped epic tasks or /james:pull for plain leaf tasks, with no child task creation, no pull or dump ceremony, and handback with james:premise-check Argdown.
tags: [workflow, dispatch, worker, execution, fast-path]
---

# Dispatch Workflow

## Purpose and Scope

Governs direct delegation of headless execution and worker dispatches to the dispatcher. The dispatcher never executes code directly; when invoked in an interactive session, the dispatcher launches isolated worker environments running `/james:supervise` for repo-scoped epic tasks or `/james:pull` for plain leaf tasks against the existing outer task without creating additional child tasks on the task graph.

## Requirements

1. **Direct delegation to dispatcher**: Dispatch the request directly to the dispatcher to launch containers running `/james:supervise` (for repo-scoped epic tasks) or `/james:pull` (for plain leaf tasks).
2. **No child task creation**: Do not create additional child tasks on the task graph; dispatch against the existing outer task.
3. **No pull or dump ceremony**: Neither the caller nor the dispatcher executes `/james:pull`, `/james:dump`, `claim_task`, or `release_task` (the dispatched worker claims and releases).
4. **Handback requirement**: Hand back with a parser-valid `james:premise-check` Argdown argument.
