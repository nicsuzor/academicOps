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

## NOT This Workflow

- Task maps to existing skill → use it
- One-off unlikely to recur → just do it
- Task unclear → [[decompose]] first

---

## Section: Dogfooding Loop

Active improvement cycle through deliberate observation.

```
EXECUTE → OBSERVE → CODIFY
   ↑                    │
   └────────────────────┘
```

### 1. Execute (Do the Work)

Complete the task while staying aware of friction points:

- What steps feel awkward or unclear?
- Where did you need clarification?
- What context was missing?

### 2. Observe (Capture Learnings)

| Observation               | Action                                    |
| ------------------------- | ----------------------------------------- |
| One-time friction         | `/log [observation]` → continue           |
| Recurring pattern (3+)    | Check HEURISTICS.md → `/learn` if missing |
| Blocking current task     | Fix minimally, note for codification      |
| Better pattern discovered | Document what worked                      |

### 3. Codify (Improve the Framework)

**Critical step most often skipped.**

| Learning Type           | Codification Target               |
| ----------------------- | --------------------------------- |
| Better workflow steps   | Update workflow .md file          |
| Missing guardrail       | Add to constraint-check or hooks  |
| Useful question pattern | Add to AskUserQuestion templates  |
| New heuristic           | Add to HEURISTICS.md via `/learn` |

### Notice List

Watch for during any task:

1. **Routing friction** - unclear which workflow applies?
2. **Missing context** - what information didn't surface?
3. **Instruction gaps** - what guidance was absent?
4. **Guardrail failures** - what would have prevented a mistake?
5. **User friction** - where did user need to correct?

### Tool Effectiveness Audit

Reflect on each tool used:

| Tool Category    | Questions                                    |
| ---------------- | -------------------------------------------- |
| Search tools     | Did queries find what I described?           |
| Memory/retrieval | Was content relevant? Fresh?                 |
| Task manager     | Did structured queries beat semantic search? |
| Graph traversal  | Could I find relationships?                  |

### Knowledge Base Hygiene

- **Task titles**: Use natural language alongside technical terms
- **Memory freshness**: Periodically check if recent work is represented
- **Graph completeness**: Relationships in your head → relationships in graph

---

## Section: Skill Piloting

Build new skills when decomposition reveals capability gaps.

### When to Pilot

- Decomposition reaches task with no matching skill
- Recurring pattern without standardized approach
- First-time task worth capturing

### Piloting Steps

1. **Articulate gap**: What? Why no existing skill?
2. **Pilot with user**: Interactive, supervised learning
3. **Reflect**: Essential vs incidental steps
4. **Draft SKILL.md**: when-to-use, steps, quality gates
5. **Test**: Apply to similar task without guidance
6. **Index**: Add to plugin.json

### Anti-Patterns

| Anti-Pattern          | Problem                     |
| --------------------- | --------------------------- |
| Premature abstraction | Skill after one use         |
| Kitchen sink          | Too much in one skill       |
| Orphan skill          | Not indexed = doesn't exist |

---

## Key Rules

1. **Don't stop to fix everything.** Log with `/log`, continue working.
2. **Do codify at session end.** Before handover, ask: what learned → what changed?
3. **Small improvements compound.** One workflow tweak per session adds up.
4. **Reflect on tools, not just tasks.** The meta-layer matters.
