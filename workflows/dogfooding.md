---
id: dogfooding
category: meta
---

# Dogfooding Workflow

Framework self-improvement during any task. Every agent interaction serves dual objectives: complete the task AND improve the system.

## When to Use

Apply during:
- Feature development on the framework itself
- Tasks where instructions feel unclear
- Work revealing gaps in context, routing, or guardrails
- Any session where you notice friction

**Key signal**: "This is harder than it should be" or "I had to work around something."

## Decision Tree

```
One-time observation? (friction, missing context)
  → /log [observation] - creates task, continue working

Recurring pattern? (3+ observations, same root cause)
  → Check HEURISTICS.md
  → If exists but not followed → note in task
  → If doesn't exist → /learn to propose

Blocking current task?
  → Fix minimally, document, use /learn for tracked intervention

Session end?
  → Framework Reflection (see [[REMINDERS.md#Session End Requirements]])
```

## During-Task Checklist

Notice:
1. **Routing friction** - unclear which workflow/skill?
2. **Missing context** - what info didn't surface?
3. **Instruction gaps** - what guidance was absent?
4. **Guardrail failures** - what constraint would have prevented mistake?
5. **Tool issues** - unexpected behavior?

**Don't stop to fix everything.** Log with `/log`, continue working.

## Integration Points

| Component | When |
|-----------|------|
| `/log` | During work - friction noticed |
| `/learn` | Pattern confirmed, fix needed |
| Framework Reflection | Every session end |
| HEURISTICS.md | 3+ issues → new heuristic |

## Quality Gates

- Observations logged to tasks (not local notes)
- Root causes identified (not proximate causes)
- Session ends with Framework Reflection
- Recurring patterns escalated via /learn
