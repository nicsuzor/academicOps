---
id: decompose
category: planning
bases: [base-task-tracking]
---

# Decompose

Break goals into actionable work under genuine uncertainty.

## Routing Signals

- Multi-month projects (dissertations, books, grants)
- "What does X actually require?"
- Vague deliverable, unclear dependencies
- Path forward is unknown

## NOT This Workflow

- Known tasks, clear steps → [[design]]
- Pure information request → [[simple-question]]

## Unique Steps

1. Articulate the goal clearly
2. Surface assumptions (what must be true?)
3. Find affordable probes (cheapest way to validate?)
4. Create coarse components (don't over-decompose)
5. Ensure at least one task is actionable NOW
6. Create REVIEW task that blocks subtasks (human approves before work starts)

## Key Principle

We decompose to **discover what we don't know**, not because we know what to do.

## Uncertainty Patterns

When decomposing under uncertainty, use **spike tasks** (type: `learn`) to investigate unknowns before committing to implementation.

### Spike vs Placeholder Decision

| Situation | Use Spike | Use Placeholder |
|-----------|-----------|-----------------|
| "We don't know if X is possible" | ✅ Investigate first | |
| "We know X is needed, details TBD" | | ✅ Capture intent |
| "We need to understand current system" | ✅ Audit/explore | |
| "Implementation approach is unclear" | ✅ Prototype/probe | |

### Sequential Discovery Pattern

```
Epic
├── Spike: Investigate unknown → type: learn
├── Task: Implement based on findings → depends_on: [spike]
└── Task: Verify implementation
```

Use `depends_on` to enforce sequencing: implementation tasks should hard-depend on their investigation spikes.

### Soft vs Hard Dependencies

When decomposing, choose relationship types based on execution semantics:

| Relationship | Field | Meaning | Use When |
|--------------|-------|---------|----------|
| **Hard** | `depends_on` | Task CANNOT proceed | Dependency produces required input |
| **Soft** | `soft_depends_on` | Task BENEFITS from context | Dependency provides optional context |

**Decision heuristic: "What happens if the dependency never completes?"**

- **Impossible or wrong output** → Hard dependency (`depends_on`)
- **Still valid but less informed** → Soft dependency (`soft_depends_on`)

**Common patterns:**

```
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

**Agent behavior with soft deps:**
- Read soft dependencies for context when claiming (if complete)
- Proceed regardless of soft dependency completion status
- Log context gaps, don't block on them

## Knowledge Flow Between Siblings

**Problem**: Sibling tasks in an epic are isolated by default. Findings in one spike don't automatically propagate to related tasks.

**Pattern: Propagate UP**

After completing a spike task:
1. Summarize key findings in parent epic body under "## Findings from Spikes"
2. Note implications for sibling tasks explicitly
3. This ensures future agents pulling sibling tasks inherit context via parent

**"Findings from Spikes" Section Format**:
```markdown
## Findings from Spikes

### [task-id] Task Title (date)
**Verdict**: One-line conclusion
**Key findings**: Bullet list
**Implications for siblings**: How this affects related work
```

**Why this works**: The `/pull` workflow reads parent context before executing child tasks. Parent epic body is the natural context hub.

### Spike Completion Checklist

When completing a spike/learn task:

1. **Write detailed findings to task body** - This is the primary output location
2. **Summarize in parent epic** - Add to "## Findings from Spikes" section
3. **Decompose actionable items** - Each recommendation/fix becomes a subtask:
   - Create subtasks with `depends_on: [this-spike-id]` or as siblings
   - Use clear action verbs: "Fix X", "Add Y", "Update Z"
   - Include enough context in subtask body to execute independently
4. **Complete the spike** - Per P#71, parent completes when decomposition is done

**Anti-pattern**: Creating standalone files (e.g., `docs/AUDIT-REPORT.md`) for spike output. The task graph IS the documentation system.

## Anti-Patterns

- Expanding everything at once (premature detail)
- Blocking on ambiguity (create placeholder tasks instead)
- Hidden assumptions (planning as if everything is known)
- **Isolated spikes**: Completing investigation tasks without propagating findings to parent epic
- **Missing sequencing**: Implementation tasks that don't depend_on their investigation spikes
