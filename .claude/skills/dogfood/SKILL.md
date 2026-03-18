---
name: dogfood
type: skill
category: meta
description: Generic reflective execution loop — learn from doing, capture friction, improve instructions
triggers:
  - "dogfood"
  - "reflective loop"
  - "learn from this"
  - "interactive development"
modifies_files: true
needs_task: true
mode: execution
domain:
  - meta
  - framework
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, mcp__pkb__create_task, mcp__pkb__update_task, mcp__pkb__append, mcp__pkb__search, mcp__pkb__retrieve_memory
version: 1.0.0
---

# Dogfood — Reflective Execution Loop

A generic loop for learning from doing. Works for framework development, research methodology, teaching design — any domain where the process itself is worth examining.

## When to Use

- Working under uncertainty (new process, unclear approach)
- Testing a procedure on real work
- Interactive sessions where energy is being spent and learnings should compound
- Any task where you want to improve the instructions, not just complete the work

## The Loop

```
EXECUTE one step → REFLECT before proceeding → CODIFY if warranted → repeat
```

Per-step, not per-session. Reflect after every step, not batched at the end.

### 1. Execute (One Step)

Do one discrete piece of work. While doing it, notice:
- What context was missing?
- What felt awkward or unclear?
- What tools didn't work or weren't available?
- Did you deviate from the plan? Why?

### 2. Reflect (Before Next Step)

Before proceeding, ask: did the process work as designed?

| Observation | Action |
|-------------|--------|
| One-time friction | Note in task body, continue |
| Recurring pattern (seen 3+ times) | Check HEURISTICS.md — codify if missing |
| Blocking current work | Fix minimally, file follow-up task |
| Better approach found | Document what worked |
| Tool or schema gap | File task under relevant project |
| Strategic misalignment | Stop. Check vision doc. Discuss with user. |

### 3. Codify (Improve Instructions)

**The step most often skipped.** Ask: "What did I learn that should change instructions for future work?"

| Learning type | Where it goes |
|---------------|---------------|
| Better workflow steps | Update the workflow .md file |
| Missing guardrail | HEURISTICS.md via /learn |
| Agent behaviour fix | CORE.md or relevant SKILL.md |
| Domain methodology update | The governing methodology doc |
| Unclear instruction | Fix the instruction directly |

## PKB Integration (Mandatory)

The loop only works if learnings are persisted as tasks. Otherwise they evaporate.

### At session start

Create or bind to a parent task for the session's work. All findings are children.

### At each reflection point

If you found something worth acting on:

```
mcp__pkb__create_task(
  title="[specific finding, not generic]",
  parent="<session-task-id>",
  tags=["learning", "<domain>"]
)
```

**Title examples**:
- Good: "Finding: hydrator workflow missing checkpoint after context gathering"
- Bad: "Finding #3"

### For plans that need feedback

When creating or revising a plan, create an explicit feedback task:

```
mcp__pkb__create_task(
  title="Review: [plan description] — get feedback on [specific question]",
  tags=["feedback", "<domain>"]
)
```

### For follow-up learning

When completing work that changed instructions or methodology:

```
mcp__pkb__create_task(
  title="Verify: [change description] — did it work in practice?",
  tags=["verification", "<domain>"],
  body="Check in 3 sessions whether [specific observable outcome]."
)
```

## Strategic Alignment

Before starting, and when strategic misalignment is detected:

1. **Identify the governing vision document** for this domain:
   - Framework work → `$AOPS/docs/VISION.md` + `$ACA_DATA/.agent/BUTLER.md`
   - Research project → the project's methodology doc
   - Teaching → course design docs
2. **Check alignment**: Does this work serve the vision, or has it drifted?
3. **If drifted**: Stop. Surface the tension to the user. Don't silently continue.

## Fix-vs-Defer Boundary

- **Fix inline**: Obvious bugs, wrong guidance, missing edge cases — anything where the correct fix is clear and localised.
- **Defer**: Design changes, structural rethinking, new features surfaced by the work. File as a task with specific title.

## Scope

When explicitly dogfooding (e.g., "dogfood this", interactive framework session), the agent has scope over both the task being executed AND the instructions being tested. This is not scope expansion — it is the task. Custodiet should not flag inline fixes to the dogfooded artifact as out-of-scope.

## Key Rules

1. **Reflect per step.** Not per session.
2. **File tasks for learnings.** If it's not in PKB, it didn't happen.
3. **Fix instructions, not just current work.** The next agent must benefit.
4. **Small improvements compound.** One instruction tweak per session adds up.
5. **Check strategic fit.** Vision alignment prevents wasted energy.

## Related

- `aops-core/commands/learn.md` — the framework's immune system (root cause → enforcement)
- `aops-core/skills/hydrator/workflows/dogfooding.md` — the original framework-specific version
- `specs/feedback-loops.md` — the full Observe→Analyze→Diagnose→Intervene→Verify architecture
