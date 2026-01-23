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

**mechanical** (immediate):
- "Rename X to Y across files"
- "Add field Z to model"
- "Fix typo in documentation"
- Single file, obvious change

**requires-judgment** (execute with discretion):
- "Debug why X fails" (known symptom, unknown cause)
- "Implement feature Y" (bounded scope, some design decisions)
- "Review and fix test failures" (investigation within session)

**multi-step** (plan with independent review):
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

**Before setting parent, search for candidate parents**:
1. Use graph search or task index to find existing work related to this task
2. Look for umbrella tasks, project containers, or feature groups that would logically contain this work
3. Check task titles and bodies for matching keywords or scope areas
4. Only assign parent if a clear relationship exists

**Set `parent` when**:
- Task is a subtask of existing project/goal
- Work contributes to a larger deliverable
- Task naturally belongs under umbrella work
- Search confirmed a relevant parent exists

**Leave `parent` null when**:
- Standalone work (bug fixes, quick tasks)
- Creating a new root-level goal
- Work genuinely has no logical parent

**Graph Structure Principle: NO ORPHANS**

Avoid creating a clump of tasks all hanging off the trunk. Tasks must be SEQUENCED on the graph with clear structure:

- **Group related work**: If you create multiple standalone tasks in the same area, consider grouping them under an umbrella task
- **Create intermediate containers**: For coherent work areas, create a parent task that holds related subtasks
- **Sequencing matters**: Tasks at the same level should be ordered by dependency or logical sequence, not just randomly grouped
- **Result**: The task graph should have STRUCTURE with depth and relationships, not a flat pile of work at the top level

Example: Instead of creating 5 separate "bug fix" tasks at trunk level, group them under a "Bug fixes: Q1" task with subtasks for each bug.

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

### Task Granularity (Anti-Over-Decomposition)

**Tasks are work units, not tool calls.** A single task may comprise many execution steps.

| Level | What it is | Decompose to this? |
|-------|-----------|-------------------|
| **Task** | Tracked work item with complexity | ✅ Yes - decompose goals → tasks |
| **TodoWrite step** | Progress tracking within execution | ❌ No - these are execution, not tasks |
| **Task() call** | Subagent invocation | ❌ No - these are execution mechanisms |

**Right granularity**: "Add pagination to API endpoint" (1 task, many steps)
**Over-decomposed**: "Write test file", "Add page parameter", "Update response format" (3 tasks for 1 feature)

**Rule of thumb**: If work can be completed in one session by one agent, it's probably ONE task with multiple execution steps, not multiple tasks.

### Project Assignment

**Project is REQUIRED** - Always set a project value:
- Work clearly belongs to a specific domain (use that project slug)
- No obvious domain match? Default to `ns` (namespace for general infrastructure/framework work)
- Multiple related tasks exist or will exist (project groups them)
- Project provides useful organizational context

**Standard projects**: `aops`, `tja`, `osb`, `buttermilk`, `ns`, etc.

**Default**: Use `ns` if no specific project fits

## Part 3: Agent Type Routing

Complexity determines which model executes the work:

| Complexity | Model | Rationale |
|------------|-------|-----------|
| `mechanical` | haiku | Fast, cheap; known steps require no judgment |
| `requires-judgment` | sonnet | Balanced capability for investigation within bounds |
| `multi-step` | sonnet | Orchestration across sessions; escalate to opus for architectural complexity |
| `needs-decomposition` | opus | Deep planning capability for breakdown; or human if strategic |
| `blocked-human` | N/A | Human handles; no model execution |

### Escalation Rules

- **haiku → sonnet**: Task hits unexpected complexity during execution
- **sonnet → opus**: Architectural decisions, framework changes, or multi-system impact
- **Any → human**: Strategic decisions, external dependencies, or policy questions

### Model Selection in Practice

When spawning `Task()` subagents, use complexity to set the model:

```python
# mechanical task
Task(subagent_type="worker", model="haiku", prompt="...")

# requires-judgment task
Task(subagent_type="worker", model="sonnet", prompt="...")

# needs-decomposition task (planning phase)
Task(subagent_type="Plan", model="opus", prompt="...")
```

## Part 4: Workflow Guidance

Complexity and workflow are related but not 1:1. The relationship:

1. **Workflow** is selected from [[WORKFLOWS]] decision tree based on **request type**
2. **Complexity** determines **how** to execute that workflow

### Complexity × Workflow Matrix

| Complexity | Typical Workflows | Execution Style |
|------------|-------------------|-----------------|
| `mechanical` | [[minor-edit]], [[direct-skill]] | Skip optional verification; fast path |
| `requires-judgment` | [[debugging]], [[design]], [[feature-dev]] | Standard execution with checkpoints |
| `multi-step` | [[decompose]] then [[feature-dev]] | Break into sessions; track cross-session |
| `needs-decomposition` | [[decompose]] | TRIAGE: decompose first, don't execute |
| `blocked-human` | None | TRIAGE: assign and halt |

### Workflow Refinement by Complexity

**mechanical + minor-edit**:
- Skip detailed critic (use fast critic or none)
- Minimal verification checkpoint
- Direct commit after change

**requires-judgment + debugging**:
- Standard verification checkpoints
- Fast critic review
- Document findings in task body

**multi-step + feature-dev**:
- Detailed critic review
- Multiple verification gates
- Session handoff documentation
- Cross-session state tracking

**needs-decomposition**:
- Use [[decompose]] workflow
- Output is subtasks, not implementation
- Each subtask should be `mechanical` or `requires-judgment`

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
    ├─ 4. Determine model (Part 3)
    │       Which model executes based on complexity?
    │
    ├─ 5. Select workflow (Part 4 + WORKFLOWS.md)
    │       What workflow applies? How does complexity refine it?
    │
    └─ 6. Create task with:
            - complexity: [classification]
            - parent: [if applicable]
            - depends_on: [blocking tasks]
            - project: [domain slug]

    Then execute with:
            - model: [from Part 3 routing]
            - workflow: [from WORKFLOWS.md decision tree]
            - refinements: [from Part 4 guidance]
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
