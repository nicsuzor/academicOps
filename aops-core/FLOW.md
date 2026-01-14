---
title: v1.0 Core Loop - Overview
type: overview
description: Concise overview of the v1.0 core loop with visual flow diagram
see_also: aops-core/specs/flow.md (comprehensive specification)
---

# v1.0 Core Loop - Overview

**For detailed specification, see**: [[aops-core/specs/flow.md]]

**Goal**: The minimal viable framework with ONE complete, working loop.

**Philosophy**: Users don't have to use aops. But if they do, it's slow and thorough. The full workflow is MANDATORY.

## Core Loop Diagram

```mermaid
flowchart TD
    subgraph "Session Initialization"
        A[Session Start] --> B[SessionStart Hook]
        B --> C[Create Session File<br>/tmp/aops-DATE-ID.json]
        C --> D[Set $AOPS, $PYTHONPATH]
        D --> E[Inject AGENTS.md + Plugin Context]
    end

    subgraph "Prompt Processing"
        E --> F[User Prompt]
        F --> G[UserPromptSubmit Hook]
        G --> H{Skip Hydration?}
        H -->|Yes: /, ., notifications| I[Direct Execution]
        H -->|No| J[Write Context to Temp File]
        J --> K[prompt-hydrator Agent<br>haiku]
    end

    subgraph "Plan Generation & Review"
        K --> L[Gather Context:<br>bd state + vector memory]
        L --> L1[Read WORKFLOWS.md Index]
        L1 --> M[Select Workflow]
        M --> M1[Read Workflow File<br>workflows/workflow-id.md]
        M1 --> N[Generate TodoWrite Plan<br>from workflow steps]
        N --> O[critic Agent<br>opus]
        O --> P{Critic Verdict}
        P -->|PROCEED| Q[Main Agent Receives Plan]
        P -->|REVISE| N
        P -->|HALT| R[Stop - Present Issues]
    end

    subgraph "Execution"
        Q --> S[Execute Plan via TodoWrite]
        S --> T{Random Audit?}
        T -->|Yes ~14%| U[custodiet Agent<br>haiku]
        T -->|No| V[Continue Work]
        U --> W{Custodiet Check}
        W -->|OK| V
        W -->|BLOCK| X[HALT - Set Block Flag<br>All Hooks Fail]
        V --> Y[Mark Todos Complete]
    end

    subgraph "Verification & Close"
        Y --> Z[qa Agent<br>opus - INDEPENDENT]
        Z --> AA{Verified?}
        AA -->|VERIFIED| AB[framework Agent<br>sonnet]
        AA -->|ISSUES| AC[Fix Issues]
        AC --> Y
        AB --> AD[Generate Reflection]
        AD --> AE[Store in bd Issues]
        AE --> AF[Write Session Insights]
        AF --> AG[Session Close:<br>format + commit + PUSH]
    end

    style X fill:#ff6666
    style AG fill:#66ff66
```

## Session Initialization (SessionStart Hook)

The core loop BEGINS with SessionStart, before any user prompt is processed.

### SessionStart Hook Dispatch

When a Claude Code session starts, `router.py` dispatches two hooks in sequence:

1. **session_env_setup.sh** - Environment configuration
   - Sets `$AOPS` to the academicOps root directory
   - Adds `$AOPS` to `$PYTHONPATH` for Python imports
   - Writes environment to `$CLAUDE_ENV_FILE` (persists for session)
   - Validates path by checking for `AXIOMS.md`

2. **unified_logger.py** - Session state initialization
   - Creates session file at `/tmp/aops-{YYYY-MM-DD}-{session_id}.json`
   - Records session start timestamp
   - Initializes empty state for hydration, subagents, and insights

### Initial File Injection (claude.md)

Claude Code's built-in `claude.md` mechanism injects context at session start:

1. **Project CLAUDE.md** (`.claude/CLAUDE.md`) - Contains `@AGENTS.md` reference
2. **AGENTS.md** (repository root) - Dogfooding instructions loaded via `@` directive
3. **Plugin context** - Any registered plugin instructions

This injection happens BEFORE the first UserPromptSubmit, ensuring the agent has:

- Framework development guidelines (dogfooding mode)
- Reflection format requirements
- Session close workflow requirements

### Hook Registration

SessionStart hooks are registered in `.claude/settings.json`:

```json
"SessionStart": [
  {
    "hooks": [{
      "type": "command",
      "command": "PYTHONPATH=$AOPS uv run python $AOPS/aops-core/hooks/router.py"
    }]
  },
  {
    "hooks": [{"type": "command", "command": "bd prime"}]
  }
]
```

The router dispatches to `session_env_setup.sh` and `unified_logger.py` based on `HOOK_REGISTRY` in `router.py`.

## What's IN (Core v1.0)

### Agents (5)

| Agent               | Model  | Purpose                                               | Trigger                      |
| ------------------- | ------ | ----------------------------------------------------- | ---------------------------- |
| **prompt-hydrator** | haiku  | Transform prompts → execution plans                   | UserPromptSubmit hook        |
| **critic**          | opus   | Review plans BEFORE execution                         | After hydration              |
| **custodiet**       | haiku  | Detect scope drift, BLOCK on violation                | Random audit (~7 tool calls) |
| **qa**     | opus   | Independent end-to-end verification                   | Before completion            |
| **framework**       | sonnet | Stateful framework understanding, manages reflections | Before session close         |

