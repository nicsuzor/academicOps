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

## What's IN (Core v1.0)

### Agents (5)

| Agent               | Model  | Purpose                                               | Trigger                         |
| ------------------- | ------ | ----------------------------------------------------- | ------------------------------- |
| **prompt-hydrator** | haiku  | Transform prompts → execution plans                   | UserPromptSubmit hook           |
| **critic**          | opus   | Review plans BEFORE execution                         | After hydration, before execute |
| **custodiet**       | haiku  | Detect scope drift, BLOCK on violation                | Compliance checkpoints          |
| **qa-verifier**     | opus   | Independent end-to-end verification                   | Before completion               |
| **framework**       | sonnet | Stateful framework understanding, manages reflections | Before session close            |

### Tools Required

| Tool               | Purpose                       | Integration                                                 |
| ------------------ | ----------------------------- | ----------------------------------------------------------- |
| **bd**             | Workflow/issue management     | Agents know to use for tracking work                        |
| **mcp__memory__*** | User context retrieval        | Existing memory server, runs parallel to $ACA_DATA markdown |
| **transcript**     | Session transcript generation | Existing skill + python script, used by framework agent     |

**Vector Memory**: Uses existing `mcp__memory__retrieve_memory` and `mcp__memory__store_memory` tools. The memory server runs parallel to `$ACA_DATA` markdown files - they are complementary systems, not integrated.

### Hooks (3 + router)

| Hook                      | Event            | Purpose                                          |
| ------------------------- | ---------------- | ------------------------------------------------ |
| **router.py**             | All              | Central dispatcher, checks custodiet block flag  |
| **user_prompt_submit.py** | UserPromptSubmit | Write context + bd state + vector memory to temp |
| **unified_logger.py**     | All              | Log events to session file                       |
| **session_env_setup.sh**  | SessionStart     | Set $AOPS, $PYTHONPATH                           |

### Execution State (Session File)

**Execution state in ~/.claude/projects**, organized by date and session hash:

```
~/.claude/projects/<project>/{YYYYMMDD}-{hash}/session-state.json
```

Contains:

- Session ID
- Date
- Custodiet block flag (true/false)
- Hook state for main agent
- Hook state for subagents (if needed)
- Hydrated prompt (for QA verifier)
- Acceptance criteria (as approved by Critic)
- Timestamps

**Note**: This is ephemeral execution state, not persistent data.

### Supporting Files

| File                                         | Purpose                                  |
| -------------------------------------------- | ---------------------------------------- |
| `lib/paths.py`                               | Path resolution                          |
| `lib/session_state.py`                       | Single session file management           |
| `lib/session_reader.py`                      | Transcript context extraction            |
| `scripts/transcript.py`                      | Generate transcript for framework agent  |
| `hooks/templates/prompt-hydrator-context.md` | Hydration template with workflow catalog |
| `AGENTS.md` (root)                           | Dogfooding instructions                  |

### Skills

**NONE in v1.0 core**. Skills are extensions, not the loop.

## What's OUT (Archived)

- All 28 skills
- All other hooks (19 archived)
- Other agents (planner, effectual-planner, framework-executor)
- Unenforced axioms/heuristics

## Composable Workflow System

**Status**: Phase 1 (Foundation) completed. Workflows stored as YAML+Markdown files in `workflows/`.

The prompt-hydrator selects from **9 composable workflows**:

### Development Workflows

| Workflow ID   | File                       | Purpose                                      | Quality Gates                          |
| ------------- | -------------------------- | -------------------------------------------- | -------------------------------------- |
| feature-dev   | workflows/feature-dev.md   | Full TDD feature development                 | Critic review, TDD, Tests pass, QA     |
| minor-edit    | workflows/minor-edit.md    | Small, focused changes                       | TDD, Tests pass                        |
| debugging     | workflows/debugging.md     | Systematic debugging with reproducible tests | Reproducible test                      |
| tdd-cycle     | workflows/tdd-cycle.md     | Classic red-green-refactor cycle             | Tests pass, No regression              |

### Planning & QA Workflows

| Workflow ID  | File                      | Purpose                      | Quality Gates                          |
| ------------ | ------------------------- | ---------------------------- | -------------------------------------- |
| spec-review  | workflows/spec-review.md  | Critic feedback iteration    | Critic feedback, Convergence           |
| qa-demo      | workflows/qa-demo.md      | Independent QA verification  | Functionality, Quality, Completeness   |

### Operations & Routing Workflows

| Workflow ID      | File                             | Purpose                         | Quality Gates                |
| ---------------- | -------------------------------- | ------------------------------- | ---------------------------- |
| batch-processing | workflows/batch-processing.md    | Parallel processing             | All items processed, Verified|
| simple-question  | workflows/simple-question.md     | Info-only, no modifications     | None (information only)      |
| direct-skill     | workflows/direct-skill.md        | Direct skill/command routing    | Delegated to skill           |

