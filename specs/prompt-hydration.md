---
title: Prompt Hydration
type: spec
category: spec
status: implemented
permalink: prompt-hydration
tags: [framework, routing, context, skills]
---

# Prompt Hydration

Transform a raw user prompt into a structured, context-rich prompt matched to the appropriate skill(s).

## Purpose

Users type terse prompts. Agents need:

- **Context** - What's relevant to this task?
- **Workflow** - What approach fits this work?
- **Skills** - Which skill(s) should be invoked?
- **Guardrails** - What constraints apply?

Prompt Hydration bridges this gap automatically on every prompt.

## When It Runs

**Every UserPromptSubmit** - not just `/do`. This closes the "control gap" where freeform prompts previously got baseline context only.

```
User types prompt
    ↓
UserPromptSubmit hook fires
    ↓
Prompt Hydration runs
    ↓
Main agent receives: original prompt + hydrated context
```

## What It Does

### 1. Context Gathering

Parallel searches to understand what's relevant:

| Source        | What                                            | Token Budget |
| ------------- | ----------------------------------------------- | ------------ |
| Memory server | Semantic search for related knowledge           | ~200         |
| Codebase      | Files relevant to the prompt                    | ~150         |
| Session       | Last 3-5 prompts, active skill, TodoWrite state | ~100         |
| Task inbox    | Related existing tasks                          | ~50          |

**Total budget**: ~500 tokens of context

### 2. Workflow Selection

Select composable workflow dimensions based on gathered context. This is intelligent decision-making, not keyword matching - the agent understands the prompt in context and selects the appropriate workflow.

#### Dimension 1: Gate

Must pass before implementation begins.

| Gate      | When to Apply                                                                                                  |
| --------- | -------------------------------------------------------------------------------------------------------------- |
| plan-mode | Framework changes, infrastructure work, multi-file refactors, anything requiring user approval before starting |
| none      | Clear scope, single-file changes, debugging, questions                                                         |

#### Dimension 2: Pre-work

What to do before implementing.

| Pre-work       | When to Apply                                                        |
| -------------- | -------------------------------------------------------------------- |
| verify-first   | Error reports, "doesn't work" complaints - reproduce before fixing   |
| research-first | Unfamiliar territory, unclear requirements, need to explore codebase |
| none           | Clear scope, well-understood domain                                  |

#### Dimension 3: Approach

How to implement.

| Approach | When to Apply                                                      |
| -------- | ------------------------------------------------------------------ |
| tdd      | Creating new functionality, refactoring with behavioral changes    |
| direct   | Bug fixes, configuration changes, documentation, simple edits      |
| none     | Questions, explanations, research tasks (no implementation needed) |

### 3. Skill Matching

Based on context and workflow, identify skill(s) to invoke:

| Domain Signal                                        | Skill                         |
| ---------------------------------------------------- | ----------------------------- |
| Framework files, AXIOMS, HEURISTICS, skills/, hooks/ | `framework`                   |
| Claude Code hooks, PreToolUse, PostToolUse           | `plugin-dev:hook-development` |
| MCP servers, tool integration                        | `plugin-dev:mcp-integration`  |
| New functionality, feature requests                  | `feature-dev`                 |
| Python code, pytest, type hints                      | `python-dev`                  |
| "Remember", "save to memory", persist knowledge      | `remember`                    |
| dbt, Streamlit, data analysis                        | `analyst`                     |
| No domain skill needed                               | (direct handling)             |

### 4. Guardrail Selection

Based on workflow dimensions, select applicable guardrails from [[RULES.md]]:

| Workflow Dimension       | Guardrails Applied                      |
| ------------------------ | --------------------------------------- |
| gate=plan-mode           | plan_mode, critic_review                |
| pre-work=verify-first    | quote_errors_exactly, fix_within_design |
| approach=tdd             | require_acceptance_test                 |
| approach=none (question) | answer_only                             |
| skill matched            | require_skill:[skill-name]              |
| any implementation       | verify_before_complete, use_todowrite   |

## Output Format

Hydration adds structured context to the agent's prompt:

```markdown
## Prompt Hydration

**Workflow**: gate=[X] pre-work=[X] approach=[X]
**Skill(s)**: [skill name(s) or "none"]
**Guardrails**: [list]

### Relevant Context

- [context item from memory/codebase/session]
- [context item]

### Session State

- Recent: "[last prompt]", "[prior prompt]"
- Active skill: [if any]
- Todos: [N] pending, [M] in_progress

### Guidance

[Workflow-specific instructions based on dimensions and guardrails]
```

## Performance Requirements

| Metric      | Target       |
| ----------- | ------------ |
| Typical     | 5-10 seconds |
| Max timeout | 15 seconds   |

Quality of context gathering matters more than speed. The hydrator should take the time needed to gather relevant context and make intelligent workflow decisions.

## Failure Modes

| Failure                         | Behavior                                                      |
| ------------------------------- | ------------------------------------------------------------- |
| Temp file write fails           | Hook exits non-zero, logs error (fail-fast)                   |
| Temp file read fails (subagent) | Subagent returns error, main agent proceeds without hydration |
| Main agent ignores instruction  | Silent failure - hydration doesn't happen (known risk)        |
| Memory search fails             | Continue with codebase/session context only                   |
| Classification uncertain        | Default to `simple`                                           |
| Timeout                         | Return partial context, log warning                           |
| Complete failure                | Return empty context, agent proceeds with baseline            |

