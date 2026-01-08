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

Select the specific track based on the user's intent.

### 1. TDD (Feature Development)

**Trigger**: "implement", "create", "refactor", "add feature"
**Mandate**: **Test-First**. No code without a failing test.

1. **Guidance**: Invoke `Skill(skill="feature-dev")`.
2. **Test**: Write a failing test (pytest) that defines success.
3. **Verify Failure**: Run test -> RED.
4. **Implement**: Write minimal code to pass test.
5. **Verify Success**: Run test -> GREEN.
6. **Refactor**: Clean up.
7. **Commit**: `git commit -m "feat: ..."`

### 2. Debugging

**Trigger**: "fix", "bug", "error", "broken"
**Mandate**: **Scientific Method**. No "trying things" without hypothesis.

1. **Hypothesis**: State what you think is wrong.
2. **Reproduction**: Create a minimal reproduction script/test.
3. **Confirm**: Run repro -> FAIL.
4. **Fix**: Apply fix.
5. **Verify**: Run repro -> PASS.
6. **Regression Check**: Run related tests.

### 3. Batch Operations

**Trigger**: "all files", "for every", "process dataset"
**Mandate**: **Resumability**. Never rely on session memory for long-running tasks.

1. **Baseline**: `git status` (clean).
2. **Tracking**: Create a durable Task file in `$ACA_DATA/tasks/tracking/` with the list of items.
   - Format: `[ ] item_path (status)`
3. **Pilot**: Process 1-3 items to validate approach. Verify.
4. **Execute**:
   - Read tracking file for "pending" items.
   - Process batch (can use `commands/parallel-batch` pattern).
   - Mark items "done" in tracking file.
   - Commit.
5. **Resume**: If interrupted, reload tracking file and continue.

### 4. Framework / Architecture

**Trigger**: "plan", "design", "structure", "system change"
**Mandate**: **Approval First**.

1. **Enter Plan Mode**: Do not change code yet.
2. **Research**: Gather deep context.
3. **Proposal**: Write a design doc or detailed plan.
4. **Critic Review**: Deep architectural review.
5. **User Approval**: **STOP**. detailed presentation to user. Wait for `y`.
6. **Execute**: Proceed to TDD or Batch workflow.

### 5. Question

**Trigger**: "?", "how", "explain", "what is"
**Mandate**: **Answer & Halt**.

1. **Context**: Search memory/codebase.
2. **Answer**: Provide clear, cited answer.
3. **STOP**: Do not offer to implement.

## ❌ Anti-Patterns (Immediate Failures)

- **"I'll just fix this quickly"** -> Violation: Missing Plan/Context.
- **"Tests passed" (without checking output)** -> Violation: QA failure (False Positive).
- **Renaming/Moving files without git** -> Violation: Lost history.
- **Asking user "what do you think?" mid-task** -> Violation: You are the orchestrator. Decide or ask specific blocker questions.
- **Skipping `remember`** -> Violation: Amnesia.

**Reference**:

- `agents/critic.md`
- `commands/qa.md`
- `commands/reflect.md`
- `skills/remember/SKILL.md`
