---
id: orchestrator-boundary
title: Orchestrator Boundary — CLI Agent as Dispositor
type: spec
status: inbox
tier: core
depends_on: [workflow-constraints, enforcement]
tags: [spec, orchestration, enforcement, polecat, dispositor]
created: 2026-04-18
---

# Orchestrator Boundary — CLI Agent as Dispositor

**Status**: Proposed (design phase — implementation tasks filed separately)

## Giving Effect

- [[specs/workflow-constraints.md]] — Dispositor pattern (Part 2) — existing partial spec
- [[aops-core/skills/aops/SKILL.md]] — "Coordinator, not executor" instruction (current Level 2)
- [[aops-core/lib/gates/definitions.py]] — Gate definitions to extend
- [[polecat/defaults/claude-settings.json]] — Worker sandbox constraints

## Problem

The general CLI agent (the main Claude Code session) is supposed to be an orchestrator: it understands intent, creates tasks, and delegates execution to polecat workers. Currently, it frequently executes work directly:

- Bypasses polecat entirely, so worker failure modes go undetected
- Creates accountability gaps (no PKB task record for work done)
- Undermines the worker model — polecat efficiency issues are invisible when the orchestrator does the work itself
- No distinction between "planning session" and "execution session"

The constraint exists today as a **prompt-level instruction only** (Level 2 in the enforcement pyramid). The `aops` SKILL.md says "You are a coordinator, not an executor", but there is no mechanical gate preventing direct execution.

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

Enforcement follows the 5-layer model in [[specs/enforcement.md]]. Current state and targets:

### Current State: Level 2 Only

Prompt-level instruction in `aops` SKILL.md: "Delegate Implementation: Create tasks for workers to execute." This is sufficient for a well-behaved session but provides no detection when violated.

### Target State: Level 2 + Level 4 Detection

**Phase 1 (Level 2 — emphatic instruction):** Strengthen the prompt-level constraint.

- Add explicit "cannot do" list to HEURISTICS.md (not AXIOMS.md — orchestrator-specific behavior tables do not belong in universal axioms)
- Update `user_prompt_submit.py` hydrator to classify work requests and inject a reminder that they should be queued, not executed directly
- Add to routing table: `type: work-request` → inject "create a task and dispatch to polecat; do not execute directly"

**Phase 2 (Level 4 — detection):** Add PostToolUse detection hook.

- Detect when the orchestrator session writes to source files that are not framework files
- Classify Edit/Write calls against a "framework paths" allowlist vs. "project work paths"
- Alert (warn mode initially) when project work paths are written outside a polecat worktree

**Phase 3 (Level 4 — block mode):** Gate on non-framework writes.

- Move detection to PreToolUse
- Block Write/Edit to project source files unless `POLECAT_WORKER_MODE=1` is set (polecat workers set this in their sandbox)
- Exceptions: `specs/`, `docs/`, `.agents/`, `aops-core/` (framework files — orchestrator may edit these). The `aops-core/` exception covers configuration, hooks, and skill files (framework maintenance). New framework features requiring substantial implementation should still be delegated to polecat workers.

### Why Not Hard Block Immediately?

1. **Polecat efficiency baseline not yet verified**: If we block the orchestrator before confirming polecat can handle the work, we create a dead end. Verify efficiency first (see [[#polecat-efficiency-audit]]).
2. **Exception paths need design**: Skills, `/pull`, and explicit user requests need clean bypass mechanisms.
3. **Framework work exception**: The orchestrator maintains framework files (specs, hooks, skills). This must remain allowed.

## Minimum Bar Before Hard Lock

The orchestrator cannot be safely locked until:

1. Polecat workers can reliably execute tasks without stalling (P0 issues resolved)
2. PKB MCP is reachable from polecat sandbox containers
3. Turn budget is calibrated to avoid exhaustion on M-complexity tasks
4. The zero-changes detection loop is fully resolved (not just marked review)
5. `create_task` defaults to `inbox` (not `queued`), so half-baked tasks don't surface for dispatch before the orchestrator locks

## Related Design Decisions

- The dispositor pattern (Part 2 of [[specs/workflow-constraints.md]]) defines the conceptual boundary; this spec makes it operational.
- Task graduation gate ([[#task-graduation-spec]]) is a prerequisite: the orchestrator needs confidence that only properly-planned tasks enter the ready queue.
