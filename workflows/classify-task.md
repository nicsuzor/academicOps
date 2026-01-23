---
id: classify-task
category: triage
bases: []
---

# Classify Task

Determine task complexity and placement on the work graph for proper sequencing.

## When to Use

- Hydrator routes here when classifying new work
- Creating tasks from inbox items
- Triaging unclear work items

## Part 1: Complexity Classification

Classify based on execution path and scope:

| Complexity | Path | Scope | Signals |
|------------|------|-------|---------|
| `mechanical` | EXECUTE | single-session | Known steps, clear deliverable, no judgment needed |
| `requires-judgment` | EXECUTE | single-session | Some unknowns, needs exploration within bounds |
| `multi-step` | EXECUTE | multi-session | Sequential orchestration, clear decomposition |
| `needs-decomposition` | TRIAGE | any | Too vague, must break down before executing |
| `blocked-human` | TRIAGE | any | Requires human decision or external input |

### Classification Heuristics

**mechanical** (haiku, immediate):
- "Rename X to Y across files"
- "Add field Z to model"
- "Fix typo in documentation"
- Single file, obvious change

**requires-judgment** (sonnet, execute with discretion):
- "Debug why X fails" (known symptom, unknown cause)
- "Implement feature Y" (bounded scope, some design decisions)
- "Review and fix test failures" (investigation within session)

**multi-step** (sonnet, TodoWrite plan):
- "Refactor system X" (clear goal, multiple sessions)
- "Migrate from A to B" (known destination, staged execution)
- "Complete feature with tests" (multiple phases)

**needs-decomposition** (TRIAGE, don't execute):
- "Build feature X" (vague scope)
- "Improve performance" (needs analysis first)
- Goal-level requests lacking clear path

**blocked-human** (TRIAGE, assign to nic):
- "Which API should we use?"
- "Need approval for architecture change"
- Missing external input, strategic decision

## Part 2: Graph Positioning

Every task exists on a work graph. Position it correctly:

### Parent Selection

**Set `parent` when**:
- Task is a subtask of existing project/goal
- Work contributes to a larger deliverable
- Task naturally belongs under umbrella work

**Leave `parent` null when**:
- Standalone work (bug fixes, quick tasks)
- No obvious parent exists
- Creating a new root-level goal

### Dependency Selection

**Set `depends_on` when**:
- Task requires output of another task
- Sequencing matters for correctness
- Blocking is intentional (human review gates)

**Common dependency patterns**:
- Schema design → implementation (can't implement without design)
- Research → build (can't build without understanding)
- Write → review → publish (sequential phases)

**Anti-pattern**: Creating dependencies that don't actually block work.

### Sequencing Principles

1. **Earlier discovery, later certainty** - Put investigative work first, implementation after
2. **Dependencies flow downward** - High-level decisions block implementation details
3. **Human gates explicit** - If human must approve, create review task as blocker
4. **Parallel when independent** - Don't serialize work that can run concurrently
5. **One actionable task NOW** - Every decomposition should produce at least one ready task

### Project Assignment

**Set `project` when**:
- Work clearly belongs to a specific domain
- Multiple related tasks exist or will exist
- Project provides useful organizational context

**Standard projects**: `aops`, `tja`, `osb`, `buttermilk`, etc.

## Decision Flow

```
New work arrives
    │
    ├─ 1. Classify complexity (Part 1)
    │       What execution path? What scope?
    │
    ├─ 2. Find/create parent (Part 2)
    │       Does this belong under existing work?
    │
    ├─ 3. Identify dependencies (Part 2)
    │       What must complete before this can start?
    │
    └─ 4. Create task with:
            - complexity: [classification]
            - parent: [if applicable]
            - depends_on: [blocking tasks]
            - project: [domain slug]
```

## Example: Classifying Real Work

**Request**: "Add pagination to the API endpoint"

1. **Complexity**: `requires-judgment` - bounded scope, some design decisions (page size, cursor vs offset)
2. **Parent**: Check if there's an "API improvements" project task
3. **Dependencies**: Does it depend on schema changes? Auth work?
4. **Project**: Match to relevant domain

**Result**:
```
create_task(
  title="Add pagination to API endpoint",
  complexity="requires-judgment",
  parent="api-improvements-project",
  depends_on=[],
  project="backend"
)
```
