# academicOps Execution Flow

Where the framework injects control during a Claude Code session.

**Spec**: [[specs/execution-flow-spec]]

---

## Universal Execution Flow

Every prompt goes through this flow. Framework insertion points branch horizontally.

```
                    ┌──────────────────┐
                    │  Session Start   │ ──────► SessionStart hook
                    └────────┬─────────┘         → hooks/sessionstart_load_axioms.py
                             │
                             │                   Loads content from:
                             │                   → FRAMEWORK.md (paths)
                             │                   → AXIOMS.md (principles)
                             │                   → HEURISTICS.md (empirical)
                             │                   → CORE.md (user context)
                             ▼
                    ┌──────────────────┐         ┌─────────────────────────────┐
                    │ 1. User Prompt   │ ──────► │ UserPromptSubmit hook       │
                    │    arrives       │         │ → hooks/user_prompt_submit.py
                    └────────┬─────────┘         │                             │
                             │                   │ Injects instruction from:   │
                             │                   │ → templates/prompt-hydration│
                             │                   │   -instruction.md           │
                             │                   └─────────────────────────────┘
                             ▼
                    ┌──────────────────┐         ┌─────────────────────────────┐
                    │ 2. Prompt        │ ──────► │ prompt-hydrator agent runs: │
                    │    Hydration     │         │ • memory search             │
                    └────────┬─────────┘         │ • codebase signals          │
                             │                   │ • session context           │
                             │                   │ → [[specs/prompt-hydration]]│
                             │                   └─────────────────────────────┘
                             ▼
                    ┌──────────────────┐         ┌─────────────────────────────┐
                    │ 3. Workflow      │ ──────► │ [[WORKFLOWS]] (routing)     │
                    │    Selection     │         │ [[hooks/guardrails]] (rules)│
                    └────────┬─────────┘         └─────────────────────────────┘
                             │
                             ▼
                    ┌──────────────────┐         ┌─────────────────────────────┐
                    │ 4. Execute       │ ──────► │ Workflow implementations:   │
                    │    Workflow      │         │ → See table below           │
                    └────────┬─────────┘         │ → [[commands/do]] (full)    │
                             │                   └─────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
    ┌──────────┐       ┌──────────┐       ┌──────────┐
    │ PreTool  │       │ Tool     │       │ PostTool │
    │ Use hook │       │ executes │       │ Use hook │
    └──────────┘       └──────────┘       └──────────┘
          │                                     │
          │                                     │
          ▼                                     ▼
    ┌──────────────┐                     ┌──────────────┐
    │ policy_      │                     │ autocommit,  │
    │ enforcer.py  │                     │ logging,     │
    │              │                     │ scribe       │
    │ Template:    │                     │              │
    │ (none - uses │                     │ Templates:   │
    │ settings.json│                     │ → scribe     │
    │ deny rules)  │                     │   reminder.md│
    └──────────────┘                     └──────────────┘
                             │
                             ▼
                    ┌──────────────────┐         ┌─────────────────────────────┐
                    │ 5. Session End   │ ──────► │ Stop hook                   │
                    │                  │         │ → hooks/request_scribe.py   │
                    └──────────────────┘         │                             │
                                                 │ Template:                   │
                                                 │ → (inline reminder)         │
                                                 └─────────────────────────────┘
```

---

## Workflow Implementations

Box 4 is pluggable. The workflow selected in Box 3 determines what happens:

| Workflow | What Happens | When Selected | Spec |
|----------|--------------|---------------|------|
| answer-only | Answer, then STOP | Questions, explanations | [[hooks/guardrails]] |
| direct | Main agent executes directly | Simple tasks, clear scope | — |
| verify-first | Reproduce → understand → fix | Bug reports, errors | [[hooks/guardrails]] |
| tdd | Test first → implement → verify | New features, refactors | [[specs/feature-dev-skill]] |
| plan-mode | Get approval → full orchestration | Framework changes, complex work | [[commands/do]] |
| checklist | Systematic verification steps | Reviews, audits | — |

**Full routing table**: [[WORKFLOWS]]

---

## Full Orchestration Workflow

When `plan-mode` is selected OR `/do` is invoked explicitly, the agent becomes a **hypervisor**.

**Command**: [[commands/do]]
**Spec**: [[specs/hypervisor-workflow]] (if exists) or inline below

