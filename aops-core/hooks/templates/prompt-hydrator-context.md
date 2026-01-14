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

Transform this user prompt into a complete execution plan.

## User Prompt

{prompt}
{session_context}

## Framework Paths

{framework_paths}

**Use these prefixes in TodoWrite plans** - never use relative paths like `specs/file.md`.

## Current Work State

{bd_state}

## Your Task

1. **Understand intent** - What does the user actually want?
2. **Select workflow** - Read WORKFLOWS.md and select the appropriate workflow
3. **Compose workflows** - Read workflow files (and any [[referenced workflows]]) as needed
4. **Generate TodoWrite plan** - Break into concrete steps following workflow guidance

## Return Format

Return this EXACT structure:

````markdown
## Prompt Hydration

**Intent**: [what user actually wants, in clear terms]
**Workflow**: [workflow name] ([quality gate])

### Relevant Context

- [context from memory/codebase search - what's relevant to this task?]
- [finding 2]
- [finding 3]

### Applicable Principles

- **P#[n] [Name]**: [Why this applies to this specific task]
- **P#[n] [Name]**: [Why this applies]

### TodoWrite Plan

**IMMEDIATELY call TodoWrite** with these steps:

```javascript
TodoWrite(todos=[
  {content: "Step 1: [action]", status: "pending", activeForm: "[present participle]"},
  {content: "Step 2: [action]", status: "pending", activeForm: "[present participle]"},
  {content: "CHECKPOINT: [verification with evidence]", status: "pending", activeForm: "Verifying"},
  {content: "QA VERIFY: Spawn qa agent before completion", status: "pending", activeForm: "Verifying with qa"},
  {content: "Commit and push", status: "pending", activeForm: "Committing"}
])
```
````

**Key insight**: The workflow is NOT mechanical. INTERPRET the workflow template for the specific user request, generating concrete steps.

**MANDATORY**: Every plan (except `question` workflow) MUST include the "QA VERIFY" step. The main agent spawns qa as an independent Task subagent to verify work before committing.
