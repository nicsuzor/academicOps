---
id: dogfooding
category: meta
bases: []
---

# Dogfooding

Framework self-improvement through deliberate learning cycles.

## When to Apply

- Working under uncertainty (new process, unclear workflow)
- Testing framework capabilities on real work
- Any task where the process itself is worth examining

## The Dogfooding Loop

Dogfooding is not just passive observation—it's an active improvement cycle:

```
EXECUTE → OBSERVE → CODIFY
   ↑                    │
   └────────────────────┘
```

### 1. Execute (Do the Work)

Complete the task while staying aware of friction points:

- What steps feel awkward or unclear?
- Where did you need to ask for clarification?
- What context was missing?

### 2. Observe (Capture Learnings)

| Observation               | Action                                    |
| ------------------------- | ----------------------------------------- |
| One-time friction         | `/log [observation]` → continue           |
| Recurring pattern (3+)    | Check HEURISTICS.md → `/learn` if missing |
| Blocking current task     | Fix minimally, note for codification      |
| Better pattern discovered | Document what worked                      |

### 3. Codify (Improve the Framework)

**This is the critical step most often skipped.**

After completing work, ask: "What did I learn that should become part of the framework?"

| Learning Type           | Codification Target               |
| ----------------------- | --------------------------------- |
| Better workflow steps   | Update workflow .md file          |
| Missing guardrail       | Add to constraint-check or hooks  |
| Useful question pattern | Add to AskUserQuestion templates  |
| New heuristic           | Add to HEURISTICS.md via `/learn` |

**Example from task recategorization session:**

- Executed: Interactive task recategorization with user
- Observed: Presenting suggestions with confidence + getting confirmation works better than guessing
- Codified: Updated classify-task.md with confirmation pattern

**Example from daily note synthesis (2026-01-27):**

- Executed: Retroactive update of yesterday's daily note from 40 session JSONs
- Observed:
  - 35/40 session JSONs had empty accomplishment arrays (Gemini mining gap)
  - "Goals vs. Achieved" reflection section revealed intention drift
  - Tracking "unplanned work that consumed the day" explained why goals weren't met
- Codified:
  - Validates priority of transcript improvement tasks (aops-3aede0df, aops-f7b56e8b)
  - Daily notes should include reflection comparing stated goals to actual achievements
  - Unplanned work should be explicitly tracked to explain goal drift

## Notice List

Watch for these during any task:

1. **Routing friction** - unclear which workflow applies?
2. **Missing context** - what information didn't surface?
3. **Instruction gaps** - what guidance was absent?
4. **Guardrail failures** - what would have prevented a mistake?
5. **User friction** - where did the user need to correct or clarify?

## Key Rules

1. **Don't stop to fix everything.** Log with `/log`, continue working.
2. **Do codify at session end.** Before handover, ask: what learned → what changed?
3. **Small improvements compound.** One workflow tweak per session adds up.