```mermaid
flowchart TD
    subgraph PLAN["1. Planning"]
        P1["Invoke domain skill"]
        P2["Define acceptance criteria<br/>(LOCKED - immutable)"]
        P3["Create TodoWrite<br/>with CHECKPOINTs"]
        P4["Critic review"]
    end

    subgraph EXECUTE["2. Execution Loop"]
        E1["Mark todo in_progress"]
        E2["Delegate to subagent"]
        E3["Subagent works"]
        E4{"CHECKPOINT<br/>passed?"}
        E5["Iterate (max 3)"]
        E6["Commit + push"]
        E7["Mark completed"]
    end

    subgraph GUARDS["Guardrails (continuous)"]
        G1{"Scope drift<br/>>20%?"}
        G2{"Thrashing?<br/>(3+ edits)"}
        G3["HALT + ask user"]
    end

    subgraph QA["3. QA Verification"]
        Q1["Verify against<br/>LOCKED criteria"]
        Q2{"Met?"}
        Q3["REJECTED → back to 2"]
        Q4["APPROVED"]
    end

    subgraph CLEANUP["4. Cleanup"]
        CL1["Final commit + push"]
        CL2["Update memory"]
        CL3["Report to user"]
    end

    P1 --> P2 --> P3 --> P4 --> E1
    E1 --> E2 --> E3 --> E4
    E4 -->|No| E5 --> E2
    E4 -->|Yes| E6 --> E7 --> E1
    E7 -->|all done| Q1
    G1 -->|Yes| G3
    G2 -->|Yes| G3
    Q1 --> Q2
    Q2 -->|No| Q3 --> E1
    Q2 -->|Yes| Q4 --> CL1 --> CL2 --> CL3

    style P1 fill:#9c27b0,color:#fff
    style P2 fill:#9c27b0,color:#fff
    style P3 fill:#9c27b0,color:#fff
    style P4 fill:#9c27b0,color:#fff
    style E1 fill:#607d8b,color:#fff
    style E2 fill:#607d8b,color:#fff
    style E3 fill:#607d8b,color:#fff
    style E4 fill:#e1bee7,color:#000
    style E5 fill:#ffb74d,color:#000
    style E6 fill:#607d8b,color:#fff
    style E7 fill:#607d8b,color:#fff
    style G1 fill:#f44336,color:#fff
    style G2 fill:#f44336,color:#fff
    style G3 fill:#f44336,color:#fff
    style Q1 fill:#ff5722,color:#fff
    style Q2 fill:#e1bee7,color:#000
    style Q3 fill:#f44336,color:#fff
    style Q4 fill:#4caf50,color:#fff
    style CL1 fill:#795548,color:#fff
    style CL2 fill:#795548,color:#fff
    style CL3 fill:#795548,color:#fff
```

### Key Principles

1. **Orchestrate, don't implement** - Hypervisor delegates edits to subagents
2. **Criteria are LOCKED** - Acceptance criteria defined in planning are immutable
3. **CHECKPOINTs require evidence** - Can't mark complete without proof
4. **Commit each cycle** - Changes pushed before next iteration
5. **Guardrails halt on problems** - Scope drift or thrashing → ask user

---

## Hook Trigger Mechanism

When Claude Code fires a hook event:

```
Event fires (e.g., UserPromptSubmit)
    ↓
Hook script receives JSON input:
  • prompt, transcript_path, tool info, etc.
    ↓
Hook loads template (if applicable):
  • templates/*.md files contain "soft tissue"
  • Python substitutes placeholders
    ↓
Hook returns JSON with additionalContext
    ↓
Claude Code injects additionalContext into agent
```

**Pattern**: Separate mechanics (Python) from content (templates).

---

## Hook Registry

| Event | Script | Template/Content | Purpose |
|-------|--------|------------------|---------|
| SessionStart | sessionstart_load_axioms.py | AXIOMS.md, HEURISTICS.md, FRAMEWORK.md, CORE.md | Load framework context |
| UserPromptSubmit | user_prompt_submit.py | templates/prompt-hydration-instruction.md | Inject prompt hydration |
| PreToolUse | policy_enforcer.py | settings.json (deny rules) | Block destructive git, oversized files |
| PostToolUse | autocommit_state.py | — | Auto-commit data/ changes |
| PostToolUse | fail_fast_watchdog.py | — | Detect errors, inject fail-fast reminder |
| PostToolUse | unified_logger.py | — | Universal event logging |
| PostToolUse:TodoWrite | request_scribe.py | (inline) | Memory documentation reminder |
| Stop | session_reflect.py | — | Session-end reflection prompt |
| Stop | request_scribe.py | (inline) | Final memory reminder |

**Exit codes**: PreToolUse `0`=allow, `1`=warn, `2`=block. PostToolUse `0`=success, `2`=report to agent.

**Full hook documentation**: [[docs/HOOKS]]

---

## Quick Capture

`/q` saves a task for later; `/do` executes it.

**Commands**: [[commands/q]], [[commands/do]]

```mermaid
flowchart LR
    U1[/"/q [task]"/] --> T1[("tasks/inbox/")] -.->|later| D1[/"/do [task]"/]

    style U1 fill:#2196f3,color:#fff
    style T1 fill:#9e9e9e,color:#fff
    style D1 fill:#ff9800,color:#fff
```
