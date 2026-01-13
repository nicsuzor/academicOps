---
name: workflows
title: Workflow Catalog
type: instruction
category: instruction
description: Universal workflow with optional extras for batch and TDD
permalink: workflows
tags: [framework, routing, workflows]
---

# Workflow Catalog

## Universal Workflow

**Every task follows this loop:**

1. **Plan** - Create TodoWrite with steps + CHECKPOINTs
2. **Execute** - For each step: mark in_progress → do it → mark completed
3. **Verify** - At CHECKPOINTs: gather evidence before proceeding
4. **Commit** - Push changes at the end

**Orchestrator principle**: The main agent coordinates. It does NOT implement. Each implementation step delegates to a subagent with skill guidance embedded.

## Workflow Selection

| Intent Signal                     | Workflow      | Delegation                       |
| --------------------------------- | ------------- | -------------------------------- |
| "implement", "create", "refactor" | **tdd**       | Test-first via subagents         |
| "fix", "bug", "error"             | **debug**     | Hypothesis → fix via subagent    |
| "all files", "batch", "for every" | **batch**     | Parallel subagents (hypervisor)  |
| "plan", "design", "system change" | **plan-mode** | EnterPlanMode → critic → approve |
| "?", "how", "explain"             | **question**  | Answer & HALT                    |
| "verify", "check", "investigate"  | **qa**        | Evidence gathering → conclusion  |

## Universal Mandates

These apply to EVERY workflow:

1. **Locked Acceptance Criteria** - Define success conditions upfront
2. **Skill-First Steps** - Every implementation step invokes one skill
3. **Agent Delegation** - Subagents execute; orchestrator coordinates
4. **Verification** - CHECKPOINT steps with evidence
5. **Atomic Commits** - Commit after each logical unit
6. **Final Push** - Never leave work stranded locally

## Optional: TDD Workflow

**When**: "implement", "create", "add feature"

```javascript
TodoWrite(todos=[
  {content: "Invoke Skill(skill='feature-dev') for TDD guidance", status: "pending", activeForm: "Loading skill"},
  {content: "Delegate test writing - Task(prompt='Write failing test for [criteria]')", status: "pending", activeForm: "Delegating test"},
  {content: "Delegate implementation - Task(prompt='Implement to pass test')", status: "pending", activeForm: "Delegating implementation"},
  {content: "CHECKPOINT: Run tests to verify all pass", status: "pending", activeForm: "Verifying"},
  {content: "Commit and push", status: "pending", activeForm: "Committing"}
])
```

## Optional: Batch Workflow (Hypervisor)

**When**: Multiple independent items to process

The orchestrator becomes a **hypervisor** - spawning parallel subagents:

```python
# Spawn multiple subagents in ONE message for parallel execution
Task(subagent_type="general-purpose", prompt="Process item 1: [details]", run_in_background=true)
Task(subagent_type="general-purpose", prompt="Process item 2: [details]", run_in_background=true)
Task(subagent_type="general-purpose", prompt="Process item 3: [details]", run_in_background=true)
# Check TaskOutput when all complete
```

```javascript
TodoWrite(todos=[
  {content: "Identify all items to process", status: "pending", activeForm: "Identifying items"},
  {content: "Spawn parallel subagents for independent items", status: "pending", activeForm: "Delegating to subagents"},
  {content: "CHECKPOINT: Verify all subagents completed", status: "pending", activeForm: "Verifying batch"},
  {content: "Aggregate results and commit", status: "pending", activeForm: "Committing"}
])
```

## Optional: Plan Mode

**When**: Complex, infrastructure, multi-step changes

1. `EnterPlanMode()` - Research and design
2. Submit to critic - `Task(subagent_type='critic')`
3. Get user approval via `ExitPlanMode()`
4. Execute approved plan

## Skill Matching Reference

| Task Type                | Skill                        |
| ------------------------ | ---------------------------- |
| Framework/plugin changes | `Skill(skill="framework")`   |
| Feature implementation   | `Skill(skill="feature-dev")` |
| Bug fix, debugging       | `Skill(skill="[domain]")`    |
| Memory persistence       | `Skill(skill="remember")`    |
| Process reflection       | `/reflect`                   |
