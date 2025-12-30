# academicOps Execution Flow

This document maps **every intervention point** where the framework injects control during a Claude Code session.

---

## Framework Goals: The Ideal Intervention Pipeline

What we're trying to achieve - independent of current implementation:

```mermaid
flowchart TB
    subgraph INPUT["📥 User Input"]
        U1[/"Simple prompt"/]
    end

    subgraph CONTEXT["1️⃣ CONTEXT INJECTION"]
        C1["Make agent stateful"]
        C2["• Knowledge base (memory server)<br/>• Relevant project files<br/>• Prior decisions/patterns<br/>• User preferences"]
    end

    subgraph STEER["2️⃣ STEERING"]
        S1["Guide toward good workflows"]
        S2["• Match task to workflow pattern<br/>• Surface relevant heuristics<br/>• Warn about failure modes<br/>• Suggest required skills"]
    end

    subgraph PLAN["3️⃣ PLANNING"]
        P1["Produce structured prompt flow"]
        P2["• Decompose into steps<br/>• Define acceptance criteria<br/>• Lock criteria (immutable)<br/>• Identify specialist tasks"]
    end

    subgraph DELEGATE["4️⃣ SKILL DELEGATION"]
        D1["Route specialist work"]
        D2["• Framework changes → framework skill<br/>• Python code → python-dev skill<br/>• Memory → remember skill<br/>• etc."]
    end

    subgraph EXECUTE["5️⃣ EXECUTION"]
        E1["Work happens here"]
        E2["• Follow the plan<br/>• Track via TodoWrite<br/>• Skills provide guardrails"]
    end

    subgraph POLICY["5️⃣b TOOL POLICY"]
        PO1["Enforce tool constraints"]
        PO2["• Block dangerous operations<br/>• Require confirmations<br/>• Restrict tools by context<br/>• Log for audit"]
    end

    subgraph GATES["6️⃣ QUALITY GATES"]
        G1["Prevent premature completion"]
        G2["• Check acceptance criteria<br/>• Verify actual state<br/>• Independent QA review<br/>• Block until criteria met"]
    end

    subgraph CLEANUP["7️⃣ POST-TASK CLEANUP"]
        CL1["Persist and document"]
        CL2["• Git commit + push<br/>• Update memory server<br/>• Document decisions<br/>• Archive task"]
    end

    subgraph MONITOR["8️⃣ COMPLIANCE MONITORING (Future)"]
        M1["Detect failure modes in-flight"]
        M2["• Review hooks during execution<br/>• Intervene on detected patterns<br/>• Log for learning"]
    end

    U1 --> CONTEXT
    CONTEXT --> STEER
    STEER --> PLAN
    PLAN --> DELEGATE
    DELEGATE --> EXECUTE
    POLICY -.->|guards each tool| EXECUTE
    EXECUTE --> GATES
    GATES -->|criteria not met| EXECUTE
    GATES -->|criteria met| CLEANUP
    MONITOR -.->|observes| EXECUTE
    MONITOR -.->|can halt| GATES

    style U1 fill:#2196f3,color:#fff
    style C1 fill:#4caf50,color:#fff
    style C2 fill:#c8e6c9,color:#000
    style S1 fill:#ff9800,color:#fff
    style S2 fill:#ffe0b2,color:#000
    style P1 fill:#9c27b0,color:#fff
    style P2 fill:#e1bee7,color:#000
    style D1 fill:#00bcd4,color:#fff
    style D2 fill:#b2ebf2,color:#000
    style E1 fill:#607d8b,color:#fff
    style E2 fill:#cfd8dc,color:#000
    style PO1 fill:#f44336,color:#fff
    style PO2 fill:#ffcdd2,color:#000
    style G1 fill:#ff5722,color:#fff
    style G2 fill:#ffccbc,color:#000
    style CL1 fill:#795548,color:#fff
    style CL2 fill:#d7ccc8,color:#000
    style M1 fill:#e0e0e0,color:#666,stroke-dasharray: 5 5
    style M2 fill:#f5f5f5,color:#666,stroke-dasharray: 5 5
```

### Goal Summary

