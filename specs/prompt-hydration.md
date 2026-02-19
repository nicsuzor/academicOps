---
title: Prompt Hydration
type: spec
category: spec
status: implemented
permalink: prompt-hydration
tags: [framework, routing, context]
---

# Prompt Hydration

Transform a raw user prompt into a complete execution plan with workflow selection and quality gates.

## Giving Effect

- [[hooks/user_prompt_submit.py]] - Entry point: extracts context, writes temp file, returns short instruction
- [[hooks/templates/prompt-hydrator-context.md]] - Full context template written to temp file
- [[agents/prompt-hydrator.md]] - Minimal routing agent (~284 lines) that delegates to workflows
- [[workflows/hydrate.md]] - Main hydration decision process workflow
- [[workflows/framework-gate.md]] - Framework modification detection and routing
- [[workflows/constraint-check.md]] - Plan constraint verification logic
- [[lib/session_reader.py]] - `extract_router_context()` for session state extraction
- [[lib/file_index.py]] - FILE_INDEX for selective path injection based on keywords
- [[INDEX.md]] - Master index pointing to all sub-indices
- [[SKILLS.md]] - Skills index with invocation patterns
- [[WORKFLOWS.md]] - Workflow decision tree and routing

## Purpose

Users type terse prompts. Agents need:

- **Intent** - What does the user actually want?
- **Workflow** - Which workflow template applies?
- **Steps** - What specific actions, in what order?
- **Guardrails** - What constraints apply?

Prompt Hydration bridges this gap automatically on every prompt, outputting a complete execution plan the agent can follow.

## Architecture (Modular Workflow System)

The hydrator follows a **composition-based architecture** where routing logic is defined in reusable workflows:

```
┌───────────────────────────────────────────────────────────────────────┐
│                       prompt-hydrator.md                              │
│                (Minimal agent - 284 lines)                            │
│                                                                       │
│  Responsibilities:                                                    │
│  - Read input file                                                    │
│  - Gather context from memory                                         │
│  - Output formatted plans                                             │
│                                                                       │
│  Delegates to workflows for decision logic:                           │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐ │
│  │ hydrate           │  │ framework-gate    │  │ constraint-check  │ │
│  │ Main decision     │  │ Framework         │  │ Plan              │ │
│  │ process           │  │ detection         │  │ verification      │ │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

Workflows referenced: hydrate, framework-gate, constraint-check (see `workflows/` directory)

### Key Workflows

| Workflow             | Purpose                                      | Location                        |
| -------------------- | -------------------------------------------- | ------------------------------- |
| [[hydrate]]          | Main hydration decision process              | `workflows/hydrate.md`          |
| [[framework-gate]]   | First check - detect framework modifications | `workflows/framework-gate.md`   |
| [[constraint-check]] | Verify plan satisfies workflow constraints   | `workflows/constraint-check.md` |

### Design Principles

1. **Composition over embedding** - Routing logic lives in workflows, not hardcoded in agent
2. **Single responsibility** - Agent handles I/O and formatting; workflows define decisions
3. **Reusable patterns** - Framework gate and constraint check can be invoked by other agents

## When It Runs

**Every UserPromptSubmit** - This closes the "control gap" where freeform prompts previously got baseline context only.

```
User types prompt
    ↓
UserPromptSubmit hook fires
    ↓
Prompt Hydration runs
    ↓
Main agent receives: complete execution plan with steps
```

## Hydrator Outputs

The hydrator outputs a complete execution plan with four components:

### 1. Intent Envelope

What the user actually wants, in clear terms:

```
Intent: Fix the type error in parser.py that's causing the build to fail
```

### 2. Selected Workflow

Which workflow from the catalog applies:

```
Workflow: design
Quality gate: Verification step required
Commit required: Yes
```

### 3. Execution Plan

The hydrator interprets the workflow for this specific task, breaking it into concrete steps:

```markdown
## Execution Steps

