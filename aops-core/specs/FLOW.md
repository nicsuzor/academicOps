---
title: Execution Flow
type: spec
description: Specifies how the aops-core plugin injects control during a Claude Code session.
---

# aops-core Execution Flow

How the plugin injects control during a Claude Code session.

## Plugin Structure

```
aops-core/
├── .claude-plugin/plugin.json   # Plugin manifest
├── agents/                      # Subagent definitions
│   ├── critic.md               # Plan review
│   ├── custodiet.md            # Ultra vires detection
│   ├── planner.md              # Task decomposition
│   └── prompt-hydrator.md      # Workflow routing
├── axioms/                      # Inviolable principles
├── commands/                    # Slash commands (/q, /log, etc.)
├── heuristics/                  # Soft guidance
├── hooks/                       # Event handlers
│   ├── router.py               # Central dispatcher
│   └── templates/              # Prompt templates
├── lib/                         # Shared Python utilities
├── skills/                      # Domain context
│   ├── audit/                  # Session auditing
│   ├── feature-dev/            # Feature development
│   ├── framework/              # Framework development
│   ├── python-dev/             # Python conventions
│   ├── remember/               # Memory persistence
│   └── tasks/                  # Task management
└── specs/                       # Specifications
```

## Complete Execution Flow

Main flow (left) with hooks and their scripts (right column).

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1a1a2e',
    'primaryTextColor': '#eaeaea',
    'primaryBorderColor': '#4a4a6a',
    'lineColor': '#6b7280',
    'fontSize': '12px'
  },
  'flowchart': { 'nodeSpacing': 25, 'rankSpacing': 35, 'curve': 'basis', 'padding': 10 }
}}%%
flowchart LR
    %% === STYLING ===
    classDef phase fill:#1e293b,stroke:#334155,stroke-width:2px,color:#f1f5f9,font-weight:bold
    classDef step fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px,color:#1e293b
    classDef gate fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e
    classDef hook fill:#fee2e2,stroke:#dc2626,stroke-width:1px,color:#991b1b
    classDef script fill:#fecaca,stroke:#b91c1c,stroke-width:1px,color:#7f1d1d,font-size:11px
    classDef agent fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px,color:#3730a3

    %% === MAIN FLOW (vertical subgraph) ===
    subgraph MAIN[" "]
        direction TB
        S0([Session Begin]) --> H1[SessionStart]
        H1 --> P1[User Prompt]
        P1 --> H2[UserPromptSubmit]
        H2 --> W1{Select Workflow}
        W1 --> T1[TodoWrite Plan]
        T1 --> E1[Call Tool]
        E1 --> H3[PreToolUse]
        H3 -->|block| E1
        H3 -->|allow| E2[Tool Executes]
        E2 --> H4[PostToolUse]
        H4 --> E3{More Work?}
        E3 -->|Yes| E1
        E3 -->|No| E4[Commit Work]
        E4 --> H5[Stop]
        H5 --> C3([End])
    end

    %% === HOOK SCRIPTS (right column) ===
    subgraph SCRIPTS["Hook Scripts"]
        direction TB
        HS1[session_env_setup.sh<br/>unified_logger.py]
        HS2[user_prompt_submit.py<br/>unified_logger.py]
        HS2 -.-> A1[prompt-hydrator]
        HS3[unified_logger.py]
        HS4[unified_logger.py]
        HS5[unified_logger.py]
    end

    %% === CONNECT HOOKS TO SCRIPTS ===
    H1 --- HS1
    H2 --- HS2
    H3 --- HS3
    H4 --- HS4
    H5 --- HS5

    %% === APPLY STYLES ===
    class S0,C3 phase
    class P1,T1,E1,E2,E4 step
    class W1,E3 gate
    class H1,H2,H3,H4,H5 hook
    class HS1,HS2,HS3,HS4,HS5 script
    class A1 agent

    %% === SUBGRAPH STYLING ===
    style MAIN fill:none,stroke:none
    style SCRIPTS fill:#fef2f2,stroke:#fca5a5,stroke-width:1px,stroke-dasharray: 5 5
```

## Workflow Selection

The prompt-hydrator routes to workflows based on task signals.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1a1a2e',
    'primaryTextColor': '#eaeaea',
    'lineColor': '#6b7280',
    'fontSize': '13px'
  }
}}%%
flowchart TB
    %% === STYLING ===
    classDef input fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af
    classDef decision fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e
    classDef workflow fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px,color:#1e293b
    classDef skill fill:#e0e7ff,stroke:#4f46e5,stroke-width:1px,color:#3730a3
    classDef agent fill:#fce7f3,stroke:#db2777,stroke-width:1px,color:#9d174d

    P[User Prompt] --> D1{Question?}

    D1 -->|Yes| WQ[Answer Only]
    D1 -->|No| D2{Framework<br/>files?}

    D2 -->|Yes| WF[Plan Mode]
    WF --> AF[planner agent]
    AF --> AC[critic agent]
    AC --> SF[framework skill]

    D2 -->|No| D3{Bug/Error?}

    D3 -->|Yes| WD[Debug]

    D3 -->|No| D4{New<br/>feature?}

    D4 -->|Yes| WT[TDD]
    WT --> SFD[feature-dev skill]

    D4 -->|No| WX[Direct Execute]

    %% === APPLY STYLES ===
    class P input
    class D1,D2,D3,D4 decision
    class WQ,WF,WD,WT,WX workflow
    class SF,SFD skill
    class AF,AC agent
```