| Stage | Purpose | Key Question |
|-------|---------|--------------|
| **1. Context** | Make agent stateful | What does the agent need to know? |
| **2. Steering** | Prevent failure modes | What patterns apply? What to avoid? |
| **3. Planning** | Structure the work | What are the steps? What's "done"? |
| **4. Delegation** | Use specialists | Which skills handle which parts? |
| **5. Execution** | Do the work | (Skills provide internal guardrails) |
| **5b. Tool Policy** | Enforce constraints | Is this tool use allowed? Safe? |
| **6. Gates** | Ensure quality | Are acceptance criteria actually met? |
| **7. Cleanup** | Persist state | Committed? Documented? Remembered? |
| **8. Monitor** | Learn and intervene | (Future: detect failures in-flight) |

### Design Decisions

1. **Single golden path** - All work goes through the full pipeline. No shortcuts.
2. **`/do` is the single orchestrator** - Kills `/supervise`. One command to rule them all.
3. **`/do` orchestrates, doesn't execute** - Like a supervisor, it coordinates but doesn't directly do work.
4. **Quality gates are baked into the plan** - Not a separate stage. Planning skills add QA checkpoints as todo items.
5. **Control the plan = control the work** - Agent must follow TodoWrite. Good plans = good work.

### The `/do` Architecture

```mermaid
flowchart LR
    subgraph INVOKE["/do [prompt]"]
        U1[/"User prompt"/]
    end

    subgraph ORCHESTRATE["Orchestrator (doesn't do work)"]
        O1["1. Gather context"]
        O2["2. Classify task"]
        O3["3. Select planning skill"]
    end

    subgraph PLAN["Planning Skill"]
        P1["Brings domain context"]
        P2["Applies domain rules"]
        P3["Creates TodoWrite with:<br/>• Work steps<br/>• QA checkpoints<br/>• Acceptance criteria"]
    end

    subgraph EXECUTE["Agent Executes"]
        E1["Follows todo items"]
        E2["Invokes specialist skills"]
        E3["QA items force verification"]
    end

    subgraph CLEANUP["Cleanup"]
        C1["Commit + push"]
        C2["Update memory"]
        C3["Archive task"]
    end

    U1 --> O1 --> O2 --> O3
    O3 --> P1 --> P2 --> P3
    P3 --> E1 --> E2 --> E3
    E3 --> C1 --> C2 --> C3

    style U1 fill:#2196f3,color:#fff
    style O1 fill:#ff9800,color:#fff
    style O2 fill:#ff9800,color:#fff
    style O3 fill:#ff9800,color:#fff
    style P1 fill:#9c27b0,color:#fff
    style P2 fill:#9c27b0,color:#fff
    style P3 fill:#9c27b0,color:#fff
    style E1 fill:#607d8b,color:#fff
    style E2 fill:#4caf50,color:#fff
    style E3 fill:#f44336,color:#fff
    style C1 fill:#795548,color:#fff
    style C2 fill:#795548,color:#fff
    style C3 fill:#795548,color:#fff
```

### How Quality Gates Work

Instead of a separate QA stage, **planning skills bake QA into the todo list**:

```
Example TodoWrite from planning skill:

1. [ ] Reproduce the issue
2. [ ] Identify root cause
3. [ ] Implement fix
4. [ ] **CHECKPOINT: Verify fix works** ← QA baked in
5. [ ] Run test suite
6. [ ] **CHECKPOINT: All tests pass** ← QA baked in
7. [ ] Commit with descriptive message
8. [ ] **CHECKPOINT: Verify commit pushed** ← QA baked in
```

The agent can't skip checkpoints because they're todo items. Control the plan, control the work.

### Planning Skills (Swappable)

Different task types can use different planning skills:

| Task Type | Planning Skill | Brings |
|-----------|----------------|--------|
| Framework changes | `framework` | Categorical imperative, skill-first rules |
| Python code | `python-dev` | TDD workflow, type safety rules |
| Debug | `debug` (future) | Verify-first, quote-errors-exactly |
| Feature dev | `feature-dev` | Acceptance criteria, plan-first |

For now, keep it simple: one planning skill that handles common cases. Specialize later.

### What Dies

- `/supervise` - redundant, `/do` does this
- Separate QA stage - baked into plan
- `hypervisor` agent - `/do` orchestrator replaces it

---

## Current Implementation Map

Every point where we can inject guidance, from session start to session end:

