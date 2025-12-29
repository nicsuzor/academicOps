# academicOps Execution Flow

This document traces the **temporal execution sequence** when a user interacts with the academicOps framework. Each diagram shows what happens step-by-step, with annotations explaining the purpose of each component.

---

## Color Legend

| Color | Meaning |
|-------|---------|
| Blue (#2196f3) | User actions |
| Purple (#9c27b0) | Hook events and scripts |
| Orange (#ff9800) | Agents (subagents) |
| Green (#4caf50) | Skills |
| Gray (#9e9e9e) | Data stores |
| Diamond shapes | Decision points |

---

## Diagram 1: Standard Prompt Flow

When a user submits a regular prompt (e.g., "help me understand this code"):

```mermaid
flowchart TD
    subgraph USER["User Action"]
        U1[/"User submits prompt"/]
    end

    subgraph SESSION_START["SessionStart Hook (if new session)"]
        S1["router.py dispatches to:"]
        S2["session_env_setup.sh<br/>Sets AOPS, PYTHONPATH"]
        S3["terminal_title.py<br/>Updates terminal title"]
        S4["sessionstart_load_axioms.py<br/>Loads FRAMEWORK, AXIOMS,<br/>HEURISTICS, CORE"]
        S5["unified_logger.py<br/>Logs event metadata"]
        S1 --> S2
        S1 --> S3
        S1 --> S4
        S1 --> S5
    end

    subgraph PROMPT_HOOK["UserPromptSubmit Hook"]
        P1["router.py receives prompt"]
        P2["prompt_router.py (ASYNC)<br/>Writes context to temp file<br/>Instructs agent to spawn<br/>intent-router subagent"]
        P3["user_prompt_submit.py<br/>Logs to Cloudflare analytics"]
        P4["unified_logger.py<br/>Logs event metadata"]
        P1 --> P2
        P1 --> P3
        P1 --> P4
        P5["Merge outputs:<br/>additionalContext concatenated<br/>Worst exit code wins"]
        P2 --> P5
        P3 --> P5
        P4 --> P5
    end

    subgraph AGENT_RECEIVES["Agent Processing"]
        A1["Agent receives:<br/>- Original prompt<br/>- Hook context (skill suggestions)<br/>- ROUTE FIRST instruction"]
        A2{"Agent decides:<br/>invoke skill?"}
        A3["Invoke Skill tool<br/>e.g., Skill(skill='python-dev')"]
        A4["Work directly<br/>(Read, Edit, Bash)"]
        A5["Spawn subagent<br/>Task tool"]
        A2 -->|skill needed| A3
        A2 -->|simple task| A4
        A2 -->|complex task| A5
    end

    subgraph INTENT_ROUTER["Intent Router (Async Background)"]
        IR1{{"intent-router agent<br/>(Haiku model)"}}
        IR2["Reads temp file with<br/>router prompt + user prompt"]
        IR3["Returns focused guidance:<br/>- Which skills apply<br/>- Required steps<br/>- Framework rules"]
        IR1 --> IR2 --> IR3
    end

    subgraph TOOL_EXECUTION["Tool Execution"]
        T1["PreToolUse hook fires"]
        T2["policy_enforcer.py<br/>Checks if tool allowed"]
        T3{"Tool<br/>allowed?"}
        T4["BLOCKED<br/>Exit code 2<br/>stderr to agent"]
        T5["Tool executes<br/>(Read, Edit, Bash, etc.)"]
        T6["PostToolUse hook fires"]
        T7["unified_logger.py<br/>Logs operation"]
        T8["autocommit_state.py<br/>Auto-commits if data/ changed"]
        T1 --> T2 --> T3
        T3 -->|No| T4
        T3 -->|Yes| T5
        T5 --> T6
        T6 --> T7
        T6 --> T8
    end

    subgraph TODO_HOOK["If TodoWrite Used"]
        TD1["PostToolUse:TodoWrite matcher"]
        TD2["request_scribe.py<br/>Reminds about memory<br/>documentation"]
    end

    subgraph STOP_HOOK["Stop Hook (Session End)"]
        ST1["Stop event fires"]
        ST2["unified_logger.py<br/>Final logging"]
        ST3["request_scribe.py<br/>Final reminder to document<br/>work to memory server"]
        ST1 --> ST2
        ST1 --> ST3
    end

    subgraph DATA["Data Stores"]
        D1[("$ACA_DATA/<br/>tasks, projects,<br/>sessions, knowledge")]
        D2[("Memory Server<br/>mcp__memory__")]
        D3[("Git<br/>autocommit")]
    end

    %% Flow connections
    U1 --> SESSION_START
    SESSION_START --> PROMPT_HOOK
    PROMPT_HOOK --> A1
    A1 --> A2
    A1 -.->|async| IR1
    IR3 -.->|guidance returned| A1
    A3 --> T1
    A4 --> T1
    A5 --> T1
    T8 -.-> D1
    T8 -.-> D3
    TD2 -.-> D2
    ST3 -.-> D2

    %% Styling
    style U1 fill:#2196f3,color:#fff
    style S1 fill:#9c27b0,color:#fff
    style S2 fill:#ce93d8,color:#000
    style S3 fill:#ce93d8,color:#000
    style S4 fill:#ce93d8,color:#000
    style S5 fill:#ce93d8,color:#000
    style P1 fill:#9c27b0,color:#fff
    style P2 fill:#ce93d8,color:#000
    style P3 fill:#ce93d8,color:#000
    style P4 fill:#ce93d8,color:#000
    style P5 fill:#9c27b0,color:#fff
    style A1 fill:#fff3e0,color:#000
    style A2 fill:#fff3e0,color:#000
    style A3 fill:#4caf50,color:#fff
    style A4 fill:#fff3e0,color:#000
    style A5 fill:#ff9800,color:#fff
    style IR1 fill:#ff9800,color:#fff
    style IR2 fill:#ffb74d,color:#000
    style IR3 fill:#ffb74d,color:#000
    style T1 fill:#9c27b0,color:#fff
    style T2 fill:#ce93d8,color:#000
    style T3 fill:#e1bee7,color:#000
    style T4 fill:#f44336,color:#fff
    style T5 fill:#fff3e0,color:#000
    style T6 fill:#9c27b0,color:#fff
    style T7 fill:#ce93d8,color:#000
    style T8 fill:#ce93d8,color:#000
    style TD1 fill:#9c27b0,color:#fff
    style TD2 fill:#ce93d8,color:#000
    style ST1 fill:#9c27b0,color:#fff
    style ST2 fill:#ce93d8,color:#000
    style ST3 fill:#ce93d8,color:#000
    style D1 fill:#9e9e9e,color:#fff
    style D2 fill:#9e9e9e,color:#fff
    style D3 fill:#9e9e9e,color:#fff
```

### Annotations: Standard Prompt Flow

| Step | Component | Purpose |
|------|-----------|---------|
| 1 | User submits prompt | Entry point - user types in Claude Code |
| 2 | SessionStart hook | Only fires on NEW session; loads framework context |
| 3 | sessionstart_load_axioms.py | Injects FRAMEWORK.md, AXIOMS.md, HEURISTICS.md, CORE.md |
| 4 | UserPromptSubmit hook | Fires on EVERY prompt |
| 5 | prompt_router.py (async) | Writes context to temp file, tells agent to spawn intent-router |
| 6 | intent-router agent | Haiku model analyzes prompt, returns task-specific guidance |
| 7 | Agent decides | Based on guidance: skill, direct work, or spawn subagent |
| 8 | PreToolUse hook | policy_enforcer.py blocks dangerous operations |
| 9 | Tool executes | Read, Edit, Bash, Grep, Glob, etc. |
| 10 | PostToolUse hook | Logs operation, auto-commits data/ changes |
| 11 | TodoWrite hook | If todo list updated, reminds about memory documentation |
| 12 | Stop hook | Final reminder to persist learnings to memory server |

---

## Diagram 2: Supervised Workflow Flow

When a user invokes `/supervise` for multi-step orchestrated work:

```mermaid
flowchart TD
    subgraph USER["User Action"]
        U1[/"User types:<br/>/supervise tdd fix the bug"/]
    end

    subgraph PROMPT_HOOK["UserPromptSubmit Hook"]
        PH1["Hook fires (same as standard)"]
        PH2["But slash command detected<br/>prompt_router.py skips routing"]
    end

    subgraph COMMAND_EXPAND["Command Expansion"]
        C1["/supervise command expands"]
        C2["Invokes Skill(skill='supervisor')"]
        C3["Skill loads supervisor.md"]
    end

    subgraph HYPERVISOR["Hypervisor Agent (Opus)"]
        H1{{"hypervisor agent<br/>spawned via Task"}}
        H2["Reads workflow template<br/>(e.g., tdd.md if specified)"]
    end

    subgraph PHASE0["Phase 0: Planning"]
        P0A["0.1: Define acceptance criteria"]
        P0B["0.2: Spawn Plan agent<br/>to investigate & plan"]
        P0C["0.3: Spawn Critic agent<br/>to review plan"]
        P0D{"Critic<br/>approves?"}
        P0E["Revise plan"]
        P0F["0.4: TodoWrite<br/>ALL steps populated"]
        P0G["Acceptance criteria LOCKED<br/>(immutable from here)"]
        P0A --> P0B --> P0C --> P0D
        P0D -->|REVISE| P0E --> P0C
        P0D -->|APPROVE| P0F --> P0G
    end

    subgraph PHASE1["Phase 1-3: Iteration Cycles"]
        I1["Mark task in_progress<br/>in TodoWrite"]
        I2["Spawn subagent with<br/>specific instructions"]
        I3["Subagent works<br/>(PreToolUse/PostToolUse<br/>hooks fire)"]
        I4["Quality gate check"]
        I5{"Gate<br/>passed?"}
        I6["Iterate on failure<br/>(max 3 attempts)"]
        I7["Git commit + push"]
        I8["Mark task completed"]
        I1 --> I2 --> I3 --> I4 --> I5
        I5 -->|No| I6 --> I2
        I5 -->|Yes| I7 --> I8
    end

    subgraph PHASE4["Phase 4: Iteration Gate"]
        G1["Scope drift detection"]
        G2{"Plan grown<br/>>20%?"}
        G3["HALT: Ask user<br/>to re-scope"]
        G4["Thrashing detection"]
        G5{"Same file<br/>modified 3+<br/>times?"}
        G6["HALT: Log thrashing<br/>Ask user for help"]
        G7["Continue to<br/>next iteration"]
        G1 --> G2
        G2 -->|Yes| G3
        G2 -->|No| G4 --> G5
        G5 -->|Yes| G6
        G5 -->|No| G7
    end

    subgraph PHASE5["Phase 5: QA Verification"]
        Q1["Spawn QA subagent"]
        Q2["QA verifies against<br/>LOCKED criteria"]
        Q3["QA runs validations<br/>with REAL data"]
        Q4{"Criteria<br/>met?"}
        Q5["REJECTED<br/>Return to implementation"]
        Q6["APPROVED<br/>with evidence"]
        Q7["Document via tasks skill"]
        Q8["Final report to user"]
        Q1 --> Q2 --> Q3 --> Q4
        Q4 -->|No| Q5
        Q4 -->|Yes| Q6 --> Q7 --> Q8
    end

    subgraph STOP["Stop Hook"]
        ST1["Stop event fires"]
        ST2["request_scribe.py<br/>Reminder to document"]
    end

    %% Flow connections
    U1 --> PH1
    PH1 --> PH2
    PH2 --> C1
    C1 --> C2 --> C3
    C3 --> H1 --> H2
    H2 --> PHASE0
    P0G --> PHASE1
    I8 --> PHASE4
    G7 --> I1
    G7 -->|all tasks done| Q1
    Q8 --> ST1

    %% Styling - User
    style U1 fill:#2196f3,color:#fff

    %% Styling - Hooks
    style PH1 fill:#9c27b0,color:#fff
    style PH2 fill:#ce93d8,color:#000
    style ST1 fill:#9c27b0,color:#fff
    style ST2 fill:#ce93d8,color:#000

    %% Styling - Command/Skill
    style C1 fill:#2196f3,color:#fff
    style C2 fill:#4caf50,color:#fff
    style C3 fill:#4caf50,color:#fff

    %% Styling - Agents
    style H1 fill:#ff9800,color:#fff
    style H2 fill:#ffb74d,color:#000

    %% Styling - Phase 0
    style P0A fill:#fff3e0,color:#000
    style P0B fill:#ff9800,color:#fff
    style P0C fill:#ff9800,color:#fff
    style P0D fill:#e1bee7,color:#000
    style P0E fill:#ffb74d,color:#000
    style P0F fill:#4caf50,color:#fff
    style P0G fill:#4caf50,color:#fff,stroke:#2e7d32,stroke-width:3px

    %% Styling - Phase 1-3
    style I1 fill:#4caf50,color:#fff
    style I2 fill:#ff9800,color:#fff
    style I3 fill:#ffb74d,color:#000
    style I4 fill:#fff3e0,color:#000
    style I5 fill:#e1bee7,color:#000
    style I6 fill:#ffb74d,color:#000
    style I7 fill:#9e9e9e,color:#fff
    style I8 fill:#4caf50,color:#fff

    %% Styling - Phase 4
    style G1 fill:#fff3e0,color:#000
    style G2 fill:#e1bee7,color:#000
    style G3 fill:#f44336,color:#fff
    style G4 fill:#fff3e0,color:#000
    style G5 fill:#e1bee7,color:#000
    style G6 fill:#f44336,color:#fff
    style G7 fill:#4caf50,color:#fff

    %% Styling - Phase 5
    style Q1 fill:#ff9800,color:#fff
    style Q2 fill:#ffb74d,color:#000
    style Q3 fill:#ffb74d,color:#000
    style Q4 fill:#e1bee7,color:#000
    style Q5 fill:#f44336,color:#fff
    style Q6 fill:#4caf50,color:#fff
    style Q7 fill:#4caf50,color:#fff
    style Q8 fill:#2196f3,color:#fff
```

### Annotations: Supervised Workflow Flow

| Phase | Step | Purpose |
|-------|------|---------|
| Entry | /supervise command | Triggers supervisor skill, spawns hypervisor agent |
| Phase 0 | Planning | Create plan, get critic review, LOCK acceptance criteria |
| Phase 0 | TodoWrite | ALL workflow steps must be in todo list BEFORE Phase 1 |
| Phase 1-3 | Iteration | One atomic task at a time; subagent implements, hypervisor verifies |
| Phase 1-3 | Quality gate | Each step must pass validation before proceeding |
| Phase 1-3 | Commit/push | Each cycle persists changes to git before next cycle |
| Phase 4 | Scope drift | If plan grows >20%, HALT and ask user |
| Phase 4 | Thrashing | If same file modified 3+ times without progress, HALT |
| Phase 5 | QA verification | Independent QA subagent verifies LOCKED criteria with evidence |
| Phase 5 | Final report | Summary of accomplishments, commits, criteria met |

### Key Enforcement Rules

1. **Supervisor Contract**: Hypervisor has NO implementation tools (Read, Edit, Bash)
2. **Criteria LOCK**: Acceptance criteria defined in Phase 0 are IMMUTABLE
3. **TodoWrite First**: ALL steps in todo list before any implementation
4. **One Step at a Time**: Subagent does single atomic step, reports back
5. **Commit Each Cycle**: No proceeding until changes pushed to remote

---

## Diagram 3: Quick Capture Flow (/q)

When a user captures an idea fragment for later execution:

```mermaid
flowchart TD
    subgraph USER["User Action"]
        U1[/"User types:<br/>/q implement dark mode"/]
        U2["User continues working<br/>(not blocked)"]
    end

    subgraph PROMPT_HOOK["UserPromptSubmit Hook"]
        PH1["Hook fires"]
        PH2["Slash command detected<br/>prompt_router.py skips routing"]
    end

    subgraph COMMAND["Command Expansion"]
        C1["/q command expands"]
        C2["Spawns prompt-writer agent<br/>with run_in_background=true"]
    end

    subgraph ASYNC["Async Background Processing"]
        A1{{"prompt-writer agent<br/>(Sonnet model)"}}
        A2["Reads context from:<br/>- Current project<br/>- Memory server<br/>- Codebase search"]
        A3["Decomposes fragment:<br/>What does user mean?<br/>What files involved?<br/>What workflow needed?"]
        A4["Determines if multi-step:<br/>Invoke task-expand skill?"]
        A5["Writes executable prompt<br/>to $ACA_DATA/queue/"]
    end

    subgraph QUEUE["Queue Storage"]
        Q1[("$ACA_DATA/queue/<br/>YYYYMMDD-HHMMSS-slug.md")]
        Q2["Prompt file contains:<br/>- Context<br/>- Goal<br/>- Approach<br/>- Relevant files<br/>- Original fragment"]
    end

    subgraph LATER["Later: /pull"]
        L1[/"User types /pull"/]
        L2["Retrieves prompt from queue"]
        L3["Executes with fresh agent"]
    end

    %% Main flow
    U1 --> PH1
    PH1 --> PH2 --> C1
    C1 --> C2
    C2 -.->|async| A1
    U1 --> U2
    A1 --> A2 --> A3 --> A4 --> A5
    A5 --> Q1
    Q1 --> Q2

    %% Later flow
    L1 --> L2
    L2 --> Q1
    L2 --> L3

    %% Styling - User
    style U1 fill:#2196f3,color:#fff
    style U2 fill:#2196f3,color:#fff
    style L1 fill:#2196f3,color:#fff
    style L2 fill:#fff3e0,color:#000
    style L3 fill:#ff9800,color:#fff

    %% Styling - Hooks
    style PH1 fill:#9c27b0,color:#fff
    style PH2 fill:#ce93d8,color:#000

    %% Styling - Command
    style C1 fill:#2196f3,color:#fff
    style C2 fill:#ff9800,color:#fff

    %% Styling - Async Agent
    style A1 fill:#ff9800,color:#fff
    style A2 fill:#ffb74d,color:#000
    style A3 fill:#ffb74d,color:#000
    style A4 fill:#ffb74d,color:#000
    style A5 fill:#ffb74d,color:#000

    %% Styling - Data
    style Q1 fill:#9e9e9e,color:#fff
    style Q2 fill:#bdbdbd,color:#000
```

### Annotations: Quick Capture Flow

| Step | Component | Purpose |
|------|-----------|---------|
| 1 | User types /q | Zero-friction idea capture |
| 2 | Command expansion | Spawns prompt-writer in background |
| 3 | User continues | NOT blocked - can alt-tab away immediately |
| 4 | prompt-writer investigates | Searches memory, codebase for context |
| 5 | Decrypts shorthand | Interprets what user actually meant |
| 6 | Determines workflow | Direct edit? /supervise? /meta? Research first? |
| 7 | Writes to queue | Self-contained executable prompt |
| 8 | Later: /pull | Retrieves and executes queued prompts |

### Key Design Decisions

1. **Async Execution**: User doesn't wait; agent works in background
2. **Context Preservation**: Agent investigates NOW while context is fresh
3. **Self-Contained Output**: Prompt file executable by fresh Claude instance
4. **Chain-Aware**: Multi-step tasks decomposed into chained prompts

---

## Hook Timing Summary

```mermaid
flowchart LR
    subgraph LIFECYCLE["Session Lifecycle"]
        direction TB
        SS["SessionStart"]
        UPS["UserPromptSubmit"]
        PTU["PreToolUse"]
        POTU["PostToolUse"]
        STOP["Stop"]
    end

    subgraph TIMING["When They Fire"]
        SS_T["Once per session start"]
        UPS_T["Every user prompt"]
        PTU_T["Before each tool call"]
        POTU_T["After each tool call"]
        STOP_T["Session end"]
    end

    SS --> SS_T
    UPS --> UPS_T
    PTU --> PTU_T
    POTU --> POTU_T
    STOP --> STOP_T

    style SS fill:#9c27b0,color:#fff
    style UPS fill:#9c27b0,color:#fff
    style PTU fill:#9c27b0,color:#fff
    style POTU fill:#9c27b0,color:#fff
    style STOP fill:#9c27b0,color:#fff
```

### Hook Registry (from router.py)

| Event | Scripts | Purpose |
|-------|---------|---------|
| SessionStart | session_env_setup.sh, terminal_title.py, sessionstart_load_axioms.py, unified_logger.py | Initialize environment, load framework context |
| UserPromptSubmit | prompt_router.py (async), user_prompt_submit.py, unified_logger.py | Route intent, log prompt, inject guidance |
| PreToolUse | policy_enforcer.py, unified_logger.py | Block dangerous ops, log |
| PostToolUse | unified_logger.py, autocommit_state.py | Log, auto-commit data/ changes |
| PostToolUse:TodoWrite | request_scribe.py | Remind about memory documentation |
| Stop | unified_logger.py, request_scribe.py | Final logging, documentation reminder |

---

## Exit Code Semantics

### PreToolUse Hooks

| Exit | Behavior | Message Shown To |
|------|----------|------------------|
| 0 | Allow | JSON stdout (verbose mode) |
| 1 | Warn but allow | stderr to **user AND agent** |
| 2 | Block execution | stderr to **agent only** |

### PostToolUse Hooks

| Exit | Behavior | Message Shown To |
|------|----------|------------------|
| 0 | Success | JSON stdout (verbose mode) |
| 1 | Non-blocking error | stderr (verbose mode only) |
| 2 | Report to agent | stderr to **agent** (for action) |
