---
name: prompt-hydrator-context
title: Prompt Hydrator Context Template
category: template
description: |
  Template written to temp file by UserPromptSubmit hook for prompt-hydrator subagent.
  Variables: {prompt} (user prompt), {session_context} (recent prompts, tools, tasks)
---

# Prompt Hydration Request

Transform this user prompt into a complete execution plan.

## User Prompt

{prompt}
{session_context}

## Workflow Catalog

Select the appropriate workflow based on task signals:

| Workflow       | Trigger Signals                                               | Quality Gate            | Iteration Unit                    |
| -------------- | ------------------------------------------------------------- | ----------------------- | --------------------------------- |
| **question**   | "?", "how", "what", "explain"                                 | Answer accuracy         | N/A (answer then stop)            |
| **minor-edit** | Single file, clear change                                     | Verification            | Edit → verify → commit            |
| **tdd**        | "implement", "add feature", "create"                          | Tests pass              | Test → code → commit              |
| **batch**      | Multiple files, "all", "each", skill discovers multiple items | Per-item + aggregate QA | Spawn parallel subagents → verify |
| **qa-proof**   | "verify", "check", "investigate"                              | Evidence gathered       | Hypothesis → test → evidence      |
| **plan-mode**  | Framework, infrastructure, multi-step                         | User approval           | Plan → approve → execute          |

## Per-Step Skill Assignment

Assign skills based on domain. The "Not For" column disambiguates similar skills:

| Use When                                                                            | Not For                                        | Skill                         |
| ----------------------------------------------------------------------------------- | ---------------------------------------------- | ----------------------------- |
| Python code, pytest, type hints, refactoring                                        | dbt models, Streamlit apps, research pipelines | `python-dev`                  |
| Framework infrastructure (hooks/, skills/, AXIOMS), generalizable patterns          | User data operations, one-off scripts          | `framework`                   |
| New user-facing feature with acceptance criteria                                    | Bug fixes, refactoring existing code           | `feature-dev`                 |
| Persist knowledge to semantic memory                                                | Temporary notes, session-specific info         | `remember`                    |
| dbt models, Streamlit dashboards, research data pipelines (look for dbt/ directory) | General Python scripts, non-research code      | `analyst`                     |
| Claude Code hooks (PreToolUse, PostToolUse, SessionStart, etc.)                     | MCP servers, skills, commands                  | `plugin-dev:hook-development` |
| MCP server integration, external service connections                                | Hooks, skills, commands                        | `plugin-dev:mcp-integration`  |

Each step can invoke a different skill. Don't assign one skill to the whole task.

## Guardrails by Workflow

| Workflow   | Guardrails                                                    |
| ---------- | ------------------------------------------------------------- |
| question   | `answer_only`                                                 |
| minor-edit | `verify_before_complete`, `fix_within_design`                 |
| tdd        | `require_acceptance_test`, `verify_before_complete`           |
| batch      | `per_item_verification`, `aggregate_qa`, `parallel_subagents` |
| qa-proof   | `evidence_required`, `quote_errors_exactly`                   |
| plan-mode  | `plan_mode`, `critic_review`, `user_approval_required`        |

## Framework Paths

{framework_paths}

**Use these prefixes in TodoWrite plans** - never use relative paths like `specs/file.md`.

## Your Task

1. **Understand intent** - What does the user actually want?
2. **Select workflow** - Which workflow from the catalog applies?
3. **Generate TodoWrite plan** - Break into concrete steps with per-step skill assignments
4. **Apply guardrails** - Select constraints based on workflow + domain

## Return Format

Return this EXACT structure:

````markdown
## Prompt Hydration

**Intent**: [what user actually wants, in clear terms]
**Workflow**: [workflow name] ([quality gate])
**Guardrails**: [comma-separated list]

### Relevant Context

- [context from memory/codebase search - what's relevant to this task?]
- [finding 2]
- [finding 3]

### Applicable Principles

- **Axiom #[n]**: [name] - [why it applies]
- **H[n]**: [name] - [why it applies]

### TodoWrite Plan

**IMMEDIATELY call TodoWrite** with these steps:

```javascript
TodoWrite(todos=[
  {{content: "Step 1: [action]", status: "pending", activeForm: "[present participle]"}},
  {{content: "Step 2: Invoke Skill(skill='[skill-name]') to [purpose]", status: "pending", activeForm: "Loading [skill]"}},
  {{content: "Step 3: [action following skill conventions]", status: "pending", activeForm: "[present participle]"}},
  {{content: "CHECKPOINT: [verification with evidence]", status: "pending", activeForm: "Verifying"}},
  {{content: "Step N: Commit and push", status: "pending", activeForm: "Committing"}}
])
```
````

**Key insight**: The workflow is NOT mechanical. INTERPRET the workflow template for the specific user request, generating concrete steps with appropriate skill invocations.
