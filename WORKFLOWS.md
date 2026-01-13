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
3. **QA VERIFICATION (MANDATORY)**: Spawn qa-verifier as independent Task subagent before completion
4. Commit and push (mandatory - work isn't done until pushed)

### Checkpoint vs QA Verifier - When to Use Each

**CRITICAL**: These serve different purposes. Don't create redundant verification steps.

**CHECKPOINTs** (interim validation during execution):
- "All tests pass" after implementing feature
- "Bug no longer reproduces" after applying fix
- "Data migration completed successfully"
- **Purpose**: Verify a specific step succeeded before proceeding to next step

**qa-verifier** (final verification against acceptance criteria):
- Automatically invoked by main agent before completion (see "QA Verification Step" below)
- Replaces what would be a final "verify everything works" checkpoint
- **Purpose**: Comprehensive check that ALL acceptance criteria met

**Never create both a final CHECKPOINT and a qa-verifier step** - that's redundant. Use interim CHECKPOINTs during execution, and let the main agent handle final qa-verifier invocation.

### QA Verification Step

**CRITICAL**: Before completing work, the main agent MUST spawn qa-verifier:

```javascript
Task(subagent_type="qa-verifier", model="opus", prompt=`
Verify the work is complete.

**Original request**: [hydrated prompt/intent]

**Acceptance criteria**:
1. [criterion from plan]
2. [criterion from plan]

**Work completed**:
- [files changed]
- [todos marked complete]

Check all three dimensions and produce verdict.
`)
```

**If VERIFIED**: Proceed to commit and push
**If ISSUES**: Fix the issues, then re-verify before completing

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

## Heuristics Selection

Instead of fixed guardrails, the hydrator reads `$AOPS/archived/HEURISTICS.md` and selects 2-4 principles relevant to the specific task. This provides task-specific guidance rather than workflow-generic rules.
