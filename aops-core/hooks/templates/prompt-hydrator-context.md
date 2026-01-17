---
name: prompt-hydrator-context
title: Prompt Hydrator Context Template
category: template
description: |
  Template written to temp file by UserPromptSubmit hook for prompt-hydrator subagent.
  Variables: {prompt} (user prompt), {session_context} (recent prompts, tools, tasks),
             {bd_state} (current work state from bd)
---

# Prompt Hydration Request

Transform this user prompt into an execution plan with scope detection and bd task routing.

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

{bd_state}

## Your Task

1. **Understand intent** - What does the user actually want?
2. **Assess scope** - Single-session (bounded, path known) or multi-session (goal-level, uncertain path)?
3. **Route to bd task** - Match to existing issue or specify new task creation
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

### BD Task Routing

[Choose ONE:]

**Existing issue found**: `[issue-id]` - [title]
- Verify first: `bd show [issue-id]` (confirm status=open/ready, not blocked/in_progress)
- Claim with: `bd update [issue-id] --status=in_progress`

**OR**

**New task needed**:
- Create with: `bd create "[title]" --type=[task|epic] --priority=[0-3] [--parent=epic-id]`

**OR**

**No bd task needed** (simple-question only)

### Acceptance Criteria

1. [Specific, verifiable condition]
2. [Another condition]

### Relevant Context

- [Context from memory search]
- [Related bd issues]

### Applicable Principles

- **P#[n] [Name]**: [Why this applies]

### Execution Plan

```javascript
TodoWrite(todos=[
  {{content: "[bd claim/create from above]", status: "pending", activeForm: "Claiming work"}},
  {{content: "[workflow step]", status: "pending", activeForm: "[participle]"}},
  {{content: "CHECKPOINT: [verification]", status: "pending", activeForm: "Verifying"}},
  {{content: "Task(subagent_type='qa', prompt='...')", status: "pending", activeForm: "QA verification"}},
  {{content: "Close bd task and commit", status: "pending", activeForm: "Completing"}}
])
```

### Deferred Work (multi-session only)

Create decomposition task for work that can't be done now:

```bash
bd create "Decompose: [goal]" --type=task --priority=2 \
  --description="Apply decompose workflow. Items:
- [Deferred 1]
- [Deferred 2]
Context: [what future agent needs]"
```

If immediate task is step 1 of a sequence, block on decomposition:
```bash
bd dep add [immediate-id] depends-on [decompose-id]
```
````

## Key Rules

- **Short confirmations**: If prompt is very short (≤10 chars: "yes", "ok", "do it", "sure"), check the MOST RECENT agent response and tools. The user is likely confirming/proceeding with what was just proposed, NOT requesting new work from bd queue.
- **Scope detection**: Multi-session = goal-level, uncertain path, spans days+. Single-session = bounded, known steps.
- **Prefer existing issues**: Search bd state before creating new tasks.
- **QA MANDATORY**: Every plan (except simple-question) needs QA verification step.
- **Deferred work**: Only for multi-session. Captures what can't be done now without losing it.
- **Block when sequential**: If immediate work is meaningless without the rest, block on decomposition task.

**Flow**: Your plan → main agent → critic reviews → main agent executes.

**NOTE**: You do NOT invoke critic. Focus on generating a good plan.
