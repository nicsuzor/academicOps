---
name: workflows
title: Workflow Catalog
type: instruction
category: instruction
description: Universal workflow with plan mode as default, plus batch and TDD variants
permalink: workflows
tags: [framework, routing, workflows]
---

# Workflow Catalog

## Universal Workflow

**Every task follows this loop:**

1. **Plan** - `EnterPlanMode()` → research → draft plan → critic review → user approval
2. **Execute** - For each step: mark in_progress → delegate to subagent → verify → mark completed
3. **Verify** - At CHECKPOINTs: gather evidence before proceeding
4. **Commit** - Push changes at the end

**Orchestrator principle**: The main agent coordinates. It does NOT implement. Each implementation step delegates to a subagent with skill guidance embedded.

## Workflow Selection

| Intent Signal                     | Workflow     | Delegation                      |
| --------------------------------- | ------------ | ------------------------------- |
| "implement", "create", "refactor" | **tdd**      | Plan → test-first via subagents |
| "fix", "bug", "error"             | **debug**    | Plan → hypothesis → fix         |
| "all files", "batch", "for every" | **batch**    | Plan → parallel subagents       |
| "?", "how", "explain"             | **question** | Answer & HALT (no plan needed)  |
| "verify", "check", "investigate"  | **qa**       | Evidence gathering → conclusion |

**Default**: All implementation workflows use plan mode. Only questions skip planning.

## Universal Mandates

These apply to EVERY workflow (except questions):

1. **Plan First** - Enter plan mode, get critic review, get user approval
2. **Locked Acceptance Criteria** - Define success conditions upfront
3. **Skill-First Steps** - Every implementation step invokes one skill
4. **Agent Delegation** - Subagents execute; orchestrator coordinates
5. **Verification** - CHECKPOINT steps with evidence
6. **Atomic Commits** - Commit after each logical unit
7. **Final Push** - Never leave work stranded locally

## Plan Mode (Required for Implementation)

All implementation tasks follow this pattern:

1. `EnterPlanMode()` - Research and design
2. Draft plan with TodoWrite steps
3. Submit to critic - `Task(subagent_type='critic')`
4. Get user approval via `ExitPlanMode()`
5. Execute approved plan

## TDD Variant

**When**: "implement", "create", "add feature"

After plan approval, execute with test-first pattern:

```javascript
TodoWrite(todos=[
  {content: "Invoke Skill(skill='feature-dev') for TDD guidance", status: "pending", activeForm: "Loading skill"},
  {content: "Delegate test writing - Task(prompt='Write failing test for [criteria]')", status: "pending", activeForm: "Delegating test"},
  {content: "Delegate implementation - Task(prompt='Implement to pass test')", status: "pending", activeForm: "Delegating implementation"},
  {content: "CHECKPOINT: Run tests to verify all pass", status: "pending", activeForm: "Verifying"},
  {content: "Commit and push", status: "pending", activeForm: "Committing"}
])
```

## Batch Variant (Hypervisor)

**When**: Multiple independent items to process

After plan approval, orchestrator becomes a **hypervisor** - spawning parallel subagents:

```python
# Spawn multiple subagents in ONE message for parallel execution
Task(subagent_type="general-purpose", prompt="Process item 1: [details]", run_in_background=true)
Task(subagent_type="general-purpose", prompt="Process item 2: [details]", run_in_background=true)
Task(subagent_type="general-purpose", prompt="Process item 3: [details]", run_in_background=true)
# Check TaskOutput when all complete
```

## Skill Matching Reference

| Task Type                | Skill                        |
| ------------------------ | ---------------------------- |
| Framework/plugin changes | `Skill(skill="framework")`   |
| Feature implementation   | `Skill(skill="feature-dev")` |
| Bug fix, debugging       | `Skill(skill="[domain]")`    |
| Memory persistence       | `Skill(skill="remember")`    |
| Process reflection       | `/reflect`                   |
