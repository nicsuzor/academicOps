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

## Key Principle

We decompose to **discover what we don't know**, not because we know what to do.

## Uncertainty Patterns

When decomposing under uncertainty, use **spike tasks** (type: `learn`) to investigate unknowns before committing to implementation.

### Spike vs Placeholder Decision

| Situation                              | Use Spike            | Use Placeholder   |
| -------------------------------------- | -------------------- | ----------------- |
| "We don't know if X is possible"       | ✅ Investigate first |                   |
| "We know X is needed, details TBD"     |                      | ✅ Capture intent |
| "We need to understand current system" | ✅ Audit/explore     |                   |
| "Implementation approach is unclear"   | ✅ Prototype/probe   |                   |

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

| Relationship | Field             | Meaning                    | Use When                             |
| ------------ | ----------------- | -------------------------- | ------------------------------------ |
| **Hard**     | `depends_on`      | Task CANNOT proceed        | Dependency produces required input   |
| **Soft**     | `soft_depends_on` | Task BENEFITS from context | Dependency provides optional context |

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

## Patterns from Real Decompositions

### Confirmed vs TBD Tables

When requirements are partially known, structure the task body with explicit decision tracking:

```markdown
## CONFIRMED

| Decision        | Status      | Notes                       |
| --------------- | ----------- | --------------------------- |
| Use framework X | ✓ Confirmed | Validates system utility    |
| Question style  | ✓ Confirmed | Content generation approach |

## TO BE DECIDED

| Decision       | Owner | Blocker              |
| -------------- | ----- | -------------------- |
| Exact template | TBD   | Needs examples first |
| Output format  | TBD   | Depends on template  |
```

**Why this works**: Makes uncertainty visible. Prevents premature decisions while documenting what IS known. Future agents can see exactly what's settled vs. open.

### Human Handoff as Blocking Dependency

When external human input is required before work can proceed:

```
[task-receive-examples] Receive X's input (complexity: blocked-human)
       ↓ blocks
[task-design-based-on-input] Design based on findings
```

Mark with `complexity: blocked-human` to signal this isn't bot-executable. The dependency enforces sequencing without pretending the bot can do the waiting.

### Soft Dependencies for Contextual Relationships

Use `soft_depends_on` for "this matters but doesn't block":

| Context Type                   | Example                          | Why Soft                                        |
| ------------------------------ | -------------------------------- | ----------------------------------------------- |
| **Strategic validation**       | Using framework X proves utility | Work can proceed; validation is bonus           |
| **Infrastructure constraints** | Hook router blocks dev work      | Planning continues; only implementation blocked |
| **Environmental factors**      | Workspace setup affects comfort  | Work possible, just less optimal                |

### Parent as Project Boundary

When tasks span multiple concerns, use parent to clarify scope:

**Anti-pattern**: Workspace constraints embedded in research task body
**Pattern**: Move to separate project with own parent, link via soft_depends_on

```
[osb-project] Research task
  soft_depends_on: [personal-workspace-goal]

[personal-project] Workspace goal
  └── KVM switch evaluation
  └── Desk layout optimization
```

The parent defines what belongs together. Cross-project relationships use soft dependencies.

### Actionable Context → Tasks

When decomposing, distinguish:

- **Actionable constraints** → Create tasks (can be worked on)
- **Informational context** → Keep in body (just background)

**Test**: "Can someone complete this independently?" If yes → task. If no → note.

### Project Structure for Visualization

Tasks cluster in visualizations based on their parent chain reaching a canonical project file. When tasks appear disconnected:

**Checklist:**

1. **Project file exists**: `$ACA_DATA/{project}/{project}.md` with `type: project`
2. **Root goals link to project**: Goals have `parent: {project-id}`
3. **Tasks link to goals**: Every task has `parent:` pointing up the chain
4. **Project field matches**: `project: {slug}` matches the project file's `id:`

**Structure:**

```
{project}.md (type: project)
├── {goal}.md (type: goal, parent: project-id)
│   └── {task}.md (type: task, parent: goal-id, project: slug)
```

**Diagnosis**: If tasks with `project: X` don't cluster, check whether `X.md` exists with `type: project`. Missing project files are a common cause of orphaned-looking tasks.

## The Graph IS the Knowledge Base

**Key insight**: The task graph is not just a todo list—it's a knowledge graph. Relationships between ideas belong as graph edges, not prose in task bodies.

### Work Backwards from Action

Before creating any node, ask: **"What would we DO with this information?"**

| Answer                    | Container                                  |
| ------------------------- | ------------------------------------------ |
| Clear next action         | Task (actionable)                          |
| Informs a future decision | Task + soft_depends_on from decision point |
| Context for current work  | Body prose (don't create node)             |
| Might be useful someday   | Memory (not task graph)                    |

**Anti-pattern**: Creating a "learn" task without knowing what happens after. If you can't answer "what does completing this enable?", you don't have a task yet.

### Go Up a Level When Uncertain

When you don't know WHICH solution is right, don't pick one prematurely:

1. Create nodes for each alternative (marked `complexity: needs-decomposition`)
2. Create or identify the spike that will inform the choice
3. Link alternatives to spike via `soft_depends_on`
4. Let the spike's findings determine which alternative to pursue

```
spike: Investigate options
  ↑ soft_depends_on
  ├── alternative-a (needs-decomposition)
  ├── alternative-b (needs-decomposition)
  └── alternative-c (needs-decomposition)
```

This captures the decision structure in the graph, not just in prose.

### Nodes Not Prose

When you observe something that might lead to action:

| Don't                                     | Do                                                      |
| ----------------------------------------- | ------------------------------------------------------- |
| Write observation as prose in parent body | Create task node with `complexity: needs-decomposition` |
| List alternatives in a bullet list        | Create nodes for each, link with soft dependencies      |
| Describe relationships in prose           | Express as `depends_on` or `soft_depends_on` edges      |

**Why**: Prose isn't traversable. Graph edges are. When you later need to find "what would benefit from X?", soft_blocks queries work; grep through prose doesn't.

## Anti-Patterns

- Expanding everything at once (premature detail)
- Blocking on ambiguity (create placeholder tasks instead)
- Hidden assumptions (planning as if everything is known)
- **Isolated spikes**: Completing investigation tasks without propagating findings to parent epic
- **Missing sequencing**: Implementation tasks that don't depend_on their investigation spikes
- **Embedded actionable context**: Putting fixable constraints in task body instead of creating proper subtasks
- **Cross-project pollution**: Putting personal/infrastructure tasks under unrelated project parents
- **Missing project anchors**: Creating goals/tasks with `project: X` but no `X.md` project file exists, causing disconnected visualization clusters
- **Reflexive task creation**: Creating tasks/spikes without knowing the action path (where does this go? what does completing it enable?)
- **Prose instead of structure**: Writing relationships as prose when they should be graph edges
