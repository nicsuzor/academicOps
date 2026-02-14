# academicOps: A constitutional automation framework for academic work

- Enforces a logical system: every rule derivable from aops-core/AXIOMS.md with aops-core/HEURISTICS.md supported by evidence.
- Reflexive, self-improving agents must follow a CATEGORICAL IMPERATIVE: every action must be supported by a general rule.
- Graduated approach to enforcement: aops-core/framework/enforcement-map.md sets out a full map of rules to enforcement mechanism, from gentle reminders to hard blocks.
- Agent autonomy is limited to the authority they were granted: live ultra vires detection loop
- Direct integration with beads for task memomory, memory mcp for vector search
- Full personal knowledge base with gardening and continuous remembering skills
- Human readable and portable Markdown files are the single sources of truth
- Everything in git for durability and observability
- Strict separation of user data (not in this repo)
- Optimised for long-term strategic planning under conditions of uncertainty
- Includes integrated MCP tooling for email and calendar access

## Installation

### Link your data repository / knowledge base

- **Environment variables** in `~/.bashrc` or `~/.zshrc`:

```bash
export ACA_DATA="$HOME/writing/data"     # Your data (NOT in git)
```

### Install plugin for Claude Code & Gemini CLI

Distribution repository: https://github.com/nicsuzor/aops-dist

Claude Code

```bash
command claude plugin marketplace add nicsuzor/aops-dist
command claude plugin marketplace update aops && command claude plugin install aops-core@aops && command claude plugin list
```

