---
name: workflows
title: Workflow Catalog
type: instruction
category: instruction
description: The authoritative guide for agent behavior. Defines strict orchestration loops, quality gates, and mandatory observability for all tasks.
permalink: workflows
tags: [framework, routing, workflows, enforcement]
---

# Workflow Catalog & Agent Mandates

**Purpose**: This file is the **OS Kernel** for the agent. It defines the strict, repeatable processes that MUST be followed to ensure quality, observability, and safety.

**Philosophy**: We are an academic framework. We value **rigor over speed**, **verification over assumption**, and **observability over magic**.

## Instructions

Your job is to determine the steps that the agent must follow to achieve the task.

1. Carefully read the prompt to understand the task

2.

## Workflow Selection (Quick Reference)

Select workflow by matching user intent to the first matching row:

| Intent Signal                                        | Workflow                                          | Primary Delegation                        |
| ---------------------------------------------------- | ------------------------------------------------- | ----------------------------------------- |
| "implement", "create", "add feature", "refactor"     | [TDD](#1-tdd-feature-development)                 | `Skill(skill="feature-dev")` → subagents  |
| "fix", "bug", "error", "broken"                      | [Debugging](#2-debugging-minor-edit--fix)         | `Skill(skill="[domain]")` → subagent      |
| "all files", "for every", "batch", "process dataset" | [Batch](#3-batch-operations)                      | Parallel `Task()` subagents               |
| "plan", "design", "structure", "system change"       | [Framework](#4-framework--architecture-plan-mode) | `EnterPlanMode()` → critic                |
| "?", "how", "explain", "what is"                     | [Question](#5-question)                           | `Skill(skill="[domain]")` → answer & HALT |
| "verify", "check", "investigate", "audit"            | [QA](#6-qa--investigation)                        | Evidence gathering → conclusion           |

**Orchestrator principle**: The main agent coordinates. It does NOT implement. Every implementation step delegates to a subagent or skill.

## 🔴 Universal Mandates (The "Rules of Engagement")

These apply to **EVERY** workflow (except direct Questions).

1. **Locked Acceptance Criteria**: You MUST state _at the outset_ clearly defined, testable conditions for "success". These cannot change mid-flight without user approval.
2. **Rigorous Planning**: Every prompt requires a structured plan (using `TodoWrite`) tracked explicitly.
3. **Independent Review**: ALL plans must be reviewed by the **Critic Agent** (`Task(subagent_type='critic')`) before execution.
4. **Verification, Not Trust**: Success is only claimed after verification against the _original_ acceptance criteria by the **QA Agent** (`commands/qa.md`).
5. **Durable Observability**:
   - **Progress**: Record semantic knowledge via `Skill(skill="remember")`.
   - **Reflection**: EVERY task concludes with a mandatory `/reflect` step.
6. **Atomic Commits**: Commit changes after every logical unit of work (passing test, completed step).
7. **Final Push**: Never leave work stranded locally. Push at the end.

## 🟢 The Orchestration Loop ("The Hypervisor")

When executing a task, you are the **Orchestrator**. Do not implement complex logic yourself. Delegate to subagents and verify their work.

### Phase 0: Context & Classification

1. **Gather Context**:
   - `mcp__memory__retrieve_memory(query="...")` for semantic context.
   - `Glob`/`Grep` for codebase context.
2. **Select Workflow**: Choose the specific track below (TDD, Batch, etc.).

### Phase 1: Planning

1. **Define Acceptance Criteria**: User outcomes, not just technical steps.
2. **Draft Plan**: Create a `TodoWrite` list with explicit **CHECKPOINT** items.
3. **Critic Review**:
   ```python
   Task(subagent_type="critic", prompt="Review this plan against [Criteria]. Check for logic gaps, assumptions, and missing verification.")
   ```
   _If Critic rejects: REVISE._

### Phase 2: Execution

1. **Delegate**: Spawn subagents for implementation.
   ```python
   Task(subagent_type="general-purpose", prompt="Context: [...]. Task: [Todo Item]. Constraint: [Skill Mandates].")
   ```
2. **Verify Step**: Check evidence before marking `TodoWrite` item complete.
3. **Commit**: `git commit -m "feat: [step completed]"`

### Phase 3: Verification (QA)

1. **QA Review**:
   ```python
   Task(subagent_type="qa", prompt="Verify these changes meet the locked Acceptance Criteria. Run tests. Inspect output.")
   ```
   _See `commands/qa.md` for the strict protocol._

### Phase 4: Conclusion

1. **Reflect**: Run `/reflect` to audit process compliance.
2. **Persist**: Use `Skill(skill="remember")` to save learnings.
3. **Push**: `git push`.

## 🔵 Workflow Tracks

Select the specific track based on the user's intent. See [Workflow Selection](#workflow-selection-quick-reference) matrix above.

**Important**: Subagents cannot invoke Skills via the `Skill` tool. The orchestrator must load skill context first, then pass relevant guidance to subagents in their prompts. Alternatively, use custom agents with skills pre-configured in their frontmatter.

### 1. TDD (Feature Development)

**Trigger**: "implement", "create", "refactor", "add feature"
**Mandate**: **Test-First**. No code without a failing test.

**Delegation Note**: Subagents cannot invoke Skills. The orchestrator must either:

- Load skill context first, then include relevant guidance in the subagent prompt
- Use a custom agent with skills pre-configured in its frontmatter

**Execution Template**:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Invoke Skill(skill='feature-dev') to load TDD guidance into orchestrator context", status: "pending", activeForm: "Loading skill"},
  {content: "Step 2: Invoke Skill(skill='[domain]') to load domain conventions", status: "pending", activeForm: "Loading skill"},
  {content: "Step 3: Define acceptance criteria (user outcomes)", status: "pending", activeForm: "Defining acceptance"},
  {content: "Step 4: Delegate test writing - Task(prompt='Write failing test for [criteria]. Follow TDD: [include key guidance from skill]')", status: "pending", activeForm: "Delegating test"},
  {content: "Step 5: Delegate implementation - Task(prompt='Implement to pass test. Follow [domain] conventions: [include key guidance]')", status: "pending", activeForm: "Delegating implementation"},
  {content: "CHECKPOINT: Run pytest to verify all tests pass", status: "pending", activeForm: "Verifying"},
  {content: "Step 7: Commit and push", status: "pending", activeForm: "Committing"}
])
```

### 2. Debugging (Minor Edit / Fix)

**Trigger**: "fix", "bug", "error", "broken"
**Mandate**: **Scientific Method**. No "trying things" without hypothesis.

**Execution Template**:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Reproduce error with a DURABLE test - run build, quote error message EXACTLY", status: "pending", activeForm: "Reproducing error"},
  {content: "Step 2: Invoke Skill(skill='[domain]') to load conventions into orchestrator context", status: "pending", activeForm: "Loading skill"},
  {content: "Step 3: Read file and understand the error state (orchestrator context-gathering)", status: "pending", activeForm: "Understanding"},
  {content: "Step 4: Delegate fix - Task(prompt='Fix [error]. Conventions: [include key guidance from skill]')", status: "pending", activeForm: "Delegating fix"},
  {content: "CHECKPOINT: Run build/repro to verify fix works", status: "pending", activeForm: "Verifying"},
  {content: "Step 6: Commit and push", status: "pending", activeForm: "Committing"}
])
```

### 3. Batch Operations

**Trigger**: "all files", "for every", "process dataset", skill discovers multiple items
**Mandate**: **Resumability + Parallel Delegation**. Never rely on session memory for long-running tasks. Spawn subagents for parallelizable items.

**Execution Template**:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Identify all items to process: [description]", status: "pending", activeForm: "Identifying items"},
  {content: "Step 2: Spawn parallel subagents for independent items", status: "pending", activeForm: "Delegating to subagents"},
  {content: "CHECKPOINT: Verify all subagents completed successfully", status: "pending", activeForm: "Verifying batch"},
  {content: "Step 3: Aggregate QA - verify all items processed", status: "pending", activeForm: "Final verification"},
  {content: "Final: Commit and push", status: "pending", activeForm: "Committing"}
])
```

**Parallel Delegation Pattern** (for independent items):

```python
# Spawn multiple subagents in a SINGLE message for parallel execution
Task(subagent_type="general-purpose", prompt="Process item 1: [details]", run_in_background=true)
Task(subagent_type="general-purpose", prompt="Process item 2: [details]", run_in_background=true)
Task(subagent_type="general-purpose", prompt="Process item 3: [details]", run_in_background=true)
# All run concurrently - check TaskOutput when done
```

### 4. Framework / Architecture (Plan Mode)

**Trigger**: "plan", "design", "structure", "system change"
**Mandate**: **Approval First**.

**Execution Template**:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Enter plan mode - invoke EnterPlanMode()", status: "pending", activeForm: "Entering plan mode"},
  {content: "Step 2: Invoke Skill(skill='[domain]') for guidance", status: "pending", activeForm: "Loading skill"},
  {content: "Step 3: Research and create plan", status: "pending", activeForm: "Planning"},
  {content: "Step 4: Define acceptance criteria", status: "pending", activeForm: "Defining acceptance"},
  {content: "Step 5: Submit to critic - Task(subagent_type='critic')", status: "pending", activeForm: "Getting review"},
  {content: "CHECKPOINT: Get user approval before proceeding", status: "pending", activeForm: "Awaiting approval"},
  // Implementation steps added after approval
])
```

### 5. Question

**Trigger**: "?", "how", "explain", "what is"
**Mandate**: **Answer & Halt**.

**Execution Template**:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Invoke Skill(skill='[domain]') for context", status: "pending", activeForm: "Loading skill"},
  {content: "Step 2: Answer the question then STOP - do NOT implement", status: "pending", activeForm: "Answering"}
])
```

### 6. QA / Investigation

**Trigger**: "verify", "check", "investigate", "audit"
**Mandate**: **Evidence-Based**.

**Execution Template**:

```javascript
TodoWrite(todos=[
  {content: "Step 1: State hypothesis: [what we're investigating]", status: "pending", activeForm: "Stating hypothesis"},
  {content: "Step 2: Gather evidence: [specific verification steps]", status: "pending", activeForm: "Gathering evidence"},
  {content: "CHECKPOINT: Quote evidence EXACTLY - no paraphrasing", status: "pending", activeForm: "Documenting evidence"},
  {content: "Step 4: Draw conclusion from evidence", status: "pending", activeForm: "Concluding"}
])
```