1. Read parser.py and understand the type error
2. Implement the fix
3. CHECKPOINT: Run pytest to verify fix works
4. Commit and push
```

### 4. Guardrails

Constraints that apply based on workflow:

```
Guardrails: verify_before_complete, fix_within_design
```

## Workflow Catalog

**Single Source of Truth**: See [[WORKFLOWS.md]] for the complete workflow index and decision tree.

The hydrator reads WORKFLOWS.md to select the appropriate workflow based on user intent. Each workflow is defined in `workflows/[workflow-id].md`.

**Key insight**: The workflow is NOT mechanical. The hydrator INTERPRETS the workflow template for the specific user request, generating concrete steps.

## Context Gathering

The hydrator follows the **Knowledge Retrieval Hierarchy** to inform workflow selection and step planning:

| Tier  | Source              | What                                                                  |
| ----- | ------------------- | --------------------------------------------------------------------- |
| **1** | **Memory Server**   | PRIMARY: Semantic search for related knowledge (mcp__memory)          |
| **2** | **Framework Specs** | SECONDARY: AXIOMS, HEURISTICS, and pre-loaded indices                 |
| **3** | **External Search** | TERTIARY: GitHub or Web search when internal sources are insufficient |
| **4** | **Transcripts**     | LAST RESORT: Raw session logs for very recent context                 |

**Total budget**: ~450 tokens of context for the hydrator itself (Tier 1 & 2). Tier 3 & 4 are suggested as execution steps for the main agent.

## Index Loading System

The hydrator receives pre-loaded indices to enable routing decisions without runtime file reads.

### Master Index

[[INDEX.md]] is the authoritative source pointing to all sub-indices:

| Index                | Purpose                      | Always Loaded |
| -------------------- | ---------------------------- | ------------- |
| [[SKILLS.md]]        | Skill invocation patterns    | Yes           |
| [[WORKFLOWS.md]]     | Workflow decision tree       | Yes           |
| [[AXIOMS.md]]        | Inviolable principles (full) | Yes           |
| [[HEURISTICS.md]]    | Guidelines (full)            | Yes           |
| [[RULES.md]]         | Quick-reference P# lookup    | On demand     |
| [[indices/FILES.md]] | File discovery               | On demand     |
| [[indices/PATHS.md]] | Resolved paths               | On demand     |

### Index Schema

Each index MUST have YAML frontmatter:

```yaml
---
name: <identifier>
title: <human title>
type: index
category: framework
description: <purpose>
---
```

### Loading Implementation

The `user_prompt_submit.py` hook loads indices into the temp file context:

1. **Always loaded** (every prompt):
   - `load_workflows_index()` → WORKFLOWS.md content
   - `load_skills_index()` → SKILLS.md content
   - `load_axioms()` → AXIOMS.md content
   - `load_heuristics()` → HEURISTICS.md content

2. **Selectively loaded** (based on prompt keywords):
   - `get_formatted_relevant_paths()` → FILE_INDEX entries matching keywords

### Design Rationale (P#58, P#43)

- **P#58 Indices Before Exploration**: Curated indices preferred over grep/fs searches
- **P#43 Just-In-Time Context**: Hydrator surfaces relevant index content automatically
- **P#60 Local AGENTS.md**: Each project can provide its own indices in `.agent/`

### Project-Specific Indices

Projects can extend the index system via `.agent/`:

```
project/
└── .agent/
    ├── context-map.json    # JIT context mapping
    └── workflows/          # Project-specific workflows
        └── TESTING.md