| Workflow        | Triggers                           | Agents          | Skill       |
| --------------- | ---------------------------------- | --------------- | ----------- |
| **Answer Only** | "what", "how", "why", questions    | -               | -           |
| **Plan Mode**   | skills/, hooks/, axioms/ edits     | planner, critic | framework   |
| **Debug**       | "fix", "broken", error messages    | -               | -           |
| **TDD**         | "add", "create", new functionality | -               | feature-dev |
| **Direct**      | Clear single-step scope            | -               | -           |

## Hook System

All hooks route through `hooks/router.py`, which dispatches to registered sub-scripts.

### Hook Registry

| Event                | Scripts                                  | Purpose                     |
| -------------------- | ---------------------------------------- | --------------------------- |
| **SessionStart**     | session_env_setup.sh, unified_logger.py  | Environment setup + logging |
| **UserPromptSubmit** | user_prompt_submit.py, unified_logger.py | Trigger prompt hydration    |
| **PreToolUse**       | unified_logger.py                        | Logging                     |
| **PostToolUse**      | unified_logger.py                        | Logging                     |
| **SubagentStop**     | unified_logger.py                        | Logging                     |
| **Stop**             | unified_logger.py                        | Logging                     |

> **Note**: Additional hooks (hydration_gate.py, policy_enforcer.py, custodiet_gate.py, etc.) are available in `archived/hooks/` and can be restored as needed.

### Exit Codes

- `0` = Allow/Success
- `1` = Warning
- `2` = Block (PreToolUse only)

### Output Merging

Router merges outputs from multiple scripts:

- `additionalContext`: Concatenate with separator
- `permissionDecision`: Most restrictive wins (deny > ask > allow)
- `continue`: AND logic
- `suppressOutput`: OR logic

## Agents

| Agent               | Purpose                                     | Spawned By             |
| ------------------- | ------------------------------------------- | ---------------------- |
| **prompt-hydrator** | Route prompt to workflow, inject guardrails | UserPromptSubmit       |
| **planner**         | Decompose complex tasks                     | Framework workflow     |
| **critic**          | Review plans before execution               | Framework workflow     |
| **custodiet**       | Detect scope drift (ultra vires)            | PostToolUse (~7 calls) |

Agent definitions in `agents/*.md`.

## Skills

Skills provide domain-specific context. Loaded via `Skill(skill="name")`.

| Skill           | Purpose                           |
| --------------- | --------------------------------- |
| **framework**   | Framework development conventions |
| **feature-dev** | TDD, user stories, test specs     |
| **python-dev**  | Python coding standards           |
| **remember**    | Memory persistence patterns       |
| **tasks**       | Task management workflows         |
| **audit**       | Session auditing                  |

Skills are read-only context - they don't execute code.

## Axioms & Heuristics

### Axioms (Inviolable)

| Axiom                   | Enforcement                                   |
| ----------------------- | --------------------------------------------- |
| trust-version-control   | policy_enforcer.py blocks destructive git ops |
| fail-fast-code          | fail_fast_watchdog.py injects reminders       |
| research-data-immutable | policy_enforcer.py blocks data/ edits         |
| data-boundaries         | Prompt guidance                               |
| single-purpose-files    | Prompt guidance                               |
| skills-are-read-only    | Prompt guidance                               |
| self-documenting        | Prompt guidance                               |

### Heuristics (Soft Guidance)

- file-category-classification
- no-horizontal-dividers
- semantic-link-density
- skills-no-dynamic-content

## Commands

Slash commands in `commands/*.md`:

| Command   | Purpose               |
| --------- | --------------------- |
| /q        | Quick task capture    |
| /log      | Learning log entry    |
| /reflect  | Session reflection    |
| /remind   | Set reminder          |
| /email    | Email workflow        |
| /qa       | Quality assurance     |
| /strategy | Strategic planning    |
| /meta     | Meta-level discussion |

## Key Principles

1. **Router consolidates hooks** - Single entry point reduces noise
2. **Hooks enforce axioms** - PreToolUse blocks violations
3. **Skills provide context** - Read-only, loaded on demand
4. **Agents handle complexity** - Subagents for routing, planning, review
5. **Custodiet detects drift** - Periodic ultra vires checks
