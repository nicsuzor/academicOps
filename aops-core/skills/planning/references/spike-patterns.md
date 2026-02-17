# Spike Patterns

Patterns for using spike tasks (type: `learn`) to investigate unknowns before committing to implementation.

## Spike vs Placeholder Decision

| Situation                              | Use Spike            | Use Placeholder   |
| -------------------------------------- | -------------------- | ----------------- |
| "We don't know if X is possible"       | Investigate first    |                   |
| "We know X is needed, details TBD"     |                      | Capture intent    |
| "We need to understand current system" | Audit/explore        |                   |
| "Implementation approach is unclear"   | Prototype/probe      |                   |

## Sequential Discovery Pattern

```
Epic
├── Spike: Investigate unknown → type: learn
├── Task: Implement based on findings → depends_on: [spike]
└── Task: Verify implementation
```

Use `depends_on` to enforce sequencing: implementation tasks should hard-depend on their investigation spikes.

## Spike Completion Checklist

When completing a spike/learn task:

1. **Write detailed findings to task body** - This is the primary output location
2. **Summarize in parent epic** - Add to "## Findings from Spikes" section
3. **Decompose actionable items** - Each recommendation/fix becomes a subtask:
   - Create subtasks with `depends_on: [this-spike-id]` or as siblings
   - Use clear action verbs: "Fix X", "Add Y", "Update Z"
   - Include enough context in subtask body to execute independently
4. **Complete the spike** - Parent completes when decomposition is done

## Anti-Patterns

- **Isolated spikes**: Completing investigation tasks without propagating findings to parent epic
- **Missing sequencing**: Implementation tasks that don't depend_on their investigation spikes
- **Reflexive task creation**: Creating spikes without knowing the action path (where does this go? what does completing it enable?)

## When NOT to Use Spikes

If you can't answer "what does completing this enable?", you don't have a task yet. Spikes must have a clear purpose - they investigate to enable subsequent action, not just to learn.
