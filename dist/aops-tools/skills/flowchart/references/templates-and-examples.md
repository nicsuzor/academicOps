---
title: Flowchart Templates and Examples
category: ref
permalink: skills-flowchart-templates
---

# Flowchart Templates and Examples

Reference templates for common Mermaid flowchart patterns.

## Template: Horizontal Process Flow (MOST COMMON - Use This for 80% of Charts)

Use this template for any linear or mostly-linear process. It spreads nicely across screens.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#2d3748',
    'lineColor': '#718096',
    'fontSize': '14px'
  },
  'flowchart': { 'nodeSpacing': 70, 'rankSpacing': 80, 'padding': 20 }
}}%%
flowchart LR
    classDef default fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    classDef start fill:#276749,stroke:#48bb78,color:#f0fff4,stroke-width:2px
    classDef decision fill:#6b46c1,stroke:#9f7aea,color:#faf5ff,stroke-width:2px
    classDef error fill:#c53030,stroke:#fc8181,color:#fff5f5

    START([Start]):::start
    INIT[Initialize]
    CHECK{Valid?}:::decision
    PROCESS[Process]
    DONE([Done]):::start
    ERR[Error]:::error

    START --> INIT --> CHECK
    CHECK -->|Yes| PROCESS --> DONE
    CHECK -->|No| ERR -.-> INIT
```

**Why this works**: With `LR` direction and adequate spacing (70/80), steps arrange left-to-right naturally, fitting modern wide screens. This is the default choice for any process you can sketch linearly.

## Template: Wide Decision Tree (Branches Spread Horizontally)

For diagrams with many branches, use `TD` layout to let branches spread horizontally:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': { 'lineColor': '#718096', 'fontSize': '14px' },
  'flowchart': { 'nodeSpacing': 60, 'rankSpacing': 70, 'padding': 20, 'curve': 'basis' }
}}%%
flowchart TD
    classDef default fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    classDef decision fill:#6b46c1,stroke:#9f7aea,color:#faf5ff,stroke-width:2px
    classDef result fill:#276749,stroke:#48bb78,color:#f0fff4

    Q1{First check?}:::decision
    Y1[Proceed A]:::result
    N1{Second check?}:::decision
    Y2[Proceed B]:::result
    N2[Fallback]:::default

    Q1 -->|Yes| Y1
    Q1 -->|No| N1
    N1 -->|Yes| Y2
    N1 -->|No| N2
```

**Why this works**: `TD` (top-down) lets branches fan out horizontally. Pairs well with proper spacing to avoid cramping.

## Template: Horizontal Multi-Phase Workflow

For complex workflows with distinct phases, arrange phases left-to-right with steps flowing top-to-bottom inside:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': { 'lineColor': '#718096', 'fontSize': '14px' },
  'flowchart': { 'nodeSpacing': 60, 'rankSpacing': 70, 'padding': 20 }
}}%%
flowchart LR
    classDef phase fill:#1a202c,stroke:#4a5568,color:#e2e8f0
    classDef step fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    classDef check fill:#6b46c1,stroke:#9f7aea,color:#faf5ff,stroke-width:2px

    subgraph SETUP["SETUP"]
        direction TB
        S1[Load config]:::step
        S2[Validate]:::step
        S1 --> S2
    end

    subgraph PROCESS["PROCESS"]
        direction TB
        P1[Execute]:::step
        P2{OK?}:::check
        P3[Commit]:::step
        P1 --> P2
        P2 -->|Yes| P3
    end

    subgraph CLEANUP["CLEANUP"]
        direction TB
        C1[Release]:::step
        C2[Report]:::step
        C1 --> C2
    end

    SETUP --> PROCESS
    PROCESS --> CLEANUP
    P2 -->|No| S1

    style SETUP fill:#1a365d,stroke:#2b6cb0
    style PROCESS fill:#22543d,stroke:#38a169
    style CLEANUP fill:#744210,stroke:#d69e2e
```

## Example: Complex System Flow (Horizontal)

For multi-phase systems like hook pipelines, use horizontal layout with vertical subgraph internals:

```mermaid
---
config:
  layout: elk
  elk:
    mergeEdges: true
