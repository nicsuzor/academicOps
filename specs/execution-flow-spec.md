---
title: Execution Flow Document Specification
type: spec
category: spec
status: implemented
permalink: execution-flow-spec
tags: [framework, documentation, architecture]
---

# Execution Flow Document Specification

Governs the structure and content of `docs/EXECUTION-FLOW.md`.

## Purpose

The execution flow document shows **where the framework injects control** during a Claude Code session. It is the architectural map for understanding how prompts flow through the system.

## Design Principles

### 1. Vertical Main Flow, Horizontal Insertion Points

The main execution flow runs vertically. Each framework insertion point (hooks, agents, templates) branches horizontally with links to its implementation.

```
┌─────────────┐         ┌─────────────────────┐
│ Main Step   │ ──────► │ Framework component │
└──────┬──────┘         │ → implementation.py │
       │                │ → template.md       │
       ▼                └─────────────────────┘
```

**Rationale**: Keeps the main flow scannable while showing where intervention happens.

### 2. Separate Hard Tissue from Soft Tissue

| Type | Contains | Location |
|------|----------|----------|
| Hard tissue | Mechanics (Python, trigger logic) | `hooks/*.py` |
| Soft tissue | Configurable content (prompts, instructions) | `hooks/templates/*.md` |

**Rationale**: Editable content should be in markdown, not buried in code.

### 3. Reference, Don't Duplicate

- Link to `WORKFLOWS.md` for routing table (don't duplicate it)
- Link to `hooks/guardrails.md` for guardrail definitions
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
5. **Quick Capture** - /q and /do relationship

## Acceptance Criteria

1. Main flow diagram is vertical with horizontal insertion points
2. Every hook in registry has its template/content source identified
3. No duplicated content from WORKFLOWS.md or guardrails.md
4. All implementation files are linked, not described inline
5. Mermaid diagrams render correctly
