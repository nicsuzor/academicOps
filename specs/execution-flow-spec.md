---
title: Execution Flow Document Specification
type: spec
category: spec
status: implemented
permalink: execution-flow-spec
tags: [framework, documentation, architecture]
---

# Execution Flow Document Specification

Governs the structure and content of `FLOW.md`.

## Purpose

The execution flow document shows **where the framework injects control** during a Claude Code session. It is the architectural map for understanding how prompts flow through the system.

See [[specs/gate-agent-architecture]] for the unified gate system design that defines how pre-action and post-action gates coordinate via shared session state.

## Design Principles

### 1. Swimlane Layout: Main Agent with Parallel Subprocesses

The diagram uses a three-lane swimlane structure:

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   MAIN AGENT    │  │     HOOKS       │  │   SUBAGENTS     │
│   (continuous   │  │   (discrete     │  │   (discrete     │
│    vertical     │  │    invocations) │  │    invocations) │
│    spine)       │  │                 │  │                 │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ Session Start   │──│ SessionStart    │  │                 │
│       ↓         │←─│                 │  │                 │
│ User prompt     │──│ UserPromptSubmit│  │                 │
│       ↓         │←─│                 │  │                 │
│ Spawn hydrator  │──│─────────────────│──│ prompt-hydrator │
│       ↓         │←─│─────────────────│←─│                 │
│ Call tool       │──│ PreToolUse      │  │                 │
│       ↓         │←─│                 │  │                 │
│ Receive result  │──│ PostToolUse     │──│ custodiet       │
│       ↓         │←─│                 │←─│                 │
│ Session End     │──│ Stop            │──│ remember        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Key principles**:

1. **Main Agent is continuous**: A single vertical flow showing the agent's progression through a session
2. **Hooks appear alongside**: Discrete boxes at the vertical level where they fire, with arrows showing data flow direction
3. **Subagents appear alongside**: Discrete boxes showing when Task() spawns them, with return arrows for results
4. **Cross-lane arrows show interaction**: Solid arrows for invocation, return arrows for responses
5. **Vertical alignment indicates timing**: Components at the same vertical level interact at that point in execution

**Rationale**: This layout shows the main agent's continuous flow while making hook/subagent intervention points visible. Reading down the left column gives the agent's journey; reading across at any row shows what external components are invoked.

### 2. Separate Hard Tissue from Soft Tissue

| Type        | Contains                                     | Location               |
| ----------- | -------------------------------------------- | ---------------------- |
| Hard tissue | Mechanics (Python, trigger logic)            | `hooks/*.py`           |
| Soft tissue | Configurable content (prompts, instructions) | `hooks/templates/*.md` |

**Rationale**: Editable content should be in markdown, not buried in code.

### 3. Reference, Don't Duplicate

- Link to `WORKFLOWS.md` for routing table (don't duplicate it)
- Link to `RULES.md` for guardrail definitions
- Link to `agents/*.md` for agent behavior
- Link to specs for detailed behavior

**Rationale**: Single source of truth. The flow doc shows structure, not content.

### 4. Show Trigger Mechanisms

For each hook, show the data flow:

```
Event fires → Hook receives JSON → Template loaded → Placeholders substituted → JSON returned
```

**Rationale**: Understanding HOW hooks work enables maintenance.

### 5. Track Templates in Hook Registry

The Hook Registry table must include a Template/Content column showing what configurable content each hook uses.

## Required Sections

1. **Universal Execution Flow** - Main diagram showing all prompts flow through boxes 1-4
2. **Workflow Implementations** - Table of Box 4 variants with links to specs
3. **Hook Trigger Mechanism** - How hooks receive input and return context
4. **Hook Registry** - Table of all hooks with scripts, templates, and purposes
5. **Session State** - Unified state file (`/tmp/claude-session/state-{hash}.json`) that coordinates gates
6. **Quick Capture** - /q and /do relationship

## Acceptance Criteria

1. Main flow diagram uses swimlane layout: Main Agent (continuous vertical) | Hooks (discrete) | Subagents (discrete)
2. Cross-lane arrows show invocation and return data flow
3. Vertical alignment indicates when components interact in the execution timeline
4. Every hook in registry has its template/content source identified
5. No duplicated content from WORKFLOWS.md or RULES.md
6. All implementation files are linked, not described inline
7. Mermaid diagrams render correctly
