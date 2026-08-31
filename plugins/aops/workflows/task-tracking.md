---
title: Task Tracking
type: template
category: fragment
description: Bookkeeping fragment to search for duplicates, wire parent epics, claim tasks, and log completion pointers. Composed into most operational workflows. Not a standalone workflow.
tags: [task-tracking, bookkeeping, graph, lifecycle, fragment]
---

# Fragment: Task Tracking

Standard task lifecycle fragment for graph and backlog management.

## 1. Duplicate Search

- Search existing tasks and backlog for matching items before creating a new node.
- If a match exists, attach to the existing task instead of creating duplicate work.

## 2. Parent Resolution and Creation

- Resolve parent context (active epic -> project root -> unassigned).
- Create task with explicit title, background, and acceptance criteria.

## 3. Claim and Execution Logging

- Claim the task (set status to in-progress) to establish worker ownership.
- Update task checklist items as work progresses.

## 4. Completion and Pointers

- Record output pointers (commit hashes, PR links, artifact paths) under task pointers.
- Set task status to completed (`done` or `merge_ready`).
