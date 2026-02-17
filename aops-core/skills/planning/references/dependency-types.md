# Dependency Types

Guidance for choosing between hard and soft dependencies when structuring task relationships.

## Hard vs Soft Dependencies

| Relationship | Field             | Meaning                    | Use When                             |
| ------------ | ----------------- | -------------------------- | ------------------------------------ |
| **Hard**     | `depends_on`      | Task CANNOT proceed        | Dependency produces required input   |
| **Soft**     | `soft_depends_on` | Task BENEFITS from context | Dependency provides optional context |

## Decision Heuristic

**Ask: "What happens if the dependency never completes?"**

- **Impossible or wrong output** → Hard dependency (`depends_on`)
- **Still valid but less informed** → Soft dependency (`soft_depends_on`)

## Common Patterns

```yaml
# Hard: Implementation needs spike findings
- id: implement-feature
  depends_on: [spike-investigate-options]  # Can't proceed without findings

# Soft: Parallel work benefits from sibling context
- id: implement-module-b
  soft_depends_on: [implement-module-a]  # Useful patterns, not required

# Soft: Review benefits from related analysis
- id: review-approach
  soft_depends_on: [analyze-alternatives]  # Informs but doesn't block
```

## Agent Behavior with Soft Dependencies

- Read soft dependencies for context when claiming (if complete)
- Proceed regardless of soft dependency completion status
- Log context gaps, don't block on them

## Contextual Relationships

Use `soft_depends_on` for "this matters but doesn't block":

| Context Type                   | Example                          | Why Soft                                        |
| ------------------------------ | -------------------------------- | ----------------------------------------------- |
| **Strategic validation**       | Using framework X proves utility | Work can proceed; validation is bonus           |
| **Infrastructure constraints** | Hook router blocks dev work      | Planning continues; only implementation blocked |
| **Environmental factors**      | Workspace setup affects comfort  | Work possible, just less optimal                |

## Human Handoff Pattern

When external human input is required before work can proceed:

```
[task-receive-examples] Receive X's input (complexity: blocked-human)
       ↓ blocks
[task-design-based-on-input] Design based on findings
```

Mark with `complexity: blocked-human` to signal this isn't bot-executable. The dependency enforces sequencing without pretending the bot can do the waiting.