### Workflow Selection

**Decision tree**: See [[WORKFLOWS.md]] for complete selection guide with decision tree.

**How hydrator uses workflows** (Phase 1 - Basic reading):

1. Read WORKFLOWS.md index to see available workflows
2. Match user intent to workflow using decision tree
3. Read selected workflow file from `workflows/[workflow-id].md`
4. Parse YAML frontmatter for structured steps
5. Read Markdown body for detailed instructions
6. Generate TodoWrite plan from workflow steps

**Workflow composition** (Phase 1 - Basic reading):
- Workflows reference other workflows using `[[wikilinks]]` in YAML frontmatter
- Example: `feature-dev` step 4 has `workflow: "[[spec-review]]"`
- Phase 1: Hydrator reads but doesn't recursively resolve wikilinks
- Phase 2: Will implement recursive wikilink resolution and full composition

### Workflow File Structure

Each workflow file contains:

**YAML Frontmatter:**
```yaml
---
id: workflow-id
title: Human Readable Title
type: workflow
category: development|planning|qa|operations|information|routing
dependencies: []
steps:
  - id: step-id
    name: Step Name
    workflow: null  # Or "[[other-workflow]]" for composition
    description: What this step does
---
```

**Markdown Body:**
- ## Overview
- ## When to Use
- ## Steps (detailed instructions for each)
- ## Success Metrics

## Hydration Context Sources

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

## Framework Reflection (MANDATORY)

After completing work, framework agent MUST output:

```
## Framework Reflection

**Request**: [Original user request in brief]
**Guidance received**: [Hydrator/custodiet advice, or "N/A - direct execution"]
**Followed**: [Yes/No/Partial - explain what was followed or skipped]
**Outcome**: [Success/Partial/Failure]
**Accomplishment**: [What was accomplished, if success/partial]
**Root cause** (if not success): [Which framework component failed]
**Proposed change**: [Specific improvement or "none needed"]
```

Reflection is stored in bd for trend analysis.

## Session Insights (Final Step)

Session insights are generated via **two workflows**:

### Workflow A: Automatic (Stop Hook)

When session ends, `unified_logger.py` automatically generates insights to:

1. **Permanent storage**: `$ACA_DATA/sessions/insights/{date}-{session_id}.json`
2. **Session state**: `session-state.json` (temporary, for QA verifier)

Currently generates **operational metrics** with minimal required fields:
- Metadata: session_id, date, project
- Summary: "Session completed"
- Outcome: "partial" (conservative default)
- Operational: workflows_used, subagents_invoked, custodiet_blocks, stop_reason

**Future**: LLM-based generation (when API integration available) will add rich insights.

### Workflow B: Manual (Gemini Post-hoc)

User invokes `/session-insights` skill to analyze transcripts with Gemini:

```bash
/session-insights {session_id}  # Specific session
/session-insights              # Current session
/session-insights batch        # Process multiple
```

Generates **rich insights**:
- Learning observations
- Skill compliance tracking
- Context gaps
- User mood/satisfaction
- Conversation flow

Overwrites automatic insights with more detailed analysis.

### Unified Schema

Both workflows write to same location with same schema:

```json
{
  "session_id": "a1b2c3d4",
  "date": "2026-01-13",
  "project": "academicOps",

  "summary": "One sentence description",
  "outcome": "success|partial|failure",
  "accomplishments": ["item1", "item2"],
  "friction_points": ["issue1"],
  "proposed_changes": ["change1"],

  "workflows_used": ["tdd"],
  "subagents_invoked": ["prompt-hydrator", "critic"],
  "subagent_count": 2,
  "custodiet_blocks": 0,
  "stop_reason": "end_turn",
  "critic_verdict": "PROCEED",
  "acceptance_criteria_count": 3,

  "learning_observations": [...],
  "skill_compliance": {...},
  "context_gaps": [...],
  "user_mood": 0.5,
  "conversation_flow": [...],
  "user_prompts": [...]
}
```

**Storage locations**:
- **Permanent**: `$ACA_DATA/sessions/insights/{date}-{session_id}.json` (research data)
- **Temporary**: `session-state.json["insights"]` (for QA verifier during session)

See `aops-core/specs/session-insights-prompt.md` for full schema specification.

## Session Close (MANDATORY)

Work is NOT complete until `git push` succeeds.

```bash
./scripts/format.sh        # Format all files
git add -A                  # Stage formatted files
git commit -m "..."         # Pre-commit validates
git pull --rebase           # Sync with remote
bd sync                     # Sync beads
git push                    # MANDATORY
git status                  # MUST show "up to date with origin"
```

**CRITICAL**: Agent MUST push. Never say "ready to push when you are".