Fail-fast on infrastructure errors (temp file). Graceful degradation only for content-gathering failures (memory, classification).

## Architecture

The implementation uses a temp file approach for token efficiency. See [[specs/gate-agent-architecture]] for the unified gate system design.

```
UserPromptSubmit hook
    ↓
Load/update unified session state
    ↓
Extract session context, write full context to temp file
    ↓
Main agent receives SHORT instruction (~100 tokens) with file path
    ↓
Main agent spawns prompt-hydrator subagent (Haiku)
    ↓
Subagent uses Read tool to load temp file, performs workflow selection
    ↓
Main agent follows guidance
```

### Session State Integration

The hook reads and updates the unified session state file (`/tmp/claude-session/state-{hash}.json`):

| Operation  | Fields                                                                      |
| ---------- | --------------------------------------------------------------------------- |
| **Reads**  | Previous `declared_workflow`, `active_skill` (for context continuity)       |
| **Writes** | `last_hydration_ts`, `declared_workflow`, `active_skill`, `intent_envelope` |

This enables cross-gate coordination - custodiet can check what workflow was declared and detect drift.

**Why temp files:**

- **Token efficiency**: Main agent sees ~100 tokens (instruction + path) vs ~500+ tokens (full embedded context)
- **Higher compliance**: Shorter instructions are less likely to be skipped (hypothesis - needs validation)
- **Subagent gets full context**: File contains complete prompt + session state + template
- **Debuggable**: Temp files can be inspected for troubleshooting

**Temp file handling:**

- **Location**: `/tmp/claude-hydrator/` (created with `makedirs` if missing)
- **Naming**: Uses `tempfile.NamedTemporaryFile` with prefix `hydrate_` to avoid collisions
- **Cleanup**: Files deleted after 1 hour via cleanup on hook invocation (delete files older than 1hr)
- **On failure**: If temp write fails, hook returns error and HALTS (no silent fallback per AXIOM #7)

**Subagent file access**: Subagents use the `Read` tool to access files. The instruction must explicitly tell the subagent to read the file path.

## Implementation

The hook (`hooks/user_prompt_submit.py`) performs these steps:

1. **Cleanup old temp files** - Delete files in `/tmp/claude-hydrator/` older than 1 hour
2. **Extract session context** via `extract_router_context()` from the transcript:
   - Last N user prompts (truncated)
   - Most recent Skill invocation
   - TodoWrite task status counts
3. **Load hydrator template** from `hooks/templates/prompt-hydrator-context.md`
4. **Build full context** by combining template + session context + user prompt
5. **Write to temp file** using `tempfile.NamedTemporaryFile(delete=False)`:
   - On success: Return instruction with file path
   - On failure (IOError, disk full): Return error, exit non-zero (fail-fast)
6. **Return short instruction** via `hookSpecificOutput.additionalContext`:
   ```
   Task(subagent_type="prompt-hydrator", model="haiku",
        prompt="Use the Read tool to read {temp_path}, then return workflow guidance")
   ```

The subagent uses Read to load the temp file, performs workflow selection, and returns structured guidance. The main agent follows the guidance.

**Note**: Subagents don't inherit session context and cannot read files directly - they must use the Read tool. The instruction explicitly tells the subagent to use Read.

## Relationship to /do

| Prompt Hydration              | /do Command                   |
| ----------------------------- | ----------------------------- |
| Automatic, every prompt       | Explicit invocation           |
| Context + classification only | Full orchestration pipeline   |
| Fast, lightweight             | Comprehensive, heavier        |
| Suggests skills               | Enforces skills + checkpoints |

With Prompt Hydration working, `/do` becomes the "extra guardrails" option for complex work, not the only way to get intelligent routing.

## Relationship to WORKFLOWS.md

`WORKFLOWS.md` is the **generated index** that reflects this spec's routing table. The `/audit` skill regenerates it from:

- This spec's workflow dimension definitions
- [[RULES.md]] guardrail definitions
- Skill descriptions

## Acceptance Criteria

1. Hydration runs on every UserPromptSubmit
2. Context written to temp file, not embedded inline
3. Main agent instruction is ≤150 tokens (file path only)
4. Temp files written to `/tmp/claude-hydrator/` with timestamp names
5. Context surfaces relevant information for workflow decisions
6. Latency meets performance requirements
7. Skills are correctly suggested based on domain signals
8. Guardrails match [[RULES.md]] definitions
9. Graceful degradation on errors
10. Agent behavior measurably improves (fewer skill bypasses)

## Files

| File                                              | Purpose                                                                      |
| ------------------------------------------------- | ---------------------------------------------------------------------------- |
| `hooks/user_prompt_submit.py`                     | Entry point - extracts context, writes temp file, returns short instruction  |
| `hooks/templates/prompt-hydrator-context.md`      | Full context template written to temp file (prompt + session + instructions) |
| `hooks/templates/prompt-hydration-instruction.md` | Short instruction template for main agent (~100 tokens)                      |
| `lib/session_reader.py`                           | `extract_router_context()` - extracts session state from transcript          |
| `agents/prompt-hydrator.md`                       | Subagent that reads temp file and performs workflow selection                |
| `RULES.md`                                        | Guardrail definitions (Soft Gate Guardrails section)                         |
| `WORKFLOWS.md`                                    | Generated routing table                                                      |
