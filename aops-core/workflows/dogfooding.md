---
id: dogfooding
category: meta
description: Framework self-improvement through deliberate learning cycles (execute, observe, codify)
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
- Conversational planning or brainstorming sessions (where facts and decisions emerge incrementally)

## Core Principle: The PKB Is Always Live

The PKB is the single source of truth. Keep it current **during** conversation, not after.

- **Write as you learn** — when the user shares facts, dimensions, decisions, or status updates, write them to the PKB immediately using the `pkb` MCP tools. Do not wait to be asked. Do not ask permission.
- **Create tasks and links proactively** — when a blocker, dependency, or next action emerges in conversation, create the task and wire up relationships (`parent`, `depends_on`, `soft_blocks`) right away.
- **Update, don't duplicate** — check if a document already exists before creating. Use `append_to_document` or `update_task` to add to existing items.
- **No workarounds** — if a PKB tool can't do what you need, or the schema doesn't fit, that's a bug. File a task under the `aops` project describing the gap. Do NOT invent a manual workaround.

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
- What tools didn't work as expected?

### 2. Observe (Capture Learnings)

| Observation                 | Action                                                |
| --------------------------- | ----------------------------------------------------- |
| One-time friction           | Note in session reflection                            |
| Recurring pattern (3+)      | Check HEURISTICS.md → `/learn` if missing             |
| Blocking current task       | Fix minimally, note for codification                  |
| Better pattern discovered   | Document what worked                                  |
| Tool gap or schema mismatch | File task under `aops` project — don't work around it |

### 3. Codify (Improve the Framework)

**This is the critical step most often skipped.**

After completing work, ask: "What did I learn that should become part of the framework?"

| Learning Type           | Codification Target               |
| ----------------------- | --------------------------------- |
| Better workflow steps   | Update workflow .md file          |
| Missing guardrail       | Add to constraint-check or hooks  |
| Useful question pattern | Add to AskUserQuestion templates  |
| New heuristic           | Add to HEURISTICS.md via `/learn` |
| Agent behaviour issue   | Add to CORE.md Agent Rules        |
| PKB schema gap          | Task under aops project           |

## Conversational Knowledge Capture

When working through a planning or brainstorming session with the user, follow this pattern:

1. **Facts → PKB immediately.** User says "the workbench is 4080 aluminium" → update the project document right now.
2. **Decisions → Decision Log.** User resolves an open question → append to the document's Decision Log section.
3. **Blockers → Tasks.** A dependency or unknown emerges → create a task, wire it as a blocker.
4. **Cross-project links → Wire them.** One project enables another → add `soft_blocks` or `related` relationships.
5. **Never ask "want me to update?"** — just update. The user will correct you if you got it wrong.

## Notice List

Watch for these: routing friction, missing context, instruction gaps, guardrail failures, user friction, tool gaps, permission-seeking.

## Key Rules

1. **Don't stop to fix everything.** Log observation, continue working.
2. **Do codify at session end.** Before handover, ask: what learned → what changed?
3. **Small improvements compound.** One workflow tweak per session adds up.
4. **Write to PKB as you go.** Don't batch knowledge capture to session end.
5. **File tool gaps as tasks.** Workarounds hide bugs.