Gemini CLI (warning: auto accept flag below, remove --consent if you're concerned)

```bash
(command gemini extensions uninstall aops-core || echo Gemini plugin not installed -- not removing.) && command gemini extensions install git@github.com:nicsuzor/aops-dist.git --consent --auto-update --pre-release
```

## Core Loop

**For detailed specification, see**: [[specs/flow.md]]

**Goal**: The minimal viable framework with ONE complete, working loop.

**Philosophy**: Users don't have to use aops. But if they do, it's slow and thorough. The full workflow is MANDATORY.

### Core Loop Diagram

```mermaid
flowchart TD
    %% Node Definitions
    Start([Session Start])

    subgraph Initialization [1. Initialization]
        SStart[SessionStart Event] --> Router1{Universal Router}
        Router1 -.-> Setup[session_env_setup.py]
        Router1 -.-> StartGate[session_start gate]
        StartGate --> State[(Create State File)]
        StartGate --- InitExpl[Loads environment paths,<br/>AXIOMS, and HEURISTICS]
    end

    subgraph Hydration [2. Hydration & Review]
        UPS[UserPromptSubmit Event] --> Router2{Universal Router}
        Router2 -.-> SkipCheck{Skip Hydration?}
        SkipCheck -- No --> Context[Context -> Temp File]
        Context --> Hydrator[[prompt-hydrator Subagent]]
        Hydrator --> Plan[/Hydration Plan/]
        Hydrator --> GateCr[Critic Gate: CLOSED]

        Hydrator --- HydrateExpl[Fetches: Task queue, memory server,<br/>WORKFLOWS index, and relevant files]

        Plan --> Critic[[critic Subagent]]
        Critic --> CriticCheck{Plan Approved?}
        CriticCheck -- REVISE --> Plan
        CriticCheck -- PROCEED --> OpenCr[Critic Gate: OPEN]
        Critic --- CriticExpl[Evaluates plan for assumptions,<br/>safety gaps, and logic errors]
    end

    subgraph Execution [3. Execution & Hard Gates]
        PreTool[PreToolUse Event] --> Router3{Universal Router}

        Router3 -.-> GateH[Hydration Gate]
        GateH --> GateT[Task Gate]
        GateT --> GateCr_Exec[Critic Gate]

        GateH --- HExpl[Blocks mutating tools until<br/>an execution plan is generated]
        GateT --- TExpl[Enforces work tracking by requiring<br/>an active task for destructive actions]
        GateCr_Exec --- CrExpl[Blocks edit tools until plan is reviewed]

        GateCr_Exec --> ThresholdCheck{Audit Threshold?}
        ThresholdCheck -- Yes ~15 ops --> GateC[Custodiet Gate]
        ThresholdCheck -- No --> Tool[[Execute Tool]]

        GateC --- CExpl[Reviews session history for<br/>principle violations and scope drift]
        GateC --> Tool

        Tool --> PostTool[PostToolUse Event]
        PostTool --> Router4{Universal Router}
        Router4 -.-> Accountant[Accountant: Update Counters]
    end

    subgraph Termination [4. Reflection & Close]
        AfterAgent[AfterAgent Event] --> Router5{Universal Router}
        Router5 -.-> GateHa[Handover Gate]
        GateHa --- HaExpl[Ensures Framework Reflection includes<br/>all 8 required metadata fields]

        GateHa --> Stop[Stop Event]
        Stop --> Router6{Universal Router}
        Router6 -.-> GateQ[QA Gate]
        GateQ --> Commit[Commit & Close]

        GateQ --- QExpl[Final gate: Mandates independent<br/>QA passage and clean git state]
    end

    %% Flow Connections
    Start --> SStart
    State --> UPS
    SkipCheck -- Yes --> PreTool
    OpenCr --> PreTool
    Accountant --> AfterAgent
    Commit --> End([Session End])

    %% Styling (Light & Dark Theme Compatible)
    classDef hook fill:#0277bd,stroke:#01579b,stroke-width:2px,color:#fff
    classDef gate fill:#c62828,stroke:#b71c1c,stroke-width:2px,color:#fff
    classDef agent fill:#6a1b9a,stroke:#4a148c,stroke-width:2px,color:#fff
    classDef state fill:#ef6c00,stroke:#e65100,stroke-width:2px,color:#fff
    classDef event fill:#424242,stroke:#212121,stroke-width:2px,color:#fff
    classDef explain fill:none,stroke:#888,stroke-width:1px,color:#888,font-style:italic

    class Router1,Router2,Router3,Router4,Router5,Router6,Setup,Accountant,Commit hook
    class StartGate,SkipCheck,GateH,GateT,GateC,GateCr,OpenCr,GateCr_Exec,GateHa,GateQ,ThresholdCheck gate
    class Hydrator,Critic agent
    class State,Plan,Context state
    class SStart,UPS,PreTool,PostTool,AfterAgent,Stop event
    class InitExpl,HydrateExpl,CriticExpl,HExpl,TExpl,CrExpl,CExpl,HaExpl,QExpl explain

    %% Subgraph Styling
    style Initialization fill:none,stroke:#888,stroke-dasharray: 5 5
    style Hydration fill:none,stroke:#888,stroke-dasharray: 5 5
    style Execution fill:none,stroke:#888,stroke-dasharray: 5 5
    style Termination fill:none,stroke:#888,stroke-dasharray: 5 5
```

## Core Concepts

### The Logical Derivation System

academicOps is built as a **validated logical system**. Every rule traces back to first principles:

| Level | Document                                | Contains                    | Status                           |
| ----- | --------------------------------------- | --------------------------- | -------------------------------- |
| 1     | **aops-core/AXIOMS.md**                 | Inviolable principles       | Cannot be violated               |
| 2     | **aops-core/HEURISTICS.md**             | Empirically validated rules | Can be revised with evidence     |
| 3     | **aops-core/framework/enforcement-map.md** | Enforcement mechanisms      | Maps rules to technical controls |

**The derivation rule**: Every convention MUST trace to an axiom. If it can't be derived, the convention is invalid.

### Axioms vs Heuristics

**Axioms** are inviolable—they define what the system IS:

- "Fail-Fast": No defaults, no fallbacks, no silent failures
- "Skills Are Read-Only": No dynamic data in skills
- "Research Data Is Immutable": Never modify source datasets

**Heuristics** are working hypotheses validated by evidence:

- "Semantic Link Density": Related files MUST link to each other
- "Skills Contain No Dynamic Content": Current state lives in $ACA_DATA

The difference: axioms cannot be violated; heuristics can and _should be_ be revised when evidence shows they're wrong.

### Skills vs Workflows

The framework distinguishes between **what** to do and **how** to do it:

|              | Skills                           | Workflows                      |
| ------------ | -------------------------------- | ------------------------------ |
| **Answer**   | "How do I do X?"                 | "What should I do?"            |
| **Nature**   | Fungible instructions            | Composable chains of steps     |
| **Examples** | Create a PDF, generate a mindmap | Feature development, TDD cycle |

**Skills** are interchangeable recipes—any skill that creates a PDF can substitute for another. They're the building blocks.

**Workflows** orchestrate those building blocks into coherent processes. A workflow defines the sequence (spec review → implementation → QA), while skills handle each step's mechanics.

For full specification, see [[specs/workflow-system-spec.md]].

### Enforcement Levels

Rules aren't just documented—they're enforced at multiple levels:

| Level          | Mechanism                                  | Example                                   |
| -------------- | ------------------------------------------ | ----------------------------------------- |
| **Hard Gate**  | Blocks action entirely                     | PreToolUse hooks block `git reset --hard` |
| **Soft Gate**  | Injects guidance, agent can proceed        | prompt-hydrator suggests skills           |
| **Prompt**     | Instructional (AXIOMS.md at session start) | "Verify First" reminder                   |
| **Detection**  | Logs for analysis                          | custodiet compliance checks               |
| **Pre-commit** | Blocks commits                             | Orphan file detection                     |

### The Self-Reflexive Framework Agent

This framework treats itself as a hypothesis. Agents are **co-developers**, not just executors:

```
When you encounter friction—something that doesn't fit, a question
the schema can't answer, a pattern that needs a name—do this:

1. Log it.
2. Propose an amendment if you see one.
3. Don't force it. If something doesn't fit, that's data.
```

The framework **evolves through use**. When agents hit friction:

- Violations are logged as bd issues (operational observations)
- Patterns that emerge get named and proposed as new heuristics
- Heuristics that prove themselves get promoted or consolidated
- Rules that don't work get revised

This creates a feedback loop: the framework improves based on real usage, not theoretical design.

### How the Framework Improves Itself

The self-improvement cycle has three phases:

**1. Observe** - Every session generates observables:

- **Framework Reflections**: Agent self-reports at session end (outcome, friction, proposals)
- **Token metrics**: Usage by model, agent, and tool (cache efficiency, throughput)
- **Skill compliance**: Which suggested skills were actually invoked
- **Learning observations**: Mistakes and corrections with root cause categories

See [[specs/framework-observability.md]] for details

**2. Analyze** - Humans identify patterns:

- Recurring friction points → systemic problems
- Low skill compliance → discovery or routing issues
- Token inefficiency → optimize hydration or caching

**3. Intervene** - Apply graduated fixes via `/learn`:

- Start at lowest effective level (corollary, then heuristic, then hook)
- Document root cause and intervention in a task
- Verify improvement in subsequent sessions

See [[specs/feedback-loops.md]] for the complete improvement workflow.

### Memory Architecture

The framework distinguishes between two types of knowledge:

| Type         | Storage            | Example                                               |
| ------------ | ------------------ | ----------------------------------------------------- |
| **Episodic** | task+git issues    | "I tried X and it failed" (time-stamped observations) |
| **Semantic** | $ACA_DATA markdown | "X doesn't work because Y" (timeless truths)          |

$ACA_DATA is a **current state machine**—always up to date, always perfect. The memory server (accessed via `mcp__memory__retrieve_memory`) is a semantic search index derived from this markdown.

## Architecture

### Core Components

| Category    | Components                                                                                                                                                                 |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Skills (24) | remember, analyst, audit, session-insights, garden, hypervisor, task-viz, etc.                                                                                             |
| Agents (5)  | prompt-hydrator, critic, custodiet, qa, effectual-planner                                                                                                                  |
| Hooks (19)  | router.py (Universal Hook Router), unified_logger.py, user_prompt_submit.py, session_env_setup.py, gate system (hydration, task, critic, custodiet, qa, handover)         |
| Governance  | 30+ axioms and heuristics with mechanical and instructional enforcement                                                                                                    |

### Key Agents

| Agent               | Model | Role                                                                    |
| ------------------- | ----- | ----------------------------------------------------------------------- |
| **framework**       | opus  | Primary entry point for framework changes. Handles full task lifecycle. |
| **prompt-hydrator** | haiku | Enriches prompts with context, suggests workflows, applies guardrails   |
| **critic**          | opus  | Reviews plans for errors and hidden assumptions before execution        |
| **custodiet**       | haiku | Periodic compliance audits (every 15 tool calls). Detects drift.        |
| **qa**              | opus  | Independent verification that acceptance criteria are met               |

The **framework agent** embodies the self-reflexive principle—it both executes framework tasks AND proposes improvements to the framework itself.

## Commands

| Command          | Purpose                                                |
| ---------------- | ------------------------------------------------------ |
| /aops            | Show framework capabilities and help                   |
| /diag            | Quick diagnostic of what's loaded in session           |
| /pull            | Pull a task from the queue and claim it                |
| /q               | Quick-queue a task for later                           |
| /learn           | Make minimal framework tweaks with experiment tracking |
| /work            | Collaborative task execution                           |
| /log             | Log framework observations for continuous improvement  |
| /dump            | Emergency work handover and session exit               |
| /bump            | Increment framework version                            |
| /acceptance_test | Run automated acceptance tests for a feature           |

## Key Skills

| Skill             | Purpose                                               |
| ----------------- | ----------------------------------------------------- |
| /analyst          | Academic research data analysis (dbt, Streamlit)      |
| /audit            | Comprehensive framework governance audit              |
| /daily            | Daily note lifecycle, morning briefing, and sync      |
| /remember         | Persist knowledge to markdown and memory server       |
| /session-insights | Generate structured insights from session transcripts |
| /task-viz         | Generate network graph of tasks and notes             |
| /convert-to-md    | Batch convert documents to markdown                   |
| /pdf              | Generate professionally formatted academic PDFs       |
| /hypervisor       | Parallel batch task processing                        |
| /excalidraw       | Create hand-drawn style diagrams and mind maps        |

## Project Configuration

Projects can customize the hydrator's behavior by adding files to a `.agent/` directory in the project root.

### `.agent/context-map.json`

Maps project documentation to topics for just-in-time context injection. The hydrator presents this index to agents, who decide which files to read based on relevance.

```json
{
  "docs": [
    {
      "topic": "authentication",
      "path": "docs/auth-flow.md",
      "description": "OAuth2 implementation with JWT tokens",
      "keywords": ["oauth", "jwt", "login", "session", "token"]
    },
    {
      "topic": "database_schema",
      "path": "docs/schema.md",
      "description": "PostgreSQL table definitions and migrations",
      "keywords": ["postgres", "tables", "migrations", "sql"]
    },
    {
      "topic": "api_endpoints",
      "path": "docs/api.md",
      "description": "REST API reference",
      "keywords": ["api", "rest", "endpoints", "http"]
    }
  ]
}
```

**Fields**:

- `topic`: Short identifier for the documentation area
- `path`: Relative path from project root to the documentation file
- `description`: Brief explanation of what the file covers
- `keywords`: Terms that trigger relevance (agent makes semantic decision, not keyword matching)

### `.agent/rules/`

Project-specific rules that apply to ALL work in the project. Files in this directory are pre-loaded into the hydrator context and presented as binding constraints.

```
project/
├── .agent/
│   ├── rules/
│   │   ├── testing.md      # "All PRs require 80% coverage"
│   │   ├── code-style.md   # "Use ruff, not black"
│   │   └── architecture.md # "No direct DB access from handlers"
```

Rules are loaded automatically—agents don't need to search for them.

### `.agent/workflows/`

Project-specific workflows that supplement the global workflow index. Use for project-specific processes (e.g., release procedures, review checklists).
