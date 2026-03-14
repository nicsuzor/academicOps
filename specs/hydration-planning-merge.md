---
title: Hydration and Planning Merge
type: spec
status: proposal
tier: architecture
depends_on: [prompt-hydration, effectual-planning-agent, workflow-system-spec]
tags: [hydration, planning, decomposition, architecture]
---

# Hydration and Planning Merge

This specification outlines the architectural shift to merge Prompt Hydration with the Effectual Planning Agent. It transitions hydration from an **ephemeral decomposition** process (generating session-bound workplans) into a **formal decomposition** process (generating durable Task Graph nodes in the PKB).

## Problem Statement

Currently, the `prompt-hydrator` intercepts user intents and generates an ephemeral execution plan for the session. While this bridges the gap between terse prompts and actionable steps, the plan itself is discarded when the session ends unless explicitly saved.

Simultaneously, the Effectual Planning Agent (`effectual-planner.md`) provides formal "Mode 2: Epic Decomposition" via the `[[decompose]]` workflow. This mode breaks down work into concrete, durable Task Graph nodes in the PKB.

Having two separate systems for decomposition—one ephemeral (hydration) and one formal (planning)—creates redundancy and prevents the framework from fully leveraging the Task Graph as the primary coordinator and QA guarantee.

## The Solution: Hydration IS Formal Decomposition

We will merge the two concepts: **Hydration is simply the entry point for formal decomposition.**

When a user provides a prompt that requires decomposition, the Hydrator will no longer generate a transient markdown list of steps. Instead, it will interface directly with the Effectual Planning Agent's capabilities to create durable `task` and `epic` nodes in the PKB.

### Target Architecture

1. **Intent Reception**: `UserPromptSubmit` hook fires as usual.
2. **Hydrator Analysis**: The `prompt-hydrator` agent determines if the prompt represents a simple action, an existing task continuation, or a new scope requiring decomposition.
3. **Formal Decomposition**: If new scope is detected, the Hydrator invokes the planning module's Mode 2 (Epic Decomposition).
4. **Graph Artifacts**: Instead of outputting a `<hydration_result>` with a markdown "Execution Plan," the system creates formal tasks in the PKB using tools like `mcp__pkb__decompose_task`.
5. **Execution Handoff**: The session begins with the agent bound to the newly created leaf tasks in the graph, subject to standard QA and verification gates.

## Conceptual Distinction: Hydrator vs Effectual Planner

A critical question in this merge is whether the Hydrator and the Effectual Planner are functionally the same thing. They both share the same underlying LLM mechanics and use high-level workflows to drive decomposition, but they serve distinct architectural purposes:

1. **Workflows as Guardrails (The Hydrator's Primary Role)**:
   - **Context Independence**: Guardrails can be set without full PKB access. This makes the Hydrator highly portable.
   - **Function**: The Hydrator intercepts a vague command, identifies the workflow, and outputs the _process steps_ needed to plan or execute safely. It acts as the tactical boundary providing JIT (Just-In-Time) execution context to agents.
2. **Workflows as Strategic Plans (The Planner's Primary Role)**:
   - **Context Dependence**: Strategic planning _requires_ full PKB access to map dependencies, surface assumptions, and coordinate across sessions.
   - **Function**: The Planner takes the process steps identified by the Hydrator and embeds them into the semantic graph, creating a formal Execution Plan of durable nodes.

While the boundaries blur, the distinction allows for a flexible deployment model where guardrails can run anywhere, but deep strategic planning remains anchored to the PKB.

## Phase 1 Prototype Requirements

To prove this model, the first working prototype of the merged system must support two deployment paradigms for the Hydrator, operating from a secure machine:

1. **JIT Mode (Portable/Live)**: The Hydrator provides input _anywhere_ to agents as they need them. In this mode, the Hydrator finds relevant execution context (memories) to help a polecat agent _execute_ immediately, without relying on the PKB task graph.
2. **Advance Mode (Graph-Integrated)**: The Hydrator updates the PKB task with information for any agent to read _with_ the task it pulls. The Effectual Planner takes the vague command and decomposes it into a series of PKB steps for execution later.

### Prototype Deliverables

- **Memories (Context)**: The Hydrator finds relevant context to help an agent **execute** (delivered live or via a task file).
- **Workflows (Guardrails)**: The Hydrator reads workflows and outputs relevant process steps needed to **plan** tasks (delivered live to the Effectual Planner).
- **Execution Plan (Strategy)**: The Effectual Planner translates the vague command into a durable series of execution steps (delivered via PKB task files to polecat workers).

### 1. `prompt-hydrator` Agent Update

- **Remove**: The requirement to generate a transient "Execution Plan" list.
- **Add**: Instructions to invoke formal decomposition tools (`mcp__pkb__create_task`, `mcp__pkb__decompose_task`) when a new epic or complex intent is detected.
- **Modify**: The `<hydration_result>` schema to output a list of _created Task Graph nodes_ rather than ephemeral steps.

### 2. `effectual-planning-agent` Integration

- The Hydrator will act as the automatic, conversational frontend for Mode 2 (Epic Decomposition).
- The planning module's heuristics for identifying assumptions, downstream weights, and task sizing will be applied at the moment of hydration.

### 3. Hook Redirection (`user_prompt_submit.py`)

- The hook must wait for the PKB artifacts to be created before handing control back to the main session agent, ensuring the session starts strictly bound to a tracked Task Graph node.

## Success Criteria

1. **No Ephemeral Plans**: Terse prompts resulting in multi-step work automatically generate durable PKB tasks.
2. **Unified Flow**: The `/planning` skill and the pre-prompt hydration phase share the exact same decomposition logic and graph creation tools.
3. **Graph-Driven Coordination**: Agents execute work by traversing and completing the formal nodes created during hydration, never relying on a transient markdown list.
