---
name: workflows
title: Workflow Catalog
type: instruction
category: instruction
description: Workflow templates for prompt hydration. The hydrator selects and interprets these for specific tasks.
permalink: workflows
tags: [framework, routing, workflows]
---

# Workflow Catalog

Workflow templates that the prompt-hydrator uses to generate execution plans. Each workflow defines quality gates and iteration units.

**Spec**: [[specs/prompt-hydration]]

## Workflow Selection

The hydrator selects workflow based on semantic understanding of the task, not keyword matching.

| Workflow       | Trigger Signals                       | Quality Gate            | Iteration Unit               |
| -------------- | ------------------------------------- | ----------------------- | ---------------------------- |
| **question**   | "?", "how", "what", "explain"         | Answer accuracy         | N/A (answer then stop)       |
| **minor-edit** | Single file, clear change             | Verification            | Edit → verify → commit       |
| **tdd**        | "implement", "add feature", "create"  | Tests pass              | Test → code → commit         |
| **batch**      | Multiple files, "all", "each"         | Per-item + aggregate QA | Subset → apply → verify      |
| **qa-proof**   | "verify", "check", "investigate"      | Evidence gathered       | Hypothesis → test → evidence |
| **plan-mode**  | Framework, infrastructure, multi-step | User approval           | Plan → approve → execute     |

## Workflow Templates

### question

**Purpose**: Answer user's question without implementation.

**Quality gate**: Answer accuracy
**Guardrails**: `answer_only`

```
Step 1: [If domain skill needed] Invoke Skill for context
Step 2: Answer the question then STOP - do NOT implement
```

### minor-edit

**Purpose**: Single-file changes with clear scope.

**Quality gate**: Verification (change works as expected)
**Guardrails**: `verify_before_complete`, `fix_within_design`

```
Step 1: Read file and understand current state
Step 2: [If domain skill applies] Invoke Skill for conventions
Step 3: Implement the change following conventions
CHECKPOINT: Verify change works with evidence
Step 5: Commit and push
```

### tdd

**Purpose**: New functionality requiring tests.

**Quality gate**: Tests pass
**Guardrails**: `require_acceptance_test`, `verify_before_complete`

```
Step 1: Invoke Skill(skill='feature-dev') for TDD guidance
Step 2: [If additional domain skill needed] Invoke domain Skill
Step 3: Define acceptance criteria (user outcomes)
Step 4: Write failing test that defines success
Step 5: Implement to make test pass
CHECKPOINT: Run pytest to verify all tests pass
Step 7: Commit and push
```

### batch

**Purpose**: Processing multiple files or items.

**Quality gate**: Per-item verification + aggregate QA
**Guardrails**: `per_item_verification`, `aggregate_qa`
**Spec**: [[specs/parallel-batch-command]] (orchestration details, subagent design)

```
Stage 0: BASELINE - Capture state before any changes
Stage 1: PLAN - Identify items, define criteria, get critic review
Stage 2: PILOT - Test on 5-10 diverse items before scaling
Stage 3: EXECUTE - Process batches with parallel subagents
Stage 4: VERIFY - Per-batch verification + aggregate QA
Stage 5: COMMIT - Per-batch commits for rollback capability
```

**Critical patterns from experience**:

| Pattern             | Why It Matters                                                            |
| ------------------- | ------------------------------------------------------------------------- |
| Baseline first      | Enables before/after metrics; rollback reference                          |
| Pilot batch         | Validates approach before scale; catches process bugs                     |
| Critic review       | Plans reviewed before execution (H14)                                     |
| Tracking file       | `.aops/<task>/tracking.jsonl` enables cross-session resume                |
| Document exceptions | Not everything needs "fixing" - record justified exceptions               |
| Question batching   | Collect questions, present via AskUserQuestion (max 4), not one-at-a-time |

**Continuous processing with checkpoints**: Keep processing while work remains. Checkpoint for resumability, not as stopping points.

1. Read tracking file → identify unprocessed items
2. Process batch (~25-30 items)
3. Update task file with progress, commit and push checkpoint
4. **If work remains AND context allows → continue to next batch**
5. Only stop when: all items complete, context exhausted, or blocked

**Key**: Checkpoints enable resumption if interrupted - they are NOT signals to stop.

**Tracking schema**: `{file, batch, status, category, timestamp, notes}` where status = `pending|in_progress|complete|skipped|exception`

### qa-proof

**Purpose**: Investigation requiring evidence.

**Quality gate**: Evidence gathered and documented
**Guardrails**: `evidence_required`, `quote_errors_exactly`

```
Step 1: State hypothesis
Step 2: Gather evidence (specific verification steps)
CHECKPOINT: Quote evidence EXACTLY - no paraphrasing
Step 4: Draw conclusion from evidence
```

### plan-mode

**Purpose**: Complex work requiring user approval.

**Quality gate**: User approval before implementation
**Guardrails**: `plan_mode`, `critic_review`, `user_approval_required`

```
Step 1: Enter plan mode - invoke EnterPlanMode()
Step 2: Invoke domain Skill for guidance
Step 3: Research and create plan
Step 4: Define acceptance criteria (user outcomes)
Step 5: Submit to critic - Task(subagent_type='critic')
CHECKPOINT: Get user approval before proceeding
[Implementation steps added after approval]
```

## Skill Assignment

Skills are assigned per-step, not per-workflow. The hydrator matches each step to appropriate skills based on domain signals.

| Step Domain                               | Skill                         |
| ----------------------------------------- | ----------------------------- |
| Python code, pytest, types                | `python-dev`                  |
| Framework files (hooks/, skills/, AXIOMS) | `framework`                   |
| New functionality                         | `feature-dev`                 |
| Memory persistence                        | `remember`                    |
| Data analysis, dbt, Streamlit             | `analyst`                     |
| Claude Code hooks                         | `plugin-dev:hook-development` |
| MCP servers                               | `plugin-dev:mcp-integration`  |

## Key Principles

1. **Workflows are templates** — The hydrator interprets them for specific tasks
2. **Per-step skill assignment** — Each step can invoke a different skill
3. **Quality gates are mandatory** — CHECKPOINTs require evidence before proceeding
4. **Iteration units define commits** — Each workflow specifies what gets committed atomically
