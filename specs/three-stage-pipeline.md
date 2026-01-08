---
title: Prompt Hydration Architecture
type: spec
category: spec
status: draft
permalink: prompt-hydration-architecture
tags: [framework, architecture, routing, workflows]
---

# Prompt Hydration Architecture

**Status**: DRAFT - Revision of three-stage pipeline

## Problem Statement

The current prompt-hydrator output is underspecified. It needs to provide:

1. **Understood intent** — What does the user actually want?
2. **Selected workflow** — Which workflow template applies?
3. **Planned steps** — What specific actions, in what order?
4. **Per-step skills** — Which skill provides context for each step?

These are conceptually distinct concerns, but the HYDRATOR has all the information needed to determine them in a single pass:

- User prompt
- Session history
- Memory context
- Workflow catalog (from WORKFLOWS.md)

## Proposed Architecture

Single HYDRATE stage that outputs a complete execution plan:

```
PROMPT → HYDRATE → EXECUTE (following plan)
         ↓
         Outputs:
         - intent_envelope
         - selected_workflow
         - TodoWrite with STEPS
         - Per-step SKILL assignments
```

## HYDRATOR Responsibilities

**Owner**: prompt-hydrator agent (haiku)

**Inputs**:

- Raw user prompt
- Session history (last N prompts)
- Memory context (semantic search results)
- Workflow catalog (WORKFLOWS.md)
- Skill catalog (REMINDERS.md triggers)

**Outputs** (structured guidance for main agent):

### 1. Intent Envelope

What the user actually wants, in clear terms:

```
Intent: Fix the type error in parser.py that's causing the build to fail
```

### 2. Selected Workflow

Which workflow from WORKFLOWS.md applies:

```
Workflow: minor-edit
Quality gate: Verification step required
Commit required: Yes
```

### 3. TodoWrite Plan with Per-Step Skills

The hydrator interprets the workflow for this specific task, breaking it into concrete steps with skill assignments:

```javascript
TodoWrite(todos=[
  {content: "Step 1: Invoke Skill(skill='python-dev') to load coding standards", status: "pending", activeForm: "Loading skill"},
  {content: "Step 2: Read parser.py and understand the type error", status: "pending", activeForm: "Understanding"},
  {content: "Step 3: Implement the fix following python-dev conventions", status: "pending", activeForm: "Implementing"},
  {content: "CHECKPOINT: Run pytest to verify fix works", status: "pending", activeForm: "Verifying"},
  {content: "Step 5: Commit and push", status: "pending", activeForm: "Committing"}
])
```

### 4. Guardrails

Constraints that apply based on workflow + domain:

```
Guardrails: verify_before_complete, fix_within_design
```

## Workflow Catalog (WORKFLOWS.md)

The hydrator selects from a defined set of workflows. Each workflow specifies:

| Workflow       | Trigger Signals                       | Quality Gate            | Iteration Unit               |
| -------------- | ------------------------------------- | ----------------------- | ---------------------------- |
| **question**   | "?", "how", "what", "explain"         | Answer accuracy         | N/A (answer then stop)       |
| **minor-edit** | Single file, clear change             | Verification            | Edit → verify → commit       |
| **tdd**        | "implement", "add feature", "create"  | Tests pass              | Test → code → commit         |
| **batch**      | Multiple files, "all", "each"         | Per-item + aggregate QA | Subset → apply → verify      |
| **qa-proof**   | "verify", "check", "investigate"      | Evidence gathered       | Hypothesis → test → evidence |
| **plan-mode**  | Framework, infrastructure, multi-step | User approval           | Plan → approve → execute     |

**Key insight**: The workflow is NOT mechanical. The hydrator INTERPRETS the workflow template for the specific user request, generating concrete steps with appropriate skill invocations.

## Skill Assignment

The hydrator assigns skills per-step based on domain signals from REMINDERS.md:

| Step Domain                               | Skill         |
| ----------------------------------------- | ------------- |
| Python code, pytest, types                | `python-dev`  |
| Framework files (hooks/, skills/, AXIOMS) | `framework`   |
| New functionality                         | `feature-dev` |
| Memory persistence                        | `remember`    |
| Data analysis, dbt, Streamlit             | `analyst`     |

