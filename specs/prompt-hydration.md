---
title: Prompt Hydration
type: spec
category: spec
status: implemented
permalink: prompt-hydration
tags: [framework, routing, context, skills]
---

# Prompt Hydration

Transform a raw user prompt into a complete execution plan with workflow selection, per-step skill assignments, and quality gates.

## Purpose

Users type terse prompts. Agents need:

- **Intent** - What does the user actually want?
- **Workflow** - Which workflow template applies?
- **Steps** - What specific actions, in what order?
- **Skills** - Which skill provides context for each step?
- **Guardrails** - What constraints apply?

Prompt Hydration bridges this gap automatically on every prompt, outputting a complete execution plan the agent can follow.

## When It Runs

**Every UserPromptSubmit** - not just `/do`. This closes the "control gap" where freeform prompts previously got baseline context only.

```
User types prompt
    ↓
UserPromptSubmit hook fires
    ↓
Prompt Hydration runs
    ↓
Main agent receives: complete execution plan with TodoWrite steps
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
Workflow: minor-edit
Quality gate: Verification step required
Commit required: Yes
```

### 3. TodoWrite Plan with Per-Step Skills

The hydrator interprets the workflow for this specific task, breaking it into concrete steps with skill assignments:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Invoke Skill(skill='python-dev') to load coding standards", status: "pending", activeForm: "Loading skill"},
  {content: "Step 2: Read parser.py and understand the type error", status: "pending", activeForm: "Understanding"},
  {content: "Step 3: Implement the fix following python-dev conventions", status: "pending", activeForm: "Implementing"},
  {content: "CHECKPOINT: Run pytest to verify fix works", status: "pending", activeForm: "Verifying"},
  {content: "Step 5: Commit and push", status: "pending", activeForm: "Committing"}
])
```

### 4. Guardrails

Constraints that apply based on workflow + domain:

```
Guardrails: verify_before_complete, fix_within_design
```

## Workflow Catalog

The hydrator selects from a defined set of workflows. Each workflow specifies trigger signals, quality gates, and iteration units:

| Workflow       | Trigger Signals                       | Quality Gate            | Iteration Unit               |
| -------------- | ------------------------------------- | ----------------------- | ---------------------------- |
| **question**   | "?", "how", "what", "explain"         | Answer accuracy         | N/A (answer then stop)       |
| **minor-edit** | Single file, clear change             | Verification            | Edit → verify → commit       |
| **tdd**        | "implement", "add feature", "create"  | Tests pass              | Test → code → commit         |
| **batch**      | Multiple files, "all", "each"         | Per-item + aggregate QA | Subset → apply → verify      |
| **qa-proof**   | "verify", "check", "investigate"      | Evidence gathered       | Hypothesis → test → evidence |
| **plan-mode**  | Framework, infrastructure, multi-step | User approval           | Plan → approve → execute     |

**Key insight**: The workflow is NOT mechanical. The hydrator INTERPRETS the workflow template for the specific user request, generating concrete steps with appropriate skill invocations.

## Skill Assignment

The hydrator assigns skills per-step based on domain signals from [[REMINDERS.md]]:

| Step Domain                               | Skill                         |
| ----------------------------------------- | ----------------------------- |
| Python code, pytest, types                | `python-dev`                  |
| Framework files (hooks/, skills/, AXIOMS) | `framework`                   |
| New functionality                         | `feature-dev`                 |
| Memory persistence                        | `remember`                    |
| Data analysis, dbt, Streamlit             | `analyst`                     |
| Claude Code hooks                         | `plugin-dev:hook-development` |
| MCP servers                               | `plugin-dev:mcp-integration`  |

Each step in the TodoWrite can include an explicit `Invoke Skill(skill='xxx')` instruction when domain context is needed.

## Context Gathering

The hydrator gathers context to inform workflow selection and step planning:

| Source        | What                                            | Token Budget |
| ------------- | ----------------------------------------------- | ------------ |
| Memory server | Semantic search for related knowledge           | ~200         |
| Codebase      | Files relevant to the prompt                    | ~150         |
| Session       | Last 3-5 prompts, active skill, TodoWrite state | ~100         |
| Task inbox    | Related existing tasks                          | ~50          |

**Total budget**: ~500 tokens of context

## Agent Execution

The main agent receives the hydrator's output and follows the plan:

1. **Create TodoWrite** exactly as specified by hydrator
2. **For each step**:
   - Mark `in_progress`
   - If step says "Invoke Skill(...)", invoke the skill
   - Execute the step
   - Mark `completed`
3. **At CHECKPOINTs**: Verify with evidence before proceeding
4. **Cleanup**: Commit, push, reflect as directed by workflow

The agent doesn't need to make routing or skill decisions — the hydrator already made them.

## Output Format

The hydrator returns structured guidance:

````markdown
## Prompt Hydration

**Intent**: [what user wants]
**Workflow**: [workflow name] ([quality gate])
**Guardrails**: [list]

### Relevant Context

- [context from memory/codebase/session]

### TodoWrite Plan

```javascript
TodoWrite(todos=[
  {content: "Step 1: ...", status: "pending", activeForm: "..."},
  ...
])
```
````

```
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
Load/update unified session state
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

