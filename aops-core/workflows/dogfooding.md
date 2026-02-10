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

## Tool Effectiveness Audit

**Add to the Observe phase**: Reflect on each tool you used. Did it work? Why/why not?

### Questions to Ask

| Tool Category | Questions |
|---------------|-----------|
| **Search tools** | Did queries find what I described? What query worked vs failed? |
| **Memory/retrieval** | Was content relevant? Fresh? Did vector search beat keyword? |
| **Task manager** | Did structured queries (list by project/status) beat semantic search? |
| **Graph traversal** | Could I find relationships? Were soft dependencies useful? |

### Common Failure Patterns

1. **Natural language vs technical titles**: User describes "sorting through ideas" but task is titled "VoI formulation attempt"
2. **Stale corpus**: Memory contains old content; new work isn't indexed
3. **Wrong tool for query**: Semantic search when structured query would work
4. **Missing edges**: Relationships exist conceptually but aren't in graph

### Recording Tool Observations

When a tool fails or surprises you:

1. **In-session**: Note it, continue working (don't derail)
2. **At reflection**: Create `type: learn` task if pattern seems systemic
3. **Link appropriately**: If the observation might inform tooling decisions, add soft_depends_on to relevant spikes

**Example from bazaar PoC session (2026-02-10):**

- Task search failed 4 natural language queries before finding task via `list_tasks(project=...)`
- Memory search returned December 2025 content, nothing about current work
- Created learn task about memory server effectiveness
- Created 3 alternative tooling nodes, linked to VoI spike via soft_depends_on

## Knowledge Base Hygiene

The knowledge base is only useful if it's findable. Periodic maintenance:

### Task Titles
- Use natural language alongside technical terms
- "VoI formulation attempt" → "Estimate task value using information theory (VoI/EVPI)"
- Tags can supplement but don't replace clear titles

### Memory Freshness
- Memory MCP content can go stale
- Periodically check: is recent work represented?
- Consider: should task data sync to memory for discoverability?

### Graph Completeness
- Relationships in your head → relationships in the graph
- "This would inform that" → soft_depends_on edge
- Missing edges = missing traversability

## Key Rules

1. **Don't stop to fix everything.** Log with `/log`, continue working.
2. **Do codify at session end.** Before handover, ask: what learned → what changed?
3. **Small improvements compound.** One workflow tweak per session adds up.
4. **Reflect on tools, not just tasks.** The meta-layer matters.
