---
id: base-dogfood
category: base
---

# Base: Dogfood

**Composable base pattern.** Apply when exercising framework functions.

## Pattern

1. **Execute** the work while noting friction points:
   - What steps feel awkward or unclear?
   - What context was missing?
   - What tools didn't work as expected?

2. **Observe** and classify:

| Observation | Action |
|-------------|--------|
| One-time friction | `/learn [observation]` → continue |
| Recurring pattern (3+) | Check HEURISTICS.md → `/learn` if missing |
| Blocking current task | Fix minimally, note for codification |
| Tool gap or schema mismatch | File task under `aops` project |

3. **Codify** before session end:

| Learning Type | Target |
|---------------|--------|
| Better workflow steps | Update workflow file |
| Missing guardrail | Add to hooks or constraint-check |
| New heuristic | `/learn` |
| Agent behaviour issue | CORE.md Agent Rules |
| PKB schema gap | Task under aops project |

## When to Apply

- Working under uncertainty (new process, unclear workflow)
- Testing framework capabilities on real work
- Any task where the process itself is worth examining

## When to Skip

- Routine tasks using well-established skills
- [[simple-question]]