### Hooks (3 + router)

| Hook                      | Event            | Purpose                                         |
| ------------------------- | ---------------- | ----------------------------------------------- |
| **router.py**             | All              | Central dispatcher, checks custodiet block flag |
| **user_prompt_submit.py** | UserPromptSubmit | Write context to temp, trigger hydration        |
| **unified_logger.py**     | All              | Log events to session file                      |
| **session_env_setup.sh**  | SessionStart     | Set $AOPS, $PYTHONPATH                          |

### Supporting Libraries

| File                    | Purpose                        |
| ----------------------- | ------------------------------ |
| `lib/paths.py`          | Path resolution                |
| `lib/session_state.py`  | Single session file management |
| `lib/session_reader.py` | Transcript context extraction  |

### External Tools

| Tool               | Purpose                   | Integration           |
| ------------------ | ------------------------- | --------------------- |
| **bd**             | Workflow/issue management | Agents invoke CLI     |
| **mcp__memory__*** | User context retrieval    | MCP server (existing) |

### Skills

**NONE in v1.0 core.** Skills are extensions, not the loop.

## What's OUT (Archived)

- All 28 skills (in archived/skills/)
- 19 additional hooks (in archived/hooks/)
- Other agents: planner, effectual-planner, framework-executor
- Unenforced axioms/heuristics

## Composable Workflow System (LLM-Native)

**NEW in v1.0**: Simple markdown workflows that LLMs read and compose.

**Key insight**: No parsing - LLMs read markdown and understand it.

### Current Status

**Phase 1 (Foundation) - COMPLETE**:
- ✅ 9 workflow files in `workflows/` directory
- ✅ WORKFLOWS.md index with decision tree
- ✅ Hydrator reads and selects workflows
- ⚠️ Workflows still have complex YAML frontmatter (legacy from pre-LLM design)

**Phase 2 (LLM-Native Composition) - NEXT**:
- 🔄 Simplify workflows: remove YAML structure, keep human-readable markdown
- 🔄 Update hydrator: "When you see [[spec-review]], read that file"
- 🔄 Inline expansion by LLM understanding (not parsing code)
- 🔄 Mid-grained TodoWrite plans (not every git command)

### The 9 Workflows

**Development**: feature-dev, minor-edit, debugging, tdd-cycle
**Planning & QA**: spec-review, qa-demo
**Operations & Routing**: batch-processing, simple-question, direct-skill

**Composition**: Workflows reference each other with `[[wikilinks]]`
- Example: `feature-dev` → Follow [[spec-review]] workflow for critic feedback
- LLM reads referenced file and generates unified plan
- No code needed - LLM composes by understanding

### How It Works

1. **Hydrator reads** WORKFLOWS.md and selects workflow
2. **Hydrator reads** `workflows/feature-dev.md` (simple markdown)
3. **Hydrator sees** "Follow [[spec-review]] workflow"
4. **Hydrator reads** `workflows/spec-review.md` inline
5. **Hydrator generates** unified TodoWrite plan with mid-grained tasks
6. **No parsing** - just LLM reading markdown and understanding it

### bd Issue Granularity

**Mid-grained tasks** (good):
- "Implement user auth" with list: create model, add JWT, write tests
- "Land changes" with list: format, git add, commit, push

**Too fine-grained** (bad):
- Separate issues for "git add", "git commit", "git push"

**Rule**: < 30 seconds = list item. Needs decision-making = separate task.

## Quality Gates

Three mandatory quality gates ensure correctness:

1. **Critic** (BEFORE execution) - Reviews plan, outputs `PROCEED` | `REVISE` | `HALT`
2. **Custodiet** (DURING execution) - Random audit, can BLOCK all hooks on violation
3. **QA Verifier** (BEFORE completion) - Independent verification, outputs `VERIFIED` | `ISSUES`

**See**: [[aops-core/specs/flow.md]] for detailed specifications.

## Session Reflection & Insights

**Automatic Insights** (Stop Hook):
- JSON insights automatically generated when session ends
- Contains: operational metrics, workflows used, subagents invoked
- Stored: `$ACA_DATA/sessions/insights/{date}-{session_id}.json`
- No agent action required

**Framework Issue Logging** (`/log` command):
- Used when framework friction or failures observed during work
- Invokes framework agent to generate structured reflection
- Creates bd issue for tracking (failures/improvements only)
- NOT for routine session ends with no issues

**Rich Analysis** (`/session-insights` skill):
- Optional post-hoc analysis with Gemini
- Generates detailed insights: learning observations, skill compliance, context gaps
- Overwrites automatic insights with richer data

**User-facing workflow**: Work completes → Stop hook persists insights → (Optional) User runs `/session-insights` for deep analysis → Issues filed via `/log` as needed

## Session Close

Work is NOT complete until `git push` succeeds. See AGENTS.md for full landing protocol.

---

**For comprehensive details**, see [[aops-core/specs/flow.md]]
