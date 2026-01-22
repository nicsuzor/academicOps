---
name: prompt-hydrator-context
title: Prompt Hydrator Context Template
category: template
description: |
  Template written to temp file by UserPromptSubmit hook for prompt-hydrator subagent.
  Variables: {prompt} (user prompt), {session_context} (recent prompts, tools, tasks),
             {task_state} (current work state from tasks MCP)
---

# Prompt Hydration Request

Transform this user prompt into an execution plan with scope detection and task routing.

## User Prompt

{prompt}
{session_context}

## Framework Paths

{framework_paths}

**Use these prefixes in TodoWrite plans** - never use relative paths like `specs/file.md`.

### File Placement Rules

| Content Type | Directory | Example |
|--------------|-----------|---------|
| **Specs** (design docs, architecture) | `$AOPS/aops-core/specs/` | `specs/workflow-system-spec.md` |
| **Workflows** (step-by-step procedures) | `$AOPS/workflows/` | `workflows/feature-dev.md` |
| **Agents** (subagent definitions) | `$AOPS/aops-core/agents/` | `agents/prompt-hydrator.md` |
| **Skills** (user-invocable commands) | `$AOPS/aops-core/skills/` | `skills/commit/SKILL.md` |

**CRITICAL**: Specs go in `specs/`, not alongside the thing they describe. Never create `workflows/SPEC.md` - use `specs/workflows.md`.

## Workflow Index (Pre-loaded)

{workflows_index}

## Skills Index (Pre-loaded)

{skills_index}

## Heuristics (Pre-loaded)

{heuristics}

## Current Work State

{task_state}

## Your Task

1. **Understand intent** - What does the user actually want?
2. **Assess scope** - Single-session (bounded, path known) or multi-session (goal-level, uncertain path)?
3. **Route to task** - Match to existing task or specify new task creation
4. **Select workflow** - Use the pre-loaded Workflow Index above to select the appropriate workflow
5. **Compose workflows** - Read workflow files in `$AOPS/workflows/` (and any [[referenced workflows]])
6. **Capture deferred work** - For multi-session scope, create decomposition task for future work

## Return Format

Return this EXACT structure:

````markdown
## HYDRATION RESULT

**Intent**: [what user actually wants, in clear terms]
**Scope**: single-session | multi-session
**Workflow**: [[workflows/[workflow-id]]]

### Task Routing

[Choose ONE:]

**Existing task found**: `[task-id]` - [title]
- Verify first: `mcp__plugin_aops-core_tasks__get_task(id="[task-id]")` (confirm status=active or inbox)
- Claim with: `mcp__plugin_aops-core_tasks__update_task(id="[task-id]", status="active")`

**OR**

**New task needed**:
- Create with: `mcp__plugin_aops-core_tasks__create_task(task_title="[title]", type="task", project="aops", priority=2)`

**OR**

**No task needed** (simple-question only)

### Acceptance Criteria

1. [Specific, verifiable condition]
2. [Another condition]

### Relevant Context

- [Context from memory search]
- [Related tasks]

### Applicable Principles

- **P#[n] [Name]**: [Why this applies]

### Execution Plan

```javascript
TodoWrite(todos=[
  {{content: "[task claim/create from above]", status: "pending", activeForm: "Claiming work"}},
  {{content: "[workflow step]", status: "pending", activeForm: "[participle]"}},
  {{content: "CHECKPOINT: [verification]", status: "pending", activeForm: "Verifying"}},
  {{content: "Task(subagent_type='qa', prompt='...')", status: "pending", activeForm: "QA verification"}},
  {{content: "Complete task and commit", status: "pending", activeForm: "Completing"}}
])
```

### Deferred Work (multi-session only)

Create decomposition task for work that can't be done now:

```
mcp__plugin_aops-core_tasks__create_task(
  title="Decompose: [goal]",
  type="task",
  project="aops",
  priority=2,
  body="Apply decompose workflow. Items:\n- [Deferred 1]\n- [Deferred 2]\nContext: [what future agent needs]"
)
```

If immediate task depends on decomposition, set dependency:
```
mcp__plugin_aops-core_tasks__create_task(
  title="[immediate task]",
  depends_on=["[decompose-task-id]"],
  ...
)
```
````

## Utility Scripts (Not Skills)

These scripts exist but aren't user-invocable skills. Provide exact invocation when relevant:

| Request | Script | Invocation |
|---------|--------|------------|
| "save transcript", "export session" | `session_transcript.py` | `uv run python $AOPS/scripts/session_transcript.py <session.jsonl> -o output.md` |

## Key Rules

- **Framework Gate (CHECK FIRST)**: If prompt involves modifying `$AOPS/` (framework files), route to `[[framework-change]]` (governance) or `[[feature-dev]]` (code). NEVER route framework work to `[[simple-question]]` or `[[minor-edit]]`. Include Framework Change Context in output.
- **Python Code Changes → TDD**: When debugging or fixing Python code (`.py` files), include `Skill(skill="python-dev")` in the execution plan. The python-dev skill enforces TDD: write failing test FIRST, then implement fix. No trial-and-error edits.
- **Short confirmations**: If prompt is very short (≤10 chars: "yes", "ok", "do it", "sure"), check the MOST RECENT agent response and tools. The user is likely confirming/proceeding with what was just proposed, NOT requesting new work from task queue.
- **Scope detection**: Multi-session = goal-level, uncertain path, spans days+. Single-session = bounded, known steps.
- **Prefer existing tasks**: Search task state before creating new tasks.
- **QA MANDATORY**: Every plan (except simple-question) needs QA verification step.
- **Deferred work**: Only for multi-session. Captures what can't be done now without losing it.
- **Set dependency when sequential**: If immediate work is meaningless without the rest, set depends_on.

## ⛔ Task-Gated Permissions (ENFORCED)

**Write/Edit operations will be BLOCKED** until a task is bound to the session.

The `task_required_gate` PreToolUse hook enforces this:
- **Claim existing**: `mcp__plugin_aops-core_tasks__update_task(id="...", status="active")`
- **Create new**: `mcp__plugin_aops-core_tasks__create_task(...)`

Until one of these runs, the agent CANNOT modify files. This is architectural enforcement, not a suggestion.

**Bypass**: User prefix `.` bypasses this gate for emergency/trivial fixes.

**Flow**: Your plan → main agent → (optional critic review) → main agent executes.

**NOTE**: You do NOT invoke critic. Main agent decides based on plan complexity:
- **Skip critic**: simple-question workflow, direct skill routes, trivial single-step tasks
- **Invoke critic**: multi-step execution plans, file modifications, architectural decisions
