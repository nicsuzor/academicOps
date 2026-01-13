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

All work MUST follow one ofhe workflows in this file. No exceptions.


Not every prompt needs a TodoWrite plan. Two scenarios should execute immediately without TodoWrite:

### 1. Simple Questions
When the prompt is a simple question that can be answered directly:
- **Signals**: "?", "how does X work", "what is Y", "explain Z"
- **Action**: Answer the question directly, then HALT
- **No TodoWrite**: Questions don't require multi-step plans
- **No commit**: Pure information requests don't modify code

### 2. Direct Skill/Command Invocation
When the prompt is a 1:1 match for an existing skill or command:
- **Signals**: "generate transcript for today", "commit", "create session insights"
- **Action**: Invoke the skill/command directly without wrapping in TodoWrite
- **Example**: "generate transcript for today" → `Task(subagent_type="framework", prompt="Generate transcript for today's date")`
- **Why**: Skills already contain their own workflows; wrapping adds no value

**For all other workflows**, generate a TodoWrite plan as described below.

## Workflow Selection Table

| Trigger Signals                      | Workflow       | Core Instruction to Main Agent                     |
| ------------------------------------ | -------------- | -------------------------------------------------- |
| "?", "how", "what", "explain"        | **question**   | Answer directly, no plan mode, no commit           |
| "implement", "add feature", "create" | **tdd**        | Plan mode, test-first, delegate to subagents       |
| "fix", "bug", "error"                | **debug**      | Plan mode, reproduce → hypothesis → fix → verify   |
| Multiple items, "all", "each"        | **batch**      | Plan mode, spawn parallel subagents, aggregate QA  |
| "verify", "check", "investigate"     | **qa-proof**   | Gather evidence, quote errors exactly, no guessing |
| Complex, infrastructure, multi-step  | **plan-mode**  | Plan mode required, critic review, user approval   |

## Detection Rules

- **No TodoWrite - Simple question**: "?", "how", "what", "explain" with no action needed → Just answer, no plan
- **No TodoWrite - Direct skill/command**: 1:1 match with existing skill/command → Invoke directly, no wrapper
- **Batch**: Multiple independent items → workflow=batch, parallel subagents
- **Interactive**: "one by one", "work through" → AskUserQuestion checkpoints
- **bd issue correlation**: Multi-session work or dependencies → Check `bd ready`, note relevant issues

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


## TodoWrite Structure by Workflow

### Simple question:
```
1. Answer the user's question: 
2. HALT after answering and await further instructions.
```

### Minor edit:

```
1. Fetch or create `bd` issue, mark as in-progress
2. Invoke `ttd` to create a failing test
2. Invoke `python-dev` to [change]
2. CHECKPOINT: Verify change works
3. Commit and push
```

### Development work:

Full TTD is required for all development work. 

```
0. Fetch or create `bd` issue, mark as in-progress
1. Articulate clear acceptance criteria
2. Create a plan, save to `bd` issue
3. Get critic review
4. Execute plan steps:
  - **Red**: Write failing test for [criterion]
  - **Green**: Minimal implementation to pass
  - **Evidence**: `uv run pytest -v` output
  - **Commit**: Descriptive message with phase reference
  - Repeat
6. CHECKPOINT: All tests pass
7. Invoke QA agent to validate against acceptance criteria
5. Commit, push, update `bd` issue
```

### Debugging:

```
0. Fetch or create `bd` issue, mark as in-progress
1. Articulate clear acceptance criteria
2. Use python-dev skill to design a durable test for success
3. Report findings and save to `bd` issue
4. Commit and push
```

### Batch processing:

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

## Beads (bd) Workflow - Issue Tracking

**When to use bd vs TodoWrite:**
- **bd (beads issues)**: Strategic work spanning multiple sessions, with dependencies, or discovered during work
- **TodoWrite**: Simple single-session execution tracking

**Core principle**: When in doubt, prefer bd—persistence you don't need beats lost context.

### Essential bd Commands

**Finding work:**
- `bd ready` - Show issues ready to work (no blockers)
- `bd list --status=open` - All open issues
- `bd show <id>` - Detailed issue view with dependencies

**Creating & updating:**
- `bd create --title="..." --type=task|bug|feature --priority=2` - New issue
  - Priority: 0-4 or P0-P4 (0=critical, 2=medium, 4=backlog)
- `bd update <id> --status=in_progress` - Claim work
- `bd close <id>` - Mark complete
- `bd close <id1> <id2> ...` - Close multiple (more efficient)

**Dependencies:**
- `bd dep add <issue> <depends-on>` - Add dependency (issue depends on depends-on)
- `bd blocked` - Show all blocked issues

**Sync:**
- `bd sync` - Sync with git remote (run at session end)

### bd Workflow Integration

When hydrator identifies work that should be tracked as a bd issue:
1. Check if related issue exists: `bd ready` or `bd list --status=open`
2. If creating new issues for multi-step work, recommend parallel creation
3. Include bd issue IDs in "Relevant Context" section
4. For session completion, remind: `bd sync` before `git push`
