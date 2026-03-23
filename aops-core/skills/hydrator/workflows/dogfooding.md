---
id: dogfooding
category: meta
description: Framework self-improvement through deliberate learning cycles (execute, reflect, codify)
triggers:
  - "dogfood"
  - "self-improve"
  - "framework improvement"
  - "learn from usage"
bases: []
---

# Dogfooding

Framework self-improvement through deliberate learning cycles.

## When to Apply

- Working under uncertainty (new process, unclear workflow)
- Testing framework capabilities on real work
- Any task where the process itself is worth examining
- Conversational planning or brainstorming sessions

## Core Principles

- **PKB is always live.** Write facts, decisions, and status to PKB immediately. Do not wait to be asked.
- **Anchor findings to a task.** Create a parent task for the session. All findings are children with specific titles referencing the artifact and finding — not generic "finding #1." (e.g., "Finding: dogfooding.md - Unclear Reflect/Codify separation")
- **Create tasks and links proactively.** Wire up `parent`, `depends_on`, `soft_blocks` as they emerge.
- **Update, don't duplicate.** Use `append` or `update_task` for existing items.
- **Don't be selfish.** Every fix to current work MUST propagate to instructions governing future work. The next agent must benefit from your learning.
- **No workarounds.** If a PKB tool can't do what you need, file a task. Don't invent a manual workaround.

## The Loop

`EXECUTE → REFLECT → CODIFY` (per step, not per session)

### 1. Execute (One Step)

Complete one discrete step. Notice: What felt awkward? What context was missing? What tools didn't work?

### 2. Reflect (Before Proceeding)

Before the next step: Did the process work as designed? Did you need human input the process should have handled? Is there a finding worth recording? **Record findings immediately — don't wait to be asked.**

| Observation            | Action                                                  |
| ---------------------- | ------------------------------------------------------- |
| One-time friction      | Note in session reflection                              |
| Recurring pattern (3+) | Check HEURISTICS.md, record for codification if missing |
| Blocking current task  | Fix minimally, note for codification                    |
| Better pattern found   | Document what worked                                    |
| Tool/schema gap        | File task under `aops` project                          |
| Process gap            | Record as PKB insight for codification                  |

### 3. Codify (Improve the Framework)

**Most often skipped.** Ask: "What did I learn that should become part of the framework?"

| Learning Type       | Codification Target              |
| ------------------- | -------------------------------- |
| Better workflow     | Update workflow .md file         |
| Missing guardrail   | Add to constraint-check or hooks |
| New heuristic       | Add to HEURISTICS.md via /learn  |
| Agent behaviour fix | Add to CORE.md Agent Rules       |
| PKB schema gap      | Task under aops project          |

## Conversational Knowledge Capture

1. **Facts → PKB immediately.** Don't ask "want me to update?" — just update.
2. **Decisions → Decision Log** section of the relevant document.
3. **Blockers → Tasks.** Wire as blockers.
4. **Cross-project links → Wire them** with `soft_blocks` or `related`.

## Post-Run Assessment (MANDATORY)

After a dogfood run completes, file structured follow-ups — these ARE the output:

1. **"Pre-next-run fixes" epic** — everything to fix before repeating (infra + process issues)
2. **Blocked "repeat and reassess" task** — depends on fixes epic, includes baseline metrics and AC for improvement
3. **GitHub Issues** (`/learn`) for systemic problems — especially wasted work on wrong targets (wrong repo, deprecated code)
4. **Update these instructions** with new limitations or patterns

Follow-up tasks are durable; session notes evaporate.

## Key Rules

1. **Reflect per step.** Complete one step → reflect → codify → next step.
2. **Record automatically.** Don't wait for the user to say "record this."
3. **Propagate, don't hoard.** Fix instructions, not just your current work.
4. **Small improvements compound.** One workflow tweak per session adds up.
5. **File tool gaps as tasks.** Workarounds hide bugs.

## Scope

**Dual scope authorization**: When dogfooding is requested, the agent has scope over both the task AND the tooling being tested. Custodiet should not flag inline fixes to the dogfooded artifact as out-of-scope.

**Fix-vs-defer boundary**:

- **Fix inline**: Obvious bugs, wrong API calls, missing edge cases, incorrect guidance — clear and localized fixes.
- **Defer**: Design changes, structural rethinking, new features. Log in `### Dogfooding observations` section and create follow-up tasks.
