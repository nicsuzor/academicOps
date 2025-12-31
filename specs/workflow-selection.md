---
title: Workflow Selection
type: spec
status: draft
permalink: workflow-selection
tags: [framework, workflows, routing]
---

# Workflow Selection

**Status**: Draft - model under review

## The Question

When a task comes in, the system decides HOW to handle it. What exactly are we deciding?

## Goals

1. **Prevent known failure modes** - Inject the right constraints at the right time
2. **Load appropriate context** - Different work needs different skill context
3. **Set quality gates** - Some work needs more verification than others
4. **Match user expectations** - Questions get answers, not implementations

## The Insight: Composable Dimensions, Not Exclusive Workflows

These are NOT mutually exclusive alternatives:

| Concept | What it actually is |
|---------|---------------------|
| plan-mode | A **gate** - requires approval before implementation |
| tdd | An **approach** - structured sequence (test → implement → verify) |
| verify-first | A **phase** - understand before acting |
| answer-only | A **constraint** - don't implement anything |
| direct | Absence of special process |

They COMPOSE:
- Debug = verify-first + direct approach + no gate
- Framework = plan-mode gate + tdd approach
- Question = answer-only (nothing else applies)

## Proposed Model

### Dimension 1: Gates

Must pass before any implementation begins.

| Gate | When Required |
|------|---------------|
| plan-mode | High-stakes changes (framework, hooks, MCP) |
| none | Everything else |

### Dimension 2: Pre-work

What to do before implementing.

| Pre-work | When To Use |
|----------|-------------|
| verify-first | Debug - reproduce and understand before fixing |
| research-first | Unknown territory - explore before proposing |
| none | Clear scope, proceed directly |

### Dimension 3: Approach

How to implement.

| Approach | What It Means |
|----------|---------------|
| tdd | Write failing test → implement → verify passes |
| direct | Just do it |
| none | No implementation (questions, pure info) |

### Guardrails (Orthogonal)

Constraints during execution - applied on top of the workflow dimensions:

- `verify_before_complete` - all implementation
- `quote_errors_exactly` - debug tasks
- `fix_within_design` - debug tasks
- `require_acceptance_test` - feature/python work
- `critic_review` - framework changes

## Routing Table

| Type | Gate | Pre-work | Approach | Skill | Guardrails |
|------|------|----------|----------|-------|------------|
| framework | plan-mode | - | tdd | framework | critic_review |
| cc_hook | plan-mode | - | tdd | plugin-dev:hook-development | - |
| cc_mcp | plan-mode | - | direct | plugin-dev:mcp-integration | - |
| debug | - | verify-first | direct | - | quote_errors, fix_within_design |
| feature | - | - | tdd | feature-dev | require_acceptance_test |
| python | - | - | tdd | python-dev | require_acceptance_test |
| question | - | - | none | - | answer_only |
| persist | - | - | direct | remember | - |
| analysis | - | - | direct | analyst | - |
| review | - | - | direct | - | verify_before_complete |
| simple | - | - | direct | - | - |

## Open Questions

1. Is this the right set of dimensions? Are there others?
2. Should pre-work be a dimension or just prose guidance in the type description?
3. How does this relate to `/meta` vs `/supervise` routing?

## Acceptance Criteria

1. Task types map to clear dimension combinations
2. Dimensions compose without conflicts
3. Adding a new task type = filling in the routing table, not inventing concepts
4. WORKFLOWS.md reflects this structure
