---
name: do
description: Execute work with full context enrichment and guardrails
allowed-tools: Task, TodoWrite, Skill, Read, Grep, Glob, Edit, Write, Bash, mcp__memory__retrieve_memory
permalink: commands/do
---

# /do - Execute With Context

**Single entry point for all work.** Enriches your fragment, creates a todo list, applies guardrails, executes.

## How It Works

1. Intent-router agent gathers context and classifies your task
2. Todo list created from returned steps
3. Guardrails applied based on task type
4. Work executes with full context

## Execution

### Step 1: Invoke Intent Router

```
Task(
  subagent_type="intent-router",
  model="sonnet",
  description="Route: [first 3 words of fragment]",
  prompt="User fragment: $ARGUMENTS"
)
```

### Step 2: Parse Response

The intent-router returns structured YAML with:
- `task_type` - classification
- `workflow` - execution approach
- `skills_to_invoke` - skills to call first
- `guardrails` - failure prevention rules
- `enriched_context` - gathered context
- `todo_items` - steps to execute
- `warnings` - things to watch out for
- `original_fragment` - preserved input

### Step 3: Create Todo List

Create TodoWrite from the returned `todo_items`:

```
TodoWrite(todos=[
  {content: "[step 1]", status: "pending", activeForm: "[step 1 -ing form]"},
  {content: "[step 2]", status: "pending", activeForm: "[step 2 -ing form]"},
  ...
])
```

### Step 4: Apply Guardrails

Check the `guardrails` object and enforce:

| Guardrail | If True |
|-----------|---------|
| `plan_mode` | Enter Plan Mode before implementation |
| `answer_only` | Answer the question, then STOP. No implementation. |
| `require_skill` | Invoke the specified skill before proceeding |
| `verify_before_complete` | Must verify actual state before claiming done |
| `require_acceptance_test` | Todo list must include verification step |
| `quote_errors_exactly` | Quote error messages verbatim, no paraphrasing |
| `fix_within_design` | Fix bugs within current architecture, don't redesign |

### Step 5: Display Context and Proceed

Show the user:
1. What was understood (task type, workflow)
2. Enriched context summary
3. Todo list
4. Any warnings

Then proceed with execution:
- If `skills_to_invoke` is set, invoke those skills first
- If `plan_mode` is true, enter Plan Mode
- If `answer_only` is true, answer and stop
- Otherwise, work through the todo list

## Example Flow

User types: `/do fix the dashboard session panel`

Intent-router returns:
```yaml
task_type: debug
workflow: verify-first
guardrails:
  verify_before_complete: true
  quote_errors_exactly: true
  fix_within_design: true
enriched_context: |
  Dashboard at $AOPS/scripts/dashboard.py
  Session panel added 2025-12-18
  Data from R2 cloudflare worker
todo_items:
  - "Reproduce the issue"
  - "Check logs for errors"
  - "Identify root cause"
  - "Implement fix"
  - "Verify fix works"
  - "Commit"
warnings:
  - "Don't redesign - fix within current architecture"
```

You see:
```
Task: debug (verify-first workflow)

Context: Dashboard session panel, data from R2

Guardrails:
- Quote errors exactly
- Fix within current design
- Verify before claiming complete

Todo:
1. [ ] Reproduce the issue
2. [ ] Check logs for errors
3. [ ] Identify root cause
4. [ ] Implement fix
5. [ ] Verify fix works
6. [ ] Commit

Warning: Don't redesign - fix within current architecture

Proceeding...
```

Then execution begins, following the todo list with guardrails enforced.

## What /do Replaces

| Old | New |
|-----|-----|
| `/q` (queue capture) | `/do` enriches and executes immediately |
| `/pull` (queue retrieval) | Not needed - work tracked via TodoWrite |
| `prompt_router.py` hook | `/do` handles routing |
| `prompt-writer` agent | `intent-router` agent |

## When NOT to Use /do

- Quick questions you already know the answer to (just answer)
- Single-line commands (`git status`, `ls`)
- When user explicitly says "just do X" without context needed

For these, respond directly without the routing overhead.
