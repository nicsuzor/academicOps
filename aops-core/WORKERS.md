---
name: workers
title: Worker Registry
type: index
category: framework
description: |
    Configurable worker types, capabilities, selection rules, and operational
    thresholds for the swarm-supervisor skill. Modify this file to customize
    worker dispatch behavior without changing the core skill prompt.
permalink: workers
tags: [framework, routing, workers, swarm, index]
---

> **Deployment-specific configuration** - Customize for your environment.
> Core dispatch protocol is in `skills/swarm-supervisor/SKILL.md`; this file
> contains only the configurable parameters.

# Worker Registry

Configuration for worker dispatch in the swarm-supervisor lifecycle.

## Worker Types

Available worker types and their profiles. Add or modify workers here to change
what the supervisor can dispatch to.

| Worker           | Capabilities                              | Cost | Speed | Max Concurrent | Best For                     |
| ---------------- | ----------------------------------------- | ---- | ----- | -------------- | ---------------------------- |
| `polecat-claude` | code, docs, refactor, test, debug         | 3    | 5     | 2              | Most tasks                   |
| `polecat-gemini` | code, docs, analysis, bulk-ops            | 1    | 3     | 4              | High-volume, simpler tasks   |
| `jules`          | deep-code, architecture, complex-refactor | 5    | 1     | 1              | Critical path, complex logic |

**Cost/Speed Scale**: 1-5 where 5 is highest. Cost = token/API expense, Speed = tasks/hour.

## Capability Definitions

Capabilities that can be assigned to workers. Used for task-to-worker matching.

| Capability         | Description                                     |
| ------------------ | ----------------------------------------------- |
| `code`             | Standard implementation work                    |
| `docs`             | Documentation, comments, README updates         |
| `refactor`         | Code restructuring without behavior change      |
| `test`             | Test writing and updates                        |
| `debug`            | Bug investigation and fixes                     |
| `analysis`         | Code review, spike investigations               |
| `bulk-ops`         | Repetitive changes across many files            |
| `deep-code`        | Complex algorithms, performance-critical code   |
| `architecture`     | System design changes, API contracts            |
| `complex-refactor` | Multi-file refactors with behavior preservation |