```mermaid
flowchart TB
    subgraph SESSION["SESSION LIFECYCLE"]
        direction TB

        subgraph START["🟢 Session Start"]
            SS[["SessionStart Hook<br/>HIGH CONTROL"]]
            SS_DO["Inject: AXIOMS, HEURISTICS,<br/>FRAMEWORK, CORE"]
        end

        subgraph LOOP["🔄 Prompt Loop (repeats)"]
            direction TB

            subgraph PROMPT["Each Prompt"]
                UP[["UserPromptSubmit Hook<br/>LOW (noop)"]]
                UP_FUTURE["Future: Prompt Enricher"]
            end

            subgraph ROUTE["Claude Code Routes"]
                R{{"Starts with /"}}
            end

            subgraph PATHS["Intervention Paths"]
                CMD[["Load command/*.md<br/>HIGH CONTROL"]]
                SKILL[["Skill() invoked<br/>HIGH CONTROL"]]
                FREE["Freeform prompt<br/>NO ACTIVE CONTROL"]
            end

            subgraph TOOLS["Tool Execution"]
                PRE[["PreToolUse Hook<br/>MED (logging, can block)"]]
                TOOL["Tool runs"]
                POST[["PostToolUse Hook<br/>MED (logging, autocommit)"]]
            end

            subgraph SUB["Subagent Work"]
                SUBRUN["Subagent executes"]
                SUBSTOP[["SubagentStop Hook<br/>LOW (logging)"]]
            end
        end

        subgraph END["🔴 Session End"]
            STOP[["Stop Hook<br/>LOW (reminder)"]]
            STOP_DO["request_scribe.py"]
        end
    end

    SS --> SS_DO --> LOOP
    UP -.->|future| UP_FUTURE
    UP --> R
    R -->|Yes| CMD
    R -->|No| FREE
    CMD -.->|may invoke| SKILL
    FREE -.->|may invoke| SKILL
    CMD --> TOOLS
    SKILL --> TOOLS
    FREE --> TOOLS
    PRE --> TOOL --> POST
    TOOL -.->|spawns| SUBRUN
    SUBRUN --> SUBSTOP
    LOOP --> END
    STOP --> STOP_DO

    style SS fill:#4caf50,color:#fff
    style SS_DO fill:#c8e6c9,color:#000
    style UP fill:#ffcdd2,color:#000
    style UP_FUTURE fill:#e0e0e0,color:#666,stroke-dasharray: 5 5
    style R fill:#9c27b0,color:#fff
    style CMD fill:#4caf50,color:#fff
    style SKILL fill:#4caf50,color:#fff
    style FREE fill:#ffcdd2,color:#000
    style PRE fill:#fff3e0,color:#000
    style TOOL fill:#2196f3,color:#fff
    style POST fill:#fff3e0,color:#000
    style SUBRUN fill:#ff9800,color:#fff
    style SUBSTOP fill:#ffcdd2,color:#000
    style STOP fill:#ffcdd2,color:#000
    style STOP_DO fill:#ffe0b2,color:#000
```

### Intervention Point Summary

| Event | Hook/Mechanism | What We Do | Control |
|-------|----------------|------------|---------|
| **Session start** | `SessionStart` hook | Inject AXIOMS, HEURISTICS, FRAMEWORK, CORE | 🟢 HIGH |
| **Every prompt** | `UserPromptSubmit` hook | Currently noop | 🔴 LOW |
| **`/command` typed** | Claude Code routing → `commands/*.md` | Our command file loads with instructions | 🟢 HIGH |
| **`Skill()` invoked** | Claude Code → `skills/*/SKILL.md` | Our skill content loads | 🟢 HIGH |
| **Freeform prompt** | (none) | Only baseline context from SessionStart | 🔴 NONE |
| **Before tool** | `PreToolUse` hook | Logging; could block dangerous tools | 🟡 MED |
| **After tool** | `PostToolUse` hook | Logging + autocommit `data/` changes | 🟡 MED |
| **Subagent done** | `SubagentStop` hook | Logging only | 🔴 LOW |
| **Session end** | `Stop` hook | `request_scribe.py` reminder | 🔴 LOW |

### Key Insight: The Control Gap

Our **high-control** points require explicit user action (`/command`) or agent action (`Skill()`).

For **freeform prompts**, we have no active intervention - only passive baseline context. The planned **Prompt Enricher** (`specs/prompt-enricher.md`) would close this gap by analyzing each prompt and injecting relevant skill suggestions.

---

## Color Legend

| Color | Meaning |
|-------|---------|
| Green | High control - our content loads |
| Yellow/Orange | Medium control - can intervene |
| Red/Pink | Low/no control - logging or noop |
| Purple | Claude Code routing (not ours) |
| Blue | User/tool actions |
| Dashed gray | Planned/future |

