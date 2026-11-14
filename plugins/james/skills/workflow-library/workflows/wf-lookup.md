---
title: Lookup workflow
type: template
description: Lightweight lookup workflow for PKB reads, PKB writes, memory curation, and graph operations -- delegates directly to the custodian with no task creation, no pull or dump ceremony, and handback with premise-check Argdown.
tags: [workflow, lookup, pkb, graph, fast-path]
---

# Lookup Workflow

## Purpose and Scope

Governs Personal Knowledge Base (PKB) reads, PKB writes, memory curation, and graph operations. This template serves as a direct, ceremony-free execution path for fast PKB queries and graph maintenance. General web searches, filesystem lookups, and repository investigations remain outside this template and are resolved directly by internal delegates.

## Requirements

1. **Direct delegation to custodian**: Dispatch PKB reads, writes, and graph operations directly to the custodian (`pauli`).
2. **No task creation**: Do not create, queue, or compose a workflow onto a task on the task graph.
3. **No pull or dump ceremony**: Neither the caller nor the custodian executes `/james:pull`, `/james:dump`, `pkb_claim_task`, or `pkb_release_task`.
4. **Handback requirement**: Handback with a parser-valid Argdown argument per `james:premise-check`.
