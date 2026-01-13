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

## Purpose

Users type terse prompts. Agents need:

- **Intent** - What does the user actually want?
- **Workflow** - Which workflow template applies?
- **Steps** - What specific actions, in what order?
- **Guardrails** - What constraints apply?

Prompt Hydration bridges this gap automatically on every prompt, outputting a complete execution plan the agent can follow.

## When It Runs

**Every UserPromptSubmit** - This closes the "control gap" where freeform prompts previously got baseline context only.

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

### 3. TodoWrite Plan

The hydrator interprets the workflow for this specific task, breaking it into concrete steps:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Read parser.py and understand the type error", status: "pending", activeForm: "Understanding"},
  {content: "Step 2: Implement the fix", status: "pending", activeForm: "Implementing"},
  {content: "CHECKPOINT: Run pytest to verify fix works", status: "pending", activeForm: "Verifying"},
  {content: "Step 3: Commit and push", status: "pending", activeForm: "Committing"}
])
```

### 4. Guardrails

Constraints that apply based on workflow:

```
Guardrails: verify_before_complete, fix_within_design
```

## Workflow Catalog

The hydrator selects from a defined set of workflows:

| Workflow       | Trigger Signals                      | Quality Gate            | Iteration Unit               |
| -------------- | ------------------------------------ | ----------------------- | ---------------------------- |
| **question**   | "?", "how", "what", "explain"        | Answer accuracy         | N/A (answer then stop)       |
| **minor-edit** | Single file, clear change            | Verification            | Edit → verify → commit       |
| **tdd**        | "implement", "add feature", "create" | Tests pass              | Test → code → commit         |
| **batch**      | Multiple files, "all", "each"        | Per-item + aggregate QA | Subset → apply → verify      |
| **qa-proof**   | "verify", "check", "investigate"     | Evidence gathered       | Hypothesis → test → evidence |
| **plan-mode**  | Complex, infrastructure, multi-step  | User approval           | Plan → approve → execute     |

**Key insight**: The workflow is NOT mechanical. The hydrator INTERPRETS the workflow template for the specific user request, generating concrete steps.

## Context Gathering

The hydrator gathers context to inform workflow selection and step planning:

| Source        | What                                  | Token Budget |
| ------------- | ------------------------------------- | ------------ |
| Memory server | Semantic search for related knowledge | ~200         |
| Codebase      | Files relevant to the prompt          | ~150         |
| Session       | Last 3-5 prompts, TodoWrite state     | ~100         |

**Total budget**: ~450 tokens of context

## Agent Execution

The main agent receives the hydrator's output and follows the plan:

1. **Create TodoWrite** exactly as specified by hydrator
2. **For each step**:
   - Mark `in_progress`
   - Execute the step
   - Mark `completed`
3. **At CHECKPOINTs**: Verify with evidence before proceeding
4. **Cleanup**: Commit, push as directed by workflow

The agent doesn't need to make routing decisions — the hydrator already made them.

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
2. Hydrator outputs complete TodoWrite plan
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
| `agents/prompt-hydrator.md`                  | Subagent that reads temp file and generates execution plan                  |
