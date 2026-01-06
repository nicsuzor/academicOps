---
name: guardrails
title: Guardrail Definitions
type: reference
description: Modular guardrail definitions for preventing known failure patterns. Referenced by prompt-hydration, /learn, and future enforcement hooks.
permalink: guardrails
tags: [framework, enforcement, guardrails, heuristics]
---

# Guardrails

**Authoritative source** for all guardrail definitions. Referenced by:
- [[specs/prompt-hydration]] - applies guardrails based on task classification
- `commands/learn.md` - tweaks guardrails based on observed failures
- Future enforcement hooks

## Guardrail Registry

Each guardrail maps to a heuristic from HEURISTICS.md and defines when/how to apply it.

### verify_before_complete

**Heuristic**: H3 (Verification Before Assertion)
**Failure prevented**: Claiming success without checking actual state
**When to apply**: ALL tasks (default true)
**Instruction**: "VERIFY actual state before claiming task is complete. Run commands, read files, show evidence."

### answer_only

**Heuristic**: H19 (Questions Require Answers)
**Failure prevented**: Jumping to implementation when user asked a question
**When to apply**: Task type = `question`
**Instruction**: "Answer the question, then STOP. Do NOT implement, modify, or take action."

### require_skill

**Heuristic**: H2 (Skill-First Action)
**Failure prevented**: Skipping skill invocation for domain work
**When to apply**: Task matches a skill domain
**Instruction**: "Invoke Skill(skill='[name]') BEFORE proceeding with domain work."
**Values**: skill name (e.g., "framework", "python-dev", "analyst")

### plan_mode

**Heuristic**: H2, AXIOMS #23 (Plan-First Development)
**Failure prevented**: Making framework changes without plan approval
**When to apply**: Task type = `framework`, `cc_hook`, or complex feature work
**Instruction**: "Enter Plan Mode before implementation. Get user approval for the plan."

### require_acceptance_test

**Heuristic**: H28 (Mandatory Acceptance Testing)
**Failure prevented**: Claiming feature complete without e2e verification
**When to apply**: Task type = `feature`, `python`
**Instruction**: "TodoWrite MUST include e2e verification step. Test against real data before claiming complete."

### quote_errors_exactly

**Heuristic**: H5 (Error Messages Are Primary Evidence)
**Failure prevented**: Paraphrasing errors, losing diagnostic information
**When to apply**: Task type = `debug`
**Instruction**: "Quote error messages EXACTLY. Do not paraphrase, interpret, or summarize."

### fix_within_design

**Heuristic**: H27 (Debug Don't Redesign)
**Failure prevented**: Pivoting to architecture changes during debugging
**When to apply**: Task type = `debug`
**Instruction**: "Fix bugs within current architecture. Do NOT propose redesigns without explicit user approval."

### follow_literally

**Heuristic**: H4 (Explicit Instructions Override Inference)
**Failure prevented**: Interpreting or "improving" explicit user instructions
**When to apply**: User gave specific, detailed requirements
**Instruction**: "Follow user instructions LITERALLY. Do not interpret, soften, or improve them."

### critic_review

**Heuristic**: H14 (Mandatory Second Opinion)
**Failure prevented**: Presenting flawed plans without review
**When to apply**: Task type = `framework`, complex plans
**Instruction**: "Invoke Task(subagent_type='critic') to review plan before presenting to user."

### use_todowrite

**Heuristic**: H29 (TodoWrite vs Persistent Tasks)
**Failure prevented**: Losing track of multi-step work
**When to apply**: Any multi-step task
**Instruction**: "Create TodoWrite to track progress. Mark items complete as you go."

### criteria_gate

**Heuristic**: AXIOMS #23 (Plan-First Development), H25 (User-Centric Acceptance Criteria), H28 (Mandatory Acceptance Testing)
**Failure prevented**: Jumping to implementation without defining acceptance criteria
**When to apply**: Any implementation task (approach = tdd, direct, or plan)
**Enforcement**: PreToolUse hook (`criteria_gate.py`) blocks Edit/Write/Bash until gate file exists
**Instruction**: "Before ANY implementation: (1) Define acceptance criteria (user outcomes), (2) Invoke critic to review, (3) Create TodoWrite with CHECKPOINTs, (4) Create gate file. Hook will block until steps completed."

## Task Type → Guardrail Mapping

Default guardrails applied by task type:

| Task Type | Guardrails Applied |
|-----------|-------------------|
| `framework` | verify_before_complete, require_skill:framework, plan_mode, critic_review, criteria_gate, use_todowrite |
| `cc_hook` | verify_before_complete, require_skill:plugin-dev:hook-development, plan_mode, criteria_gate, use_todowrite |
| `cc_mcp` | verify_before_complete, require_skill:plugin-dev:mcp-integration, plan_mode, criteria_gate, use_todowrite |
| `debug` | verify_before_complete, quote_errors_exactly, fix_within_design, criteria_gate, use_todowrite |
| `feature` | verify_before_complete, require_acceptance_test, criteria_gate, use_todowrite |
| `python` | verify_before_complete, require_skill:python-dev, require_acceptance_test, criteria_gate, use_todowrite |
| `question` | answer_only |
| `persist` | require_skill:remember |
| `analysis` | require_skill:analyst, criteria_gate, use_todowrite |
| `review` | verify_before_complete, use_todowrite |
| `simple` | verify_before_complete, criteria_gate |

## Adding/Modifying Guardrails

Use `/learn` to adjust guardrails based on observed failures:

1. **New guardrail**: Add entry to Guardrail Registry above
2. **Adjust trigger**: Modify Task Type → Guardrail Mapping table
3. **Strengthen instruction**: Edit the guardrail's Instruction text
4. **Track change**: Create experiment in `$AOPS/experiments/`

**Principle**: Guardrails trace to HEURISTICS.md. If adding a new guardrail, ensure there's a corresponding heuristic (or create one via `/log`).

## Integration Points

### Prompt Hydration (Current)

The [[specs/prompt-hydration]] process applies guardrails based on task classification.

### PreToolUse Hook (Active)

The `criteria_gate.py` hook enforces the criteria_gate guardrail:
- Blocks Edit/Write/Bash until gate file exists (`/tmp/claude-criteria-gate-{session_id}`)
- Gate file created after completing /do Phase 1 (acceptance criteria → critic → TodoWrite)
- 30-minute expiry on gate file
- Read-only Bash commands (ls, cat, git status, etc.) bypass gate

### Future: PostToolUse Hook

Guardrails could be verified via PostToolUse hook:
- Check if TodoWrite includes acceptance test step
- Warn if verification step missing

## Guardrail Output Format

When prompt hydration returns guardrails, use this structure:

```yaml
guardrails:
  verify_before_complete: true
  answer_only: false
  require_skill: "framework"  # or null
  plan_mode: true
  require_acceptance_test: false
  quote_errors_exactly: false
  fix_within_design: false
  follow_literally: false
  critic_review: true
  use_todowrite: true
  criteria_gate: true  # enforced by PreToolUse hook
```
