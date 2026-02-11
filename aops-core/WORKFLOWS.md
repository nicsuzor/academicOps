---
name: workflows
title: Workflow Index
type: index
category: framework
description: Formal logic for prompt-to-workflow routing and execution
permalink: workflows
tags: [framework, routing, workflows, index]
---

# Workflow Index

Workflows are **hydrator hints** that define the execution path. They compose **Base Patterns** with **Unique Steps**.

## Routing Logic (Formal)

The hydrator maps prompts to workflows using these priority-ordered rules:

| Match (Intent + Target) | Context/Signal | Route | Bases |
| :--- | :--- | :--- | :--- |
| **Simple Inquiry** | Pure info, no file modifications | [[simple-question]] | - |
| **Direct Action** | Slash command, explicit skill name | [[direct-skill]] | - |
| **Follow-up** | Session continuation, "continue" | [[interactive-followup]] | verification |
| **Ambiguity** | Multi-month, "figure out", vague | [[decompose]] | task-tracking |
| **Architecture** | "design", architecture, specifications | [[design]] | task-tracking, verification, commit |
| **Standard Dev** | "implement", "add", known code change | [[tdd-cycle]] | task-tracking, tdd, verification, commit |
| **Investigation** | "debug", "error", "failing" (unknown) | [[debugging]] | task-tracking, verification |
| **Quality Review** | "verify completion", "run QA" | [[qa-demo]] | verification |
| **Acceptance Test** | "user testing", "E2E verification" | [[qa-test]] | task-tracking, verification |
| **Critic/Audit** | "audit", "review plan", "critique" | [[critic-fast]] | - |
| **Governance** | AXIOMS, HEURISTICS, Framework rules | [[framework-change]] | task-tracking, verification, commit |
| **Operational** | "batch update", "sync tasks" | [[batch-processing]] | task-tracking |
| **Exploratory** | "brainstorm", "explore ideas" | [[collaborate]] | task-tracking |
| **Closure** | "handover", "done for today" | [[handover]] | - |

## Base Patterns (Composables)

These are the reusable blocks of logic that specialized workflows compose.

| Pattern | Logic |
| :--- | :--- |
| [[base-task-tracking]] | Search → Create → Claim → Update → Complete |
| [[base-tdd]] | Red (failing test) → Green (impl) → Refactor |
| [[base-verification]] | Sanity check → Evidence capture → User sign-off |
| [[base-commit]] | Stage → Atomic commit (Why) → Push |

## Execution Catalog

### Planning & Discovery
- [[decompose]]: Break high-level goals into actionable epics.
- [[design]]: Architecture and specification for known work.
- [[collaborate]]: Open-ended discovery and brainstorming.

### Development & Maintenance
- [[tdd-cycle]]: Standard red-green-refactor for features/fixes.
- [[debugging]]: Root cause investigation and fix verification.
- [[framework-change]]: Evolution of framework axioms and heuristics.

### Quality Assurance
- [[qa-demo]]: Manual/Qualitative verification of completion.
- [[qa-test]]: End-to-end user acceptance testing.
- [[critic-fast]]: Rapid automated sanity checking (Default).
- [[critic-detailed]]: Deep architectural or research review.

### Operations & Meta
- [[batch-processing]]: Scaling operations to multiple items.
- [[handover]]: Ending sessions and persisting state.
- [[skill-pilot]]: Developing new skills from observed gaps.
- [[dogfooding]]: Using the framework to improve the framework.

### Internal / Hydration
These workflows support automated prompt hydration and plan verification.
- [[framework-gate]]: Initial check to detect framework modifications.
- [[constraint-check]]: Verifies that a plan satisfies workflow constraints.
- [[version-bump]]: Automated versioning and release logic.

---
> **Design Note**: Workflows should be lean. Move complex procedures to separate specs or skill-specific workflows.
