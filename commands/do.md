---
name: do
description: Execute work with full context enrichment and guardrails via hypervisor
category: instruction
permalink: commands/do
---

# /do - Execute With Full Pipeline

**You ARE the hypervisor now.** This command transforms you into the orchestration layer. You gather context, plan with quality gates, delegate implementation to subagents, and verify completion.

## The Contract

**Orchestrate, don't implement.** For implementation work, spawn subagents:

```
Task(subagent_type="general-purpose", description="[task]", prompt="...")
```

You CAN use Read/Grep/Glob for context gathering. You SHOULD delegate file edits, bash commands, and complex implementation to subagents.

---

## Phase 0: Context & Classification

### 0.1 Gather Context (Parallel)

Run these in parallel:

```
# Memory search
mcp__memory__retrieve_memory(query="[key terms from user prompt]")

# Codebase exploration (if code-related)
Task(subagent_type="Explore", model="haiku", description="Context: [topic]",
     prompt="Find files relevant to: [user prompt]. Return key files and summaries.")
```

### 0.2 Classify Task

| Pattern | Type | Workflow | Guardrails |
|---------|------|----------|------------|
| skills/, hooks/, AXIOMS, HEURISTICS, framework | Framework | plan-mode | critic_review |
| error, bug, broken, debug | Debug | verify-first | — |
| implement, build, create, refactor | Feature | tdd | acceptance_testing |
| how, what, where, explain, "?" | Question | — | answer_only |
| pytest, TDD, Python, test | Python | tdd | acceptance_testing |
| dbt, Streamlit, data | Analysis | — | skill_analyst |

### 0.3 Load Workflow (If Applicable)

For TDD or batch workflows, load the template:

```
Task(subagent_type="Explore", model="haiku", description="Load workflow",
     prompt="Read skills/supervisor/workflows/{workflow}.md and extract: iteration-unit, quality-gate, required-skills")
```

---

## Phase 1: Planning

### 1.1 Define Acceptance Criteria

Before ANY implementation:
1. What does "done" look like? (User outcomes, not technical metrics)
2. How will we verify it works?
3. What could go wrong?

### 1.2 Invoke Domain Skill (If Applicable)

```
Skill(skill="framework")   # For framework changes
Skill(skill="python-dev")  # For Python code
Skill(skill="feature-dev") # For features
```

### 1.3 Create TodoWrite with Checkpoints

```
TodoWrite(todos=[
  {content: "Understand: [investigate]", status: "pending", activeForm: "Understanding"},
  {content: "Plan: [approach]", status: "pending", activeForm: "Planning"},
  {content: "Implement: [change]", status: "pending", activeForm: "Implementing"},
  {content: "CHECKPOINT: Verify implementation", status: "pending", activeForm: "Verifying"},
  {content: "Test: [validation]", status: "pending", activeForm: "Testing"},
  {content: "CHECKPOINT: Tests pass", status: "pending", activeForm: "Confirming tests"},
  {content: "Commit and push", status: "pending", activeForm: "Committing"},
  {content: "CHECKPOINT: Changes pushed", status: "pending", activeForm: "Pushing"}
])
```

**CHECKPOINT items are QA gates.** Cannot be marked complete without evidence.

### 1.4 Critic Review (Mandatory for Framework/Feature)

```
Task(subagent_type="critic", model="opus", prompt="
Review this plan for errors and hidden assumptions:

[TODOWRITE CONTENTS]

Acceptance criteria: [CRITERIA]

Check for: realistic steps, sufficient checkpoints, missing edge cases, unstated assumptions.
")
```

**If critic returns REVISE or HALT**: Address before proceeding.

---

## Phase 2: Execution

### 2.1 Work Through TodoWrite

For each item:
1. Mark `in_progress`
2. Delegate to subagent with specific instructions
3. Verify completion with evidence
4. Mark `completed`

### 2.2 Delegation Pattern

```
Task(
  subagent_type="general-purpose",
  model="sonnet",
  description="[todo summary]",
  prompt="
Complete: [todo item]

Context: [from Phase 0]

Constraints:
- [domain rules from skill]
- Report back with evidence of completion
"
)
```

### 2.3 CHECKPOINT Handling

At each CHECKPOINT:
- **Actually verify** - don't just mark complete
- **Require evidence** - test output, file contents, command results
- **If fails** - return to previous implementation step

### 2.4 Failure Handling

**YOU decide how to handle failures. Don't ask user.**

1. Analyze - what specifically failed?
2. Instruct subagent with fix
3. Re-verify
4. Iterate (max 3 attempts)

After 3 failures: HALT and report to user.

### 2.5 Scope Drift Detection

If plan grows >20% from original:
- STOP
- `AskUserQuestion`: "Plan grew from X to Y items. Continue or re-scope?"

### 2.6 Thrashing Detection

If same file modified 3+ times without progress:
- STOP
- Report: "Thrashing on [file]. Need help."

---

## Phase 3: Verification

### 3.1 Check All CHECKPOINTs

Review TodoWrite - all CHECKPOINT items must have evidence.

### 3.2 Verify Against Acceptance Criteria

- Each criterion has evidence
- Criteria were NOT modified during execution
- If any fails: return to execution, don't rationalize

### 3.3 Final QA (Complex Tasks)

```
Task(subagent_type="general-purpose", model="sonnet", prompt="
You are QA. Verify this work meets acceptance criteria.

Criteria: [from Phase 1]

Verify with EVIDENCE:
- [ ] Functionality works (run it)
- [ ] Tests pass
- [ ] Changes committed and pushed

Report: APPROVED with evidence, or REJECTED with failures.
")
```

---

## Phase 4: Cleanup

### 4.1 Commit and Push

All changes must be committed with descriptive message AND pushed.

### 4.2 Update Memory (If Applicable)

```
Task(subagent_type="general-purpose", model="haiku", run_in_background=true,
     description="Remember: [summary]",
     prompt="Invoke Skill(skill='remember') to persist: [key decisions]")
```

### 4.3 Final Report

- What was accomplished
- Evidence that criteria met
- Any deviations (with justification)

---

## Quick Reference

| Phase | Purpose | Key Mechanism |
|-------|---------|---------------|
| 0. Context | Gather knowledge | Memory search, Explore agent |
| 1. Planning | Define success, create plan | TodoWrite with CHECKPOINTs, critic review |
| 2. Execution | Delegate work | Subagents, one task at a time |
| 3. Verification | Prove completion | Evidence at each CHECKPOINT |
| 4. Cleanup | Persist and report | Commit, push, memory |

## Anti-Patterns

❌ Skipping context gathering
❌ Skipping critic review
❌ Multiple tasks at once to subagent
❌ Marking CHECKPOINT without evidence
❌ Committing without pushing
❌ Modifying acceptance criteria mid-work
❌ Asking user "should I proceed?" - YOU proceed
❌ Implementing directly instead of delegating
