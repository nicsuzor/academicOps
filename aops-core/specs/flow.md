---
title: v1.0 Core Loop Specification
type: spec
description: The complete execution flow for aops-core v1.0 - hydration, workflow, QA, reflection
status: DRAFT - PENDING APPROVAL (v2)
---

# v1.0 Core Loop

**Goal**: The minimal viable framework with ONE complete, working loop.

**Philosophy**: Users don't have to use aops. But if they do, it's slow and thorough. The full workflow is MANDATORY.

## The Loop

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              v1.0 CORE LOOP                                   │
│                                                                              │
│    Session Start  (from any arbitrary working dir)                           │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ SessionStart Hook   │  Creates session file                             │
│    │                     │  Sets $AOPS, $PYTHONPATH                          │
│    │                     │  Logs session start                               │
│    └─────────────────────┘                                                   │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ Initial Context     │  AGENTS.md injected (dogfooding instructions)     │
│    │ Injection           │  Inject CORE.md if it exists in CWD               │
│    │                     │  Plugin context loaded                            │
│    └─────────────────────┘  Inject AXIOMS.md from $AOPS                      │
│         │                                                                    │
│         ▼                                                                    │
│    User Prompt                                                               │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ UserPromptSubmit    │  Hook writes context to temp file                 │
│    │ Hook                │                                                   │
│    │                     │  Returns: "Spawn prompt-hydrator"                 │
│    └─────────────────────┘                                                   │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ Prompt Hydrator     │  Reads temp file                                  │
│    │ Agent (haiku)       │  Queries bd for work state                        │
│    │                     │  Queries vector memory for user context           │
│    │                     │  Reads WORKFLOWS.md index                         │
│    │                     │  Selects workflow → reads workflow file           │
│    │                     │  Generates TodoWrite plan from workflow steps     │
│    └─────────────────────┘                                                   │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ Critic Agent        │  Reviews plan BEFORE execution                    │
│    │ (opus)              │  PROCEED / REVISE / HALT                          │
│    │                     │  Identifies problems with the plan                │
│    └─────────────────────┘                                                   │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ Main Agent          │  Receives hydrated + reviewed plan                │
│    │ Executes Plan       │  Uses bd for workflow management                  │
│    │                     │  Marks tasks in_progress → completed              │
│    └─────────────────────┘                                                   │
│         │                                                                    │
│         ├─── [random chance audit]  ────┐                                    │
│         │                               ▼                                    │
│         │                  ┌─────────────────────┐                           │
│         │                  │ Custodiet Agent     │  Checks compliance        │
│         │                  │ (haiku)             │  OK / BLOCK               │
│         │                  │                     │  BLOCKS ALL HOOKS         │
│         │                  │                     │  until flag cleared       │
│         │                  └─────────────────────┘                           │
│         │                               │                                    │
│         │    ┌──────────────────────────┘                                    │
│         │    │ [If BLOCK: immediate HALT, write up progress and error]       │
│         │    │                                                               │
│         ◄────┘                                                               │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ QA Verification     │  MANDATORY end-to-end check                       │
│    │ (independent)       │  Full verification before completion              │
│    │                     │  Not the same agent that did the work             │
│    └─────────────────────┘                                                   │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ Framework Agent     │  Stateful agent that understands framework        │
│    │                     │  Manages its own reflections (in bd)              │
│    │                     │  Generates transcript via skill and python script │
│    │                     │  Outputs structured reflection                    │
│    └─────────────────────┘                                                   │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ Session Insights    │  Written to session file                          │
│    │ Summary             │  Final step of mandatory workflow                 │
│    └─────────────────────┘                                                   │
│         │                                                                    │
│         ▼                                                                    │
│    ┌─────────────────────┐                                                   │
│    │ Session Close       │  Format + commit                                  │
│    │                     │  Push (MANDATORY)                                 │
│    │                     │  Verify "up to date with origin"                  │
│    └─────────────────────┘                                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Features (Core v1.0)

### Agents (5)

