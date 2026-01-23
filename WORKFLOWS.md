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

Workflows are **hydrator hints**, not complete instructions. They tell the hydrator:
1. When this workflow applies (routing signals)
2. What's unique to this workflow
3. Which base workflows to compose

## Base Workflows (Composable Patterns)

**Always consider these.** Most workflows compose one or more base patterns.

| Base | Pattern | Skip When |
|------|---------|-----------|
| [[base-task-tracking]] | Claim/create task, update progress, complete | [[simple-question]], [[direct-skill]] |
| [[base-tdd]] | Red-green-refactor cycle | Non-code changes |
| [[base-verification]] | Checkpoint before completion | Trivial changes |
| [[base-commit]] | Stage, commit (why not what), push | No file modifications |

## Decision Tree

```
User request
    │
    ├─ Explicit skill mentioned? ──────────────> [[direct-skill]]
    │
    ├─ Simple question only? ──────────────────> [[simple-question]]
    │
    ├─ Goal-level / multi-month work? ─────────> [[decompose]]
    │   (uncertain path, need to figure out steps)
    │       └─ Task doesn't map to any skill? ─> [[skill-pilot]]
    │
    ├─ Multiple similar items? ────────────────> [[batch-processing]]
    │
    ├─ Investigating/debugging? ───────────────> [[debugging]]
    │
    ├─ Planning/designing known work? ─────────> [[design]]
    │   (know what to build, designing how)
    │
    ├─ Small, focused change? ─────────────────> [[minor-edit]]
    │
    ├─ Need QA verification? ──────────────────> [[qa-demo]]
    │
    └─ Framework governance change? ───────────> [[framework-change]]
```

## Scope-Based Routing

| Signal | Route to |
|--------|----------|
| "Write a paper", "Build X", "Plan the project" | [[decompose]] |
| "Add feature X", "Fix bug Y" (clear steps) | [[design]] → [[minor-edit]] |
| "How do I..." (information only) | [[simple-question]] |
| "Process all X", "batch update" | [[batch-processing]] |
| "/commit", "/email" (skill name) | [[direct-skill]] |

## Available Workflows

### Development

| Workflow | When to Use | Bases |
|----------|-------------|-------|
| [[minor-edit]] | Single file, obvious change | task-tracking, tdd, verification, commit |
| [[tdd-cycle]] | Any testable code change | tdd |
| [[debugging]] | Cause unknown, investigating | task-tracking, verification |

### Planning

| Workflow | When to Use | Bases |
|----------|-------------|-------|
| [[decompose]] | Multi-month, uncertain path | task-tracking |
| [[design]] | Known work, need architecture | task-tracking |

### Quality Assurance

| Workflow | When to Use | Bases |
|----------|-------------|-------|
| [[critic-fast]] | Quick sanity check (default) | - |
| [[critic-detailed]] | Framework/architectural changes | - |
| [[qa-demo]] | Pre-completion verification | - |
| [[prove-feature]] | Integration validation | - |

### Operations

| Workflow | When to Use | Bases |
|----------|-------------|-------|
| [[batch-processing]] | Multiple independent items | task-tracking |
| [[triage-email]] | Email classification | - |
| [[email-reply]] | Drafting replies | task-tracking |
| [[interactive-triage]] | Backlog grooming | - |
| [[peer-review]] | Grant/fellowship reviews | task-tracking |

### Information & Routing

| Workflow | When to Use | Bases |
|----------|-------------|-------|
| [[simple-question]] | Pure information, no modifications | - |
| [[direct-skill]] | 1:1 skill mapping | - |

### Meta

| Workflow | When to Use | Bases |
|----------|-------------|-------|
| [[skill-pilot]] | Building new skills from gaps | task-tracking |
| [[dogfooding]] | Framework self-improvement | - |

### Governance

| Workflow | When to Use | Bases |
|----------|-------------|-------|
| [[framework-change]] | AXIOMS/HEURISTICS/enforcement | task-tracking |

## Key Distinctions

| If you're unsure between... | Ask... |
|-----------------------------|--------|
| [[decompose]] vs [[design]] | "Figure out what to do" vs "design how to do it" |
| [[qa-demo]] vs [[prove-feature]] | "Does it run?" vs "Does it integrate correctly?" |
| [[minor-edit]] vs [[design]] | Single file, obvious fix vs multi-file, decisions needed |
| [[simple-question]] vs [[debugging]] | Pure info vs leads to investigation |
