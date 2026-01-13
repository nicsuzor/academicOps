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

| Workflow       | Trigger Signals                      | Quality Gate      | Iteration Unit                    |
| -------------- | ------------------------------------ | ----------------- | --------------------------------- |
| **question**   | "?", "how", "what", "explain"        | Answer accuracy   | N/A (answer then stop)            |
| **minor-edit** | Single file, clear change            | Verification      | Edit → verify → commit            |
| **tdd**        | "implement", "add feature", "create" | Tests pass        | Test → code → commit              |
| **batch**      | Multiple files, "all", "each"        | Per-item + agg QA | Spawn parallel subagents → verify |
| **qa-proof**   | "verify", "check", "investigate"     | Evidence gathered | Hypothesis → test → evidence      |
| **plan-mode**  | Complex, infrastructure, multi-step  | User approval     | Plan → approve → execute          |

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
3. **Generate TodoWrite plan** - Break into concrete steps
4. **Apply guardrails** - Select constraints based on workflow

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
  {{content: "Step 2: [action]", status: "pending", activeForm: "[present participle]"}},
  {{content: "CHECKPOINT: [verification with evidence]", status: "pending", activeForm: "Verifying"}},
  {{content: "Step N: Commit and push", status: "pending", activeForm: "Committing"}}
])
```
````

**Key insight**: The workflow is NOT mechanical. INTERPRET the workflow template for the specific user request, generating concrete steps.