````
**Why temp files:**

- **Token efficiency**: Main agent sees ~100 tokens (instruction + path) vs ~500+ tokens (full embedded context)
- **Subagent gets full context**: File contains complete prompt + session state + workflow catalog
- **Debuggable**: Temp files can be inspected for troubleshooting

**Temp file handling:**

- **Location**: `/tmp/claude-hydrator/` (created with `makedirs` if missing)
- **Naming**: Uses `tempfile.NamedTemporaryFile` with prefix `hydrate_` to avoid collisions
- **Cleanup**: Files deleted after 1 hour via cleanup on hook invocation
- **On failure**: If temp write fails, hook returns error and HALTS (no silent fallback per AXIOM #7)

## Relationship to /do

| Prompt Hydration              | /do Command                        |
| ----------------------------- | ---------------------------------- |
| Automatic, every prompt       | Explicit invocation                |
| Outputs complete plan         | Executes plan with extra oversight |
| Fast, single haiku call       | May involve multiple checkpoints   |
| Per-step skill assignment     | Same skills, more enforcement      |

With Prompt Hydration outputting complete plans, `/do` becomes simpler — it receives the hydrated plan and executes it with additional oversight for complex work.

## Relationship to WORKFLOWS.md

`WORKFLOWS.md` is the **workflow catalog** that the hydrator references. It contains:

- Workflow templates with trigger signals
- Quality gates for each workflow
- Iteration units (what gets committed atomically)

The hydrator interprets these templates for specific user requests.

## Acceptance Criteria

1. Hydration runs on every UserPromptSubmit
2. Hydrator outputs complete TodoWrite plan with per-step skill assignments
3. Each workflow type has defined quality gates (CHECKPOINTs)
4. Skills are embedded in step content, not inferred later
5. Main agent can execute plan without making routing decisions
6. Latency meets performance requirements
7. Graceful degradation on errors

### Session Context Sufficiency (Validated 2026-01-11)

The hydrator receives sufficient session context to make routing decisions mid-session. Acceptance criteria:

**Required context elements:**
- Recent prompts: At least 5 prior user prompts (truncated to ~400 chars each)
- Recent agent responses: Last 3 agent responses (for conversational continuity)
- Recent tool calls: Last 10 tool calls with key parameters (Read/Edit file paths, Bash commands, Task subagent types)
- TodoWrite state: Pending/in_progress/completed counts + current in_progress task name
- Active skill: Most recent Skill invocation (if within lookback window)

**Qualitative test**: Given these elements, the hydrator can:
1. Understand what the session has been working on (via tool calls + agent responses)
2. Know the current task structure (via TodoWrite state)
3. See the trajectory of user intent (via recent prompts)
4. Detect conversational continuity vs. new topic (via prompt sequence)

**Evidence (from live session test):**
```markdown
## Session Context

Recent prompts:
1. "prove to me using your debug skills that, when run in the middle of a long sessoin..."

Recent agent responses:
1. "I can see `{session_context}` is right after `{prompt}` on line 17..."
2. "Let me check where the debug file might be..."
3. "Let me find the current session's JSONL file..."

Recent tools:
  - Read(session_reader.py)
  - Read(prompt-hydrator-context.md)
  - Bash(cat /home/nic/src/academicOps/.claude/hook-debug.j...)
  ...

Tasks: 4 pending, 1 in_progress ("Step 1: Inspect hydrator temp file..."), 0 completed
````

This context is sufficient for the hydrator to understand session trajectory and make informed workflow/skill routing decisions.

## Files

| File                                              | Purpose                                                                     |
| ------------------------------------------------- | --------------------------------------------------------------------------- |
| `hooks/user_prompt_submit.py`                     | Entry point - extracts context, writes temp file, returns short instruction |
| `hooks/templates/prompt-hydrator-context.md`      | Full context template written to temp file                                  |
| `hooks/templates/prompt-hydration-instruction.md` | Short instruction template for main agent (~100 tokens)                     |
| `lib/session_reader.py`                           | `extract_router_context()` - extracts session state from transcript         |
| `agents/prompt-hydrator.md`                       | Subagent that reads temp file and generates execution plan                  |
| `WORKFLOWS.md`                                    | Workflow catalog with templates                                             |
| `REMINDERS.md`                                    | Skill triggers for per-step assignment                                      |

```
```