## Execution State File Structure

Single state file per session at `~/.claude/projects/<project>/{YYYYMMDD}-{hash}/session-state.json`:

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
    "qa-verifier": { "last_invoked": "...", "result": "VERIFIED" }
  },

  "insights": null
}
```

**Note**: This is ephemeral execution state in /tmp. Persistent data (reflections, learnings) goes to bd.

## Hook Event Flow

```
SessionStart
    │
    ├── [CHECK custodiet_blocked flag] → If blocked, FAIL
    ├── session_env_setup.sh → Set environment
    └── unified_logger.py → Log to session file

UserPromptSubmit (each prompt)
    │
    ├── [CHECK custodiet_blocked flag] → If blocked, FAIL
    ├── user_prompt_submit.py:
    │     1. Load bd state (open issues, blockers)
    │     2. Query vector memory for user context
    │     3. Write temp file with full context
    │     4. Return hydration instruction
    └── unified_logger.py → Log to session file

PreToolUse (each tool call)
    │
    ├── [CHECK custodiet_blocked flag] → If blocked, FAIL
    └── unified_logger.py → Log to session file

PostToolUse (each tool result)
    │
    ├── [CHECK custodiet_blocked flag] → If blocked, FAIL
    └── unified_logger.py → Log to session file

Stop (session end)
    │
    └── unified_logger.py → Write session insights, close session file
```

## Success Criteria for v1.0

- [ ] Fresh session triggers hydration automatically
- [ ] Hydration includes bd state and vector memory context
- [ ] Critic reviews plan BEFORE execution
- [ ] Custodiet BLOCKS all hooks when violation detected
- [ ] User can clear custodiet block via bd command
- [ ] QA verifier independently checks work before completion
- [ ] Framework agent generates transcript and reflection
- [ ] Session insights written to single session file
- [ ] Commit + push completes every session
- [ ] All agents know to use bd for workflow management

## Implementation Status

**Constraint**: NO NEW CODE - wiring only. Gaps require spec review.

| Component             | Status | Wiring Task                                               |
| --------------------- | ------ | --------------------------------------------------------- |
| router.py             | EXISTS | Wire: add custodiet block flag check                      |
| user_prompt_submit.py | EXISTS | Wire: call mcp__memory, call bd                           |
| unified_logger.py     | EXISTS | Wire: write to /tmp execution state file                  |
| Execution state file  | WIRE   | Create file in SessionStart, update throughout            |
| prompt-hydrator.md    | EXISTS | Wire: add mcp__memory + bd tools to definition            |
| critic.md             | EXISTS | Wire: output acceptance_criteria to state file            |
| custodiet.md          | EXISTS | Wire: HALT behavior, write to state file                  |
| qa-verifier.md        | EXISTS | Use archived/specs/qa-eval.md spec + create agent def     |
| framework.md          | EXISTS | Use archived/agents/framework-executor.md, adapt for v1.0 |
| transcript skill      | EXISTS | In archived/skills/ - move to core if needed              |
| mcp__memory__*        | EXISTS | Already available MCP tools                               |
| bd                    | EXISTS | CLI tool, agents already know it                          |
| Demo tests            | TODO   | Use existing test infrastructure                          |

**GAP = requires spec review before proceeding**

## Resolved Questions

1. **Custodiet on BLOCK**: Immediate HALT. No automatic clearing for now - user must restart session after investigating.
2. **Vector memory**: Uses existing `mcp__memory__*` server. Runs parallel to $ACA_DATA markdown (complementary systems).
3. **Framework agent state**: Stores all learnings in `bd` issues (reflections, patterns, improvements).
4. **QA verifier input**: Gets original hydrated prompt + acceptance criteria (as approved by Critic) from execution state file.
5. **Execution state location**: `~/.claude/projects/<project>/{YYYYMMDD}-{hash}/session-state.json` (organized by date and session).

## Implementation Constraint

**CRITICAL: NO NEW CODE**

Everything described in this spec ALREADY EXISTS in the codebase. The v1.0 implementation is about:

1. **Wiring existing components together** - connecting hooks, agents, tools that already exist
2. **Configuration changes** - updating settings, templates, agent definitions
3. **Moving files** - from archived/ to aops-core/ as needed

**Where gaps are found**:

- HALT implementation
- Request full spec review from user
- Do NOT write new code without explicit approval

**Existing components to wire**:

- `mcp__memory__retrieve_memory` / `mcp__memory__store_memory` - existing MCP tools
- `bd` - existing CLI tool, agents already know how to use it
- `scripts/transcript.py` - likely exists or has equivalent
- Hooks in `aops-core/hooks/` - already implemented
- Agents in `aops-core/agents/` - already defined

**If something doesn't exist**: Stop, document the gap, request spec review.