---
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e293b',
    'lineColor': '#64748b',
    'fontSize': '13px'
  },
  'flowchart': { 'nodeSpacing': 50, 'rankSpacing': 55, 'padding': 12 }
}}%%
flowchart LR
    classDef default fill:#334155,stroke:#475569,color:#e2e8f0
    classDef entry fill:#166534,stroke:#22c55e,color:#f0fdf4,stroke-width:2px
    classDef gate fill:#7c3aed,stroke:#a78bfa,color:#f5f3ff,stroke-width:2px
    classDef state fill:#0369a1,stroke:#38bdf8,color:#f0f9ff

    IN([Prompt]):::entry

    subgraph PRE["PRE-ACTION"]
        direction TB
        H1[Hook fires]
        H2[Load state]:::state
        H3[Spawn hydrator]:::gate
        H1 --> H2 --> H3
    end

    subgraph EXEC["EXECUTION"]
        direction TB
        A1[Agent executes]
        A2{Gate check}:::gate
        A3[Tool runs]
        A1 --> A2
        A2 -->|Pass| A3
    end

    subgraph POST["POST-ACTION"]
        direction TB
        P1[Increment counter]
        P2{Threshold?}:::gate
        P3[Spawn audit]
        P1 --> P2
        P2 -->|Yes| P3
    end

    OUT([Done]):::entry

    IN --> PRE
    PRE --> EXEC
    EXEC --> POST
    POST --> OUT
    A2 -->|Fail| H3

    style PRE fill:#1e3a5f,stroke:#3b82f6
    style EXEC fill:#14532d,stroke:#22c55e
    style POST fill:#581c87,stroke:#a855f7
```

**Key techniques used**:

- `layout: elk` for automatic optimal positioning
- `flowchart LR` with `direction TB` subgraphs
- 4 colors only: default (slate), entry (green), gate (purple), state (blue)
- Links between subgraphs, not internal nodes
- Generous spacing (50/55) with padding

## Quick Reference: When to Use Which Template

| Your Diagram | Template to Use | Layout | Spacing |
|---|---|---|---|
| Simple pipeline (6-10 steps in a line) | Horizontal Process Flow | `LR` | `70/80` |
| Process with branches/conditions | Wide Decision Tree | `TD` | `60/70` |
| Distinct phases + steps in each phase | Horizontal Multi-Phase | `LR` + `TB` subgraphs | `60/70` |
| Complex with many interconnections | Complex System Flow with ELK | `LR` + `TB` subgraphs + ELK | `50+` |

## Horizontal Space Best Practices Checklist

Before finalizing any flowchart, check these spacing items:

**SPACING (Critical for readability)**:
- [ ] `nodeSpacing: 60` minimum (increase to 70-80 for clarity)
- [ ] `rankSpacing: 70` minimum (increase to 80+ for multi-phase)
- [ ] `padding: 20` to prevent label cutoff
- [ ] For horizontal layouts, prioritize nodeSpacing over rankSpacing

**LAYOUT (Use screen real estate effectively)**:
- [ ] Using `LR` for linear/mostly-linear diagrams (DEFAULT choice)
- [ ] Using `TD` only when branches need horizontal spread
- [ ] Subgraph phasing arranges left-to-right, internals top-to-bottom
- [ ] Links go between subgraphs, not leaking out of internal nodes

**COLOR & VISUALS**:
- [ ] 4-5 colors maximum (one dominant 60%, accent 30%, highlight 10%)
- [ ] Color has semantic meaning (not just decoration)
- [ ] Solid backgrounds always (never transparent)
- [ ] `stroke-width: 2px` for emphasis on decisions/starts

**LABELS**:
- [ ] 3-9 words per node (move long text to notes/subgraphs)
- [ ] Verbs at start ("Process data", "Check valid", not just "Data" or "Valid")
- [ ] Consistent casing (sentence case for labels, CAPS for subgraph titles)
- [ ] Font size 14px minimum

**ANTI-PATTERNS TO AVOID**:
- ❌ Using default spacing (35/45) - always feels cramped
- ❌ TD layout for everything - creates tall, scrolly charts
- ❌ Mixing LR and TD at same level - confusing flow direction
- ❌ Links crossing main flow - use subgraph boundaries instead
- ❌ 8+ distinct colors - visual noise, no hierarchy
