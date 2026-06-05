# 10 — Reflective Execution Loop (Dogfooding)

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

| Observation                       | Action                                     |
| --------------------------------- | ------------------------------------------ |
| One-time friction                 | Note in task body, continue                |
| Recurring pattern (seen 3+ times) | Check HEURISTICS.md — codify if missing    |
| Blocking current work             | Fix minimally, file follow-up task         |
| Better approach found             | Document what worked                       |
| Tool or schema gap                | File task under relevant project           |
| Strategic misalignment            | Stop. Check vision doc. Discuss with user. |

### 3. Codify (Improve Instructions)

**The step most often skipped.** Ask: "What did I learn that should change instructions for future work?"

| Learning type             | Where it goes                 |
| ------------------------- | ----------------------------- |
| Better workflow steps     | Update the workflow .md file  |
| Missing guardrail         | HEURISTICS.md via /learn      |
| Agent behaviour fix       | CORE.md or relevant SKILL.md  |
| Domain methodology update | The governing methodology doc |
| Unclear instruction       | Fix the instruction directly  |

## PKB Integration (Mandatory)

The loop only works if learnings are persisted as tasks. Otherwise they evaporate.

At session start, create or bind to a parent task. All findings become children via `pkb__create_task(title="Finding: [specific]", parent="<session-task-id>", tags=["learning", "<domain>"])`.

For plans needing feedback: `pkb__create_task(title="Review: [plan] — [question]", tags=["feedback"])`.
For follow-up verification: `pkb__create_task(title="Verify: [change] — did it work?", tags=["verification"])`.

Good titles are specific ("hydrator missing checkpoint after context gathering"), not generic ("Finding #3").

## Strategic Alignment

Before starting, and when strategic misalignment is detected:

1. **Identify the governing vision document** — framework: `VISION.md` + PKB `aops-state`; research: project methodology doc; teaching: course design docs.
2. **Check alignment**: Does this work serve the vision, or has it drifted?
3. **If drifted**: Stop. Surface the tension to the user.

## Key Rules

1. **Reflect per step.** Not per session.
2. **File tasks for learnings.** If it's not in PKB, it didn't happen.
3. **Fix instructions, not just current work.** The next agent must benefit.
4. **Fix inline** obvious bugs and wrong guidance; **defer** design changes as tasks.
5. **Dogfooding scope**: when explicitly dogfooding, scope covers both the task AND the instructions being tested.