---

## Detailed Flows

The following diagrams show specific intervention paths in detail.

### Session Initialization

The framework lifecycle starts when Claude Code launches, NOT when the user submits a prompt.

```mermaid
flowchart LR
    subgraph LAUNCH["1. Launch"]
        L1[/"User opens<br/>Claude Code"/]
    end

    subgraph SESSION_START["2. SessionStart Hook"]
        S1["settings.json →<br/>router.py →<br/>sessionstart_load_axioms.py"]
    end

    subgraph INJECTION["3. Baseline Injected"]
        I1["• FRAMEWORK.md (paths)<br/>• AXIOMS.md (principles)<br/>• HEURISTICS.md (patterns)<br/>• CORE.md (identity)"]
    end

    subgraph READY["4. Ready"]
        R1[/"Agent waiting<br/>for input"/]
    end

    L1 --> S1 --> I1 --> R1

    style L1 fill:#2196f3,color:#fff
    style S1 fill:#9c27b0,color:#fff
    style I1 fill:#fff3e0,color:#000
    style R1 fill:#2196f3,color:#fff
```

### SessionStart Hook: Implementation Details

| Component | Value |
|-----------|-------|
| **Trigger** | `settings.json` → `hooks` → `SessionStart` |
| **Entry point** | `hooks/router.py` |
| **Dispatches to** | `hooks/sessionstart_load_axioms.py` |
| **Input (stdin)** | `{"hook_event_name": "SessionStart", "session_id": "...", "cwd": "..."}` |
| **Output (stdout)** | `{"hookSpecificOutput": {"additionalContext": "...", "filesLoaded": [...]}}` |
| **Exit code** | `0` = success, `1` = fatal (missing files) |

### Files Loaded at SessionStart

| File | Source | Purpose |
|------|--------|---------|
| `FRAMEWORK.md` | `$AOPS/FRAMEWORK.md` | Resolved paths (WHERE) |
| `AXIOMS.md` | `$AOPS/AXIOMS.md` | Inviolable principles (WHAT) |
| `HEURISTICS.md` | `$AOPS/HEURISTICS.md` | Empirical patterns (HOW) |
| `CORE.md` | `$ACA_DATA/CORE.md` | User identity (WHO) |

**Spec**: `specs/session-start-injection.md`

---

### /do Command Flow

The `/do` command provides intelligent context enrichment and guardrailed execution.

```mermaid
flowchart LR
    subgraph INPUT["1. /do Command"]
        U1[/"/do fix the dashboard"/]
    end

    subgraph SPAWN["2. Spawn Agent"]
        SP1["Task(intent-router,<br/>model=sonnet)"]
    end

    subgraph ROUTER["3. intent-router Agent"]
        R1["1. Memory + codebase search<br/>2. Read relevant files<br/>3. Classify task type<br/>4. Select workflow<br/>5. Select guardrails<br/>6. Decompose into steps"]
    end

    subgraph OUTPUT["4. YAML Output"]
        O1["task_type, workflow,<br/>guardrails, context,<br/>todo_items, warnings"]
    end

    subgraph APPLY["5. Apply Guardrails"]
        A1{{"Check<br/>flags"}}
        A2["plan_mode → Plan Mode"]
        A3["answer_only → Answer, STOP"]
        A4["require_skill → Skill(X)"]
        A5["default → Execute todos"]
    end

    U1 --> SP1 --> R1 --> O1 --> A1
    A1 --> A2
    A1 --> A3
    A1 --> A4
    A1 --> A5

    style U1 fill:#2196f3,color:#fff
    style SP1 fill:#ff9800,color:#fff
    style R1 fill:#ffb74d,color:#000
    style O1 fill:#fff3e0,color:#000
    style A1 fill:#e1bee7,color:#000
    style A2 fill:#ce93d8,color:#000
    style A3 fill:#ce93d8,color:#000
    style A4 fill:#4caf50,color:#fff
    style A5 fill:#fff3e0,color:#000
```

### /do Command: Implementation Details

| Component | Value |
|-----------|-------|
| **Command file** | `commands/do.md` |
| **Spawns** | `intent-router` agent via Task tool |
| **Model** | Sonnet (or configurable) |
| **Router location** | `agents/intent-router.md` |
| **Guardrails source** | `hooks/guardrails.md` |

