# Knowledge Flow Between Siblings

How to propagate findings from one task to related tasks in an epic.

## The Problem

Sibling tasks in an epic are isolated by default. Findings in one spike don't automatically propagate to related tasks.

## Pattern: Propagate UP

After completing a spike task:

1. Summarize key findings in parent epic body under "## Findings from Spikes"
2. Note implications for sibling tasks explicitly
3. This ensures future agents pulling sibling tasks inherit context via parent

## "Findings from Spikes" Section Format

```markdown
## Findings from Spikes

### [task-id] Task Title (date)

**Verdict**: One-line conclusion
**Key findings**: Bullet list
**Implications for siblings**: How this affects related work
```

## Why This Works

The `/pull` workflow reads parent context before executing child tasks. Parent epic body is the natural context hub.

## Confirmed vs TBD Tables

When requirements are partially known, structure the task body with explicit decision tracking:

```markdown
## CONFIRMED

| Decision        | Status      | Notes                       |
| --------------- | ----------- | --------------------------- |
| Use framework X | Confirmed   | Validates system utility    |
| Question style  | Confirmed   | Content generation approach |

## TO BE DECIDED

| Decision       | Owner | Blocker              |
| -------------- | ----- | -------------------- |
| Exact template | TBD   | Needs examples first |
| Output format  | TBD   | Depends on template  |
```

**Why this works**: Makes uncertainty visible. Prevents premature decisions while documenting what IS known. Future agents can see exactly what's settled vs. open.

## Actionable Context → Tasks

When decomposing, distinguish:

- **Actionable constraints** → Create tasks (can be worked on)
- **Informational context** → Keep in body (just background)

**Test**: "Can someone complete this independently?" If yes → task. If no → note.

## The Graph IS the Knowledge Base

The task graph is not just a todo list - it's a knowledge graph. Relationships between ideas belong as graph edges, not prose in task bodies.

### Work Backwards from Action

Before creating any node, ask: **"What would we DO with this information?"**

| Answer                    | Container                                  |
| ------------------------- | ------------------------------------------ |
| Clear next action         | Task (actionable)                          |
| Informs a future decision | Task + soft_depends_on from decision point |
| Context for current work  | Body prose (don't create node)             |
| Might be useful someday   | Memory (not task graph)                    |

### Nodes Not Prose

| Don't                                     | Do                                                      |
| ----------------------------------------- | ------------------------------------------------------- |
| Write observation as prose in parent body | Create task node with `complexity: needs-decomposition` |
| List alternatives in a bullet list        | Create nodes for each, link with soft dependencies      |
| Describe relationships in prose           | Express as `depends_on` or `soft_depends_on` edges      |

**Why**: Prose isn't traversable. Graph edges are. When you later need to find "what would benefit from X?", soft_blocks queries work; grep through prose doesn't.
