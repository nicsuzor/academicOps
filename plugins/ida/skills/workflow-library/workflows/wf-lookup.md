---
title: Lookup workflow
type: template
description: Lightweight lookup workflow for PKB reads, PKB writes, memory curation, and graph operations -- delegates directly to Pauli with no task creation, no pull or dump ceremony, and handback with premise-check Argdown.
tags: [workflow, lookup, pkb, graph, pauli, fast-path]
---

# Lookup Workflow

## Purpose and Scope

Governs Personal Knowledge Base (PKB) reads, PKB writes, memory curation, and graph operations. This template serves as a direct, ceremony-free execution path for fast PKB queries and graph maintenance. General web searches, filesystem lookups, and repository investigations remain outside this template and are resolved directly by internal subagents (Sub-Ida).

## Requirements

1. **Direct delegation to Pauli**: Dispatch PKB reads, writes, and graph operations directly to `pauli`.
2. **No task creation**: Do not create, queue, or reify a task on the task graph.
3. **No pull or dump ceremony**: Neither the caller nor `pauli` executes `/pull`, `/dump`, `claim_task`, or `release_task`.
4. **Handback requirement**: Handback with an Argdown argument in the correct format.