### Intent Router: Input/Output

**Input** (Task tool prompt):
```
User fragment: [whatever user typed after /do]
```

**Output** (structured YAML):
```yaml
task_type: [debug|feature|question|framework|...]
workflow: [verify-first|tdd|direct|...]
skills_to_invoke: [skill names]
guardrails:
  plan_mode: true/false
  verify_before_complete: true/false
  answer_only: true/false
  require_acceptance_test: true/false
  quote_errors_exactly: true/false
  fix_within_design: true/false
  require_skill: [skill name or null]
enriched_context: |
  [Summary of memory search + codebase search results]
todo_items:
  - "[Step 1]"
  - "[Step 2]"
warnings:
  - "[Potential issues]"
original_fragment: |
  [User's exact words]
```

### Guardrails Applied by /do

| Guardrail | When True |
|-----------|-----------|
| `plan_mode` | Enter Plan Mode before implementation |
| `answer_only` | Answer the question, then STOP |
| `require_skill` | Invoke the specified skill first |
| `verify_before_complete` | Must verify actual state before claiming done |
| `require_acceptance_test` | Todo list must include verification step |
| `quote_errors_exactly` | Quote error messages verbatim |
| `fix_within_design` | Fix bugs within current architecture |

**Spec**: `commands/do.md`, `agents/intent-router.md`

---

### /supervise Workflow Flow

When a user invokes `/supervise` for multi-step orchestrated work:

```mermaid
flowchart TD
    subgraph ENTRY["Entry"]
        U1[/"User types:<br/>/supervise tdd fix the bug"/]
        PH1["Hook fires → slash command<br/>detected → skips routing"]
        C1["/supervise → Skill(supervisor)<br/>→ loads supervisor.md"]
        H1{{"hypervisor agent<br/>(Opus) spawned"}}
        H2["Reads workflow template"]
        U1 --> PH1 --> C1 --> H1 --> H2
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
    H2 --> PHASE0
    P0G --> PHASE1
    I8 --> PHASE4
    G7 --> I1
    G7 -->|all tasks done| Q1
    Q8 --> ST1

    %% Styling - Entry
    style U1 fill:#2196f3,color:#fff
    style PH1 fill:#9c27b0,color:#fff
    style C1 fill:#4caf50,color:#fff
    style H1 fill:#ff9800,color:#fff
    style H2 fill:#ffb74d,color:#000

    %% Styling - Stop
    style ST1 fill:#9c27b0,color:#fff
    style ST2 fill:#ce93d8,color:#000

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

### /q Quick Capture Flow

When a user captures an idea fragment for later execution:

```mermaid
flowchart TD
    subgraph USER["User Action"]
        U1[/"User types:<br/>/q implement dark mode"/]
        U2["User continues working<br/>(not blocked)"]
    end

    subgraph PROMPT_HOOK["UserPromptSubmit Hook"]
        PH1["Hook fires"]
        PH2["Slash command detected<br/>hook skips routing"]
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

## Hook Implementation Details

The master map above shows intervention control levels. This section details the actual hook implementations.

### Hook Sequence

```mermaid
flowchart LR
    SS["SessionStart<br/>(once)"] --> UPS["UserPromptSubmit<br/>(every prompt)"] --> PTU["PreToolUse<br/>(before tool)"] --> POTU["PostToolUse<br/>(after tool)"] --> STOP["Stop<br/>(session end)"]

    style SS fill:#4caf50,color:#fff
    style UPS fill:#ffcdd2,color:#000
    style PTU fill:#fff3e0,color:#000
    style POTU fill:#fff3e0,color:#000
    style STOP fill:#ffcdd2,color:#000
```

### Hook Registry (from router.py)

| Event | Scripts | Purpose |
|-------|---------|---------|
| SessionStart | session_env_setup.sh, terminal_title.py, sessionstart_load_axioms.py, unified_logger.py | Initialize environment, load framework context |
| UserPromptSubmit | user_prompt_submit.py, unified_logger.py | Log prompt, inject context from prompts/user-prompt-submit.md |
| PreToolUse | policy_enforcer.py, unified_logger.py | Block dangerous ops, log |
| PostToolUse | unified_logger.py, autocommit_state.py | Log, auto-commit data/ changes |
| PostToolUse:TodoWrite | request_scribe.py | Remind about memory documentation |
| SubagentStop | unified_logger.py | Log subagent completion |
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
