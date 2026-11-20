---
title: Lookup workflow
type: template
description: Lightweight lookup workflow for PKB reads, PKB writes, memory curation, and graph operations -- delegates directly to the custodian with no task creation, no pull or dump ceremony, and handback with premise-check Argdown.
tags: [workflow, lookup, pkb, graph, fast-path]
---

# Lookup Workflow

## Purpose and Scope

Governs Personal Knowledge Base (PKB) reads, PKB writes, memory curation, graph operations, and checks for existing, related, or overlapping open work. Provides a direct, ceremony-free execution path for fast PKB queries, overlap checks, and graph maintenance. General web searches, filesystem lookups, and repository investigations remain outside this workflow and are handled directly by internal delegates.

## Requirements

1. **Direct delegation to custodian**: Dispatch PKB reads, writes, graph operations, and overlap searches directly to the PKB custodian, who queries with short (5--15 word) conceptual queries distilled from the ask rather than raw prompt text.
2. **No task creation**: Do not create, queue, or reify a task on the task graph.
3. **No pull or dump ceremony**: Neither the caller nor the custodian executes `/pull`, `/dump`, or task claim or release.
4. **Handback requirement**: Hand back with a valid `premise-check` Argdown argument.
