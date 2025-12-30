---
title: Supervisor Skill
type: spec
status: implemented
permalink: supervisor-skill
tags:
  - spec
  - skill
  - orchestration
  - multi-agent
  - quality-gates
---

# Supervisor Skill

**Status**: Implemented

## Workflow

```mermaid
graph TD
    A[/supervise workflow] --> B[Load Workflow Template]
    B --> C[Phase 0: Planning]
    C --> D[Define Acceptance Criteria]
    D --> E[Create Plan]
    E --> F[Critic Review]
    F --> G{Approved?}
    G -->|No| E
    G -->|Yes| H[Lock Criteria]

    H --> I[Phase 1-3: Iteration]
    I --> J[Spawn Subagent]
    J --> K[One Atomic Task]
    K --> L[Verify Result]
    L --> M{Quality Gate?}
    M -->|Fail| N[Fix - Max 3 Tries]
    N --> J
    M -->|Pass| O[Commit + Push]

    O --> P[Phase 4: Gate]
    P --> Q{Scope Drift >20%?}
    Q -->|Yes| R[Stop - Get Approval]
    Q -->|No| S{More Steps?}
    S -->|Yes| I
    S -->|No| T[Phase 5: QA]

    T --> U[Spawn QA Agent]
    U --> V{All Criteria Met?}
    V -->|No| I
    V -->|Yes| W[Document + Report]
```

## Purpose

Orchestrate multi-agent workflows with quality gates, acceptance criteria lock, and scope drift detection. The supervisor enforces discipline on subagents to ensure reliable task completion.

## Problem Statement

Multi-agent workflows risk:
- Subagents making autonomous decisions that derail scope
- Acceptance criteria shifting mid-workflow
- Quality gates skipped under pressure
- Scope creep without detection
- Thrashing on the same file without progress
- Implementation details leaking to orchestration layer

## Solution

A pure orchestration skill with NO implementation tools. Can only spawn subagents, invoke skills, track progress, and ask questions. Enforces workflow templates, locked acceptance criteria, and mandatory quality gates.

## How It Works

### Invocation

```
/supervise {workflow-name} [task description]
```

Loads workflow template from `workflows/{name}.md` and applies it to the task.

### Core Contract (Inviolable)

**Allowed tools ONLY**: Task, Skill, TodoWrite, AskUserQuestion

The supervisor:
- ❌ CANNOT Read, Edit, Write, Bash, Grep, Glob
- ✅ CAN spawn subagents to do implementation work
- ✅ CAN invoke skills for specialized behavior
- ✅ CAN track progress with TodoWrite
- ✅ CAN ask user clarifying questions

### Five-Phase Workflow

| Phase | Purpose |
|-------|---------|
| 0. Planning | Load workflow, define acceptance criteria, create plan, critic review |
| 1-3. Iteration | Execute atomic steps per workflow template |
| 4. Gate | Verify quality, detect scope drift, check for thrashing |
| 5. Completion | QA verification, document outcomes, final report |

### Acceptance Criteria Lock

Before ANY implementation:
1. Define acceptance criteria with Plan agent
2. Present for user approval
3. Populate TodoWrite with ALL steps (including QA)
4. **Criteria become IMMUTABLE** once locked

If criteria cannot be met: HALT and report. No goal post shifting.

### Subagent Control

Supervisor gives subagents:
- ✅ Which file to modify
- ✅ Which tools to use
- ✅ Which skill to invoke
- ✅ Behavior/functionality needed
- ✅ Constraints from quality gate
- ✅ Success criteria

Subagent decides:
- ✅ Exact implementation approach
- ✅ How to structure the work

ONE atomic task at a time. Wait for report. Verify before next step.

### Quality Enforcement

**Scope Drift Detection**: If plan grows >20% from original, STOP and get user approval.

**Thrashing Detection**: If same file modified 3+ times without progress, STOP and ask for help.

**Iteration Protocol**: On failure, supervisor decides fix strategy and iterates (max 3 attempts). Does NOT ask user.

**Commit Each Cycle**: Changes committed AND pushed before next iteration.

## Relationships

### Depends On
- [[AXIOMS]] #1 (Categorical Imperative - supervisor is authorized exception), #22 (Acceptance Criteria Own Success)
- [[HEURISTICS]] #H14 (Mandatory Second Opinion), #H25 (User-Centric Criteria)
- Workflow templates in `workflows/` directory

### Uses
- [[critic]] agent - Plan review before implementation
- General-purpose subagents - Implementation work
- [[tasks-skill]] - Document outcomes

### Workflows (bundled)
- `workflows/tdd.md` - Test-first development
- `workflows/batch-review.md` - Parallel batch processing
- `workflows/skill-audit.md` - Skill content review

## Success Criteria

1. **No implementation leakage**: Supervisor never uses Read/Edit/Write/Bash
2. **Locked criteria**: Acceptance criteria immutable after approval
3. **Atomic steps**: Subagents do one task, report back, wait for next
4. **Scope control**: Drift >20% requires explicit approval
5. **Quality gates**: Every iteration passes workflow-specific validation
6. **Persistence**: Each cycle committed and pushed before next

## Design Rationale

**Why no implementation tools?**

Per [[AXIOMS]] #1: Actions must flow through generalizable patterns. The supervisor's job is orchestration, not implementation. Giving implementation tools would let it bypass the discipline it's meant to enforce. Tool restriction is mechanically enforced by Claude Code.

**Why acceptance criteria lock?**

Per [[AXIOMS]] #22: Acceptance criteria own success. Agents naturally rationalize and weaken criteria when implementation gets hard. Locking criteria before work begins prevents goal post shifting. If criteria can't be met, that's signal to HALT, not to weaken requirements.

**Why atomic steps?**

Subagents left unsupervised make autonomous decisions that accumulate into mess. One atomic step at a time keeps the supervisor in control. Wait for report, verify result, then issue next step.

**Why scope drift detection?**

Scope creep is invisible until it's too late. Quantifying plan growth (>20%) makes it visible. Getting explicit approval for scope expansion prevents runaway projects.
