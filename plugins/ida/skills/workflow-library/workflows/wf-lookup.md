---
title: Lookup workflow
type: template
description: Lightweight lookup workflow for PKB reads, writes, simple info lookups, and web searches -- delegates directly to Pauli with no task creation, no pull or dump ceremony, and handback with premise-check Argdown.
tags: [workflow, lookup, pkb, search, pauli, fast-path]
---

# Lookup Workflow

## Purpose and Scope

Governs all Personal Knowledge Base (PKB) reads and writes, simple information lookups, and web searches. This template serves as a direct, ceremony-free execution path for fast informational queries.

## Requirements

1. **Direct delegation to Pauli**: Dispatch the request directly to `pauli`.
2. **No task creation**: Do not create, queue, or reify a task on the task graph.
3. **No pull or dump ceremony**: Neither the caller nor `pauli` executes `/pull`, `/dump`, `claim_task`, or `release_task`.
4. **Handback requirement**: Handback with an Argdown argument in the correct format.