```

The hydrator checks for project indices and includes them when present.

## Agent Execution

The main agent receives the hydrator's output and follows the plan:

1. **Follow execution steps** exactly as specified by hydrator
2. **For each step**: Execute sequentially
3. **At CHECKPOINTs**: Verify with evidence before proceeding
4. **Cleanup**: Commit, push as directed by workflow

The agent doesn't need to make routing decisions — the hydrator already made them.

> **Note on CHECKPOINTs**: The `CHECKPOINT:` prefix in execution steps is **behavioral guidance**, not programmatic enforcement. The agent is expected to gather evidence and verify before proceeding, but no code blocks progress if verification is skipped or fails. Reliability depends on agent instruction-following. This is an intentional design choice favoring simplicity over enforcement complexity.

## Output Format

The hydrator returns structured guidance:

````markdown
## Prompt Hydration

**Intent**: [what user wants]
**Workflow**: [workflow name] ([quality gate])
**Guardrails**: [list]

### Relevant Context

- [context from memory/codebase/session]

### Execution Plan

```markdown
## Execution Steps

1. [Step description]
2. CHECKPOINT: [verification]
3. [Final step]
```
````

## Performance Requirements

| Metric      | Target       |
| ----------- | ------------ |
| Typical     | 5-10 seconds |
| Max timeout | 15 seconds   |

Quality of context gathering and plan generation matters more than speed.

## Failure Modes

| Failure                         | Behavior                                                      |
| ------------------------------- | ------------------------------------------------------------- |
| Temp file write fails           | Hook exits non-zero, logs error (fail-fast)                   |
| Temp file read fails (subagent) | Subagent returns error, main agent proceeds without hydration |
| Main agent ignores instruction  | Silent failure - hydration doesn't happen (known risk)        |
| Memory search fails             | Continue with codebase/session context only                   |
| Workflow uncertain              | Default to `plan-mode` for safety                             |
| Timeout                         | Return partial context, log warning                           |
| Complete failure                | Return empty context, agent proceeds with baseline            |

Fail-fast on infrastructure errors (temp file). Graceful degradation only for content-gathering failures.

## Architecture

The implementation uses a temp file approach for token efficiency:

```
UserPromptSubmit hook
↓
Extract session context, write full context to temp file
↓
Main agent receives SHORT instruction (~100 tokens) with file path
↓
Main agent spawns prompt-hydrator subagent (Haiku)
↓
Subagent reads temp file, generates complete execution plan
↓
Main agent follows the plan
```

**Why temp files:**

- **Token efficiency**: Main agent sees ~100 tokens (instruction + path) vs ~500+ tokens (full embedded context)
- **Subagent gets full context**: File contains complete prompt + session state + workflow catalog
- **Debuggable**: Temp files can be inspected for troubleshooting

**Temp file handling:**

- **Location**: `/tmp/claude-hydrator/` (created with `makedirs` if missing)
- **Naming**: Uses `tempfile.NamedTemporaryFile` with prefix `hydrate_` to avoid collisions
- **Cleanup**: Files deleted after 1 hour via cleanup on hook invocation
- **On failure**: If temp write fails, hook returns error and HALTS (no silent fallback per AXIOM #7)

## Acceptance Criteria

1. Hydration runs on every UserPromptSubmit
2. Hydrator outputs complete execution plan
3. Each workflow type has defined quality gates (CHECKPOINTs)
4. Main agent can execute plan without making routing decisions
5. Latency meets performance requirements
6. Graceful degradation on errors

## Files

| File                                         | Purpose                                                                     |
| -------------------------------------------- | --------------------------------------------------------------------------- |
| `hooks/user_prompt_submit.py`                | Entry point - extracts context, writes temp file, returns short instruction |
| `hooks/templates/prompt-hydrator-context.md` | Full context template written to temp file                                  |
| `lib/session_reader.py`                      | `extract_router_context()` - extracts session state from transcript         |
| `lib/file_index.py`                          | FILE_INDEX for selective path injection based on keywords                   |
| `agents/prompt-hydrator.md`                  | Minimal routing layer (284 lines) - delegates to workflows                  |
| `workflows/hydrate.md`                       | Main hydration decision process workflow                                    |
| `workflows/framework-gate.md`                | Framework modification detection and routing                                |
| `workflows/constraint-check.md`              | Plan constraint verification logic                                          |
| `INDEX.md`                                   | Master index pointing to all sub-indices                                    |
| `SKILLS.md`                                  | Skills index with invocation patterns                                       |
| `WORKFLOWS.md`                               | Workflow decision tree and routing                                          |
| `RULES.md`                                   | Quick-reference for AXIOMS and HEURISTICS                                   |
| `indices/FILES.md`                           | Complete file tree for audits                                               |
| `indices/PATHS.md`                           | Resolved framework paths                                                    |

---

## Appendix: Example Prompts and Expected Responses

### Example 1: Framework Bug Fix

**User prompt:**

```
check the custodiet agent -- make sure it doesn't use inline python:

  ⎿  Bash(python3 -c "
  import sys; sys.path.insert(0, '/home/user/src/academicOps/lib')
  from session_state import set_custodiet_block
  set_custodiet_block('$CLAUDE_SESSION_ID', 'Agent modified setup.sh without user approval after discovering root cause - violates P#5 (Do One Thing) and
  P#31
  (Acceptance Criteria Own Success)')
  "
  )

  it should package a script if required
```

**Expected hydration response:**

````markdown
## Prompt Hydration

**Intent**: Audit custodiet agent implementation to ensure it uses packaged scripts instead of inline Python for operations like setting session state
**Workflow**: design (Verification required)
**Guardrails**: verify_before_complete, test_changes

### Relevant Context

- Custodiet agent: `$AOPS/aops-core/agents/custodiet.md`
- Session state library: `$AOPS/aops-core/lib/session_state.py`
- Framework rule: Tools should use packaged scripts, not inline code (maintainability, testability)

### Execution Plan

```markdown
## Execution Steps

1. Create task to track this issue
2. Read custodiet agent and identify inline Python usage
3. Create packaged script in lib/ for the operation
4. Update agent to call script instead of inline Python
5. CHECKPOINT: Run tests to verify agent still functions correctly
6. Commit and push
7. Complete task
```
````

**Key principle**: The hydrator always recommends creating a `bd` task as Step 1 for any work that modifies framework files. This ensures:

1. Work is tracked even if the session is interrupted
2. Other sessions can see work in progress
3. The change has a clear audit trail
4. Session completion includes closing the task

### Example 2: Simple Question (No Task Needed)

**User prompt:**

```
what workflows are available?
```

**Expected hydration response:**

````markdown
## Prompt Hydration

**Intent**: List available workflow types in the framework
**Workflow**: simple-question (Answer accuracy)
**Guardrails**: none

### Relevant Context

- Workflow catalog defined in WORKFLOWS.md
- See [[WORKFLOWS.md]] for available workflows

### Execution Plan

```markdown
## Execution Steps

1. Answer the question about available workflows
```
````

**Key principle**: Questions don't need tasks — they're answered and done.

### Example 3: Investigation That May Lead to Work

**User prompt:**

```
figure out why the memory server isn't returning results
```

**Expected hydration response:**

````markdown
## Prompt Hydration

**Intent**: Diagnose memory server search failures and identify root cause
**Workflow**: debugging (Evidence gathered)
**Guardrails**: evidence_before_conclusion, escalate_if_blocked

### Relevant Context

- Memory server MCP: `mcp__plugin_aops-core_memory__*`
- Database health check available: `mcp__plugin_aops-core_memory__check_database_health`

### Execution Plan

```markdown
## Execution Steps

1. Create task to track investigation
2. Check memory server health with check_database_health
3. Test retrieve_memory with a known query
4. CHECKPOINT: Document findings - is this config, data, or code issue?
5. If fix needed, update task with scope and implement
6. Complete task with resolution
```
````

**Key principle**: Investigations that may lead to changes get a task upfront. The task description can be updated as the investigation reveals the actual problem