| Agent               | Model  | Purpose                                               | Trigger                                      |
| ------------------- | ------ | ----------------------------------------------------- | -------------------------------------------- |
| **prompt-hydrator** | haiku  | Transform prompts → execution plans                   | UserPromptSubmit hook instruction            |
| **critic**          | opus   | Review plans BEFORE execution                         | Main agent after hydrator returns            |
| **custodiet**       | haiku  | Detect scope drift, BLOCK on violation                | PostToolUse hook (periodic)                  |
| **qa**              | opus   | Independent end-to-end verification                   | TodoWrite step before commit                 |
| **framework**       | sonnet | Stateful framework understanding, manages reflections | Before session close                         |

### Tools Required

| Tool               | Purpose                       | Integration                                                 |
| ------------------ | ----------------------------- | ----------------------------------------------------------- |
| **bd**             | Workflow/issue management     | Agents know to use for tracking work                        |
| **mcp__memory__*** | User context retrieval        | Existing memory server, runs parallel to $ACA_DATA markdown |
| **transcript**     | Session transcript generation | Existing skill + python script, used by framework agent     |

**Vector Memory**: Uses existing `mcp__memory__retrieve_memory` and `mcp__memory__store_memory` tools. The memory server runs parallel to `$ACA_DATA` markdown files - they are complementary systems, not integrated.

### Hooks (5 + router)

| Hook                        | Event            | Purpose                                              |
| --------------------------- | ---------------- | ---------------------------------------------------- |
| **router.py**               | All              | Central dispatcher, checks custodiet block flag      |
| **user_prompt_submit.py**   | UserPromptSubmit | Write context + bd state + vector memory to temp     |
| **unified_logger.py**       | All              | Log events to session file                           |
| **session_env_setup.sh**    | SessionStart     | Set $AOPS, $PYTHONPATH                               |
| **custodiet_gate.py**       | PostToolUse      | Periodic compliance check, triggers custodiet agent  |
| **overdue_enforcement.py**  | PreToolUse       | Blocks mutating tools when compliance check overdue  |

### Execution State (Session File)

**Execution state in ~/.claude/projects**, organized by date and session hash: 
- `~/.claude/projects/<project>/{YYYYMMDD}-{hash}/session-state.json`.


<!-- NS: schema should be in separate spec for session state management -->
```json
{
  "session_id": "abc123",
  "date": "2026-01-13",
  "started_at": "2026-01-13T10:00:00Z",
  "ended_at": null,

  "state": {
    "custodiet_blocked": false,
    "custodiet_block_reason": null,
    "current_workflow": "tdd",
    "hydration_pending": false
  },

  "hydration": {
    "original_prompt": "...",
    "hydrated_intent": "...",
    "acceptance_criteria": ["criterion 1", "criterion 2"],
    "critic_verdict": "PROCEED"
  },

  "main_agent": {
    "current_task": "ns-xyz",
    "todos_completed": 3,
    "todos_total": 5
  },

  "subagents": {
    "prompt-hydrator": { "last_invoked": "...", "result": "..." },
    "critic": { "last_invoked": "...", "verdict": "PROCEED", "acceptance_criteria": [...] },
    "custodiet": { "last_invoked": "...", "result": "OK" },
    "qa": { "last_invoked": "...", "result": "VERIFIED" }
  },

  "insights": null
}
```


## Composable Workflow System (LLM-Native Design)

**Status**:
- Phase 1 (Foundation) - COMPLETE
- Phase 2 (LLM-Native Composition) - NEXT

**Paradigm shift**: Pre-LLM structured parsing → LLM-native markdown comprehension

**Key insight**: Workflows are simple markdown that LLMs read and understand. No parsing, no resolvers, no structured data - just readable markdown with [[wikilinks]].

The prompt-hydrator selects from **composable workflows** in `./workflows/`.

**Decision tree**: See [[WORKFLOWS.md]] for complete selection guide.

**How hydrator uses workflows** (LLM-Native Composition):

1. Read WORKFLOWS.md index and match user intent to workflow
2. Read selected workflow file (e.g., `workflows/feature-dev.md`)
3. **LLM reads and understands** the markdown content
4. When it sees "Follow [[spec-review]] workflow", **LLM reads that file too**
5. **LLM composes by understanding** - generates unified TodoWrite plan
6. No parsing code, no resolver utilities - just LLM reading markdown

### Hydration Context Sources

The prompt-hydrator gathers context from:

1. **bd (beads)** - Current work state
   - Open issues assigned to user
   - Blocked issues and blockers
   - Recent activity