Each step in the TodoWrite can include an explicit `Invoke Skill(skill='xxx')` instruction when domain context is needed.

## Agent Execution

The main agent receives the hydrator's output and simply follows the plan:

1. **Create TodoWrite** exactly as specified by hydrator
2. **For each step**:
   - Mark `in_progress`
   - If step says "Invoke Skill(...)", invoke the skill
   - Execute the step
   - Mark `completed`
3. **At CHECKPOINTs**: Verify with evidence before proceeding
4. **Cleanup**: Commit, push, reflect as directed by workflow

The agent doesn't need to make routing or skill decisions — the hydrator already made them.

## Architectural Changes

### prompt-hydrator agent

**Before**: Outputs workflow dimensions + guardrails, agent interprets
**After**: Outputs complete TodoWrite plan with per-step skill assignments

### WORKFLOWS.md

**Before**: Routing table with dimensions (gate/pre-work/approach)
**After**: Workflow catalog with full templates the hydrator can interpret

### /do command

**Before**: Has its own Phase 0-4 classification and orchestration
**After**: Simpler — receives hydrated plan, executes it

### REMINDERS.md

**Before**: Skill triggers for hydrator to match upfront
**After**: Same purpose, but hydrator assigns skills per-step in the plan

## Example: Multi-Step Task

**User prompt**: "Add a pre-commit hook that runs pytest before commits"

**Hydrator output**:

````markdown
## Prompt Hydration

**Intent**: Add a pre-commit hook to run pytest before git commits
**Workflow**: tdd (new functionality requires tests)
**Guardrails**: require_acceptance_test, verify_before_complete

### TodoWrite Plan

```javascript
TodoWrite(todos=[
  {content: "Step 1: Invoke Skill(skill='framework') for hook conventions", status: "pending", activeForm: "Loading framework skill"},
  {content: "Step 2: Invoke Skill(skill='python-dev') for coding standards", status: "pending", activeForm: "Loading python-dev skill"},
  {content: "Step 3: Write failing test for pre-commit hook behavior", status: "pending", activeForm: "Writing test"},
  {content: "Step 4: Implement pre-commit hook in hooks/", status: "pending", activeForm: "Implementing"},
  {content: "CHECKPOINT: Run pytest to verify hook works", status: "pending", activeForm: "Verifying"},
  {content: "Step 6: Update .pre-commit-config.yaml", status: "pending", activeForm: "Configuring"},
  {content: "CHECKPOINT: Run pre-commit to verify integration", status: "pending", activeForm: "Verifying integration"},
  {content: "Step 8: Commit and push", status: "pending", activeForm: "Committing"}
])
```
````

```
The main agent then just follows this plan step-by-step.

---

## Benefits

1. **Single decision point**: Hydrator makes all routing/skill decisions
2. **No latency penalty**: Still one haiku call
3. **Complete plan upfront**: Agent knows exactly what to do
4. **Per-step skills**: Right skill for each step, not one guess for whole task
5. **Workflow-appropriate quality**: Each workflow embeds its own CHECKPOINTs
6. **Simpler agent logic**: Just follow the plan

---

## Relationship to Existing Specs

| Spec | Relationship |
|------|--------------|
| [[specs/prompt-hydration]] | Updates output format to include TodoWrite plan |
| [[agents/prompt-hydrator]] | Updates to generate full plan, not just dimensions |
| [[WORKFLOWS.md]] | Becomes workflow catalog with templates |
| [[REMINDERS.md]] | Same triggers, used by hydrator for per-step assignment |

---

## Acceptance Criteria

1. Hydrator outputs complete TodoWrite plan with per-step skill assignments
2. WORKFLOWS.md contains clear templates for each workflow type
3. Main agent can execute plan without making routing decisions
4. Each workflow type includes appropriate CHECKPOINTs
5. Skill invocations are embedded in step content, not inferred later
```
