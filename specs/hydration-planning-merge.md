---
title: Hydration and Planning Merge
type: spec
status: proposal
tier: architecture
depends_on: [prompt-hydration, effectual-planning-agent, workflow-system-spec]
tags: [hydration, planning, decomposition, architecture]
---

# Hydration and Planning Merge

This specification outlines the architectural shift that redefines Prompt Hydration as **Task Enrichment**. Hydration is something done TO tasks: given a terse prompt, the Hydrator creates or binds to a Task Graph node and enriches it with execution context (memories, workflow steps, acceptance criteria, guardrails) so that any worker can execute it.

## Problem Statement

Currently, the `prompt-hydrator` intercepts user intents and generates an ephemeral execution plan for the session. The plan is discarded when the session ends unless explicitly saved. This means:

1. Workers start from scratch — no prior context, no guardrails, no acceptance criteria unless manually assembled.
2. The same context-gathering work is repeated every session.
3. There is no durable record of what execution context was available when work was attempted.

Simultaneously, the Effectual Planning Agent provides formal decomposition into durable Task Graph nodes. But decomposition and enrichment are different operations — a task can exist in the graph without having the context a worker needs to execute it.

## The Solution: Hydration IS Task Enrichment

**Hydration is something done TO tasks.** It is the process of enriching a Task Graph node with the context a worker needs to execute it.

When a user provides a prompt, the Hydrator:

1. Extracts intent (base-extract: every atomic unit captured)
2. Binds to an existing task or creates a new one in the PKB
3. Searches PKB for relevant memories, related tasks, and dependencies
4. Selects and reads the applicable workflow
5. Writes enriched context into the task body: memories, workflow steps, acceptance criteria, guardrails

The enriched task is a durable artifact. Any worker — local or remote — can pull it and execute without additional context gathering.

### Target Architecture

1. **Intent Reception**: User prompt arrives (via hook, batch queue, or manual invocation).
2. **Hydrator Analysis**: The task-hydrator determines if the prompt maps to an existing task or requires a new one.
3. **Task Enrichment**: The Hydrator searches PKB for relevant context and writes it into the task body.
4. **Scope Detection**: If the work is complex/multi-session, the Hydrator flags `needs_decomposition: true` — it does NOT decompose itself.
5. **Execution Handoff**: A worker pulls the enriched task and executes with full context. The Effectual Planner handles decomposition separately when flagged.

## Conceptual Distinction: Hydrator vs Effectual Planner

The Hydrator and the Effectual Planner are complementary, not redundant. They operate on different axes:

| Aspect          | Task Hydrator                                | Effectual Planner                            |
| --------------- | -------------------------------------------- | -------------------------------------------- |
| **Operates on** | Individual tasks                             | Task hierarchies (Epic → Task)               |
| **Function**    | Enriches a task with execution context       | Decomposes complex work into task trees      |
| **PKB access**  | Full (memories, tasks, documents)            | Full (graph topology, dependencies, metrics) |
| **Output**      | Enriched task body (context + workflow + AC) | New task nodes in the graph                  |
| **When**        | Before a worker pulls a task                 | When complex work needs structuring          |
| **Model**       | Sonnet (speed)                               | Opus (strategic depth)                       |

**Both require PKB access. Both run on the secure machine.** The earlier framing of the Hydrator as "portable" or "context-independent" was aspirational but architecturally incorrect — memories live in the PKB, and the Hydrator needs them.

The clean boundary: **Planner creates tasks. Hydrator enriches them.** When the Hydrator detects work that needs decomposition, it flags it for the Planner rather than decomposing itself.

## Phase 1 Prototype: Task Enrichment

Phase 1 proves the core model: **the Hydrator enriches tasks with context so workers can execute them.**

The Hydrator runs on the secure machine with full PKB access. Given a terse prompt or task ID, it produces an enriched task that any worker can pull and execute without additional context gathering.

### What the Hydrator Writes Into a Task

```markdown
## Intent

[1-sentence: what the user wants accomplished]

## Context

[Relevant memories and prior knowledge — 3-5 bullets max]

## Workflow: [workflow-name]

1. [Process step from workflow]
2. [Process step]
3. CHECKPOINT: [verification step]
4. [Completion step]

## Acceptance Criteria

1. [Measurable outcome]
2. [Measurable outcome]

## Dependencies

- blocking-task-id: title (status)

## Guardrails

- Applicable constraints
```

### 1. `task-hydrator` Agent (new)

A new agent definition (`agents/task-hydrator.md`) replaces the ephemeral output model:

- **Input**: Terse prompt + optional task ID
- **Tools**: `read_file`, PKB search/get/create/update, `retrieve_memory`, `get_dependency_tree`, `task_search`
- **Output**: Enriched task node in PKB
- **Speed target**: ≤5 PKB tool calls, <15 seconds
- **Scope detection**: Flags `needs_decomposition: true` for complex work — does NOT decompose

### 2. Entry Points

Two ways to invoke the Hydrator:

1. **Interactive**: Hook fires → main agent spawns task-hydrator → enriched task created → main agent works on it (same session)
2. **Batch**: Supervisor identifies unenriched tasks → spawns task-hydrator for each → workers pull enriched tasks later

### 3. Planner Handoff

When the Hydrator flags `needs_decomposition: true`, the Effectual Planner (Mode 2: Epic Decomposition) takes over. The Planner creates the subtask tree; the Hydrator then enriches each leaf task before workers pull them.

### What's Deferred to Phase 2

- **JIT Mode** (live context delivery to remote workers without task persistence)
- **Sensitive information filtering** (abstracting memories for external workers)
- **Hook architecture changes** (the existing spawn-subagent pattern works for Phase 1)

## Success Criteria

1. **Enriched tasks are self-contained**: A worker pulling an enriched task can begin execution without searching for context, reading workflows, or querying memories itself.
2. **Context is durable**: The execution context (memories, workflow steps, AC) persists in the task body — not lost when a session ends.
3. **Scope is correctly detected**: Complex/multi-step work is flagged for decomposition, not silently treated as a single task.
4. **Speed**: Task enrichment completes in <15 seconds with ≤5 PKB tool calls.
