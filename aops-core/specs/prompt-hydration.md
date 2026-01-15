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

**Single Source of Truth**: See [[WORKFLOWS.md]] for the complete workflow index and decision tree.

The hydrator reads WORKFLOWS.md to select the appropriate workflow based on user intent. Each workflow is defined in `workflows/[workflow-id].md`.

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

---

## Appendix: Example Prompts and Expected Responses

### Example 1: Framework Bug Fix

**User prompt:**

```
check the custodiet agent -- make sure it doesn't use inline python:

  ⎿  Bash(python3 -c "
  import sys; sys.path.insert(0, '/home/nic/src/academicOps/lib')
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
**Workflow**: minor-edit (Verification required)
**Guardrails**: verify_before_complete, test_changes

### Relevant Context

- Custodiet agent: `$AOPS/aops-core/agents/custodiet.md`
- Session state library: `$AOPS/aops-core/lib/session_state.py`
- Framework rule: Tools should use packaged scripts, not inline code (maintainability, testability)

### TodoWrite Plan

```javascript
TodoWrite(todos=[
  {content: "Step 1: Create bd task to track this issue", status: "pending", activeForm: "Creating issue"},
  {content: "Step 2: Read custodiet agent and identify inline Python usage", status: "pending", activeForm: "Auditing"},
  {content: "Step 3: Create packaged script in lib/ for the operation", status: "pending", activeForm: "Implementing"},
  {content: "Step 4: Update agent to call script instead of inline Python", status: "pending", activeForm: "Refactoring"},
  {content: "CHECKPOINT: Run tests to verify agent still functions correctly", status: "pending", activeForm: "Verifying"},
  {content: "Step 5: Commit and push", status: "pending", activeForm: "Committing"},
  {content: "Step 6: Close bd task", status: "pending", activeForm: "Closing issue"}
])
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

### TodoWrite Plan

```javascript
TodoWrite(todos=[
  {content: "Answer the question about available workflows", status: "pending", activeForm: "Answering"}
])
```
````

**Key principle**: Questions don't need `bd` tasks — they're answered and done.

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

### TodoWrite Plan

```javascript
TodoWrite(todos=[
  {content: "Step 1: Create bd task to track investigation", status: "pending", activeForm: "Creating issue"},
  {content: "Step 2: Check memory server health with check_database_health", status: "pending", activeForm: "Checking health"},
  {content: "Step 3: Test retrieve_memory with a known query", status: "pending", activeForm: "Testing retrieval"},
  {content: "CHECKPOINT: Document findings - is this config, data, or code issue?", status: "pending", activeForm: "Documenting"},
  {content: "Step 4: If fix needed, update task with scope and implement", status: "pending", activeForm: "Implementing fix"},
  {content: "Step 5: Update and close bd task with resolution", status: "pending", activeForm: "Closing issue"}
])
```
````

**Key principle**: Investigations that may lead to changes get a `bd` task upfront. The task description can be updated as the investigation reveals the actual problem
