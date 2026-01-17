---
name: workflows
title: Workflow Index
type: index
category: framework
description: Index of all available workflows for routing and execution
permalink: workflows
tags: [framework, routing, workflows, index]
---


<!-- NS: file should be dynamically generated after any change in workflows/. format should be revised to ensure agent has sufficient detail to make the choice between workflows -->

# Workflow Index

All work MUST follow one of the workflows in this index. No exceptions.

## Available Workflows

### Development Workflows

#### [[feature-dev]]
- **ID**: `feature-dev`
- **Title**: Feature Development Workflow
- **Category**: development
- **When to use**: Adding new features, complex modifications, architectural decisions
- **Key steps**: User story → Acceptance criteria → Spec review → Approval → TDD → QA verification
- **Quality gates**: Critic review, TDD, QA verification

#### [[minor-edit]]
- **ID**: `minor-edit`
- **Title**: Minor Edit Workflow
- **Category**: development
- **When to use**: Small bug fixes, typo fixes, minor refactoring, simple one-file changes
- **Key steps**: Claim issue → Write test → Implement → Verify → Commit
- **Quality gates**: TDD, test checkpoint

#### [[debugging]]
- **ID**: `debugging`
- **Title**: Debugging Workflow
- **Category**: development
- **When to use**: Investigating bugs, root cause analysis, reproducing issues
- **Key steps**: Claim issue → Define success → Design durable test → Investigate → Report findings
- **Quality gates**: Reproducible test

#### [[tdd-cycle]]
- **ID**: `tdd-cycle`
- **Title**: Test-Driven Development Cycle
- **Category**: development
- **When to use**: Implementing features, fixing bugs, any testable code change
- **Key steps**: Red (failing test) → Green (minimal implementation) → Refactor → Commit
- **Quality gates**: Tests pass, no regression

### Planning Workflows

#### [[decompose]]
- **ID**: `decompose`
- **Title**: Progressive Decomposition Workflow
- **Category**: planning
- **When to use**: Multi-month/year goals, uncertain path forward, need to figure out steps before acting
- **Key steps**: Articulate goal → Surface assumptions → Identify coarse components → Sequence by information value → Expand just-in-time → Mark ready work
- **Quality gates**: Goal articulated, assumptions surfaced, at least one actionable task identified
- **Scope signals**: Goal-level requests, "write a paper", "build a feature", "plan the project"

#### [[spec-review]]
- **ID**: `spec-review`
- **Title**: Spec Review Loop (Critic Feedback)
- **Category**: planning
- **When to use**: Designing features, planning refactoring, architectural decisions
- **Key steps**: Create spec → Invoke critic → Analyze feedback → Iterate → Converge
- **Quality gates**: Critic approval, convergence criteria

### Quality Assurance Workflows

#### [[qa-demo]]
- **ID**: `qa-demo`
- **Title**: QA Verification Demo
- **Category**: quality-assurance
- **When to use**: Before completing features, after tests pass, for user-facing changes
- **Key steps**: Gather context → Invoke QA → Analyze verdict → Fix issues → Re-verify
- **Quality gates**: QA verification (functionality, quality, completeness)

### Operations Workflows

#### [[bd-workflow]]
- **ID**: `bd-workflow`
- **Title**: BD Issue Tracking Workflow
- **Category**: operations
- **When to use**: Beginning and end of any tracked work (features, bugs, planning, batch ops)
- **Key steps**: Check for issues → Create if needed → Mark in-progress → Do work → Close and sync
- **Quality gates**: Issue tracked, work completed, issue closed, bd synced

#### [[batch-processing]]
- **ID**: `batch-processing`
- **Title**: Batch Processing Workflow
- **Category**: operations
- **When to use**: Processing multiple similar items, batch updates, parallel work
- **Key steps**: Claim issue → Identify scope → Spawn parallel agents → Monitor → Checkpoint → Commit
- **Quality gates**: All items processed, results verified

### Information Workflows

#### [[simple-question]]
- **ID**: `simple-question`
- **Title**: Simple Question Workflow
- **Category**: information
- **When to use**: Pure informational questions, no modifications needed
- **Key steps**: Answer question → HALT
- **Quality gates**: None (information only)

### Routing Workflows

#### [[direct-skill]]
- **ID**: `direct-skill`
- **Title**: Direct Skill/Command Invocation
- **Category**: routing
- **When to use**: User request maps 1:1 to existing skill/command
- **Key steps**: Identify skill → Invoke directly (no TodoWrite wrapping)
- **Quality gates**: None (delegated to skill)

## Workflow Selection Guide

### Decision Tree

```
User request
    │
    ├─ Explicit skill mentioned? ─────────────> [[direct-skill]]
    │
    ├─ Simple question only? ─────────────────> [[simple-question]]
    │
    ├─ Goal-level / multi-month work? ────────> [[decompose]]
    │   (uncertain path, need to figure out steps)
    │
    ├─ Multiple similar items? ───────────────> [[batch-processing]]
    │
    ├─ Investigating/debugging? ──────────────> [[debugging]]
    │
    ├─ Planning/designing known work? ────────> [[spec-review]]
    │   (know what to build, designing how)
    │
    ├─ Small, focused change? ────────────────> [[minor-edit]]
    │
    ├─ New feature or complex work? ──────────> [[feature-dev]]
    │
    └─ Need QA verification? ─────────────────> [[qa-demo]]
```

## Specification

For complete documentation of workflow structure, composition rules, and how the hydrator selects workflows, see [[workflows/SPEC]].

### Scope-Based Routing

When hydrator detects **multi-session scope**, routing changes:

| Signal | Indicates | Route to |
|--------|-----------|----------|
| "Write a paper", "Build X", "Plan the project" | Goal-level, uncertain path | [[decompose]] |
| "Add feature X", "Fix bug Y" | Known deliverable, clear steps | [[feature-dev]] or [[minor-edit]] |
| "How do I..." | Information need | [[simple-question]] |

**Key distinction**: [[decompose]] is for "figure out what to do", [[spec-review]] is for "design how to do it".