2. **Vector Memory** - User knowledge context
   - Integrated with markdown knowledge base at $ACA_DATA
   - Personal notes, preferences, domain knowledge

3. **Session Transcript** - Recent conversation
   - Recent prompts and responses
   - Tool calls and results

## QA Gates

### Critic (BEFORE execution)

**When**: After hydration generates plan, BEFORE main agent executes

**Purpose**: Identify problems with the plan before wasting effort

**Checks**:

1. Logical errors - Flawed reasoning, non-sequiturs
2. Unstated assumptions - What's taken for granted?
3. Missing verification - Claims without evidence
4. Scope drift - Does plan address what was asked?
5. Missing edge cases - What could go wrong?
6. Feasibility - Can this plan actually be executed?

**Output**: `PROCEED` | `REVISE` | `HALT`

### Custodiet (BLOCKING gate)

**When**: Random chance audit during execution (not every tool call)

**CRITICAL**: When custodiet detects a violation:

- Sets `custodiet_blocked: true` in temp execution file
- Immediate HALT - write up progress and error
- ALL hooks check this flag and FAIL until cleared
- Agent cannot proceed with any work

**On BLOCK**:

- Immediate HALT (no further execution)
- Write up current progress to bd issue
- Write up the error/violation found
- Session cannot continue until user intervenes

**Clearing the flag**:

- For now: immediate HALT, no automatic clearing
- User must manually restart session after investigating
- Future: may add `bd session clear-block` command

**Checks**:

1. Axiom/heuristic compliance
2. Scope drift from original request
3. Ultra vires actions (beyond granted authority)

**Output**: `OK` | `BLOCK` (sets flag, immediate HALT)

### QA Verifier (BEFORE completion)

**When**: After execution complete, before reflection

**CRITICAL**: Must be INDEPENDENT agent, not the one that did the work

**Purpose**: Full end-to-end verification that work is actually correct

**Input** (from execution state file):

- Original hydrated prompt (what was requested)
- Acceptance criteria (as approved by Critic agent)
- Current state of work

**Checks**:

1. Does output match original hydrated intent?
2. Are all acceptance criteria (from Critic) met?
3. Do tests pass?
4. Is documentation updated?
5. Are there any obvious errors?

**Output**: `VERIFIED` | `ISSUES` (list problems to fix)

## Framework Agent

**Purpose**: Stateful agent that completely understands the framework

**Capabilities**:

1. Manages its own reflections (stored in bd issues)
2. Generates transcript using existing skill + python script
3. Understands full framework architecture
4. Tracks patterns across sessions via bd issues

**State Storage**: Framework agent stores all cross-session learnings in `bd` issues:

- Reflections → `bd create --type=task --title="Reflection: ..."`
- Patterns observed → `bd create --type=task --title="Learning: ..."`
- Framework improvements → `bd create --type=feature`

**Workflow**:

1. Invoke transcript skill to generate session transcript
2. Analyze what happened in the session
3. Generate structured reflection
4. Store reflection in bd (linked to session)
5. Identify framework improvements → create bd issues

### Framework Reflection

<!-- NS: link missing -->
Framework reflection workflow is defined in __MISSING__

- Stop hook **reminds** agents to reflect (does not automate it)
- Agents MUST output Framework Reflection at end of every session (MANDATORY)
- Agents use `/log` command when framework friction/failures observed during work
- Reflection format and workflow details in AGENTS.md (single source of truth)

## Session Insights

Session insights are generated via **two workflows**.

See `aops-core/specs/session-insights-prompt.md` for full schema specification.

### Workflow A: Agent Reflection (MANDATORY)

At the end of every session, the agent MUST output Framework Reflection (see AGENTS.md "Hand off" section):
- Summary of what was accomplished
- Outcome (success/partial/failure)
- Friction points observed
- Proposed improvements
- Next steps

The Stop hook provides a **reminder** to generate this reflection, but does not automate it.

### Workflow B: Manual (Gemini Post-hoc)

Gemini uses the **same prompt** as Workflow A (Claude in-stream) to generate rich insights.

<!-- NS: invocation may be different now -->
User invokes `/session-insights` skill to analyze transcripts with Gemini:

```bash
/session-insights {session_id}  # Specific session
/session-insights              # Current session
/session-insights batch        # Process multiple
```


## Hook Event Flow

See [[README]]
