---
id: orchestrator-boundary
title: Orchestrator Boundary — CLI Agent as Dispositor
type: spec
status: inbox
tier: core
depends_on: [enforcement]
tags: [spec, orchestration, enforcement, polecat, dispositor]
created: 2026-04-18
---

# Orchestrator Boundary — CLI Agent as Dispositor

**Status**: Proposed (design phase — implementation tasks filed separately)

## Giving Effect

- [[aops-core/skills/aops/SKILL.md]] — "Coordinator, not executor" instruction

## Problem

The general CLI agent (the main Claude Code session) is supposed to be an orchestrator: it understands intent, creates tasks, and delegates execution to polecat workers. Left unconstrained, it instead executes work directly — bypassing polecat so worker failure modes go undetected, creating accountability gaps (no PKB task record for the work), and undermining the worker model. The constraint exists today as a prompt-level instruction only; there is no mechanical gate preventing direct execution.

## What the CLI Agent Can and Cannot Do

### Can Do (Orchestrator Scope)

| Action                                    | Rationale                           |
| ----------------------------------------- | ----------------------------------- |
| Read files for context                    | Read-only, no state change          |
| Create/update/query tasks via PKB MCP     | Planning and routing, not execution |
| Run `/pull` explicitly when user requests | `/pull` IS the execution path       |
| Run skills invoked explicitly by user     | User intent is direct execution     |
| Answer questions                          | No state changes                    |
| Decompose epics into subtasks             | Planning work                       |
| Run `/daily`, `/planner`, `/dump`         | Meta-management, not feature work   |
| Run `polecat` CLI commands                | Dispatch, not direct execution      |
| File follow-up tasks                      | Planning                            |

### Cannot Do (Worker Scope)

| Action                                  | Rationale                         |
| --------------------------------------- | --------------------------------- |
| Edit source files for feature work      | This is polecat's job             |
| Write new implementation code           | Dispatch the task instead         |
| Run tests as part of task execution     | Worker verifies its own work      |
| Make feature commits                    | Polecat commits on its own branch |
| Push code and open PRs for feature work | Polecat handles its own PR        |

**Exception**: Hotfixes, one-liners, and urgent fixes may bypass this boundary only when the user explicitly requests direct execution. The agent cannot judge whether work is "too small to queue" — that classification belongs to the user.

## Enforcement Strategy

Enforcement follows the layered model in [[specs/enforcement.md]]: today the boundary is a prompt-level instruction only ("Delegate Implementation: Create tasks for workers to execute" in `aops` SKILL.md), sufficient for a well-behaved session but with no detection when violated. The target state adds a detection layer — flagging when the orchestrator session writes to project source files outside a polecat worktree — before escalating to a hard pre-execution block. Framework files (`specs/`, `docs/`, `.agents/`, `aops-core/`) remain an explicit exception the orchestrator may always edit directly.

A hard block is deferred until: polecat workers reliably execute tasks without stalling, the PKB MCP is reachable from polecat sandboxes, turn budgets are calibrated for M-complexity tasks, and `create_task` defaults to `inbox` rather than `queued` (so half-baked tasks don't surface for dispatch before the boundary locks).
