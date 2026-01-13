---
name: workflows
title: Workflow Reference for Hydrator
type: instruction
category: instruction
description: What the hydrator tells the main agent for each workflow type
permalink: workflows
tags: [framework, routing, workflows]
---

# Workflow Reference

The hydrator selects a workflow and generates a TodoWrite plan for the main agent.

## Workflow Selection Table

| Trigger Signals                      | Workflow       | Core Instruction to Main Agent                     |
| ------------------------------------ | -------------- | -------------------------------------------------- |
| "?", "how", "what", "explain"        | **question**   | Answer directly, no plan mode, no commit           |
| Single file, clear change            | **minor-edit** | Skip plan mode, edit → verify → commit             |
| "implement", "add feature", "create" | **tdd**        | Plan mode, test-first, delegate to subagents       |
| "fix", "bug", "error"                | **debug**      | Plan mode, reproduce → hypothesis → fix → verify   |
| Multiple items, "all", "each"        | **batch**      | Plan mode, spawn parallel subagents, aggregate QA  |
| "verify", "check", "investigate"     | **qa-proof**   | Gather evidence, quote errors exactly, no guessing |
| Complex, infrastructure, multi-step  | **plan-mode**  | Plan mode required, critic review, user approval   |

## Fixed Execution Loop (All Except Questions)

The main agent ALWAYS follows this sequence - hydrator doesn't repeat it:

1. Execute TodoWrite steps (delegate implementation to subagents)
2. At CHECKPOINTs: gather evidence before proceeding
3. QA verifier checks work independently before completion
4. Commit and push (mandatory - work isn't done until pushed)

## What Hydrator Outputs

For each workflow, hydrator generates:

1. **Intent** - What user actually wants
2. **Workflow** - One of the above
3. **Acceptance criteria** - Specific, verifiable conditions for success
4. **TodoWrite plan** - Steps for main agent to execute

### TodoWrite Structure by Workflow

**question**: No TodoWrite. Just answer.

**minor-edit**:

```
1. Edit [file] to [change]
2. CHECKPOINT: Verify change works
3. Commit and push
```

**tdd**:

```
1. Write failing test for [criterion]
2. Implement to pass test
3. CHECKPOINT: All tests pass
4. Commit and push
```

**debug**:

```
1. Reproduce the bug
2. Form hypothesis
3. Implement fix
4. CHECKPOINT: Bug no longer reproduces
5. Commit and push
```

**batch**:

```
1. Spawn parallel subagents for items 1-N (use run_in_background=true)
2. Collect results via TaskOutput
3. CHECKPOINT: All items processed successfully
4. Commit and push
```

**qa-proof**:

```
1. Gather evidence for [claim]
2. CHECKPOINT: Evidence supports conclusion
3. Report findings (no commit unless changes made)
```

**plan-mode**:

```
1. EnterPlanMode()
2. Research and draft plan
3. Get critic review
4. ExitPlanMode() for user approval
5. [Execute approved plan steps]
6. CHECKPOINT: Acceptance criteria met
7. Commit and push
```

## Guardrails by Workflow

Include these in the hydration output:

| Workflow   | Guardrails                                                    |
| ---------- | ------------------------------------------------------------- |
| question   | `answer_only`                                                 |
| minor-edit | `verify_before_complete`, `fix_within_design`                 |
| tdd        | `require_acceptance_test`, `verify_before_complete`           |
| debug      | `reproduce_first`, `verify_before_complete`                   |
| batch      | `per_item_verification`, `aggregate_qa`, `parallel_subagents` |
| qa-proof   | `evidence_required`, `quote_errors_exactly`                   |
| plan-mode  | `plan_mode`, `critic_review`, `user_approval_required`        |
