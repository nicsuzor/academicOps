---
title: Lookup workflow
type: template
description: Lightweight lookup workflow for PKB reads, PKB writes, memory curation, and graph operations -- delegates directly to the custodian with no task creation, no pull or dump ceremony, and Argdown-only handback per premise-check.
tags: [workflow, lookup, pkb, graph, fast-path]
---

# Lookup Workflow

## Purpose and Scope

Governs Personal Knowledge Base (PKB) reads, PKB writes, memory curation, graph operations, and checks for existing, related, or overlapping open work. Provides a direct, ceremony-free execution path for fast PKB queries, overlap checks, and graph maintenance. General web searches, filesystem lookups, and repository investigations remain outside this workflow and are handled directly by internal delegates.

## Requirements

1. **Direct delegation to custodian**: Dispatch PKB reads, writes, graph operations, and overlap searches directly to the PKB custodian.
2. **No task creation**: Do not create, queue, or reify a task on the task graph.
3. **No pull or dump ceremony**: Neither the caller nor the custodian executes `/pull`, `/dump`, or task claim or release.
4. **Handback requirement**: Report back solely in clean Argdown prose per `premise-check`, stating the original ask upfront and quoting deciding evidence inline.
