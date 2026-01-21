---
name: workflows
title: Workflow Index
type: index
category: framework
description: Index of all available workflows for routing and execution
permalink: workflows
tags: [framework, routing, workflows, index]
---

# Workflow Index

All work MUST follow one of the workflows in this index.

## Decision Tree

```
User request
    │
    ├─ Explicit skill mentioned? ──────────────> direct-skill
    │
    ├─ Simple question only? ──────────────────> simple-question
    │
    ├─ Goal-level / multi-month work? ─────────> decompose
    │   (uncertain path, need to figure out steps)
    │       └─ Task doesn't map to any skill? ─> skill-pilot
    │
    ├─ Multiple similar items? ────────────────> batch-processing
    │
    ├─ Investigating/debugging? ───────────────> debugging
    │
    ├─ Planning/designing known work? ─────────> design
    │   (know what to build, designing how)
    │
    ├─ Small, focused change? ─────────────────> minor-edit
    │
    ├─ Need QA verification? ──────────────────> qa-demo
    │
    └─ Framework governance change? ───────────> framework-change
```

## Scope-Based Routing

| Signal | Route to |
|--------|----------|
| "Write a paper", "Build X", "Plan the project" | decompose |
| "Add feature X", "Fix bug Y" (clear steps) | design → minor-edit |
| "How do I..." (information only) | simple-question |
| "Process all X", "batch update" | batch-processing |
| "/commit", "/email" (skill name) | direct-skill |

## Available Workflows

### Development

| Workflow | When to Use | Routing Signal |
|----------|-------------|----------------|
| **minor-edit** | Typo/bug fixes, one-file changes, simple refactoring | "quick fix", single file, obvious change |
| **tdd-cycle** | Any testable code change, feature implementation | Code change requiring tests |
| **debugging** | Investigating bugs, root cause analysis | "why doesn't this work?", cause unknown |

### Planning

| Workflow | When to Use | Routing Signal |
|----------|-------------|----------------|
| **decompose** | Multi-month projects, unclear path, goal-level work | "write a paper", "build X", uncertain deliverables |
| **design** | Features needing spec, architectural decisions | "add feature", requirements unclear |

### Quality Assurance

| Workflow | When to Use | Routing Signal |
|----------|-------------|----------------|
| **qa-demo** | Pre-completion verification, user-facing changes | Feature complete, before final commit |
| **prove-feature** | Validating framework integration | "does it integrate correctly?" |

### Operations

| Workflow | When to Use | Routing Signal |
|----------|-------------|----------------|
| **batch-processing** | Multiple similar items, parallel work | "process all", multiple independent tasks |
| **triage-email** | Email classification during daily/email processing | Inbox processing, email skill |
| **email-reply** | Drafting email replies for tasks | Task title starts with "Reply to" |
| **interactive-triage** | Backlog grooming, task organization | Periodic review, batch classification |
| **peer-review** | Grant/fellowship application reviews | Assessment packages, review templates |

### Information

| Workflow | When to Use | Routing Signal |
|----------|-------------|----------------|
| **simple-question** | Pure information request, no modifications | "what is...", "how does...", no action needed |

### Routing

| Workflow | When to Use | Routing Signal |
|----------|-------------|----------------|
| **direct-skill** | Request maps 1:1 to existing skill | "/commit", explicit skill name |

### Meta

| Workflow | When to Use | Routing Signal |
|----------|-------------|----------------|
| **skill-pilot** | Building new skills from capability gaps | Decomposition reveals no matching skill |
| **dogfooding** | Framework self-improvement during work | Friction noticed, "harder than it should be" |

### Governance

| Workflow | When to Use | Routing Signal |
|----------|-------------|----------------|
| **framework-change** | Modifying AXIOMS/HEURISTICS/enforcement | Governance file modification |

## Key Distinctions

| If you're unsure between... | Ask... |
|-----------------------------|--------|
| **decompose** vs **design** | "Figure out what to do" vs "design how to do it" |
| **qa-demo** vs **prove-feature** | "Does it run?" vs "Does it integrate correctly?" |
| **minor-edit** vs **design** | Single file, obvious fix vs multi-file, decisions needed |
| **simple-question** vs **debugging** | Pure info vs leads to investigation |
