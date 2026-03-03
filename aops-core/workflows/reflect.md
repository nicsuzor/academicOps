---
id: meta-improvement
category: meta
bases: [base-task-tracking, base-handover]
---

# Meta Improvement

Framework self-improvement through deliberate learning and skill development.

## Routing Signals

- Working under uncertainty (new process, unclear workflow)
- Testing framework capabilities on real work
- Decomposition reveals capability gaps
- Recurring pattern worth capturing

---

## Dogfooding Loop

Active improvement cycle through deliberate observation.

```
EXECUTE → OBSERVE → CODIFY
   ↑                    │
   └────────────────────┘
```

### 1. Execute (Do the Work)

Complete the task while staying aware of friction points: awkward steps, needed clarifications, or missing context.

### 2. Observe (Capture Learnings)

| Observation               | Action                                    |
| ------------------------- | ----------------------------------------- |
| One-time friction         | `/learn [observation]` → continue         |
| Recurring pattern (3+)    | Check HEURISTICS.md → `/learn` if missing |
| Blocking current task     | Fix minimally, note for codification      |
| Better pattern discovered | Document what worked                      |

### 3. Codify (Improve the Framework)

| Learning Type           | Codification Target               |
| ----------------------- | --------------------------------- |
| Better workflow steps   | Update workflow .md file          |
| Missing guardrail       | Add to constraint-check or hooks  |
| Useful question pattern | Add to AskUserQuestion templates  |
| New heuristic           | Add to HEURISTICS.md via `/learn` |

---

## Further Meta-Activities

For auditing and piloting procedures, see **[[references/meta-details]]**:

- **Tool Effectiveness Audit** - Reflect on search, memory, and graph tools
- **Section: Skill Piloting** - How to build new standardized skills
- **Anti-Patterns** - Common pitfalls to avoid when abstracting

---

## Key Rules

1. **Don't stop to fix everything.** Log with `/learn`, continue working.
2. **Do codify at session end.** Before handover, ask: what learned → what changed?
3. **Small improvements compound.** One workflow tweak per session adds up.
4. **Reflect on tools, not just tasks.** The meta-layer matters.
